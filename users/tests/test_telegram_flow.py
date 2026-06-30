import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from users.models import CustomUser
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.django_db

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture(autouse=True)
def mock_recaptcha_settings(settings):
    settings.RECAPTCHA_SECRET_KEY = 'test_secret_key'
    settings.RECAPTCHA_THRESHOLD = 0.5
    settings.DEBUG = True # Enable debug logging in tests

@patch('users.otp_service.verify_recaptcha')
@patch('users.otp_service.create_otp_session')
@patch('users.otp_service.store_bot_otp')
@patch('users.otp_service.bind_session_to_user')
def test_telegram_login_returns_session_id_and_deeplink(
    mock_bind_session_to_user,
    mock_store_bot_otp,
    mock_create_otp_session,
    mock_verify_recaptcha,
    api_client: APIClient
):
    """
    Test that the Telegram login endpoint returns a session_id and deeplink,
    and handles reCAPTCHA conditionally.
    """
    phone_number = "+998901234567"
    name = "Test User"
    login_telegram_url = reverse("login-telegram")

    # Mock successful reCAPTCHA for incognito flow
    mock_verify_recaptcha.return_value = {'success': True, 'score': 0.9, 'action': 'login_telegram'}
    
    # Mock OTP session creation
    mock_session = MagicMock(session_id='mock_session_id_telegram')
    mock_create_otp_session.return_value = mock_session

    # --- Test Incognito Flow (reCAPTCHA required) ---
    payload_incognito = {
        "phone_number": phone_number,
        "name": name,
        "incognito": True,
        "recaptcha_token": "mock_recaptcha_token_incognito"
    }
    headers_incognito = {'X-Incognito': 'true'}

    response_incognito = api_client.post(login_telegram_url, payload_incognito, format="json", headers=headers_incognito)

    assert response_incognito.status_code == status.HTTP_200_OK
    response_data_incognito = response_incognito.json()
    assert "session_id" in response_data_incognito
    assert response_data_incognito["session_id"] == 'mock_session_id_telegram'
    assert "deeplink" in response_data_incognito
    assert "otp_sent" in response_data_incognito
    assert response_data_incognito["otp_sent"] is True
    mock_verify_recaptcha.assert_called_once_with("mock_recaptcha_token_incognito", action='login_telegram')
    mock_create_otp_session.assert_called_once_with(purpose="telegram")
    mock_store_bot_otp.assert_called_once()
    mock_bind_session_to_user.assert_called_once_with('mock_session_id_telegram', MagicMock(), phone_number) # user_id will be a mock object

    # Reset mocks for next test case
    mock_verify_recaptcha.reset_mock()
    mock_create_otp_session.reset_mock()
    mock_store_bot_otp.reset_mock()
    mock_bind_session_to_user.reset_mock()

    # --- Test Non-Incognito Flow (reCAPTCHA skipped) ---
    payload_normal = {
        "phone_number": phone_number,
        "name": name,
        "incognito": False,
        # No recaptcha_token sent
    }
    headers_normal = {'X-Incognito': 'false'}

    response_normal = api_client.post(login_telegram_url, payload_normal, format="json", headers=headers_normal)

    assert response_normal.status_code == status.HTTP_200_OK
    response_data_normal = response_normal.json()
    assert "session_id" in response_data_normal
    assert "deeplink" in response_data_normal
    assert "otp_sent" in response_data_normal
    assert response_data_normal["otp_sent"] is True
    mock_verify_recaptcha.assert_not_called() # reCAPTCHA should be skipped
    mock_create_otp_session.assert_called_once_with(purpose="telegram")
    mock_store_bot_otp.assert_called_once()
    mock_bind_session_to_user.assert_called_once_with('mock_session_id_telegram', MagicMock(), phone_number) # user_id will be a mock object

