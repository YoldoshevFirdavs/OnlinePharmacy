import logging
import os
import time

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core.cache import cache
from django.core.signing import BadSignature, SignatureExpired, dumps, loads
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, permissions, status, viewsets
from rest_framework.generics import CreateAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

import users.otp_service as otp_service
from dashboard.forms import AccountSettingsForm
from security.locks import is_locked
from security.middleware import get_client_ip
from security.models import AuditLog, BanRecord

from .models import CustomUser, Seller, SubscribedUser

# Import dashboard permissions
try:
    from dashboard.permissions import is_admin
except ImportError:
    # Fallback if dashboard app not available
    def is_admin(user):
        try:
            return user.is_authenticated and getattr(user, "role", None) == "admin"
        except Exception:
            return False


from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import FormView, TemplateView
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated

import users.tasks as tasks
from orders.models import Order
from security.ip_score import decr_ip_score

from .otp_service import (
    ADMIN_SESSION_TTL,
    TELEGRAM_OTP_LENGTH,
    OtpHash,
    bind_session_to_user,
    check_rate_limit,
    claim_admin_session,
    create_admin_session,
    create_otp_session,
    generate_numeric_code,
    get_admin_session_meta,
    is_banned,
    refresh_session_ttl,
    store_bot_otp,
    store_otp_hash,
)
from .permissions import IsOwnerOrAdmin
from .serializers import (
    AdminLoginSerializer,
    GmailOAuthSerializer,
    RegisterSerializer,
    RoleDetermineSerializer,
    SellerSerializer,
    SubscribedUserSerializer,
    TelegramLoginSerializer,
    TestAdminLoginSerializer,
    UserPublicSerializer,
    UserSerializer,
    VerifyOTPSerializer,
)

logger = logging.getLogger(__name__)

OTP_STORE = {}
OTP_EXPIRY_SECONDS = 300
OTP_RATE_LIMIT_SECONDS = 60


def mask(identifier: str) -> str:
    """Mask identifier for logging (email or phone)."""
    if not identifier:
        return "N/A"
    if "@" in identifier:
        parts = identifier.split("@")
        local = parts[0]
        domain = parts[1]
        if len(local) > 1:
            masked_local = local[0] + "***"
        else:
            masked_local = "*"
        if len(domain) > 3:
            masked_domain = domain[:2] + "***"
        else:
            masked_domain = domain
        return f"{masked_local}@{masked_domain}"
    # Phone number
    if len(identifier) > 3:
        return identifier[:1] + "***" + identifier[-1:]
    return identifier[:1] + "***"


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


def _is_admin_identity(user: CustomUser) -> bool:
    if not user:
        return False
    role = str(getattr(user, "role", "") or "").lower()
    return bool(role == "admin" and getattr(user, "is_staff", False) and getattr(user, "is_superuser", False))


def _write_auth_audit(request, user, action, description, *, target_type="auth", target_id=None, meta=None):
    with transaction.atomic():
        AuditLog.objects.create(
            user=user,
            action=action,
            description=description,
            ip_address=getattr(request, "META", {}).get("REMOTE_ADDR"),
            target_type=target_type,
            target_id=getattr(user, "id", target_id),
            meta={
                **(meta or {}),
                "ip": getattr(request, "META", {}).get("REMOTE_ADDR"),
                "request_path": getattr(request, "path", None),
                "request_method": getattr(request, "method", None),
            },
        )


def _create_phone_otp_fallback(request, user):
    if not user or not user.phone_number:
        return None

    with transaction.atomic():
        otp_code = generate_numeric_code(TELEGRAM_OTP_LENGTH)
        hashed_otp, salt = otp_service.hash_otp_with_salt(otp_code)
        session = create_otp_session(purpose="telegram")
        store_otp_hash(
            user.phone_number,
            OtpHash(hash=hashed_otp, salt=salt),
            ttl=300,
        )
        bind_session_to_user(
            session.session_id,
            user.id,
            user.phone_number,
            ttl=300,
        )
        _write_auth_audit(
            request,
            user,
            "Phone OTP requested",
            "Non-admin OTP fallback requested after Telegram login attempt.",
        )
    return session


def _create_telegram_otp_session(request, user, identifier):
    with transaction.atomic():
        session = create_otp_session(purpose="telegram")
        otp_code = generate_numeric_code(TELEGRAM_OTP_LENGTH)
        store_bot_otp(session.session_id, otp_code, ttl=ADMIN_SESSION_TTL)

        # Use admin_session namespace for consistency with admin flow
        session_id = session.session_id
        admin_session = {
            "user_id": user.id,
            "phone_number": str(identifier),
            "flow": "telegram_user",  # Non-admin Telegram flow marker
            "created_at": int(time.time()),
        }
        cache.set(f"admin_session:{session_id}", admin_session, timeout=ADMIN_SESSION_TTL)

        _write_auth_audit(
            request,
            user,
            "Telegram OTP requested",
            "Telegram OTP login flow started for a non-admin user.",
        )
    return session


def _check_password_if_required(user: CustomUser, password: str | None) -> None:
    if not _user_requires_password(user):
        return
    if not password or not user.check_password(password):
        raise ValueError("PASSWORD_REQUIRED")


User = get_user_model()

MAX_ATTEMPTS = getattr(settings, "ADMIN_LOGIN_MAX_ATTEMPTS", 5)
BAN_SECONDS = getattr(settings, "ADMIN_BAN_SECONDS", 3600)
SESSION_TIMEOUT = getattr(settings, "ADMIN_SESSION_TIMEOUT", 600)
ADMIN_LINK_TTL = 300
ADMIN_DEEPLINK_MAX_ATTEMPTS = 10


class AdminLoginViewSet(viewsets.ViewSet):
    serializer_class = AdminLoginSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=AdminLoginSerializer)
    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        action = data.get("action")
        phone_number = data.get("phone_number")
        username = data.get("username")
        email = data.get("email")

        identifier = email or phone_number or username or request.META.get("REMOTE_ADDR")

        if otp_service.is_banned(identifier):
            return Response(
                {
                    "banned": True,
                    "message": "Siz bloklandingiz. Ko‘p marta noto‘g‘ri urinishlar.",
                    "redirect": "/not_allowed/?from=admin_login",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if action == "credentials":
            return self._handle_credentials_login(request, data, identifier)
        elif action == "telegram":
            return self._handle_telegram_login(request, data, identifier)
        elif action == "request_otp":
            return self._handle_request_otp(request, data, identifier)
        elif action == "verify_otp":
            return self._handle_verify_otp(request, data, identifier)
        elif action == "request_verification":
            return self._handle_request_verification(request, data, identifier)
        elif action == "gmail_oauth":
            return self._handle_gmail_oauth(request, data, identifier)

        return Response({"error": "Noma'lum action"}, status=status.HTTP_400_BAD_REQUEST)

    def _login_user(self, request, user, identifier):
        if not _is_admin_identity(user):
            otp_service.record_failed_attempt(identifier)
            return Response({"error": "Foydalanuvchi admin emas."}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            user.backend = "django.contrib.auth.backends.ModelBackend"
            login(request, user)
            request.session.set_expiry(SESSION_TIMEOUT)
            _write_auth_audit(
                request,
                user,
                "Admin password login successful",
                "Admin login completed with password.",
            )
        otp_service.reset_failed_attempts(identifier)

        # FIXED: Role is determined from server-side data, not hardcoded
        from .serializers import determine_role

        computed_role = determine_role(user)

        return Response(
            {
                "success": True,
                "redirect": reverse("dashboard:dashboard-admin"),
                "role": computed_role,  # Use determined role
                "avatar_url": user.get_avatar_url,
            },
            status=status.HTTP_200_OK,
        )

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
                return Response(
                    {
                        "banned": True,
                        "message": "Siz bloklandingiz. Ko‘p marta noto‘g‘ri urinishlar.",
                        "redirect": "/not_allowed/?from=admin_login",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            return Response(
                {"error": "Login yoki parol noto‘g‘ri."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return self._login_user(request, user, identifier)

    def _handle_telegram_login(self, request, data, identifier):

        phone_number = data.get("phone_number")
        telegram_id = data.get("telegram_id")

        user = None
        if phone_number:
            try:
                user = CustomUser.objects.get(phone_number=phone_number)
            except CustomUser.DoesNotExist:
                with transaction.atomic():
                    user = CustomUser.objects.create(
                        phone_number=phone_number,
                        telegram_id=telegram_id or None,
                        role="user",
                    )
                    _write_auth_audit(
                        request,
                        user,
                        "Telegram user created",
                        "New user created from an unknown Telegram login phone.",
                    )
        elif telegram_id:
            try:
                user = CustomUser.objects.get(telegram_id=telegram_id)
            except CustomUser.DoesNotExist:
                pass

        if user is None:
            otp_service.record_failed_attempt(identifier)
            return Response(
                {
                    "fallback": "otp",
                    "message": "Telegram akkaunti admin bilan bog‘lanmagan. Telefon OTP orqali kiring.",
                    "otp_endpoint": "/api/v1/users/login/telegram/",
                    "session_id": None,
                    "expected_length": TELEGRAM_OTP_LENGTH,
                    "deeplink": None,
                    "verification_link": None,
                    "otp_sent": False,
                    "role": "user",
                    "is_admin": False,
                    "bot_message": "Telefon OTP orqali kiring.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not _is_admin_identity(user):
            otp_service.record_failed_attempt(identifier)
            return Response(
                {
                    "fallback": "otp",
                    "message": "Telegram login faqat adminlar uchun. Telefon OTP orqali kiring.",
                    "otp_endpoint": "/api/v1/users/login/telegram/",
                    "session_id": None,
                    "expected_length": TELEGRAM_OTP_LENGTH,
                    "deeplink": None,
                    "otp_sent": False,
                    "role": "user",
                    "is_admin": False,
                    "bot_message": "Telefon OTP orqali kiring.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        otp_identifier = phone_number if phone_number else telegram_id

        if not otp_identifier:
            return Response(
                {"error": "OTP yuborish uchun identifikator kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session_info = create_admin_session(str(phone_number), user_id=user.id)
        session_id = session_info.get("session_id")
        if not session_id:
            return Response(
                {"error": "Admin session yaratishda xatolik."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        admin_session = cache.get(f"admin_session:{session_id}") or {}
        admin_session["phone_number"] = str(phone_number)
        admin_session["flow"] = "telegram_deeplink"
        cache.set(f"admin_session:{session_id}", admin_session, timeout=1800)

        _write_auth_audit(
            request,
            user,
            "Admin Telegram login requested",
            "Admin Telegram login flow started.",
        )

        logger.info("Telegram login initiated for identifier=%s", mask_pii(str(otp_identifier)))

        return Response(
            {
                "session_id": session_id,
                "message": "Telegram orqali admin tasdiqlashi kutilmoqda.",
                "expected_length": 0,
                "deeplink": f"https://t.me/{os.getenv('AUTH_BOT_USERNAME', 'authversabot').lstrip('@')}?start={session_id}",
                "otp_sent": False,
                "role": "admin",
                "is_admin": True,
                "bot_message": "Telegram orqali admin tasdiqlashi kutilmoqda.",
                "avatar_url": user.get_avatar_url,
            },
            status=status.HTTP_200_OK,
        )

    def _handle_request_otp(self, request, data, identifier):
        phone_number = data.get("phone_number")
        email = data.get("email")

        if not (phone_number or email):
            return Response(
                {"error": "Telefon raqami yoki email kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
            return Response({"error": "Admin topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        if not _is_admin_identity(user):
            otp_service.record_failed_attempt(identifier)
            return Response(
                {"error": "Bu OTP faqat adminlar uchun."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not _is_admin_identity(user):
            otp_service.record_failed_attempt(identifier)
            return Response({"error": "Foydalanuvchi admin emas."}, status=status.HTTP_403_FORBIDDEN)

        otp = generate_numeric_code(length=6)
        logger.info("Generated OTP for admin login for %s", mask_pii(str(identifier)))

        session_info = create_admin_session(email or user.email, user_id=user.id)
        session_id = session_info.get("session_id")
        if not session_id:
            return Response(
                {"error": "Admin session yaratishda xatolik."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        otp_service.store_admin_code_hash(session_id, otp)

        _write_auth_audit(
            request,
            user,
            "Admin OTP requested",
            "Admin OTP login flow started.",
        )

        if email:
            tasks.send_otp_email.delay(email, otp)

        logger.info("OTP request handled for identifier=%s", mask_pii(str(identifier)))

        return Response(
            {
                "session_id": session_id,
                "message": "OTP yuborildi.",
                "avatar_url": user.get_avatar_url,
            },
            status=status.HTTP_200_OK,
        )

    def _handle_verify_otp(self, request, data, identifier):
        phone_number = data.get("phone_number")
        email = data.get("email")
        otp_code = data.get("otp")
        session_id = data.get("session_id")

        if not (phone_number or email) or not otp_code or not session_id:
            return Response(
                {"error": "Telefon raqami/email, session_id va OTP kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_valid, session_meta = otp_service.verify_admin_code(session_id, otp_code)

        if not is_valid:
            # Incorrect OTP, record failed attempt
            banned = otp_service.record_failed_attempt(identifier)
            if banned:
                return Response(
                    {
                        "banned": True,
                        "message": "Siz bloklandingiz. Ko‘p marta noto‘g‘ri urinishlar.",
                        "redirect": "/not_allowed/?from=admin_login",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            return Response({"error": "OTP noto‘g‘ri."}, status=status.HTTP_400_BAD_REQUEST)

        # OTP is correct, retrieve user from session meta
        user = None

        if session_meta and session_meta.get("user_id"):
            try:
                user = CustomUser.objects.get(id=session_meta["user_id"])
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
            return Response({"error": "Admin topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        otp_service.delete_admin_code(session_id)  # Delete OTP from cache
        otp_service.delete_admin_session(session_id)  # Delete session after successful login

        with transaction.atomic():
            login(request, user)
            _write_auth_audit(
                request,
                user,
                "Admin OTP login successful",
                "Admin login completed with OTP.",
            )

        # FIXED: Use determine_role() helper instead of hardcoded logic
        from .serializers import determine_role

        computed_role = determine_role(user)

        # Determine redirect based on role
        redirect_url = "/account/"
        if computed_role == "admin":
            redirect_url = "/dashboard/admin/"
        elif computed_role == "seller":
            redirect_url = "/dashboard/seller/"

        return Response(
            {
                "success": True,
                "role": computed_role,  # Use determined role
                "redirect": redirect_url,
                "avatar_url": user.get_avatar_url,
            },
            status=status.HTTP_200_OK,
        )

    def _handle_request_verification(self, request, data, identifier):
        # This action seems redundant with request_otp and is based on the old model.
        # It's safer to deprecate it in favor of the explicit request_otp flow.
        return self._handle_request_otp(request, data, identifier)

    def _handle_gmail_oauth(self, request, data, identifier):
        serializer = GmailOAuthSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        # Placeholder for actual Google OAuth exchange logic
        # In a real scenario, we'd exchange the code for a token and find/create a user.
        return Response(
            {"error": "Google OAuth bu yerda toʻliq joriy etilmagan."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    def verify(self, request, *args, **kwargs):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response({"detail": "session_id required"}, status=status.HTTP_400_BAD_REQUEST)

        session_meta = otp_service.get_admin_session_meta(session_id)
        if not session_meta:
            return Response({"status": "not_found"}, status=status.HTTP_404_NOT_FOUND)

        identifier = session_meta.get("identifier")
        if otp_service.is_banned(identifier):
            return Response({"status": "banned"}, status=status.HTTP_403_FORBIDDEN)
        # Check if session is expired (based on creation time and duration)
        created_at_timestamp = session_meta.get("created_at")
        if created_at_timestamp and (time.time() - created_at_timestamp) > settings.ADMIN_SESSION_DURATION:
            return Response({"status": "expired"}, status=status.HTTP_200_OK)

        # The 'verify' endpoint is for polling. The actual login happens in 'verify_otp'.
        # This logic is for a different flow (e.g., magic link) which isn't fully implemented here.
        # Let's adjust it for a polling scenario.

        if session_meta.get("verified"):
            user_id = session_meta.get("user_id")
            user = User.objects.filter(id=user_id).first()
            if not user:
                return Response(
                    {"status": "verified", "user_not_found": True},
                    status=status.HTTP_200_OK,
                )

            if not _is_admin_identity(user):
                return Response({"status": "rejected"}, status=status.HTTP_403_FORBIDDEN)

            if session_meta.get("flow") == "telegram_deeplink":
                bot_username = os.getenv("AUTH_BOT_USERNAME", "authversabot").lstrip("@")
                return Response(
                    {
                        "status": "verified",
                        "success": True,
                        "verified": True,
                        "requires_deeplink": True,
                        "verification_link": f"https://t.me/{bot_username}?start={session_id}",
                    },
                    status=status.HTTP_200_OK,
                )

            with transaction.atomic():
                login(request, user)
                _write_auth_audit(
                    request,
                    user,
                    "Admin Telegram login successful",
                    "Admin Telegram callback completed.",
                )
                refresh = RefreshToken.for_user(user)

            otp_service.delete_admin_session(session_id)

            # FIXED: Determine role from server-side data, not hardcoded
            from .serializers import determine_role

            computed_role = determine_role(user)

            return Response(
                {
                    "status": "verified",
                    "success": True,
                    "verified": True,
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "redirect": reverse("dashboard:dashboard-admin"),
                    "role": computed_role,  # Use determined role
                    "avatar_url": user.get_avatar_url,
                },
                status=status.HTTP_200_OK,
            )

        return Response({"status": "pending"}, status=status.HTTP_200_OK)

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
                {"error": "session_id and code are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Rate limiting check
        if identifier:
            is_allowed, remaining = otp_service.check_rate_limit(f"admin_login:{identifier}")
            if not is_allowed:
                logger.warning("Rate limit exceeded for admin login: identifier=%s", identifier)
                return Response(
                    {
                        "banned": True,
                        "message": "Siz bloklandingiz. Ko‘p marta noto‘g‘ri urinishlar.",
                        "retry_after": remaining,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        is_valid, session_meta = otp_service.verify_admin_code(session_id, code)

        if not is_valid:
            # Incorrect OTP, record failed attempt
            banned = otp_service.record_failed_attempt(identifier)
            if banned:
                return Response(
                    {
                        "banned": True,
                        "message": "Siz bloklandingiz. Ko‘p marta noto‘g‘ri urinishlar.",
                        "redirect": "/not_allowed/?from=admin_login",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            return Response({"error": "OTP noto‘g‘ri."}, status=status.HTTP_400_BAD_REQUEST)

        # OTP is correct, retrieve user from session meta
        user = None

        if session_meta and session_meta.get("user_id"):
            try:
                user = CustomUser.objects.get(id=session_meta["user_id"])
            except CustomUser.DoesNotExist:
                pass

        if user is None:
            # Try to find user by phone_number or email if provided
            if data.get("phone_number"):
                try:
                    user = CustomUser.objects.get(phone_number=data["phone_number"])
                except CustomUser.DoesNotExist:
                    pass
            elif data.get("email"):
                try:
                    user = CustomUser.objects.get(email=data["email"])
                except CustomUser.DoesNotExist:
                    pass

        if user is None:
            otp_service.record_failed_attempt(identifier)
            return Response({"error": "Admin topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        otp_service.delete_admin_code(session_id)  # Delete OTP from cache
        otp_service.delete_admin_session(session_id)  # Delete session after successful login

        # Reset rate limit on successful login
        if identifier:
            otp_service.reset_rate_limit(f"admin_login:{identifier}")

        # Create Django session so dashboard (session-auth) works
        user.backend = "django.contrib.auth.backends.ModelBackend"
        login(request, user)
        request.session.set_expiry(SESSION_TIMEOUT)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # FIXED: Determine role from server-side data, not hardcoded
        from .serializers import determine_role

        computed_role = determine_role(user)

        return Response(
            {
                "ok": True,
                "token": str(refresh.access_token),
                "refresh": str(refresh),
                "next": reverse("dashboard:dashboard-admin"),
                "user_id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": computed_role,  # Use determined role
                "is_verified": True,
                "avatar_url": user.get_avatar_url,
            },
            status=status.HTTP_200_OK,
        )


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
            user, created = CustomUser.objects.get_or_create(
                phone_number=phone, defaults={"email": email, "full_name": full_name}
            )
        elif email:
            user, created = CustomUser.objects.get_or_create(
                email=email, defaults={"phone_number": phone, "full_name": full_name}
            )
        else:

            return Response(
                {"error": "Telefon raqami yoki email kiritilishi shart."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

        incognito_header = request.headers.get("X-Incognito", "false").lower() == "true"
        incognito_payload = request.data.get("incognito", False)
        incognito = incognito_header or incognito_payload

        logger.info("OTP generated for method=%s", "telegram" if phone else "email")

        request.session["auth_identifier"] = identifier
        request.session["auth_session_id"] = session.session_id
        request.session["auth_user_id"] = user.id
        request.session.save()

        bot_username = os.getenv("AUTH_BOT_USERNAME", "authversabot").lstrip("@")
        deeplink = f"https://t.me/{bot_username}?start={session.session_id}"
        logger.info("Registration handled for user_id=%s", user.id)

        response = Response(
            {
                "message": "OTP yuborildi",
                "session_id": session.session_id,
                "expected_length": otp_length,
                "deeplink": deeplink,
                "incognito": incognito,
                "avatar_url": user.get_avatar_url,
            },
            status=status.HTTP_200_OK,
        )
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

        identifier = phone_number

        ip_address = request.META.get("REMOTE_ADDR")
        account_key = f"telegram:{identifier}" if telegram_id else f"phone:{phone_number}"

        if is_locked(account_key):
            logger.warning(f"Account locked out for IP {ip_address}.")
            return Response(
                {"detail": "Account temporarily locked. Please try again later."},
                status=status.HTTP_423_LOCKED,
            )

        if is_banned(identifier):
            return Response(
                {
                    "fallback": "otp",
                    "message": "Bu login identifikatori permanent banlangan.",
                    "otp_required": False,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        incognito_header = request.headers.get("X-Incognito", "false").lower() == "true"
        incognito_payload = request.data.get("incognito", False)
        incognito = incognito_header or incognito_payload

        user = CustomUser.objects.filter(phone_number=phone_number).first()

        if user is None and phone_number:
            with transaction.atomic():
                user = CustomUser.objects.create(
                    phone_number=phone_number,
                    telegram_id=telegram_id or None,
                    full_name=name,
                    role="user",
                )
                _write_auth_audit(
                    request,
                    user,
                    "Telegram user created",
                    "New user created with a Telegram identity.",
                )
        elif user is not None and telegram_id and not user.telegram_id:
            with transaction.atomic():
                user.telegram_id = telegram_id
                if name and not user.full_name:
                    user.full_name = name
                user.save(update_fields=["telegram_id", "full_name"])
                _write_auth_audit(
                    request,
                    user,
                    "Telegram identity linked",
                    "Telegram identity linked to an existing user.",
                )

        if not user or not _is_admin_identity(user):
            session = _create_telegram_otp_session(request, user, identifier) if user else None
            if session:
                return Response(
                    {
                        "fallback": "otp",
                        "message": "Telegram orqali 4 xonali OTP yuborildi.",
                        "otp_required": True,
                        "session_id": session.session_id,
                        "expected_length": TELEGRAM_OTP_LENGTH,
                        "delivery": "telegram",
                        "deeplink": f"https://t.me/{os.getenv('AUTH_BOT_USERNAME', 'authversabot').lstrip('@')}?start={session.session_id}",
                        "otp_sent": True,
                        "role": "user",
                        "is_admin": False,
                        "bot_message": "Telegram botdagi 4 xonali kodni kiriting.",
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(
                {
                    "fallback": "otp",
                    "message": "Telegram login faqat adminlar uchun. Telefon OTP orqali kiring.",
                    "otp_required": True,
                    "expected_length": TELEGRAM_OTP_LENGTH,
                    "session_id": None,
                    "deeplink": None,
                    "otp_sent": False,
                    "role": "user",
                    "is_admin": False,
                    "bot_message": "Telefon OTP orqali kiring.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        session = create_otp_session(purpose="telegram")
        otp_length = TELEGRAM_OTP_LENGTH
        otp_code = generate_numeric_code(otp_length)

        store_bot_otp(session.session_id, otp_code)

        bind_session_to_user(session.session_id, user.id, identifier)

        bot_username = os.getenv("AUTH_BOT_USERNAME", "authversabot").lstrip("@")
        web_link = f"https://t.me/{bot_username}?start={session.session_id}"

        _write_auth_audit(
            request,
            user,
            "Admin Telegram login requested",
            "Admin Telegram login flow started.",
        )

        logger.info(f"Telegram login initiated for user_id={user.id}, role={user.role}")

        decr_ip_score(ip_address, delta=getattr(settings, "AUTH_IP_SCORE_DECAY_SUCCESS", 5))

        response_data = {
            "message": "Admin Telegram tasdiqlashi boshlandi.",
            "session_id": session.session_id,
            "expected_length": otp_length,
            "deeplink": web_link,
            "otp_sent": True,
            "incognito": incognito,
            "avatar_url": user.get_avatar_url,
            "role": "admin",
            "is_admin": True,
            "bot_message": "Admin Telegram tasdiqlashi boshlandi.",
        }

        return Response(response_data, status=status.HTTP_200_OK)


class EmailLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(request_body=RegisterSerializer)
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data.get("email")
        full_name = serializer.validated_data.get("full_name", "")

        if not email:
            return Response({"email": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

        ip_address = request.META.get("REMOTE_ADDR")
        account_key = f"email:{email}"

        if is_locked(account_key):
            logger.warning(f"Account locked out for IP {ip_address}.")
            return Response(
                {"detail": "Account temporarily locked. Please try again later."},
                status=status.HTTP_423_LOCKED,
            )

        try:
            allowed, _ = check_rate_limit(f"email_login_ip:{ip_address}")
            if not allowed:
                logger.warning(f"Rate limit exceeded for IP: {ip_address} on Email login.")
                return Response(
                    {"detail": "Too many requests. Please try again later."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
        except Exception as e:
            logger.error("Rate limit check error")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            with transaction.atomic():
                user, created = CustomUser.objects.get_or_create(email=email)
                # Update full_name if provided and user was just created or full_name is empty
                if full_name and (created or not user.full_name):
                    user.full_name = full_name
                    user.save()
        except Exception as e:
            logger.error("User get_or_create error")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        otp_length = 6
        try:
            otp_code = generate_numeric_code(otp_length)
            hashed_otp, salt = otp_service.hash_otp_with_salt(otp_code)
            otp_hash_obj = OtpHash(hash=hashed_otp, salt=salt)
        except Exception as e:
            logger.error("OTP hash creation error")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            store_otp_hash(email, otp_hash_obj, ttl=900)
        except Exception as e:
            logger.error("OTP hash storage error")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            session = create_otp_session(purpose="email")
            bind_session_to_user(session.session_id, user.id, email)
        except Exception as e:
            logger.error("OTP session creation/binding error")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        request.session["auth_identifier"] = email
        request.session["auth_session_id"] = session.session_id
        request.session["auth_user_id"] = user.id
        request.session.save()

        try:
            if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False) or not getattr(settings, "USE_CELERY", True):
                tasks.send_otp_email(email, otp_code)
                logger.info("Email OTP sent")
            else:
                tasks.send_otp_email.delay(email, otp_code)
                logger.info("Email OTP enqueued")
        except Exception as e:
            logger.error("Email enqueue/send error")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        decr_ip_score(ip_address, delta=getattr(settings, "AUTH_IP_SCORE_DECAY_SUCCESS", 5))

        return Response(
            {
                "session_id": session.session_id,
                "expected_length": otp_length,
                "message": "OTP sent to email",
                "avatar_url": user.get_avatar_url,
            },
            status=status.HTTP_200_OK,
        )


class VerifyOtpView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(request_body=VerifyOTPSerializer)
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"ok": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session_id = serializer.validated_data.get("session_id")
        code = serializer.validated_data.get("code")
        identifier = serializer.validated_data.get("identifier", "")

        try:
            # Refresh session TTL when user submits OTP code
            refresh_session_ttl(session_id, ttl=ADMIN_SESSION_TTL)

            is_valid, message, session = otp_service.verify_otp_once(session_id, code, identifier)

            if is_valid:
                user_id = session.get("user_id")
                if not user_id:
                    return Response(
                        {"ok": False, "error": "Foydalanuvchi topilmadi."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                try:
                    user = CustomUser.objects.get(id=user_id)

                    if _is_admin_identity(user):
                        return Response(
                            {
                                "ok": False,
                                "error": "Adminlar Telegram orqali alohida login qiladi.",
                            },
                            status=status.HTTP_403_FORBIDDEN,
                        )

                    # Create Django session
                    with transaction.atomic():
                        login(request, user)
                        _write_auth_audit(
                            request,
                            user,
                            "OTP login successful",
                            "Non-admin OTP login completed.",
                        )

                        # Generate JWT tokens
                        refresh = RefreshToken.for_user(user)

                    # FIXED: Use determine_role() helper for consistency
                    from .serializers import determine_role

                    role = determine_role(user)

                    # Determine redirect URL based on role
                    redirect_url = reverse("account")  # Default redirect for simple users
                    if role == "admin":
                        redirect_url = reverse("dashboard:dashboard-admin")
                    elif role == "seller":
                        redirect_url = "/dashboard/seller/"

                    return Response(
                        {
                            "ok": True,
                            "token": str(refresh.access_token),
                            "refresh": str(refresh),
                            "user_id": user.id,
                            "phone_number": user.phone_number,
                            "email": user.email,
                            "is_verified": True,
                            "role": role,  # Use determined role
                            "redirect_url": redirect_url,
                            "avatar_url": user.get_avatar_url,  # Added avatar_url
                        }
                    )
                except CustomUser.DoesNotExist:
                    return Response(
                        {"ok": False, "error": "Foydalanuvchi topilmadi."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                # Handle different error types
                http_status = status.HTTP_400_BAD_REQUEST

                if message == "invalid_code":
                    http_status = status.HTTP_401_UNAUTHORIZED
                elif message == "too_many_attempts":
                    http_status = status.HTTP_403_FORBIDDEN
                elif message == "session_not_found_or_expired":
                    http_status = status.HTTP_400_BAD_REQUEST

                return Response({"ok": False, "error": message}, status=http_status)

        except Exception as e:
            logger.exception("OTP verify error for session_id=%s error=%s", session_id, str(e)[:100])
            log_error_to_dashboard("verify_otp", identifier, str(e)[:200])
            return Response(
                {"ok": False, "error": "server_error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


def log_error_to_dashboard(component: str, masked_identifier: str, short_error: str):
    """Log error to dashboard_error.md in masked format."""
    import os
    from datetime import datetime, timezone

    from django.conf import settings

    error_file = os.path.join(settings.BASE_DIR, "errors", "dashboard_error.md")
    timestamp = datetime.now(timezone.utc).isoformat()

    log_entry = f"\nTIMESTAMP: {timestamp}\n"
    log_entry += f"COMPONENT: {component}\n"
    log_entry += f"USER: {masked_identifier}\n"
    log_entry += f"ERROR: {short_error}\n"
    log_entry += "ACTION: OTP verification failed due to error.\n"

    try:
        os.makedirs(os.path.dirname(error_file), exist_ok=True)
        with open(error_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as write_error:
        logger.error(f"Failed to write error log: {str(write_error)[:100]}")


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        user = self.request.user
        logger.debug(f"MeView - User: {user.id}, email: {user.email}, full_name: {user.full_name}, role: {user.role}")
        return user


class UserProfileViewSet(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        old_email = instance.email
        old_phone = instance.phone_number

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_user = serializer.save()

        if (updated_user.email != old_email and old_email is not None) or (
            updated_user.phone_number != old_phone and old_phone is not None
        ):
            updated_user.is_verified = False
            updated_user.save()
            return Response(
                {
                    "message": "reverify",
                    "detail": "Email yoki telefon o'zgardi. Qayta tasdiqlash kerak.",
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.data)


class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


class SellerViewSet(viewsets.ModelViewSet):
    queryset = Seller.objects.all().order_by("id")
    serializer_class = SellerSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Seller.objects.all().order_by("id")
        if user.is_authenticated:
            return Seller.objects.filter(user=user).order_by("id")
        return Seller.objects.all().order_by("id")


class SubscribedUserViewSet(viewsets.ModelViewSet):
    queryset = SubscribedUser.objects.all()
    serializer_class = SubscribedUserSerializer

    def get_permissions(self):
        if self.action == "create":
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
            verify_url = f"{self.request.build_absolute_uri('/subscribe/')}{token}/"
            try:
                tasks.send_subscription_verification_email.delay(subscriber.email, verify_url)
            except Exception as e:
                logger.error("Subscription email enqueue failed")

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
            return Response(
                {"detail": "Token noto‘g‘ri yoki muddati o‘tgan."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception("Error during email verification")
            return Response(
                {"detail": "Xato yuz berdi"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
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
                logger.error("Subscription email enqueue failed")


@method_decorator(csrf_exempt, name="dispatch")
class CookieRefreshView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(request_body=RegisterSerializer)
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh_token")
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


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        with transaction.atomic():
            logout(request)
            refresh_token = request.COOKIES.get("refresh_token")
            if refresh_token:
                try:
                    RefreshToken(refresh_token).blacklist()
                except Exception:
                    logger.warning("Refresh token blacklist failed during logout")
            response = Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
            for cookie_name in (
                settings.SESSION_COOKIE_NAME,
                settings.CSRF_COOKIE_NAME,
                "access_token",
                "refresh_token",
            ):
                response.delete_cookie(cookie_name)
        return response


class LogoutJWTView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        with transaction.atomic():
            response = Response({"detail": "Successfully logged out from JWT."}, status=status.HTTP_200_OK)
            refresh_token = request.COOKIES.get("refresh_token")
            if refresh_token:
                try:
                    RefreshToken(refresh_token).blacklist()
                except Exception:
                    logger.warning("Failed to blacklist refresh token")
            for cookie_name in (
                settings.SESSION_COOKIE_NAME,
                settings.CSRF_COOKIE_NAME,
                "access_token",
                "refresh_token",
            ):
                response.delete_cookie(cookie_name)
        return response


class DetermineRoleView(APIView):
    """
    Determine user's role from server-side authoritative sources.

    Frontend uses this to route user to correct login endpoint:
    - admin → /api/v1/users/admin/login/
    - seller → /api/v1/users/login/ (or specific seller endpoint)
    - user → /api/v1/users/login/

    Role is computed server-side using determine_role() helper.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        from .serializers import determine_role

        serializer = RoleDetermineSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "role": "user",
                    "detail": "Telefon raqami noto'g'ri. Iltimos, +998 90 123 45 67 kabi haqiqiy raqam kiriting.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        phone_number = serializer.validated_data.get("phone_number")
        email = serializer.validated_data.get("email")

        user = None
        if request.user and request.user.is_authenticated:
            user = request.user
        elif phone_number:
            user = CustomUser.objects.filter(phone_number=phone_number).first()
        elif email:
            user = CustomUser.objects.filter(email=email).first()

        if not user:
            # If user is not found, create a new one for registration flow
            try:
                with transaction.atomic():
                    create_params = {}
                    if phone_number:
                        create_params["phone_number"] = phone_number
                    elif email:
                        create_params["email"] = email

                    if not create_params:
                        return Response(
                            {"detail": "Email or phone number required to determine role or create user."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    user, created = CustomUser.objects.get_or_create(
                        defaults={"role": "user"},
                        **create_params,
                    )
                    if created:
                        logger.info(f"New user created via determine_role: {user.id}")
                        # FIXED: Use determine_role() helper for consistency
                        return Response(
                            {
                                "role": determine_role(user),  # Server-side authoritative role
                                "avatar_url": user.get_avatar_url,
                            },
                            status=status.HTTP_201_CREATED,
                        )
            except Exception as e:
                logger.error(f"Error creating user in determine_role: {e}")
                return Response(
                    {"detail": "Could not create user profile."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        # Debugging: Log user's staff/superuser status
        if settings.DEBUG and user:
            logger.debug(
                f"DetermineRoleView: User {user.email} (ID: {user.id}) - is_staff: {user.is_staff}, is_superuser: {user.is_superuser}"
            )

        # FIXED: Use determine_role() helper instead of hardcoded logic
        role = determine_role(user)
        return Response({"role": role, "avatar_url": user.get_avatar_url}, status=status.HTTP_200_OK)


class UniqueFieldAvailabilityView(APIView):
    """Return whether a given user field value already exists."""

    permission_classes = [AllowAny]
    field_name = None

    def _normalize_value(self, value):
        value = str(value or "").strip()
        if not value:
            return ""
        if self.field_name == "email":
            return value.lower()

        digits = "".join(ch for ch in value if ch.isdigit())
        if not digits:
            return ""
        if value.startswith("+") or value.startswith("00"):
            return "+" + digits.lstrip("0") if digits.startswith("998") else "+" + digits
        if len(digits) == 9:
            return f"+{settings.PHONENUMBER_DEFAULT_REGION_CODE}{digits}"
        return "+" + digits

    def _get_value(self, request):
        if self.field_name == "email":
            value = request.GET.get("email") or request.POST.get("email") or (request.data or {}).get("email")
        else:
            value = (
                request.GET.get("phone_number")
                or request.POST.get("phone_number")
                or (request.data or {}).get("phone_number")
                or request.GET.get("phone")
                or request.POST.get("phone")
                or (request.data or {}).get("phone")
            )
        return value

    def _get_exclude_user_id(self, request):
        value = (
            request.GET.get("exclude_user_id")
            or request.POST.get("exclude_user_id")
            or (request.data or {}).get("exclude_user_id")
        )
        if value is None:
            return None
        value = str(value).strip()
        return value if value.isdigit() else None

    def _handle(self, request, *args, **kwargs):
        value = self._get_value(request)
        if value is None or str(value).strip() == "":
            return Response({"exists": False, "valid": False}, status=400)

        normalized_value = self._normalize_value(value)
        if not normalized_value:
            return Response({"exists": False, "valid": False}, status=400)

        queryset = CustomUser.objects.all()
        if self.field_name == "email":
            queryset = queryset.filter(email__iexact=normalized_value)
        else:
            queryset = queryset.filter(phone_number=normalized_value)

        exclude_user_id = self._get_exclude_user_id(request)
        if exclude_user_id is not None:
            queryset = queryset.exclude(id=exclude_user_id)

        return Response({"exists": queryset.exists(), "value": normalized_value})

    def get(self, request, *args, **kwargs):
        return self._handle(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self._handle(request, *args, **kwargs)


class CheckEmailView(UniqueFieldAvailabilityView):
    field_name = "email"


class CheckPhoneView(UniqueFieldAvailabilityView):
    field_name = "phone_number"


class AccountDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "templates/account.html "

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "dashboard/index.html"

    def test_func(self):
        user = self.request.user
        return bool(
            user.is_authenticated
            and user.is_staff
            and user.is_superuser
            and str(getattr(user, "role", "") or "").lower() == "admin"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["total_users"] = CustomUser.objects.count()
        context["total_orders"] = Order.objects.count()
        context["total_products"] = 150
        context["recent_activities"] = [
            {"timestamp": "2023-10-26 10:00", "description": "User registered."},
            {"timestamp": "2023-10-26 09:30", "description": "Order" "#12345 placed."},
            {"timestamp": "2023-10-25 18:00", "description": "Product updated."},
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
        return Response({"ok": True, "user": serializer.data}, status=status.HTTP_200_OK)


class StripeConfigView(APIView):
    permission_classes = []

    def get(self, request):
        return Response({"publishableKey": settings.STRIPE_PUBLISHABLE_KEY})


class TestAdminLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(request_body=TestAdminLoginSerializer)
    def post(self, request):
        if not settings.DEBUG:
            raise Http404("This endpoint is only available in DEBUG mode.")

        serializer = TestAdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        phone_number = data.get("phone_number")
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")

        identifier = email or phone_number or username or request.META.get("REMOTE_ADDR")

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
            return Response({"error": "Noto‘g‘ri ma’lumotlar."}, status=status.HTTP_401_UNAUTHORIZED)

        if not _is_admin_identity(user):
            return Response({"error": "Kirish huquqi yo‘q."}, status=status.HTTP_403_FORBIDDEN)

        login(request, user)

        # FIXED: Determine role from server-side data, not hardcoded
        from .serializers import determine_role

        computed_role = determine_role(user)

        return Response(
            {
                "ok": True,
                "next": reverse("dashboard:dashboard-admin"),
                "role": computed_role,  # Use determined role
                "avatar_url": user.get_avatar_url,
            },
            status=status.HTTP_200_OK,
        )


def auth_view(request):
    return render(request, "auth.html")


class AccountView(FormView):
    template_name = "account.html"
    form_class = AccountSettingsForm
    success_url = "/account/"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        return self.request.user

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.get_object()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context["user"] = user
        context["user_role"] = user.role if user.role else "user"
        context["show_old_password"] = user.has_usable_password()

        # Add orders if available
        try:
            from orders.models import Order

            context["orders"] = Order.objects.filter(user=user).order_by("-date")[:10]
        except Exception:
            context["orders"] = []

        return context

    def form_valid(self, form):
        from django.contrib import messages
        from django.db import transaction

        from users.avatar_handler import handle_avatar_upload

        user = form.save(commit=False)

        try:
            with transaction.atomic():
                # Handle avatar upload if provided
                avatar_file = self.request.FILES.get("avatar")
                if avatar_file:
                    success, file_path, error = handle_avatar_upload(user, avatar_file)
                    if not success:
                        form.add_error("avatar", error)
                        messages.error(self.request, f"Avatar yuklashda xatolik: {error}")
                        return self.form_invalid(form)

                # Handle password change
                old_password = form.cleaned_data.get("old_password")
                new_password1 = form.cleaned_data.get("new_password1")
                new_password2 = form.cleaned_data.get("new_password2")

                if new_password1:
                    if user.has_usable_password() and (not old_password or not user.check_password(old_password)):
                        form.add_error("old_password", "Eski parol noto'g'ri")
                        return self.form_invalid(form)

                    if new_password1 != new_password2:
                        form.add_error("new_password2", "Yangi parollar mos kelmadi")
                        return self.form_invalid(form)

                    user.set_password(new_password1)

                # Save user
                user.save(update_fields=["full_name", "email", "phone_number", "telegram_id", "address"])

                if avatar_file:
                    messages.success(self.request, "Avatar muvaffaqiyatli yuklandi!")
                else:
                    messages.success(self.request, "Profil ma'lumotlari muvaffaqiyatli saqlandi!")

        except Exception as e:
            messages.error(self.request, f"Saqlashda xatolik yuz berdi: {str(e)}")
            return self.form_invalid(form)

        return super().form_valid(form)

    def form_invalid(self, form):
        from django.contrib import messages

        messages.error(self.request, "Forma xatolar bilan to'ldirilgan")
        return self.render_to_response(self.get_context_data(form=form))


class AdminCheckView(TemplateView):
    template_name = "admin_check_deeplink.html"

    @staticmethod
    def _is_expired(session_data):
        created_at = session_data.get("created_at")
        return bool(session_data.get("expired") or (created_at and time.time() - created_at >= ADMIN_LINK_TTL))

    @staticmethod
    def _mark_expired(session_id, session_data):
        session_data["expired"] = True
        cache.set(f"admin_session:{session_id}", session_data, timeout=1800)

    @staticmethod
    def _json_request(request):
        return request.headers.get("X-Requested-With") == "XMLHttpRequest"

    @staticmethod
    def _request_fingerprint(request):
        return (
            request.COOKIES.get("device_fp")
            or request.META.get("HTTP_X_DEVICE_FINGERPRINT")
            or request.META.get("HTTP_AUTHORIZATION_FINGERPRINT")
        )

    def get(self, request, *args, **kwargs):
        session_id = request.GET.get("session")
        otp = request.GET.get("otp")

        if not session_id:
            return self.render_to_response({"session_expired": True})

        stored_data = cache.get(f"admin_session:{session_id}")

        if not stored_data:
            return self.render_to_response({"session_expired": True})

        if self._is_expired(stored_data):
            self._mark_expired(session_id, stored_data)
            return self.render_to_response(
                {
                    "session_id": session_id,
                    "session_expired": True,
                }
            )

        if stored_data.get("used"):
            return self.render_to_response(
                {
                    "session_id": session_id,
                    "already_completed": True,
                }
            )

        return self.render_to_response(
            {
                "session_id": session_id,
                "pending_verification": bool(stored_data),
                "telegram_verified": bool(stored_data.get("verified")),
                "attempts": stored_data.get("attempts", 0),
            }
        )

    def post(self, request, *args, **kwargs):
        fingerprint = self._request_fingerprint(request)
        client_ip = get_client_ip(request)
        session_id = request.GET.get("session", "").strip() or request.POST.get("session_id", "").strip()
        stored_data = get_admin_session_meta(session_id)

        if stored_data and int(stored_data.get("attempts", 0)) >= ADMIN_DEEPLINK_MAX_ATTEMPTS:
            banned_user = request.user if request.user.is_authenticated else None
            ban_reason = "10 ta noto'g'ri admin deep-link urinishidan keyin permanent ban"
            with transaction.atomic():
                BanRecord.objects.create(
                    ip=client_ip or None,
                    fingerprint=fingerprint,
                    user=banned_user,
                    reason=ban_reason,
                    ban_type="permanent",
                    created_by="telegram",
                    attempts=int(stored_data.get("attempts", 0)),
                    source=request.path,
                    meta={"session_id": session_id, "flow": "telegram_deeplink"},
                )
            return redirect("not_allowed")

        if not stored_data:
            response = {"session_id": session_id, "session_expired": True, "error": "Session ended"}
            return (
                JsonResponse(response, status=410) if self._json_request(request) else self.render_to_response(response)
            )

        if self._is_expired(stored_data):
            self._mark_expired(session_id, stored_data)
            response = {"session_id": session_id, "session_expired": True, "error": "Session ended"}
            return (
                JsonResponse(response, status=410) if self._json_request(request) else self.render_to_response(response)
            )

        if stored_data.get("used"):
            response = {"session_id": session_id, "already_completed": True}
            return JsonResponse(response) if self._json_request(request) else self.render_to_response(response)

        if not stored_data.get("verified"):
            response = {
                "session_id": session_id,
                "pending_verification": True,
                "error": "Avval Telegramdagi telefon tasdiqlashni yakunlang.",
            }
            return (
                JsonResponse(response, status=400) if self._json_request(request) else self.render_to_response(response)
            )

        try:
            user = CustomUser.objects.get(id=stored_data.get("user_id"))
        except CustomUser.DoesNotExist:
            response = {"session_id": session_id, "error": "Admin topilmadi."}
            return (
                JsonResponse(response, status=404) if self._json_request(request) else self.render_to_response(response)
            )

        submitted_phone = request.POST.get("phone_number", "").strip()
        submitted_name = request.POST.get("full_name", "").strip()
        submitted_email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        normalize_phone = lambda value: "".join(ch for ch in str(value or "") if ch.isdigit())
        expected_phone = stored_data.get("phone_number") or stored_data.get("identifier")
        matches_admin = (
            submitted_email.casefold() == (user.email or "").casefold()
            and normalize_phone(submitted_phone) == normalize_phone(expected_phone)
            and submitted_name == (user.full_name or "")
            and user.check_password(password)
        )
        if not matches_admin or not _is_admin_identity(user):
            stored_data["attempts"] = int(stored_data.get("attempts", 0)) + 1
            with transaction.atomic():
                cache.set(f"admin_session:{session_id}", stored_data, timeout=1800)
                if stored_data["attempts"] >= ADMIN_DEEPLINK_MAX_ATTEMPTS:
                    ban_reason = "10 ta noto'g'ri admin deep-link urinishidan keyin permanent ban"
                    banned_user = request.user if request.user.is_authenticated else None
                    BanRecord.objects.create(
                        ip=client_ip or None,
                        fingerprint=fingerprint,
                        user=banned_user,
                        reason=ban_reason,
                        ban_type="permanent",
                        created_by="telegram",
                        attempts=stored_data["attempts"],
                        source=request.path,
                        meta={"session_id": session_id, "flow": "telegram_deeplink"},
                    )
            response = {
                "session_id": session_id,
                "pending_verification": True,
                "error": "Admin ma'lumotlari mos kelmadi.",
                "attempts": stored_data["attempts"],
            }
            if stored_data["attempts"] >= ADMIN_DEEPLINK_MAX_ATTEMPTS:
                return redirect("not_allowed")
            return (
                JsonResponse(response, status=400) if self._json_request(request) else self.render_to_response(response)
            )

        if not claim_admin_session(session_id):
            response = {"session_id": session_id, "already_completed": True}
            return JsonResponse(response) if self._json_request(request) else self.render_to_response(response)

        refresh = RefreshToken.for_user(user)
        with transaction.atomic():
            login(request, user)
            _write_auth_audit(
                request,
                user,
                "Admin Telegram callback successful",
                "Admin Telegram callback completed.",
            )

        response = {
            "success": True,
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "username": user.full_name or user.email,
            "user_role": "admin",
            "avatar_url": user.get_avatar_url,
        }
        return JsonResponse(response) if self._json_request(request) else self.render_to_response(response)


# ============================================
# SUBSCRIPTION VERIFICATION PAGE
# ============================================


class SubscriptionVerifyPageView(TemplateView):
    """Subscription verification page - standalone template view."""

    template_name = "subscribe.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        token = self.kwargs.get("token")
        context["token"] = token
        return context
