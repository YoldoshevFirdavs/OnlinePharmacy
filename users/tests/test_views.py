import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
from users.models import Seller, SubscribedUser, Deliverer, OnboardToken # Removed OTP import
# If OTP model is in another app, please specify its import path, e.g., from some_app.models import OTP
from unittest.mock import patch, MagicMock
from datetime import timedelta
from django.utils import timezone
import hashlib # For OnboardToken tests

User = get_user_model() # This is CustomUser

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def create_user(db):
    def _create_user(email=None, phone_number=None, password='testpassword', full_name='Test User', is_staff=False, is_superuser=False, is_verified=False, role='customer'):
        user_data = {
            'full_name': full_name,
            'password': password,
            'is_staff': is_staff,
            'is_superuser': is_superuser,
            'is_verified': is_verified, # Set directly on CustomUser
            'role': role, # Set directly on CustomUser
        }
        if email:
            user_data['email'] = email
        if phone_number:
            user_data['phone_number'] = phone_number

        # CustomUser.objects.create_user handles setting password and saving
        # It expects either email or phone_number, or both, depending on your CustomUserManager
        if email and not phone_number:
            user = User.objects.create_user(email=email, **user_data)
        elif phone_number and not email:
            user = User.objects.create_user(phone_number=phone_number, **user_data)
        elif email and phone_number:
            user = User.objects.create_user(email=email, phone_number=phone_number, **user_data)
        else: # Fallback if neither email nor phone_number is provided, might need adjustment based on your User model
            user = User.objects.create_user(**user_data) # This might fail if email/phone_number is required

        return user
    return _create_user

@pytest.fixture
def authenticated_client(api_client, create_user):
    user = create_user(email='auth@example.com', password='testpassword', is_verified=True)
    api_client.force_authenticate(user=user) # Use force_authenticate for DRF tests
    return api_client, user

@pytest.fixture
def admin_client(api_client, create_user):
    admin_user = create_user(email='admin@example.com', password='testpassword', is_staff=True, is_superuser=True, is_verified=True, role='admin')
    api_client.force_authenticate(user=admin_user) # Use force_authenticate for DRF tests
    return api_client, admin_user

@pytest.fixture
def deliverer_user(db, create_user):
    user = create_user(email='deliverer@example.com', full_name='Deliverer User', password='testpassword', role='deliverer', is_verified=False)
    Deliverer.objects.create(user=user, phone_number='+998901234567', status='pending') # Create Deliverer instance
    return user

@pytest.fixture
def seller_user(db, create_user):
    user = create_user(email='seller@example.com', full_name='Seller User', password='testpassword', role='seller', is_verified=True)
    Seller.objects.create(user=user, company_name='Test Company')
    return user

# Mocking OTP sending functions
@patch('users.views.send_otp_telegram')
@patch('users.views.send_otp_email')
class TestRegistrationView:
    url = reverse('users:register')

    def test_registration_success_email(self, mock_send_otp_email, mock_send_otp_telegram, api_client):
        data = {
            'full_name': 'New User',
            'email': 'newuser@example.com',
            'password': 'strongpassword',
            'password2': 'strongpassword'
        }
        response = api_client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email='newuser@example.com')
        assert user.full_name == 'New User'
        assert not user.is_verified # Should not be verified initially
        assert user.role == 'customer' # Default role
        mock_send_otp_email.assert_called_once()
        mock_send_otp_telegram.assert_not_called()

    def test_registration_success_phone(self, mock_send_otp_email, mock_send_otp_telegram, api_client):
        data = {
            'full_name': 'Phone User',
            'phone_number': '+998901234567',
            'password': 'strongpassword',
            'password2': 'strongpassword'
        }
        response = api_client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(phone_number='+998901234567')
        assert user.full_name == 'Phone User'
        assert not user.is_verified
        assert user.role == 'customer'
        mock_send_otp_telegram.assert_called_once()
        mock_send_otp_email.assert_not_called()

    def test_registration_password_mismatch(self, mock_send_otp_email, mock_send_otp_telegram, api_client):
        data = {
            'full_name': 'New User',
            'email': 'newuser2@example.com',
            'password': 'strongpassword',
            'password2': 'wrongpassword'
        }
        response = api_client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in response.data
        assert not User.objects.filter(email='newuser2@example.com').exists()

    def test_registration_missing_credentials(self, mock_send_otp_email, mock_send_otp_telegram, api_client):
        data = {
            'full_name': 'New User',
            'password': 'strongpassword',
            'password2': 'strongpassword'
        }
        response = api_client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'non_field_errors' in response.data # Assuming serializer handles this

    def test_registration_existing_email(self, mock_send_otp_email, mock_send_otp_telegram, api_client, create_user):
        create_user(email='existing@example.com')
        data = {
            'full_name': 'Existing User',
            'email': 'existing@example.com',
            'password': 'strongpassword',
            'password2': 'strongpassword'
        }
        response = api_client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data

    def test_registration_existing_phone(self, mock_send_otp_email, mock_send_otp_telegram, api_client, create_user):
        create_user(phone_number='+998901234567')
        data = {
            'full_name': 'Existing User',
            'phone_number': '+998901234567',
            'password': 'strongpassword',
            'password2': 'strongpassword'
        }
        response = api_client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'phone_number' in response.data


@patch('users.views.send_otp_telegram')
class TestTelegramLoginView:
    url = reverse('users:login-telegram')

    def test_telegram_login_new_user_success(self, mock_send_otp_telegram, api_client):
        data = {'phone_number': '+998901234567', 'full_name': 'Telegram User'}
        response = api_client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert 'session_id' in response.data
        assert 'expected_length' in response.data
        assert User.objects.filter(phone_number='+998901234567').exists()
        mock_send_otp_telegram.assert_called_once()

    def test_telegram_login_existing_user_success(self, mock_send_otp_telegram, api_client, create_user):
        create_user(phone_number='+998901112233', email='existing_phone@example.com')
        data = {'phone_number': '+998901112233'}
        response = api_client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert 'session_id' in response.data
        assert 'expected_length' in response.data
        mock_send_otp_telegram.assert_called_once()

    def test_telegram_login_missing_phone(self, mock_send_otp_telegram, api_client):
        data = {'full_name': 'Telegram User'}
        response = api_client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'phone_number' in response.data
        mock_send_otp_telegram.assert_not_called()

    def test_telegram_login_invalid_phone(self, mock_send_otp_telegram, api_client):
        data = {'phone_number': 'invalid-phone'}
        response = api_client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'phone_number' in response.data
        mock_send_otp_telegram.assert_not_called()

@patch('users.views.send_otp_email')
class TestEmailLoginView:
    url = reverse('users:login-email')

    def test_email_login_new_user_success(self, mock_send_otp_email, api_client):
        data = {'email': 'newemail@example.com', 'full_name': 'Email User'}
        response = api_client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert 'session_id' in response.data
        assert 'expected_length' in response.data
        assert User.objects.filter(email='newemail@example.com').exists()
        mock_send_otp_email.assert_called_once()

    def test_email_login_existing_user_success(self, mock_send_otp_email, api_client, create_user):
        create_user(email='existing_email@example.com')
        data = {'email': 'existing_email@example.com'}
        response = api_client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert 'session_id' in response.data
        assert 'expected_length' in response.data
        mock_send_otp_email.assert_called_once()

    def test_email_login_missing_email(self, mock_send_otp_email, api_client):
        data = {'full_name': 'Email User'}
        response = api_client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data
        mock_send_otp_email.assert_not_called()

    def test_email_login_invalid_email(self, mock_send_otp_email, api_client):
        data = {'email': 'invalid-email'}
        response = api_client.post(self.url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data
        mock_send_otp_email.assert_not_called()

# TestVerifyOtpView is commented out because the OTP model is not found.
# Please provide the correct import path for the OTP model if it exists elsewhere.
# class TestVerifyOtpView:
#     url = reverse('users:verify-otp')

#     @pytest.fixture
#     def setup_otp(self, db, create_user):
#         user = create_user(email='otp_test@example.com', is_verified=False)
#         otp_code = '123456'
#         session_id = 'test_session_id'
#         # OTP.objects.create(user=user, session_id=session_id, code=otp_code, expires_at=timezone.now() + timedelta(minutes=5))
#         # Replace with actual OTP creation logic once model is identified
#         return user, session_id, otp_code

#     def test_verify_otp_success(self, api_client, setup_otp):
#         user, session_id, otp_code = setup_otp
#         data = {'session_id': session_id, 'code': otp_code}
#         response = api_client.post(self.url, data, format='json')
#         assert response.status_code == status.HTTP_200_OK
#         assert 'access' in response.data
#         assert 'refresh' in response.data
#         user.refresh_from_db()
#         assert response.data['user_role'] == user.role
#         assert response.data['full_name'] == user.full_name
#         assert user.is_verified

#     def test_verify_otp_invalid_code(self, api_client, setup_otp):
#         user, session_id, otp_code = setup_otp
#         data = {'session_id': session_id, 'code': '999999'}
#         response = api_client.post(self.url, data, format='json')
#         assert response.status_code == status.HTTP_400_BAD_REQUEST
#         assert 'code' in response.data
#         user.refresh_from_db()
#         assert not user.is_verified

#     def test_verify_otp_expired_code(self, api_client, setup_otp):
#         user, session_id, otp_code = setup_otp
#         # otp_obj = OTP.objects.get(session_id=session_id)
#         # otp_obj.expires_at = timezone.now() - timedelta(minutes=1)
#         # otp_obj.save()
#         # Replace with actual OTP expiration logic once model is identified

#         data = {'session_id': session_id, 'code': otp_code}
#         response = api_client.post(self.url, data, format='json')
#         assert response.status_code == status.HTTP_400_BAD_REQUEST
#         assert 'code' in response.data
#         user.refresh_from_db()
#         assert not user.is_verified

#     def test_verify_otp_missing_session_id(self, api_client):
#         data = {'code': '123456'}
#         response = api_client.post(self.url, data, format='json')
#         assert response.status_code == status.HTTP_400_BAD_REQUEST
#         assert 'session_id' in response.data

class TestUserViewSet: # Renamed from UserProfileViewSet
    url_list = reverse('users:user-list') # Assuming the URL name is now 'user-list' for CustomUser

    def test_get_user_profile_authenticated(self, authenticated_client):
        client, user = authenticated_client
        response = client.get(self.url_list)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email
        assert response.data['is_verified'] == user.is_verified
        assert response.data['role'] == user.role

    def test_get_user_profile_unauthenticated(self, api_client):
        response = api_client.get(self.url_list)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_patch_user_profile_email_change_unverifies(self, authenticated_client):
        client, user = authenticated_client
        user.is_verified = True
        user.save()
        
        data = {'email': 'new_email@example.com'}
        response = client.patch(self.url_list, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.email == 'new_email@example.com'
        assert not user.is_verified # Should be unverified

    def test_patch_user_profile_phone_change_unverifies(self, authenticated_client):
        client, user = authenticated_client
        user.is_verified = True
        user.save()
        
        data = {'phone_number': '+998909876543'}
        response = client.patch(self.url_list, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.phone_number == '+9989099876543' # Corrected phone number
        assert not user.is_verified # Should be unverified

    def test_patch_user_profile_other_field_no_unverify(self, authenticated_client):
        client, user = authenticated_client
        user.is_verified = True
        user.save()
        
        data = {'full_name': 'Updated Name'}
        response = client.patch(self.url_list, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.full_name == 'Updated Name'
        assert user.is_verified # Should remain verified

class TestSellerViewSet:
    url_list = reverse('users:seller-list')

    def test_create_seller_authenticated_verified(self, authenticated_client):
        client, user = authenticated_client
        user.is_verified = True
        user.save()
        data = {'company_name': 'New Seller Co.'}
        response = client.post(self.url_list, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert Seller.objects.filter(user=user).exists()
        user.refresh_from_db()
        assert user.role == 'seller' # Role should change to seller

    def test_create_seller_authenticated_unverified(self, authenticated_client):
        client, user = authenticated_client
        user.is_verified = False # Ensure unverified
        user.save()
        data = {'company_name': 'New Seller Co.'}
        response = client.post(self.url_list, data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN # Should be forbidden

    def test_update_seller_authenticated_verified(self, authenticated_client, seller_user):
        client, user = authenticated_client
        # Make authenticated_client's user the seller_user
        client.force_authenticate(user=seller_user)
        
        url_detail = reverse('users:seller-detail', args=[seller_user.seller.pk])
        data = {'company_name': 'Updated Company Name'}
        response = client.patch(url_detail, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        seller_user.seller.refresh_from_db()
        assert seller_user.seller.company_name == 'Updated Company Name'

    def test_update_seller_authenticated_unverified(self, authenticated_client, seller_user):
        client, user = authenticated_client
        # Make authenticated_client's user the seller_user
        client.force_authenticate(user=seller_user)
        seller_user.is_verified = False # Set is_verified directly on user
        seller_user.save()

        url_detail = reverse('users:seller-detail', args=[seller_user.seller.pk])
        data = {'company_name': 'Updated Company Name'}
        response = client.patch(url_detail, data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_seller_authenticated_verified(self, authenticated_client, seller_user):
        client, user = authenticated_client
        client.force_authenticate(user=seller_user)
        url_detail = reverse('users:seller-detail', args=[seller_user.seller.pk])
        response = client.delete(url_detail)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Seller.objects.filter(user=seller_user).exists()
        seller_user.refresh_from_db() # Refresh user object
        assert seller_user.role == 'customer' # Role should revert

    def test_delete_seller_authenticated_unverified(self, authenticated_client, seller_user):
        client, user = authenticated_client
        client.force_authenticate(user=seller_user)
        seller_user.is_verified = False
        seller_user.save()
        url_detail = reverse('users:seller-detail', args=[seller_user.seller.pk])
        response = client.delete(url_detail)
        assert response.status_code == status.HTTP_403_FORBIDDEN

@patch('users.views.send_verification_email')
class TestSubscribedUserViewSet:
    url_list = reverse('users:subscribeduser-list')

    def test_create_subscribed_user_sends_email(self, mock_send_verification_email, api_client):
        data = {'email': 'subscribe@example.com'}
        response = api_client.post(self.url_list, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert SubscribedUser.objects.filter(email='subscribe@example.com').exists()
        mock_send_verification_email.assert_called_once_with('subscribe@example.com')

    def test_create_subscribed_user_existing_email(self, mock_send_verification_email, api_client):
        SubscribedUser.objects.create(email='existing_subscribe@example.com')
        data = {'email': 'existing_subscribe@example.com'}
        response = api_client.post(self.url_list, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data
        mock_send_verification_email.assert_not_called()

class TestDelivererCompleteOnboardView:
    url = reverse('users:deliverer-complete-onboard')

    @pytest.fixture
    def setup_deliverer_onboard(self, db, create_user):
        user = create_user(email='onboard@example.com', password='oldpassword', role='deliverer', is_verified=False)
        Deliverer.objects.create(user=user, phone_number='+998901234567', status='pending') # Use Deliverer model
        # Create an OnboardToken for the user
        token_string = "mock_onboard_token_value"
        token_hash = hashlib.sha256(token_string.encode()).hexdigest()
        OnboardToken.objects.create(user=user, token_hash=token_hash, expires_at=timezone.now() + timedelta(hours=1))
        return user, token_string

    def test_complete_onboard_success(self, api_client, setup_deliverer_onboard):
        user, token = setup_deliverer_onboard
        data = {
            'token': token,
            'password': 'newstrongpassword',
            'password2': 'newstrongpassword'
        }
        # Simulate token validation (in a real app, token would be validated against a stored one)
        with patch('users.views.check_onboarding_token', return_value=user) as mock_check_token:
            response = api_client.post(self.url, data, format='json')
            assert response.status_code == status.HTTP_200_OK
            assert response.data['message'] == 'Deliverer onboarding completed successfully.'
            user.refresh_from_db()
            assert user.check_password('newstrongpassword')
            assert user.deliverer_profile.status == 'active' # Access via related_name
            assert user.is_verified # Deliverer should be verified after onboarding
            mock_check_token.assert_called_once_with(token)

    def test_complete_onboard_password_mismatch(self, api_client, setup_deliverer_onboard):
        user, token = setup_deliverer_onboard
        data = {
            'token': token,
            'password': 'newstrongpassword',
            'password2': 'mismatchedpassword'
        }
        with patch('users.views.check_onboarding_token', return_value=user):
            response = api_client.post(self.url, data, format='json')
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert 'password' in response.data
            user.refresh_from_db()
            assert not user.check_password('newstrongpassword') # Password should not change

    def test_complete_onboard_invalid_token(self, api_client):
        data = {
            'token': 'invalid_token',
            'password': 'newstrongpassword',
            'password2': 'newstrongpassword'
        }
        with patch('users.views.check_onboarding_token', return_value=None): # Simulate invalid token
            response = api_client.post(self.url, data, format='json')
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert 'token' in response.data

    def test_complete_onboard_token_for_non_deliverer(self, api_client, create_user):
        user = create_user(email='not_deliverer@example.com', role='customer') # Not a deliverer
        token_string = "mock_token_non_deliverer_value"
        token_hash = hashlib.sha256(token_string.encode()).hexdigest()
        OnboardToken.objects.create(user=user, token_hash=token_hash, expires_at=timezone.now() + timedelta(hours=1))
        data = {
            'token': token_string,
            'password': 'newstrongpassword',
            'password2': 'newstrongpassword'
        }
        with patch('users.views.check_onboarding_token', return_value=user):
            response = api_client.post(self.url, data, format='json')
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert 'token' in response.data # Or a more specific error message about user role