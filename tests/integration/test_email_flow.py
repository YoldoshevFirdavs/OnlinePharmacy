import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.core import mail
from users.otp_service import store_otp_hash, OtpHash, hash_otp_with_salt
from users.models import CustomUser

pytestmark = pytest.mark.django_db

def test_email_login_returns_otp_sent_and_sends_email(api_client: APIClient, settings):
    """
    Test that the email login endpoint returns otp_sent: True and sends an email.
    """
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    settings.DEFAULT_FROM_EMAIL = 'test@example.com'
    settings.USE_CELERY = False # Ensure synchronous email sending for test

    email = "test@example.com"
    name = "Test User"
    login_data = {"email": email, "full_name": name}

    response = api_client.post(reverse("login-email"), login_data, format="json")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "session_id" in response_data
    assert response_data["otp_sent"] is True
    assert "message" in response_data
    assert response_data["message"] == "Email queued"

    # Verify that an email was sent
    assert len(mail.outbox) == 1
    sent_email = mail.outbox[0]
    assert sent_email.to == [email]
    assert "OnlinePharmacy - Tasdiqlash kodi" in sent_email.subject
    assert "Sizning kodingiz:" in sent_email.body

    # Optionally, verify OTP code if DEBUG is True
    if settings.DEBUG:
        assert "otp_code" in response_data
        # Further verification of OTP can be done here if needed
