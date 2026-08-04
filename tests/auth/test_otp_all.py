from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from unittest.mock import patch
from users.otp_service import get_session_meta, get_otp_hash, OtpHash, OtpSession, generate_numeric_code, store_otp_hash
from django.conf import settings
from django.core import mail
import pytest

User = get_user_model()

pytestmark = pytest.mark.django_db

class UnifiedOtpTests(APITestCase):
    def setUp(self):
        self.email = "test@example.com"
        self.phone_number = "+998901234567"
        self.password = "StrongPassword123"
        self.user_email = User.objects.create_user(email=self.email, password=self.password)
        self.user_phone = User.objects.create_user(phone_number=self.phone_number, password=self.password)
        self.login_email_url = reverse("login-email")
        self.login_telegram_url = reverse("login-telegram")
        self.verify_otp_url = reverse("verify-otp")

    @patch("custom_auth.tasks.send_otp_email.delay")
    def test_gmail_login_sends_otp_and_creates_session(self, mock_send_otp_email_delay):
        data = {"email": self.email}
        response = self.client.post(self.login_email_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("session_id", response.data)
        self.assertEqual(response.data["message"], "Email queued")
        session_id = response.data["session_id"]
        session_meta = get_session_meta(session_id)
        self.assertIsNotNone(session_meta)
        self.assertEqual(session_meta["user_id"], self.user_email.id)
        self.assertEqual(session_meta["identifier"], self.email)
        self.assertEqual(session_meta["purpose"], "email")
        otp_hash_obj = get_otp_hash(self.email)
        self.assertIsNotNone(otp_hash_obj)
        mock_send_otp_email_delay.assert_called_once()
        args, kwargs = mock_send_otp_email_delay.call_args
        self.assertEqual(args[0], self.email)
        self.assertRegex(args[1], r"^\d{6}$")
        if settings.DEBUG:
            self.assertIn("otp_code", response.data)
            self.assertRegex(response.data["otp_code"], r"^\d{6}$")

    def test_gmail_login_sends_email(self):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        settings.DEFAULT_FROM_EMAIL = "test@example.com"
        settings.USE_CELERY = False
        data = {"email": self.email, "full_name": "Test User"}
        response = self.client.post(self.login_email_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("session_id", response.data)
        self.assertTrue(response.data["otp_sent"])
        self.assertEqual(response.data["message"], "Email queued")
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, [self.email])
        self.assertIn("OnlinePharmacy - Tasdiqlash kodi", sent_email.subject)
        self.assertIn("Sizning kodingiz:", sent_email.body)
        if settings.DEBUG:
            self.assertIn("otp_code", response.data)

    def test_telegram_login_sends_otp(self):
        data = {"phone_number": self.phone_number}
        response = self.client.post(self.login_telegram_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session_id = response.data["session_id"]
        otp = generate_numeric_code(4)
        store_otp_hash(
            session=OtpSession(session_id=session_id, purpose="telegram"),
            code=otp,
            ttl_seconds=180,
        )
        verify_data = {"channel": "telegram", "session_id": session_id, "code": otp}
        verify_response = self.client.post(self.verify_otp_url, verify_data, format="json")
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", verify_response.data)
        self.assertIn("refresh_token", verify_response.cookies)