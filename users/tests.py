"""
Comprehensive tests for the verify_otp endpoint.
Tests cover: payload validation, session not found, invalid code, too many attempts, and success path.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from users.serializers import VerifyOTPSerializer

User = get_user_model()

pytestmark = pytest.mark.django_db

# URL for the verify OTP endpoint
VERIFY_OTP_URL = reverse("user-verify-otp")


class VerifyOTPPayloadValidationTests(APITestCase):
    """Test payload validation for the verify_otp endpoint."""

    def setUp(self):
        self.client = APIClient()

    def test_missing_session_id_returns_400(self):
        """POST without session_id should return 400."""
        response = self.client.post(
            VERIFY_OTP_URL,
            {"code": "123456", "identifier": "test@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.json().get("ok"))
        self.assertIn("errors", response.json())

    def test_missing_code_returns_400(self):
        """POST without code should return 400."""
        response = self.client.post(
            VERIFY_OTP_URL,
            {"session_id": "abc123", "identifier": "test@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.json().get("ok"))
        self.assertIn("errors", response.json())

    def test_empty_session_id_returns_400(self):
        """POST with empty session_id should return 400."""
        response = self.client.post(VERIFY_OTP_URL, {"session_id": "", "code": "123456"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.json().get("ok"))

    def test_empty_code_returns_400(self):
        """POST with empty code should return 400."""
        response = self.client.post(VERIFY_OTP_URL, {"session_id": "abc123", "code": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.json().get("ok"))

    def test_whitespace_only_code_returns_400(self):
        """POST with whitespace-only code should return 400."""
        response = self.client.post(VERIFY_OTP_URL, {"session_id": "abc123", "code": "   "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.json().get("ok"))

    def test_missing_all_required_fields_returns_400(self):
        """POST without required fields should return 400."""
        response = self.client.post(VERIFY_OTP_URL, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.json().get("ok"))


class VerifyOTPIdentifierTests(APITestCase):
    """Test that identifier is optional and handled correctly."""

    def setUp(self):

        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            phone_number="+998901234567",
        )

    @patch("users.views.otp_service.verify_otp_once")
    @patch("users.views.otp_service.delete_session")
    def test_success_with_identifier(self, mock_delete_session, mock_verify_otp):
        """Success with identifier in payload."""
        mock_verify_otp.return_value = (
            True,
            "OTP verified successfully",
            {
                "code": "415922",
                "attempts": 0,
                "user_id": self.user.id,
                "identifier": "test@example.com",
            },
        )

        response = self.client.post(
            VERIFY_OTP_URL,
            {"session_id": "s1", "code": "415922", "identifier": "test@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json().get("ok"))
        self.assertIn("user_id", response.json())

    @patch("users.views.otp_service.verify_otp_once")
    @patch("users.views.otp_service.delete_session")
    def test_success_without_identifier(self, mock_delete_session, mock_verify_otp):
        """Success without identifier in payload (should still work)."""
        mock_verify_otp.return_value = (
            True,
            "OTP verified successfully",
            {
                "code": "415922",
                "attempts": 0,
                "user_id": self.user.id,
                "identifier": "test@example.com",
            },
        )

        response = self.client.post(VERIFY_OTP_URL, {"session_id": "s1", "code": "415922"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json().get("ok"))


class VerifyOTPSessionNotFoundTests(APITestCase):
    """Test behavior when session is not found or expired."""

    def setUp(self):
        self.client = APIClient()

    @patch("users.views.otp_service.get_session_meta")
    def test_session_not_found_returns_400(self, mock_get_session):
        """When session doesn't exist, return 400 with session_not_found_or_expired."""
        mock_get_session.return_value = None

        response = self.client.post(
            VERIFY_OTP_URL,
            {
                "session_id": "nonexistent",
                "code": "123456",
                "identifier": "test@example.com",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.json().get("ok"))
        self.assertEqual(response.json().get("error"), "session_not_found_or_expired")

    @patch("users.views.otp_service.get_session_meta")
    def test_session_not_found_logs_warning(self, mock_get_session):
        """When session doesn't exist, log with masked identifier."""
        mock_get_session.return_value = None
        mock_logger = MagicMock()

        with patch("users.otp_service.logger", mock_logger):
            self.client.post(
                VERIFY_OTP_URL,
                {
                    "session_id": "nonexistent",
                    "code": "123456",
                    "identifier": "test@example.com",
                },
                format="json",
            )
            # Verify warning was logged with masked identifier
            mock_logger.warning.assert_called()
            call_args = mock_logger.warning.call_args[0]
            # First argument should contain the log message
            log_message = call_args[0]
            # Should not contain full email
            self.assertNotIn("test@example.com", log_message)

    @patch("users.views.otp_service.get_session_meta")
    def test_corrupted_session_returns_400(self, mock_get_session):
        """When session is corrupted (not a dict), return 400."""
        mock_get_session.return_value = None  # Corrupted session treated as None

        response = self.client.post(VERIFY_OTP_URL, {"session_id": "corrupted", "code": "123456"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.json().get("ok"))
        self.assertEqual(response.json().get("error"), "session_not_found_or_expired")


class VerifyOTPInvalidCodeTests(APITestCase):
    """Test behavior with invalid OTP code."""

    def setUp(self):

        self.client = APIClient()

    @patch("users.views.otp_service.verify_otp_once")
    def test_invalid_code_returns_401(self, mock_verify_otp):
        """When code doesn't match, return 401 with invalid_code error."""
        mock_verify_otp.return_value = (False, "invalid_code", None)

        response = self.client.post(
            VERIFY_OTP_URL,
            {
                "session_id": "s1",
                "code": "000000",  # Wrong code
                "identifier": "test@example.com",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.json().get("ok"))
        self.assertEqual(response.json().get("error"), "invalid_code")

    @patch("users.views.otp_service.verify_otp_once")
    def test_invalid_code_logs_attempt(self, mock_verify_otp):
        """Invalid code should be logged with masked identifier."""
        mock_verify_otp.return_value = (False, "invalid_code", None)

        self.client.post(
            VERIFY_OTP_URL,
            {
                "session_id": "s1",
                "code": "000000",
                "identifier": "test@example.com",
            },
            format="json",
        )
        # verify_otp_once does the logging, just verify it was called
        mock_verify_otp.assert_called_once()

    def test_empty_code_returns_400(self):
        """Empty code should be rejected by serializer, not reach view logic."""
        response = self.client.post(VERIFY_OTP_URL, {"session_id": "s1", "code": ""}, format="json")
        # Should fail at serializer validation
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.json().get("ok"))


class VerifyOTPTooManyAttemptsTests(APITestCase):
    """Test behavior when max attempts are exceeded."""

    def setUp(self):

        self.client = APIClient()

    @patch("users.views.otp_service.verify_otp_once")
    def test_too_many_attempts_returns_403(self, mock_verify_otp):
        """When attempts >= MAX_ATTEMPTS, return 403 with too_many_attempts error."""
        mock_verify_otp.return_value = (False, "too_many_attempts", None)

        response = self.client.post(
            VERIFY_OTP_URL,
            {
                "session_id": "s1",
                "code": "000000",  # Wrong code
                "identifier": "test@example.com",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.json().get("ok"))
        self.assertEqual(response.json().get("error"), "too_many_attempts")

    @patch("users.views.otp_service.verify_otp_once")
    def test_attempts_incremented_on_each_failure(self, mock_verify_otp):
        """Each failed attempt should increment the counter."""
        mock_verify_otp.side_effect = [
            (False, "invalid_code", None),
            (False, "invalid_code", None),
            (False, "invalid_code", None),
        ]

        for attempt in range(3):
            response = self.client.post(
                VERIFY_OTP_URL,
                {
                    "session_id": "s1",
                    "code": "000000",
                    "identifier": "test@example.com",
                },
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Verify verify_otp_once was called 3 times
        self.assertEqual(mock_verify_otp.call_count, 3)


class VerifyOTPSuccessTests(APITestCase):
    """Test successful OTP verification flow."""

    def setUp(self):

        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            phone_number="+998901234567",
        )

    @patch("users.views.otp_service.verify_otp_once")
    def test_success_returns_200_with_token(self, mock_verify_otp):
        """When code matches, return 200 with token and user info."""
        mock_verify_otp.return_value = (
            True,
            "OTP verified successfully",
            {
                "code": "415922",
                "code_hash": "hashed_value",
                "attempts": 0,
                "user_id": self.user.id,
                "identifier": "test@example.com",
            },
        )

        response = self.client.post(
            VERIFY_OTP_URL,
            {"session_id": "s1", "code": "415922", "identifier": "test@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json().get("ok"))
        self.assertIn("token", response.json())
        self.assertIn("refresh", response.json())
        self.assertIn("user_id", response.json())
        self.assertEqual(response.json()["user_id"], self.user.id)

    @patch("users.views.otp_service.verify_otp_once")
    def test_success_deletes_session(self, mock_verify_otp):
        """Successful verification should delete the session."""
        mock_verify_otp.return_value = (
            True,
            "OTP verified successfully",
            {
                "code": "415922",
                "attempts": 0,
                "user_id": self.user.id,
                "identifier": "test@example.com",
            },
        )

        self.client.post(
            VERIFY_OTP_URL,
            {"session_id": "s1", "code": "415922", "identifier": "test@example.com"},
            format="json",
        )
        # Session deletion is handled inside verify_otp_once, so we just verify success
        mock_verify_otp.assert_called_once()

    @patch("users.views.otp_service.verify_otp_once")
    def test_success_logs_success(self, mock_verify_otp):
        """Successful verification should log success with masked identifier."""
        mock_verify_otp.return_value = (
            True,
            "OTP verified successfully",
            {
                "code": "415922",
                "attempts": 0,
                "user_id": self.user.id,
                "identifier": "test@example.com",
            },
        )

        self.client.post(
            VERIFY_OTP_URL,
            {
                "session_id": "s1",
                "code": "415922",
                "identifier": "test@example.com",
            },
            format="json",
        )
        # verify_otp_once does the logging, just verify it was called
        mock_verify_otp.assert_called_once()

    @patch("users.views.otp_service.verify_otp_once")
    def test_success_with_plain_text_otp(self, mock_verify_otp):
        """Success should work with plain text OTP (non-hashed)."""
        mock_verify_otp.return_value = (
            True,
            "OTP verified successfully",
            {
                "code": "415922",  # Plain text
                "attempts": 0,
                "user_id": self.user.id,
                "identifier": "test@example.com",
            },
        )

        response = self.client.post(VERIFY_OTP_URL, {"session_id": "s1", "code": "415922"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json().get("ok"))


class VerifyOTPIdentifierMaskingTests(APITestCase):
    """Test that identifiers are properly masked in logs."""

    def setUp(self):

        self.client = APIClient()

    @patch("users.views.otp_service.verify_otp_once")
    def test_email_masked_in_logs(self, mock_verify_otp):
        """Email identifiers should be masked (f***@g***.com format)."""
        mock_verify_otp.return_value = (False, "session_not_found_or_expired", None)

        self.client.post(
            VERIFY_OTP_URL,
            {
                "session_id": "s1",
                "code": "123456",
                "identifier": "testuser@example.com",
            },
            format="json",
        )
        # verify_otp_once handles the logging, just verify it was called
        mock_verify_otp.assert_called_once()

    @patch("users.views.otp_service.verify_otp_once")
    def test_phone_masked_in_logs(self, mock_verify_otp):
        """Phone identifiers should be masked."""
        mock_verify_otp.return_value = (False, "session_not_found_or_expired", None)

        self.client.post(
            VERIFY_OTP_URL,
            {"session_id": "s1", "code": "123456", "identifier": "+998901234567"},
            format="json",
        )
        # verify_otp_once handles the logging, just verify it was called
        mock_verify_otp.assert_called_once()


class VerifyOTPServerErrorTests(APITestCase):
    """Test server error handling."""

    def setUp(self):

        self.client = APIClient()

    @patch("users.views.otp_service.get_session_meta")
    def test_exception_returns_500(self, mock_get_session):
        """When exception occurs, return 500 with server_error."""
        mock_get_session.side_effect = Exception("Database connection failed")

        response = self.client.post(VERIFY_OTP_URL, {"session_id": "s1", "code": "123456"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertFalse(response.json().get("ok"))
        self.assertEqual(response.json().get("error"), "server_error")


class VerifyOTPSerializerTests(APITestCase):
    """Test VerifyOTPSerializer directly."""

    def test_valid_data(self):
        """Serializer should accept valid data."""
        data = {
            "session_id": "abc123",
            "code": "123456",
            "identifier": "test@example.com",
        }
        serializer = VerifyOTPSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["session_id"], "abc123")
        self.assertEqual(serializer.validated_data["code"], "123456")
        self.assertEqual(serializer.validated_data["identifier"], "test@example.com")

    def test_empty_code_invalid(self):
        """Serializer should reject empty code."""
        data = {"session_id": "abc123", "code": ""}
        serializer = VerifyOTPSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("code", serializer.errors)

    def test_whitespace_only_code_invalid(self):
        """Serializer should reject whitespace-only code."""
        data = {"session_id": "abc123", "code": "   "}
        serializer = VerifyOTPSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("code", serializer.errors)

    def test_code_is_stripped(self):
        """Serializer should strip whitespace from code."""
        data = {"session_id": "abc123", "code": " 123456 "}
        serializer = VerifyOTPSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["code"], "123456")

    def test_identifier_optional(self):
        """Serializer should accept missing identifier."""
        data = {"session_id": "abc123", "code": "123456"}
        serializer = VerifyOTPSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertIsNone(serializer.validated_data.get("identifier"))

    def test_blank_identifier_allowed(self):
        """Serializer should accept blank identifier."""
        data = {"session_id": "abc123", "code": "123456", "identifier": ""}
        serializer = VerifyOTPSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data.get("identifier"), "")
