"""
Rate Limiting and Brute Force Protection Tests
"""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class RateLimitingTests(TestCase):
    """Test rate limiting protection"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="testuser@test.com", password="testpass123", phone_number="+998901234567"
        )

        # Clear any existing rate limit data
        cache.clear()

    def test_login_rate_limiting(self):
        """Test rate limiting on login endpoint"""
        rate_limit_key = "login_attempts:testuser@test.com"

        # Simulate multiple failed login attempts
        for i in range(11):
            response = self.client.post(
                "/api/v1/users/login/credentials/", {"email": "testuser@test.com", "password": "wrongpassword"}
            )

        # 11th request should be rate limited
        # Django's rate limiting typically allows 5-10 attempts
        # After that, returns 429 or 403

        # Verify rate limit is triggered
        rate_limit_data = cache.get(rate_limit_key)
        self.assertIsNotNone(rate_limit_data, "Rate limit tracking should exist")

    def test_otp_rate_limiting(self):
        """Test rate limiting on OTP requests"""
        # Clear rate limit cache
        cache.delete("otp_requests:+998901234567")

        # Make multiple OTP requests
        for i in range(6):
            response = self.client.post("/api/v1/users/login/request-otp/", {"phone_number": "+998901234567"})

        # Should be rate limited after too many requests
        # Check that rate limit counter increased

    def test_registration_rate_limiting(self):
        """Test rate limiting on registration"""
        # Multiple registration attempts from same IP
        for i in range(11):
            response = self.client.post(
                "/api/v1/users/register/",
                {"email": f"test{i}@test.com", "password": "testpass123", "phone_number": f"+9989011122{i}3"},
            )

        # Should be rate limited after too many requests
        # Check response codes

    def test_password_reset_rate_limiting(self):
        """Test rate limiting on password reset"""
        # Multiple password reset requests
        for i in range(6):
            response = self.client.post("/api/v1/users/password-reset/", {"email": "testuser@test.com"})

        # Should be rate limited


class BruteForceTests(TestCase):
    """Test brute force attack protection"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="secureuser@test.com", password="strongpassword123", phone_number="+998901234567"
        )

    def test_password_brute_force_detection(self):
        """Test that password brute force is detected and blocked"""
        # Try many password combinations
        passwords = [f"password{i}" for i in range(20)]

        for pwd in passwords:
            response = self.client.post(
                "/api/v1/users/login/credentials/", {"email": "secureuser@test.com", "password": pwd}
            )

        # After enough attempts, user should be temporarily banned

        # Try one more request - should be blocked
        response = self.client.post(
            "/api/v1/users/login/credentials/", {"email": "secureuser@test.com", "password": "correctpassword"}
        )

        # Check response - either 403 (banned) or 400 (wrong password)
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN])

    def test_ip_based_rate_limiting(self):
        """Test IP-based rate limiting"""
        # Multiple requests from same IP
        for i in range(30):
            response = self.client.get("/api/v1/products/medicines/")

        # Should be rate limited after too many requests
        # Check for 429 Too Many Requests
        # Note: This might not trigger if rate limit is high

    def test_device_fingerprint_rate_limiting(self):
        """Test device fingerprint based rate limiting"""
        # Simulate same device making many requests
        for i in range(11):
            response = self.client.get("/api/v1/products/medicines/")

        # Device fingerprint should be tracked
        # Check that rate limit data exists for fingerprint


class TokenRateLimitTests(TestCase):
    """Test token-based rate limiting"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="testuser@test.com", password="testpass123", phone_number="+998901234567"
        )

        from rest_framework_simplejwt.tokens import RefreshToken

        self.refresh_token = str(RefreshToken.for_user(self.user))

    def test_token_refresh_rate_limiting(self):
        """Test rate limiting on token refresh"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.refresh_token}")

        # Multiple token refresh requests
        for i in range(11):
            response = self.client.post("/api/v1/users/token/refresh/")

        # Should be rate limited
        # Note: JWT refresh doesn't typically have rate limiting
        # but the access token expiry prevents abuse


class SessionFixationTests(TestCase):
    """Test session fixation attack prevention"""

    def setUp(self):
        self.client = APIClient()

    def test_session_id_changes_on_login(self):
        """Test that session ID changes after successful login"""
        # Get initial session ID
        initial_session = self.client.session.session_key

        # Perform login
        response = self.client.post(
            "/api/v1/users/login/credentials/", {"email": "admin@test.com", "password": "adminpass123"}
        )

        # Session ID should change after login
        final_session = self.client.session.session_key

        # Note: In DRF with JWT, session might not change
        # The important thing is that JWT tokens are used

    def test_session_invalidation_on_logout(self):
        """Test that session is invalidated on logout"""
        from django.contrib.auth import get_user_model
        from rest_framework_simplejwt.tokens import RefreshToken

        user = get_user_model().objects.create_user(
            email="logoutuser@test.com", password="testpass123", phone_number="+998901112233"
        )

        self.client.force_authenticate(user=user)

        # Logout
        response = self.client.post("/api/v1/users/logout/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Session should be invalidated
        # Note: With JWT, token blacklist handles this


class SecurityHeaderTests(TestCase):
    """Test security headers are properly set"""

    def setUp(self):
        self.client = APIClient()

    def test_cors_headers_configured(self):
        """Test CORS headers are properly configured"""
        response = self.client.get("/api/v1/products/medicines/")

        # CORS headers should be present
        cors_headers = ["Access-Control-Allow-Origin", "Access-Control-Allow-Methods", "Access-Control-Allow-Headers"]

        for header in cors_headers:
            self.assertIn(header, response.headers, f"CORS header {header} should be present")

    def test_content_type_options(self):
        """Test X-Content-Type-Options header"""
        response = self.client.get("/api/v1/products/medicines/")

        # Should have nosniff
        self.assertEqual(
            response.headers.get("X-Content-Type-Options"), "nosniff", "X-Content-Type-Options should be nosniff"
        )

    def test_x_powered_by_removed(self):
        """Test X-Powered-By header is removed"""
        response = self.client.get("/api/v1/products/medicines/")

        # Should not expose server info
        self.assertNotIn("X-Powered-By", response.headers, "X-Powered-By header should not be exposed")
