import pytest
from unittest.mock import patch, MagicMock
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
import time

from security.redis_counters import redis_client, get_int, incr_with_ttl, set_with_ttl, delete_key
from security.locks import record_failed_attempt, is_locked, reset_lockout
from security.ip_score import incr_ip_score, decr_ip_score, get_ip_score, reset_ip_score
from users.models import CustomUser

pytestmark = pytest.mark.django_db

@pytest.fixture(autouse=True)
def clear_redis_before_each_test():
    """Clears Redis before each test to ensure isolation."""
    redis_client.flushdb()
    yield
    redis_client.flushdb()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture(autouse=True)
def mock_recaptcha_settings(settings):
    settings.RECAPTCHA_SECRET_KEY = 'test_secret_key'
    settings.RECAPTCHA_THRESHOLD = 0.5
    settings.DEBUG = True # Enable debug logging in tests
    # Set security settings for tests
    settings.AUTH_ATTEMPTS_10MIN = 3
    settings.AUTH_ATTEMPTS_DAY = 10
    settings.AUTH_LOCKOUT_TTL = 60 # 1 minute for tests
    settings.AUTH_IP_REQ_PER_MIN = 5
    settings.AUTH_IP_LOGIN_PER_HOUR = 5
    settings.AUTH_HIGH_RISK_IP_SCORE = 50
    settings.AUTH_IP_SCORE_RECAPTCHA_MISSING = 15
    settings.AUTH_IP_SCORE_RECAPTCHA_FAIL = 20
    settings.AUTH_IP_SCORE_RECAPTCHA_LOW_SCORE = 25
    settings.AUTH_IP_SCORE_OTP_FAIL = 10
    settings.AUTH_IP_SCORE_DECAY_SUCCESS = 5


# --- Unit Tests for Security Modules ---

def test_incr_with_ttl():
    key = "test_incr"
    assert incr_with_ttl(key, ttl=1) == 1
    assert redis_client.ttl(key) > 0
    assert incr_with_ttl(key, ttl=1) == 2
    time.sleep(1.1) # Wait for TTL to expire
    assert get_int(key) == 0 # Key should have expired

def test_record_failed_attempt_and_lockout():
    account_key = "test_account"
    
    # No lockout initially
    assert not is_locked(account_key)

    # Record attempts until lockout threshold
    for _ in range(settings.AUTH_ATTEMPTS_10MIN - 1):
        record_failed_attempt(account_key)
        assert not is_locked(account_key)
    
    # One more attempt should trigger lockout
    record_failed_attempt(account_key)
    assert is_locked(account_key)
    assert get_int(f"acct:lock:{account_key}") == 1
    assert redis_client.ttl(f"acct:lock:{account_key}") > 0

    # Test reset lockout
    reset_lockout(account_key)
    assert not is_locked(account_key)
    assert get_int(f"acct:fail:10min:{account_key}") == 0

def test_ip_score_increase_and_decay():
    ip = "127.0.0.1"
    
    assert get_ip_score(ip) == 0
    
    incr_ip_score(ip, delta=10)
    assert get_ip_score(ip) == 10
    
    incr_ip_score(ip, delta=20)
    assert get_ip_score(ip) == 30
    
    decr_ip_score(ip, delta=5)
    assert get_ip_score(ip) == 25
    
    # Ensure score doesn't go below 0
    decr_ip_score(ip, delta=100)
    assert get_ip_score(ip) == 0

    reset_ip_score(ip)
    assert get_ip_score(ip) == 0

# --- Integration Tests for Views with Security Logic ---

@patch('users.otp_service.verify_recaptcha')
@patch('users.otp_service.create_otp_session')
@patch('users.otp_service.store_bot_otp')
@patch('users.otp_service.bind_session_to_user')
def test_telegram_login_account_locked(mock_bind, mock_store, mock_create, mock_recaptcha, api_client: APIClient):
    phone_number = "+998901234567"
    account_key = f"phone:{phone_number}"
    set_with_ttl(f"acct:lock:{account_key}", 1, 60) # Manually lock account

    payload = {"phone_number": phone_number, "name": "Locked User"}
    response = api_client.post(reverse("login-telegram"), payload, format="json")

    assert response.status_code == status.HTTP_423_LOCKED
    assert "Account temporarily locked" in response.json()['detail']
    mock_recaptcha.assert_not_called()

@patch('users.otp_service.verify_recaptcha')
@patch('users.otp_service.create_otp_session')
@patch('users.otp_service.store_bot_otp')
@patch('users.otp_service.bind_session_to_user')
def test_telegram_login_incognito_recaptcha_fail_increases_scores(mock_bind, mock_store, mock_create, mock_recaptcha, api_client: APIClient):
    phone_number = "+998901234567"
    ip_address = '127.0.0.1' # Default IP for APIClient
    account_key = f"phone:{phone_number}"

    mock_recaptcha.return_value = {'success': False, 'score': 0.1, 'error-codes': ['bad-token']}

    payload = {"phone_number": phone_number, "name": "Test User", "incognito": True, "recaptcha_token": "bad_token"}
    headers = {'X-Incognito': 'true', 'REMOTE_ADDR': ip_address} # Simulate IP

    response = api_client.post(reverse("login-telegram"), payload, format="json", headers=headers)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "reCAPTCHA tekshiruvi muvaffaqiyatsiz tugadi" in response.json()['detail']
    mock_recaptcha.assert_called_once()
    
    # Check if failed attempt recorded and IP score increased
    assert get_int(f"acct:fail:10min:{account_key}") == 1
    assert get_ip_score(ip_address) == settings.AUTH_IP_SCORE_RECAPTCHA_FAIL

@patch('users.otp_service.verify_recaptcha')
@patch('users.otp_service.create_otp_session')
@patch('users.otp_service.store_bot_otp')
@patch('users.otp_service.bind_session_to_user')
def test_telegram_login_high_ip_score_requires_recaptcha(mock_bind, mock_store, mock_create, mock_recaptcha, api_client: APIClient):
    phone_number = "+998901234568"
    ip_address = '127.0.0.2'
    
    # Manually set high IP score
    incr_ip_score(ip_address, delta=settings.AUTH_HIGH_RISK_IP_SCORE + 10) # Score > threshold
    assert get_ip_score(ip_address) > settings.AUTH_HIGH_RISK_IP_SCORE

    mock_recaptcha.return_value = {'success': True, 'score': 0.9, 'action': 'login_telegram'}

    payload = {"phone_number": phone_number, "name": "High Risk User", "recaptcha_token": "good_token"}
    headers = {'REMOTE_ADDR': ip_address} # Simulate IP

    response = api_client.post(reverse("login-telegram"), payload, format="json", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    mock_recaptcha.assert_called_once() # reCAPTCHA should be called due to high IP score
    assert get_ip_score(ip_address) == settings.AUTH_HIGH_RISK_IP_SCORE + 10 - settings.AUTH_IP_SCORE_DECAY_SUCCESS # Score should decay

@patch('users.otp_service.verify_recaptcha')
@patch('users.otp_service.create_otp_session')
@patch('users.otp_service.store_bot_otp')
@patch('users.otp_service.bind_session_to_user')
def test_telegram_login_normal_skips_recaptcha_decays_ip_score(mock_bind, mock_store, mock_create, mock_recaptcha, api_client: APIClient):
    phone_number = "+998901234569"
    ip_address = '127.0.0.3'
    
    # Set a moderate IP score
    incr_ip_score(ip_address, delta=20)
    assert get_ip_score(ip_address) == 20

    mock_create.return_value = MagicMock(session_id='mock_session_id')

    payload = {"phone_number": phone_number, "name": "Normal User"}
    headers = {'REMOTE_ADDR': ip_address}

    response = api_client.post(reverse("login-telegram"), payload, format="json", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    mock_recaptcha.assert_not_called() # reCAPTCHA should be skipped
    assert get_ip_score(ip_address) == 20 - settings.AUTH_IP_SCORE_DECAY_SUCCESS # Score should decay

def test_ip_rate_limit_middleware(api_client: APIClient, settings):
    ip_address = '192.168.1.1'
    settings.AUTH_IP_REQ_PER_MIN = 2 # Set a low limit for testing

    headers = {'REMOTE_ADDR': ip_address}
    url = reverse("login-telegram") # Any auth endpoint

    # First requests should pass
    for _ in range(settings.AUTH_IP_REQ_PER_MIN):
        response = api_client.post(url, {"phone_number": "+998901111111"}, format="json", headers=headers)
        assert response.status_code != status.HTTP_429_TOO_MANY_REQUESTS
    
    # Next request should be rate-limited
    response = api_client.post(url, {"phone_number": "+998901111111"}, format="json", headers=headers)
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "Too many requests from IP" in response.json()['detail']

@patch('users.otp_service.verify_otp_once')
def test_verify_otp_fail_increases_ip_and_account_scores(mock_verify_otp_once, api_client: APIClient, settings):
    session_id = 'test_session_id'
    code = '123456'
    ip_address = '127.0.0.4'
    email = 'fail@example.com'
    account_key = f"email:{email}"

    # Mock session meta to get identifier for account_key
    with patch('users.otp_service.get_session_meta', return_value={'user_id': 1, 'identifier': email}):
        mock_verify_otp_once.return_value = (False, 'Invalid OTP', None) # OTP verification fails

        payload = {"session_id": session_id, "code": code}
        headers = {'REMOTE_ADDR': ip_address}

        response = api_client.post(reverse("verify-otp"), payload, format="json", headers=headers)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid OTP" in response.json()['detail']
        
        # Check if failed attempt recorded and IP score increased
        assert get_int(f"acct:fail:10min:{account_key}") == 1
        assert get_ip_score(ip_address) == settings.AUTH_IP_SCORE_OTP_FAIL

@patch('users.otp_service.verify_otp_once')
@patch('rest_framework_simplejwt.tokens.RefreshToken.for_user')
@patch('users.otp_service.get_session_meta')
def test_verify_otp_success_resets_lockout_decays_ip_score(mock_get_session_meta, mock_refresh_token, mock_verify_otp_once, api_client: APIClient, settings):
    session_id = 'test_session_id_success'
    code = '654321'
    ip_address = '127.0.0.5'
    phone_number = '+998901234500'
    account_key = f"phone:{phone_number}"

    # Setup initial state: locked account, high IP score
    record_failed_attempt(account_key) # Lock account
    record_failed_attempt(account_key)
    record_failed_attempt(account_key)
    assert is_locked(account_key)
    incr_ip_score(ip_address, delta=60) # High IP score
    assert get_ip_score(ip_address) == 60

    # Mock successful OTP verification
    mock_get_session_meta.return_value = {'user_id': CustomUser.objects.create(phone_number=phone_number).id, 'identifier': phone_number}
    mock_verify_otp_once.return_value = (True, 'OTP verified successfully', mock_get_session_meta.return_value)
    mock_refresh_token.return_value = MagicMock(access_token='mock_access', __str__=lambda x: 'mock_refresh')

    payload = {"session_id": session_id, "code": code}
    headers = {'REMOTE_ADDR': ip_address}

    response = api_client.post(reverse("verify-otp"), payload, format="json", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()['success'] is True
    
    # Check if lockout is reset and IP score decayed
    assert not is_locked(account_key)
    assert get_ip_score(ip_address) == 60 - settings.AUTH_IP_SCORE_DECAY_SUCCESS
