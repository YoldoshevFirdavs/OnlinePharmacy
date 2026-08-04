import os
from django.conf import settings
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.signing import SignatureExpired, BadSignature, dumps, loads
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status, viewsets, serializers
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser
import logging
import json
import secrets
from datetime import timedelta
from django.core.cache import cache
import hashlib
import random
import time
import string
from django.contrib.auth import authenticate, login, logout, get_user_model
from PIL import Image

from drf_yasg import openapi
from pharmacy.permissons import IsVerifiedSeller
from security.locks import is_locked, reset_lockout, record_failed_attempt
from .models import CustomUser, Seller, SubscribedUser, Deliverer, OnboardToken
import users.otp_service as otp_service

# Import dashboard permissions
try:
    from dashboard.permissions import is_deliverer, is_admin
except ImportError:
    # Fallback if dashboard app not available
    def is_deliverer(user):
        try:
            return user.is_authenticated and hasattr(user, "deliverer_profile") and user.deliverer_profile is not None
        except Exception:
            return False
    def is_admin(user):
        try:
            return user.is_authenticated and user.is_staff
        except Exception:
            return False
import users.tasks as tasks
from .otp_service import (
    create_otp_session,
    bind_session_to_user,
    generate_numeric_code,
    check_rate_limit,
    verify_otp_once,
    OtpHash,
    store_otp_hash,
    get_otp_hash,
    delete_otp,
    store_bot_otp,
    get_bot_otp,
    create_admin_session,
    get_admin_session_meta,
    delete_admin_session,
    TELEGRAM_OTP_LENGTH,
    is_banned,
    record_failed_attempt,
    reset_failed_attempts,
    store_admin_code_hash,
    get_admin_code_hash,
    delete_admin_code,
    verify_admin_code,
    verify_otp_code,
)
from .serializers import (
    RegisterSerializer,
    SellerSerializer,
    UserSerializer,
    VerifySerializer,
    VerifyOTPSerializer,
    SubscribedUserSerializer,
    DriverSerializer,
    DelivererOnboardingSerializer,
    DelivererStripeConnectSerializer,
    TestAdminLoginSerializer,
    TelegramLoginSerializer,
    AdminLoginSerializer,
    RoleDetermineSerializer,
    PhoneNumberField,
    UserPublicSerializer,
    GmailOAuthSerializer,
)
from .permissions import IsDriver, IsOwnerOrAdmin
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse
from django.http import Http404

from orders.models import Order, OrderDelivery
from orders.serializers import OrderListSerializer, OrderDetailSerializer

from security.ip_score import incr_ip_score, decr_ip_score, get_ip_score, reset_ip_score

from payments.models import Payout
from payments.serializers import PayoutSerializer

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

logger = logging.getLogger(__name__)

OTP_STORE = {}
OTP_EXPIRY_SECONDS = 300
OTP_RATE_LIMIT_SECONDS = 60


def mask(identifier: str) -> str:
    """Mask identifier for logging (email or phone)."""
    if not identifier:
        return 'N/A'
    if '@' in identifier:
        parts = identifier.split('@')
        local = parts[0]
        domain = parts[1] if len(parts) > 1 else ''
        if len(local) > 1:
            masked_local = local[0] + '***'
        else:
            masked_local = '*'
        if len(domain) > 3:
            masked_domain = domain[:2] + '***'
        else:
            masked_domain = domain
        return f"{masked_local}@{masked_domain}"
    # Phone number
    if len(identifier) > 3:
        return identifier[:1] + '***' + identifier[-1:]
    return identifier[:1] + '***'


def mask_pii(value: str, show_chars: int = 3) -> str:
    if not value:
        return "***"
    if len(value) <= show_chars:
        return value[0] + "*" * (len(value) - 1)
    return f"{value[:show_chars]}{'*' * (len(value) - show_chars)}"


def _user_requires_password(user: CustomUser) -> bool:
    if user.is_staff or user.is_superuser:
        return True
    return Seller.objects.filter(user=user).exists()


def _check_password_if_required(user: CustomUser, password: str | None) -> None:
    if not _user_requires_password(user):
        return
    if not password or not user.check_password(password):
        raise ValueError("PASSWORD_REQUIRED")


User = get_user_model()

MAX_ATTEMPTS = getattr(settings, 'ADMIN_LOGIN_MAX_ATTEMPTS', 5)
BAN_SECONDS = getattr(settings, 'ADMIN_BAN_SECONDS', 3600)
SESSION_TIMEOUT = getattr(settings, 'ADMIN_SESSION_TIMEOUT', 600)


class AdminLoginViewSet(viewsets.ViewSet):
    serializer_class = AdminLoginSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=AdminLoginSerializer)
    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        action = data.get("action")
        phone_number = data.get('phone_number')
        username = data.get('username')
        email = data.get('email')

        identifier = email or phone_number or username or request.META.get('REMOTE_ADDR')

        if otp_service.is_banned(identifier):
            return Response({
                'banned': True,
                'message': 'Siz bloklandingiz. Ko‘p marta noto‘g‘ri urinishlar.',
                'redirect': '/not_allowed/?from=admin_login'
            }, status=status.HTTP_403_FORBIDDEN)

        if action == "credentials":
            return self._handle_credentials_login(request, data, identifier)
        elif action == "telegram":
            return self._handle_telegram_login(request, data, identifier)
        elif action == "request_otp":
            return self._handle_request_otp(request, data, identifier)
        elif action == "verify_otp":
            return self._handle_verify_otp(request, data, identifier)
        elif action == 'request_verification':
            return self._handle_request_verification(request, data, identifier)
        elif action == 'gmail_oauth':
            return self._handle_gmail_oauth(request, data, identifier)

        return Response({"error": "Noma'lum action"}, status=status.HTTP_400_BAD_REQUEST)

    def _login_user(self, request, user, identifier):
        if not user.is_staff:
            otp_service.record_failed_attempt(identifier)
            return Response({"error": "Foydalanuvchi admin emas."}, status=status.HTTP_403_FORBIDDEN)

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        request.session.set_expiry(SESSION_TIMEOUT)
        otp_service.reset_failed_attempts(identifier)

        return Response({"success": True, "redirect": reverse("dashboard:dashboard-admin")}, status=status.HTTP_200_OK)

    def _handle_credentials_login(self, request, data, identifier):
        username = data.get("username")
        password = data.get("password")
        email = data.get("email")

        user = None
        if username:
            user = authenticate(request, username=username, password=password)
        elif email:
            try:
                temp_user = User.objects.get(email=email)
                if temp_user.check_password(password):
                    user = temp_user
            except User.DoesNotExist:
                pass

        if user is None:
            banned = otp_service.record_failed_attempt(identifier)
            if banned:
                return Response({
                    'banned': True,
                    'message': 'Siz bloklandingiz. Ko‘p marta noto‘g‘ri urinishlar.',
                    'redirect': '/not_allowed/?from=admin_login'
                }, status=status.HTTP_403_FORBIDDEN)
            return Response({'error': 'Login yoki parol noto‘g‘ri.'}, status=status.HTTP_400_BAD_REQUEST)

        return self._login_user(request, user, identifier)

    def _handle_telegram_login(self, request, data, identifier):

        phone_number = data.get("phone_number")
        telegram_id = data.get("telegram_id")

        user = None
        if phone_number:
            try:
                user = CustomUser.objects.get(phone_number=phone_number)
            except CustomUser.DoesNotExist:
                pass
        elif telegram_id:
            try:
                user = CustomUser.objects.get(telegram_id=telegram_id)
            except CustomUser.DoesNotExist:
                pass

        if user == None:
            otp_service.record_failed_attempt(identifier)
            return Response({"error": "Admin topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        if not user.is_staff:
            otp_service.record_failed_attempt(identifier)
            return Response({"error": "Foydalanuvchi admin emas."}, status=status.HTTP_403_FORBIDDEN)

        otp_identifier = phone_number if phone_number else telegram_id

        if not otp_identifier:
            return Response({'error': 'OTP yuborish uchun identifikator kerak.'}, status=status.HTTP_400_BAD_REQUEST)

        otp = generate_numeric_code(length=6)
        logger.info("Generated OTP for admin telegram login for %s", mask_pii(str(otp_identifier)))

        session_info = create_admin_session(user.email or str(otp_identifier), user_id=user.id)
        session_id = session_info.get('session_id')
        if not session_id:
            return Response(
                {'error': 'Admin session yaratishda xatolik.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        otp_service.store_admin_code_hash(session_id, otp)

        # Send OTP via Celery task
        if user.email:
            tasks.send_otp_email.delay(user.email, otp)

        logger.info('Telegram login initiated for identifier=%s', mask_pii(str(otp_identifier)))

        return Response({
            'session_id': session_id,
            'message': 'OTP yuborildi. Telegram orqali tasdiqlang.',
            'expected_length': 6
        }, status=status.HTTP_200_OK)

    def _handle_request_otp(self, request, data, identifier):
        phone_number = data.get("phone_number")
        email = data.get("email")

        if not (phone_number or email):
            return Response({'error': 'Telefon raqami yoki email kerak.'}, status=status.HTTP_400_BAD_REQUEST)

        user = None
        if phone_number:
            try:
                user = CustomUser.objects.get(phone_number=phone_number)
            except CustomUser.DoesNotExist:
                pass
        elif email:
            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                pass

        if user is None:
            otp_service.record_failed_attempt(identifier)
            return Response({'error': 'Admin topilmadi.'}, status=status.HTTP_404_NOT_FOUND)

        if not user.is_staff:
            otp_service.record_failed_attempt(identifier)
            return Response({"error": "Foydalanuvchi admin emas."}, status=status.HTTP_403_FORBIDDEN)

        otp = generate_numeric_code(length=6)
        logger.info("Generated OTP for admin login for %s", mask_pii(str(identifier)))

        session_info = create_admin_session(email or user.email, user_id=user.id)
        session_id = session_info.get('session_id')
        if not session_id:
            return Response(
                {'error': 'Admin session yaratishda xatolik.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        otp_service.store_admin_code_hash(session_id, otp)

        if email:
            tasks.send_otp_email.delay(email, otp)

        logger.info('OTP request handled for identifier=%s', mask_pii(str(identifier)))

        return Response({'session_id': session_id, 'message': 'OTP yuborildi.'}, status=status.HTTP_200_OK)

    def _handle_verify_otp(self, request, data, identifier):
        phone_number = data.get("phone_number")
        email = data.get("email")
        otp_code = data.get("otp")
        session_id = data.get("session_id")

        if not (phone_number or email) or not otp_code or not session_id:
            return Response(
                {'error': 'Telefon raqami/email, session_id va OTP kerak.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        is_valid, session_meta = otp_service.verify_admin_code(session_id, otp_code)

        if not is_valid:
            # Incorrect OTP, record failed attempt
            banned = otp_service.record_failed_attempt(identifier)
            if banned:
                return Response({
                    'banned': True,
                    'message': 'Siz bloklandingiz. Ko‘p marta noto‘g‘ri urinishlar.',
                    'redirect': '/not_allowed/?from=admin_login'
                }, status=status.HTTP_403_FORBIDDEN)
            return Response({'error': 'OTP noto‘g‘ri.'}, status=status.HTTP_400_BAD_REQUEST)

        # OTP is correct, retrieve user from session meta
        user = None

        if session_meta and session_meta.get('user_id'):
            try:
                user = CustomUser.objects.get(id=session_meta['user_id'])
            except CustomUser.DoesNotExist:
                pass

        if user is None:
            if phone_number:
                try:
                    user = CustomUser.objects.get(phone_number=phone_number)
                except CustomUser.DoesNotExist:
                    pass
            elif email:
                try:
                    user = CustomUser.objects.get(email=email)
                except CustomUser.DoesNotExist:
                    pass

        if user is None:
            otp_service.record_failed_attempt(identifier)
            return Response({'error': 'Admin topilmadi.'}, status=status.HTTP_404_NOT_FOUND)

        otp_service.delete_admin_code(session_id)  # Delete OTP from cache
        otp_service.delete_admin_session(session_id)  # Delete session after successful login

        return self._login_user(request, user, identifier)

    def _handle_request_verification(self, request, data, identifier):
        # This action seems redundant with request_otp and is based on the old model.
        # It's safer to deprecate it in favor of the explicit request_otp flow.
        return self._handle_request_otp(request, data, identifier)

    def _handle_gmail_oauth(self, request, data, identifier):
        serializer = GmailOAuthSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        # Placeholder for actual Google OAuth exchange logic
        # In a real scenario, we'd exchange the code for a token and find/create a user.
        return Response({'error': 'Google OAuth bu yerda toʻliq joriy etilmagan.'},
                        status=status.HTTP_501_NOT_IMPLEMENTED)

    def verify(self, request, *args, **kwargs):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response({'detail': 'session_id required'}, status=status.HTTP_400_BAD_REQUEST)

        session_meta = otp_service.get_admin_session_meta(session_id)
        if not session_meta:
            return Response({'status': 'not_found'}, status=status.HTTP_404_NOT_FOUND)

        identifier = session_meta.get('identifier')
        if otp_service.is_banned(identifier):
            return Response({'status': 'banned'}, status=status.HTTP_403_FORBIDDEN)
        # Check if session is expired (based on creation time and duration)
        created_at_timestamp = session_meta.get('created_at')
        if created_at_timestamp and (time.time() - created_at_timestamp) > settings.ADMIN_SESSION_DURATION:
            return Response({'status': 'expired'}, status=status.HTTP_200_OK)

        # The 'verify' endpoint is for polling. The actual login happens in 'verify_otp'.
        # This logic is for a different flow (e.g., magic link) which isn't fully implemented here.
        # Let's adjust it for a polling scenario.

        if session_meta.get('verified'):
            user_id = session_meta.get('user_id')
            user = User.objects.filter(id=user_id).first()
            if not user:
                return Response({'status': 'verified', 'user_not_found': True}, status=status.HTTP_200_OK)

            refresh = RefreshToken.for_user(user)
            return Response({
                'status': 'verified',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'redirect': reverse("dashboard:dashboard-admin")
            }, status=status.HTTP_200_OK)

        return Response({'status': 'pending'}, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=AdminLoginSerializer)
    def verify_otp(self, request, *args, **kwargs):
        """
        Verify OTP for admin login.
        Expects: {"action": "verify_otp", "session_id": "...", "code": "...", "identifier": "..."}
        Includes rate limiting to prevent brute force attacks.
        """
        serializer = AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        session_id = data.get("session_id")
        code = data.get("code")
        identifier = data.get("email") or data.get("phone_number") or data.get("username")

        if not session_id or not code:
            return Response(
                {'error': 'session_id and code are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Rate limiting check
        if identifier:
            is_allowed, remaining = otp_service.check_rate_limit(f"admin_login:{identifier}")
            if not is_allowed:
                logger.warning("Rate limit exceeded for admin login: identifier=%s", identifier)
                return Response({
                    'error': 'Siz juda ko‘p urinishlar yubordingiz. Iltimos keyinroq qayta urinib ko‘ring.',
                    'retry_after': remaining
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        is_valid, session_meta = otp_service.verify_admin_code(session_id, code)

        if not is_valid:
            # Incorrect OTP, record failed attempt
            banned = otp_service.record_failed_attempt(identifier)
            if banned:
                return Response({
                    'banned': True,
                    'message': 'Siz bloklandingiz. Ko‘p marta noto‘g‘ri urinishlar.',
                    'redirect': '/not_allowed/?from=admin_login'
                }, status=status.HTTP_403_FORBIDDEN)
            return Response({'error': 'OTP noto‘g‘ri.'}, status=status.HTTP_400_BAD_REQUEST)

        # OTP is correct, retrieve user from session meta
        user = None

        if session_meta and session_meta.get('user_id'):
            try:
                user = CustomUser.objects.get(id=session_meta['user_id'])
            except CustomUser.DoesNotExist:
                pass

        if user is None:
            # Try to find user by phone_number or email if provided
            if data.get('phone_number'):
                try:
                    user = CustomUser.objects.get(phone_number=data['phone_number'])
                except CustomUser.DoesNotExist:
                    pass
            elif data.get('email'):
                try:
                    user = CustomUser.objects.get(email=data['email'])
                except CustomUser.DoesNotExist:
                    pass

        if user is None:
            otp_service.record_failed_attempt(identifier)
            return Response({'error': 'Admin topilmadi.'}, status=status.HTTP_404_NOT_FOUND)

        otp_service.delete_admin_code(session_id)  # Delete OTP from cache
        otp_service.delete_admin_session(session_id)  # Delete session after successful login

        # Reset rate limit on successful login
        if identifier:
            otp_service.reset_rate_limit(f"admin_login:{identifier}")

        # Create Django session so dashboard (session-auth) works
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        request.session.set_expiry(SESSION_TIMEOUT)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'ok': True,
            'token': str(refresh.access_token),
            'refresh': str(refresh),
            'next': reverse('dashboard:dashboard-admin'),
            'user_id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'role': 'admin',
            'is_verified': True
        }, status=status.HTTP_200_OK)


class RegistrationView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(request_body=RegisterSerializer)
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data.get("phone_number")
        email = serializer.validated_data.get("email")
        full_name = serializer.validated_data.get("full_name") or ""

        if phone:
            user, created = CustomUser.objects.get_or_create(phone_number=phone,
                                                             defaults={'email': email, 'full_name': full_name})
        elif email:
            user, created = CustomUser.objects.get_or_create(email=email,
                                                             defaults={'phone_number': phone, 'full_name': full_name})
        else:

            return Response({"error": "Telefon raqami yoki email kiritilishi shart."},
                            status=status.HTTP_400_BAD_REQUEST)

        if not created:

            if full_name and user.full_name != full_name:
                user.full_name = full_name

            if not user.email and email:
                user.email = email

            if not user.phone_number and phone:
                user.phone_number = phone
            user.save()

        identifier = phone if phone else email
        otp_length = 6

        otp_code = generate_numeric_code(otp_length)
        hashed_otp, salt = otp_service.hash_otp_with_salt(otp_code)
        otp_hash_obj = OtpHash(hash=hashed_otp, salt=salt)

        store_otp_hash(identifier, otp_hash_obj, ttl=900)

        session = create_otp_session(purpose="telegram" if phone else "email")
        bind_session_to_user(session.session_id, user.id, identifier)

        incognito_header = request.headers.get('X-Incognito', 'false').lower() == 'true'
        incognito_payload = request.data.get('incognito', False)
        incognito = incognito_header or incognito_payload

        logger.info('OTP generated for method=%s', 'telegram' if phone else 'email')

        request.session['auth_identifier'] = identifier
        request.session['auth_session_id'] = session.session_id
        request.session['auth_user_id'] = user.id
        request.session.save()

        bot_username = os.getenv('AUTH_BOT_USERNAME', 'authversabot').lstrip('@')
        verification_link = f"https.t.me/{bot_username}?start={session.session_id}"
        logger.info('Registration handled for user_id=%s', user.id)

        response = Response({
            "message": "OTP yuborildi",
            "session_id": session.session_id,
            "expected_length": otp_length,
            "verification_link": verification_link,
            "incognito": incognito,
        }, status=status.HTTP_200_OK)
        return response


class TelegramLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(request_body=TelegramLoginSerializer)
    def post(self, request):
        serializer = TelegramLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data.get("phone_number")
        telegram_id = serializer.validated_data.get("telegram_id")
        name = serializer.validated_data.get("name", "")

        identifier = phone_number or telegram_id

        ip_address = request.META.get('REMOTE_ADDR')
        account_key = f"telegram:{identifier}" if telegram_id else f"phone:{phone_number}"

        if is_locked(account_key):
            logger.warning(f"Account locked out for IP {ip_address}.")
            return Response({'detail': 'Account temporarily locked. Please try again later.'},
                            status=status.HTTP_423_LOCKED)

        incognito_header = request.headers.get('X-Incognito', 'false').lower() == 'true'
        incognito_payload = request.data.get('incognito', False)
        incognito = incognito_header or incognito_payload

        user = None
        if telegram_id:
            user = CustomUser.objects.filter(telegram_id=telegram_id).first()
        if not user and phone_number:
            user = CustomUser.objects.filter(phone_number=phone_number).first()

        if not user:

            user = CustomUser.objects.create(
                phone_number=phone_number,
                telegram_id=telegram_id,
                full_name=name
            )
            logger.info("New user created via Telegram login")
        else:

            if not user.telegram_id and telegram_id:
                user.telegram_id = telegram_id
            if name and user.full_name != name:
                user.full_name = name
            if not user.phone_number and phone_number:
                user.phone_number = phone_number
            user.save()
            logger.info("Existing user updated via Telegram login")

        session = create_otp_session(purpose="telegram")
        otp_length = TELEGRAM_OTP_LENGTH
        otp_code = generate_numeric_code(otp_length)

        store_bot_otp(session.session_id, otp_code)

        bind_session_to_user(session.session_id, user.id, identifier)

        bot_username = os.getenv('AUTH_BOT_USERNAME', 'authversabot').lstrip('@')
        deeplink = f"https://t.me/{bot_username}?start={session.session_id}"

        logger.info('Telegram login initiated for user_id=%s', user.id)

        decr_ip_score(ip_address, delta=getattr(settings, 'AUTH_IP_SCORE_DECAY_SUCCESS', 5))

        response_data = {
            "message": "Telegram bot orqali kod yuborildi. Iltimos, botni tekshiring.",
            "session_id": session.session_id,
            "expected_length": otp_length,
            "deeplink": deeplink,
            "otp_sent": True,
            "incognito": incognito,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class EmailLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(request_body=RegisterSerializer)
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"email": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

        ip_address = request.META.get('REMOTE_ADDR')
        account_key = f"email:{email}"

        if is_locked(account_key):
            logger.warning(f"Account locked out for IP {ip_address}.")
            return Response({'detail': 'Account temporarily locked. Please try again later.'},
                            status=status.HTTP_423_LOCKED)

        try:
            allowed, _ = check_rate_limit(f"email_login_ip:{ip_address}")
            if not allowed:
                logger.warning(f"Rate limit exceeded for IP: {ip_address} on Email login.")
                return Response({'detail': 'Too many requests. Please try again later.'},
                                status=status.HTTP_429_TOO_MANY_REQUESTS)
        except Exception as e:
            logger.error("Rate limit check error")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            with transaction.atomic():
                user, created = CustomUser.objects.get_or_create(email=email)
        except Exception as e:
            logger.error("User get_or_create error")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        otp_length = 6
        try:
            otp_code = generate_numeric_code(otp_length)
            hashed_otp, salt = otp_service.hash_otp_with_salt(otp_code)
            otp_hash_obj = OtpHash(hash=hashed_otp, salt=salt)
        except Exception as e:
            logger.error("OTP hash creation error")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            store_otp_hash(email, otp_hash_obj, ttl=900)
        except Exception as e:
            logger.error("OTP hash storage error")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            session = create_otp_session(purpose="email")
            bind_session_to_user(session.session_id, user.id, email)
        except Exception as e:
            logger.error("OTP session creation/binding error")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        request.session['auth_identifier'] = email
        request.session['auth_session_id'] = session.session_id
        request.session['auth_user_id'] = user.id
        request.session.save()

        try:
            if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False) or not getattr(settings, 'USE_CELERY', True):
                tasks.send_otp_email(email, otp_code)
                logger.info("Email OTP sent")
            else:
                tasks.send_otp_email.delay(email, otp_code)
                logger.info("Email OTP enqueued")
        except Exception as e:
            logger.error("Email enqueue/send error")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        decr_ip_score(ip_address, delta=getattr(settings, 'AUTH_IP_SCORE_DECAY_SUCCESS', 5))

        return Response({
            "session_id": session.session_id,
            "expected_length": otp_length,
            "message": "OTP sent to email"
        }, status=status.HTTP_200_OK)


class VerifyOtpView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(request_body=VerifyOTPSerializer)
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'ok': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        session_id = serializer.validated_data.get('session_id')
        code = serializer.validated_data.get('code')
        identifier = serializer.validated_data.get('identifier', '')

        try:
            is_valid, message, session = otp_service.verify_otp_once(session_id, code, identifier)

            if is_valid:
                user_id = session.get('user_id')
                if user_id:
                    try:
                        user = CustomUser.objects.get(id=user_id)
                        refresh = RefreshToken.for_user(user)
                        
                        role = 'user'
                        if user.is_staff:
                            role = 'admin'
                        elif hasattr(user, 'deliverer_profile'):
                            role = 'deliverer'
                        elif Seller.objects.filter(user=user).exists():
                            role = 'seller'

                        return Response({
                            'ok': True,
                            'token': str(refresh.access_token),
                            'refresh': str(refresh),
                            'user_id': user.id,
                            'phone_number': user.phone_number,
                            'email': user.email,
                            'is_verified': True,
                            'role': role
                        })
                    except CustomUser.DoesNotExist:
                        pass
                
                return Response({'ok': True, 'next': '/dashboard/'})
            else:
                http_status = status.HTTP_400_BAD_REQUEST
                if message == 'too_many_attempts':
                    http_status = status.HTTP_403_FORBIDDEN
                
                return Response({'ok': False, 'error': message}, status=http_status)

        except Exception as e:
            logger.exception("OTP verify error for session_id=%s error=%s", 
                           session_id, str(e)[:100])
            log_error_to_dashboard("verify_otp", identifier, str(e)[:200])
            return Response({'ok': False, 'error': 'server_error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def log_error_to_dashboard(component: str, masked_identifier: str, short_error: str):
    """Log error to dashboard_error.md in masked format."""
    import os
    from datetime import datetime, timezone
    from django.conf import settings
    
    error_file = os.path.join(settings.BASE_DIR, 'errors', 'dashboard_error.md')
    timestamp = datetime.now(timezone.utc).isoformat()

    log_entry = f"\nTIMESTAMP: {timestamp}\n"
    log_entry += f"COMPONENT: {component}\n"
    log_entry += f"USER: {masked_identifier}\n"
    log_entry += f"ERROR: {short_error}\n"
    log_entry += "ACTION: OTP verification failed due to error.\n"

    try:
        os.makedirs(os.path.dirname(error_file), exist_ok=True)
        with open(error_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as write_error:
        logger.error(f"Failed to write error log: {str(write_error)[:100]}")


class UserProfileViewSet(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def check_permissions(self, request):
        """Check if user is deliverer or admin before allowing access"""
        super().check_permissions(request)
        
        # Check if user has deliverer or admin role
        if not is_deliverer(request.user) and not is_admin(request.user):
            # User is authenticated but not deliverer/admin
            # Return 403 Forbidden instead of redirect
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to access this resource.")

    def get_object(self):
        return self.request.user

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        old_email = instance.email
        old_phone = instance.phone_number

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_user = serializer.save()

        if (updated_user.email != old_email and old_email is not None) or \
                (updated_user.phone_number != old_phone and old_phone is not None):
            updated_user.is_verified = False
            updated_user.save()
            return Response({
                "message": "reverify",
                "detail": "Email yoki telefon o'zgardi. Qayta tasdiqlash kerak."
            }, status=status.HTTP_200_OK)

        return Response(serializer.data)

class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


class SellerViewSet(viewsets.ModelViewSet):
    queryset = Seller.objects.all()
    serializer_class = SellerSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Seller.objects.all()
        return Seller.objects.filter(user=user)


class SubscribedUserViewSet(viewsets.ModelViewSet):
    queryset = SubscribedUser.objects.all()
    serializer_class = SubscribedUserSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [AllowAny]
        else:
            self.permission_classes = [IsAdminUser]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscriber = serializer.save()

        if not subscriber.is_verified:
            token = dumps(subscriber.email)
            verify_url = f"{self.request.build_absolute_uri('/api/v1/users/subscribe/verify/')}{token}/"
            try:
                tasks.send_subscription_verification_email.delay(subscriber.email, verify_url)
            except Exception as e:
                logger.error('Subscription email enqueue failed')

        out_serializer = SubscribedUserSerializer(subscriber)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)


class VerifySubscriptionView(APIView):
    def get(self, request, token):
        try:
            email = loads(token, max_age=3600)
            user = SubscribedUser.objects.get(email=email)
            user.is_verified = True
            user.save()
            return Response({"detail": "Email tasdiqlandi."}, status=status.HTTP_200_OK)
        except (BadSignature, SignatureExpired, SubscribedUser.DoesNotExist):
            return Response({"detail": "Token noto‘g‘ri yoki muddati o‘tgan."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Error during email verification")
            return Response({"detail": "Xato yuz berdi"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"detail": "Topilmadi"}, status=status.HTTP_404_NOT_FOUND)


class SubscriberCreateView(CreateAPIView):
    serializer_class = SubscribedUserSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        subscriber = serializer.save()
        if not subscriber.is_verified:
            token = dumps(subscriber.email)
            verify_url = f"{self.request.build_absolute_uri('/api/v1/users/subscribe/verify/')}{token}/"
            try:
                tasks.send_subscription_verification_email.delay(subscriber.email, verify_url)
            except Exception as e:
                logger.error('Subscription email enqueue failed')


@method_decorator(csrf_exempt, name='dispatch')
class CookieRefreshView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(request_body=RegisterSerializer)
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return Response(
                {"detail": "Refresh token topilmadi."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            raise Exception("JWT refresh logic is incomplete or incorrect.")

        except Exception:
            logger.exception("Error refreshing token via cookie")
            return Response(
                {"detail": "Refresh token yaroqsiz yoki muddati o'tgan."},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class DriverProfileRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = DriverSerializer
    permission_classes = [permissions.IsAuthenticated, IsDriver]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user.deliverer_profile


class DriverLocationUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDriver]

    def post(self, request):
        lat = request.data.get('lat')
        lng = request.data.get('lng')

        if lat is None or lng is None:
            return Response({"detail": "Latitude and longitude are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            lat = float(lat)
            lng = float(lng)
        except ValueError:
            return Response({"detail": "Latitude and longitude must be valid numbers."},
                            status=status.HTTP_400_BAD_REQUEST)

        driver = self.request.user.deliverer_profile
        driver.update_location(lat, lng)
        return Response({"detail": "Location updated successfully."}, status=status.HTTP_200_OK)


class DriverOrdersListView(generics.ListAPIView):
    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAuthenticated, IsDriver]

    def get_queryset(self):
        deliverer_profile = getattr(self.request.user, 'deliverer_profile', None)
        if deliverer_profile is None:
            return Order.objects.none()
        return Order.objects.filter(
            driver=deliverer_profile
        ).exclude(
            status__in=['Delivered', 'Canceled', 'Returned']
        ).order_by('-created_at')


class DriverOrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsDriver]
    lookup_field = 'pk'

    def get_queryset(self):
        deliverer_profile = getattr(self.request.user, 'deliverer_profile', None)
        if deliverer_profile is None:
            return Order.objects.none()
        return Order.objects.filter(driver=deliverer_profile)


class DriverOrderAcceptView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDriver]

    def post(self, request, pk):
        order = get_object_or_404(
            Order, pk=pk, driver=getattr(request.user, 'deliverer_profile', None)
        )
        if order.status == 'Assigned':
            order.status = 'Accepted'
            order.accepted_at = timezone.now()
            order.save()
            return Response({"detail": f"Order {pk} accepted."}, status=status.HTTP_200_OK)
        return Response({"detail": "Order cannot be accepted at this stage."}, status=status.HTTP_400_BAD_REQUEST)


class DriverOrderStatusUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDriver]

    def post(self, request, pk):
        status_update = request.data.get('status')
        allowed = ['Picked Up', 'On The Way', 'Arrived', 'Delivered']
        if status_update not in allowed:
            return Response(
                {"detail": f"Invalid status. Must be one of {allowed}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order = get_object_or_404(
            Order, pk=pk, driver=getattr(request.user, 'deliverer_profile', None)
        )

        if status_update == 'Picked Up' and order.status in ['Accepted', 'Assigned']:
            order.status = 'Picked Up'
            order.picked_up_at = timezone.now()
            order.save()
            return Response({"detail": f"Order {pk} status updated to Picked Up."}, status=status.HTTP_200_OK)

        if status_update == 'On The Way' and order.status == 'Picked Up':
            order.status = 'On The Way'
            order.on_the_way_at = timezone.now()
            order.save()
            return Response({"detail": f"Order {pk} status updated to On The Way."}, status=status.HTTP_200_OK)

        if status_update == 'Arrived' and order.status in ['On The Way']:
            order.status = 'Arrived'
            order.save()
            return Response({"detail": f"Order {pk} status updated to Arrived."}, status=status.HTTP_200_OK)

        if status_update == 'Delivered' and order.status in ['On The Way', 'Arrived', 'Picked Up']:
            order.status = 'Delivered'
            order.delivered_at = timezone.now()
            order.save()
            return Response({"detail": f"Order {pk} status updated to Delivered."}, status=status.HTTP_200_OK)

        return Response(
            {"detail": f"Order cannot be updated to {status_update} at its current stage ({order.status})."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class DriverOrderArrivalView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDriver]

    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        wait_seconds = request.data.get('wait_seconds')
        try:
            wait_seconds = int(wait_seconds)
        except (TypeError, ValueError):
            return Response({"detail": "wait_seconds must be a non-negative integer."},
                            status=status.HTTP_400_BAD_REQUEST)

        if wait_seconds < 0:
            return Response({"detail": "wait_seconds must be a non-negative integer."},
                            status=status.HTTP_400_BAD_REQUEST)

        order = get_object_or_404(
            Order, pk=pk, driver=getattr(self.request.user, 'deliverer_profile', None)
        )
        order_delivery, _created = OrderDelivery.objects.get_or_create(order=order)

        if order.status in ['On The Way']:
            order.status = 'Arrived'
            order_delivery.arrived_at = timezone.now()
            order_delivery.wait_seconds = wait_seconds
            order.save()
            order_delivery.save()
            return Response({"detail": f"Order {pk} arrival time and wait seconds recorded."},
                            status=status.HTTP_200_OK)

        return Response({"detail": "Order cannot be marked as arrived at this stage."},
                        status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        response = Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        response.delete_cookie('sessionid')
        response.delete_cookie('csrftoken')
        return response


class LogoutJWTView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        response = Response({"detail": "Successfully logged out from JWT."}, status=status.HTTP_200_OK)
        refresh_token = request.COOKIES.get('refresh_token')

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
                logger.info("Refresh token blacklisted.")
            except Exception as e:
                logger.warning(f"Failed to blacklist refresh token")
        else:
            logger.info("No refresh token found in cookies to blacklist.")

        response.delete_cookie('refresh_token')
        return response


class DriverPayoutViewSet(viewsets.ModelViewSet):
    queryset = Payout.objects.all()
    serializer_class = PayoutSerializer
    permission_classes = [permissions.IsAuthenticated, IsDriver]

    def get_queryset(self):
        driver = getattr(self.request.user, 'deliverer_profile', None)
        if not driver:
            return Payout.objects.none()
        return Payout.objects.filter(driver=driver).order_by('-created_at')


class DetermineRoleView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RoleDetermineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data.get('phone_number')
        email = serializer.validated_data.get('email')

        user = None
        if request.user and request.user.is_authenticated:
            user = request.user
        elif phone_number:
            user = CustomUser.objects.filter(phone_number=phone_number).first()
        elif email:
            user = CustomUser.objects.filter(email=email).first()

        if not user:
            # If user is not found, create a new one. This is crucial for the new user registration flow
            # as the frontend expects a role to continue the OTP process.
            try:
                with transaction.atomic():
                    create_params = {}
                    if phone_number:
                        create_params['phone_number'] = phone_number
                    elif email:
                        create_params['email'] = email

                    if not create_params:
                        return Response({'detail': 'Email or phone number required to determine role or create user.'},
                                        status=status.HTTP_400_BAD_REQUEST)

                    user, created = CustomUser.objects.get_or_create(**create_params)
                    if created:
                        logger.info(f"New user created via determine_role: {user.id}")
                        # For a new user, the role is always 'user'.
                        return Response({'role': 'user'}, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Error creating user in determine_role: {e}")
                return Response({'detail': 'Could not create user profile.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        role = 'user'
        if user.is_staff:
            role = 'admin'
        elif getattr(user, 'deliverer_profile', None):
            role = 'deliverer'
        elif Seller.objects.filter(user=user).exists():
            role = 'seller'

        return Response({'role': role}, status=status.HTTP_200_OK)


class AccountDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'templates/account.html '

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['total_users'] = CustomUser.objects.count()
        context['total_orders'] = Order.objects.count()
        context['total_products'] = 150
        context['recent_activities'] = [
            {'timestamp': '2023-10-26 10:00', 'description': 'User registered.'},
            {'timestamp': '2023-10-26 09:30', 'description': 'Order' '#12345 placed.'},
            {'timestamp': '2023-10-25 18:00', 'description': 'Product updated.'},
        ]
        return context


class CheckSessionView(generics.GenericAPIView):
    """
    Checks if the user's session (via JWT token) is valid.
    Returns public user data if authenticated.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserPublicSerializer

    def get(self, request, *args, **kwargs):
        from .auth_guard import require_authenticated
        err = require_authenticated(request)
        if err:
            return err

        # Optional: if caller passes ?user_id=X, verify it matches the token owner
        target_id = request.query_params.get("user_id")
        if target_id is not None:
            from .auth_guard import require_self_or_admin
            err = require_self_or_admin(request, target_id)
            if err:
                return err

        serializer = self.get_serializer(request.user)
        return Response({
            "ok": True,
            "user": serializer.data
        }, status=status.HTTP_200_OK)


class DeliveryDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'dashboard/delivery.html'

    def test_func(self):
        return getattr(self.request.user, 'deliverer_profile', None) is not None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        deliverer = getattr(self.request.user, 'deliverer_profile', None)
        if deliverer and deliverer.status != 'active':
            context['redirect_to_onboarding'] = f"/deliverer/check/?deliverer_id={deliverer.id}&token=TEMP_TOKEN"
        elif deliverer and not deliverer.stripe_account_id:
            context['redirect_to_card_setup'] = f"/deliverer/card-setup/?deliverer_id={deliverer.id}"
        else:
            context['redirect_to_dashboard'] = "/deliverer/dashboard/"
        return context


class DelivererOnboardingVerifyView(APIView):
    permission_classes = []

    def get(self, request):
        token = request.query_params.get('token')
        deliverer_id = request.query_params.get('deliverer_id')

        if not token or not deliverer_id:
            return Response({'detail': 'Token and deliverer_id are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            deliverer = Deliverer.objects.get(id=deliverer_id)
            onboard_token = OnboardToken.objects.get(user=deliverer.user,
                                                     token_hash=hashlib.sha256(token.encode()).hexdigest(), used=False)

            if not onboard_token.check_token(token):
                return Response({'detail': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)

            return redirect(f"/deliverer/check/?token={token}&deliverer_id={deliverer_id}")

        except Deliverer.DoesNotExist:
            return Response({'detail': 'Deliverer not found.'}, status=status.HTTP_404_NOT_FOUND)
        except OnboardToken.DoesNotExist:
            return Response({'detail': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Error in DelivererOnboardingVerifyView")
            return Response({'detail': 'An error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DelivererCompleteOnboardView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = DelivererOnboardingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        full_name = serializer.validated_data['full_name']
        password = serializer.validated_data['password']

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        try:
            ot = OnboardToken.objects.get(token_hash=token_hash, used=False)
        except OnboardToken.DoesNotExist:
            return Response({'detail': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)
        if ot.expires_at < timezone.now():
            return Response({'detail': 'Token expired'}, status=status.HTTP_400_BAD_REQUEST)
        user = ot.user
        user.set_password(password)
        user.full_name = full_name
        user.save()
        ot.used = True
        ot.save()
        if Deliverer:
            deliverer, _ = Deliverer.objects.get_or_create(user=user)
            deliverer.status = 'active'
            deliverer.save()
        login(request, user)
        return Response({'ok': True, 'next': '/deliverer/card-setup/'}, status=status.HTTP_200_OK)


class DelivererStripeConnectView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = DelivererStripeConnectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        deliverer_id = serializer.validated_data['deliverer_id']
        payment_method_id = serializers.CharField(max_length=255)

        try:
            deliverer = Deliverer.objects.get(id=deliverer_id)
            deliverer.stripe_account_id = payment_method_id
            deliverer.payout_method = 'card'
            deliverer.save()

            return Response({'ok': True, 'next': '/deliverer/dashboard/'}, status=status.HTTP_200_OK)

        except Deliverer.DoesNotExist:
            return Response({'detail': 'Deliverer not found.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Error connecting Stripe for deliverer")
            return Response({'detail': 'An error occurred during Stripe connection.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StripeConfigView(APIView):
    permission_classes = []

    def get(self, request):
        return Response({'publishableKey': settings.STRIPE_PUBLISHABLE_KEY})


class TestAdminLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(request_body=TestAdminLoginSerializer)
    def post(self, request):
        if not settings.DEBUG:
            raise Http404("This endpoint is only available in DEBUG mode.")

        serializer = TestAdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        phone_number = data.get('phone_number')
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        identifier = email or phone_number or username or request.META.get('REMOTE_ADDR')
        
        user = None

        # 1. Try to authenticate directly (handles username, and email if USERNAME_FIELD is 'email')
        user = authenticate(request, username=identifier, password=password)

        # 2. Fallback: Check if identifier is an email not set as username
        if user is None:
            potential_user = User.objects.filter(email__iexact=identifier).first()
            if potential_user and potential_user.check_password(password):
                user = potential_user

        # 3. Fallback: Check if identifier is a phone number
        if user is None:
            potential_user = User.objects.filter(phone_number=identifier).first()
            if potential_user and potential_user.check_password(password):
                user = potential_user

        # After all checks, validate the user
        if user is None:
            return Response(
                {'error': 'Noto‘g‘ri ma’lumotlar.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_staff:
            return Response(
                {'error': 'Kirish huquqi yo‘q.'},
                status=status.HTTP_403_FORBIDDEN
            )

        login(request, user)

        return Response({'ok': True, 'next': reverse("dashboard:dashboard-admin")}, status=status.HTTP_200_OK)


def auth_view(request):
    return render(request, "auth.html")


class AccountView(TemplateView):
    template_name = "account.html"
    permission_classes = [IsAuthenticated]

class AdminCheckView(TemplateView):
    template_name = 'admin_check_deeplink.html'

    def get(self, request, *args, **kwargs):
        session_id = request.GET.get('session')
        otp = request.GET.get('otp')

        if not session_id or not otp:
            return redirect('auth')

        stored_data = cache.get(f"admin_session:{session_id}")
        
        if stored_data and stored_data['otp'] == otp:
            try:
                user = CustomUser.objects.get(id=stored_data['user_id'], is_staff=True)
                
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                refresh_token = str(refresh)

                cache.delete(f"admin_session:{session_id}")

                context = {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'username': user.full_name or user.email,
                    'user_role': 'admin'
                }
                return self.render_to_response(context)

            except CustomUser.DoesNotExist:
                pass
        
        return redirect('auth')