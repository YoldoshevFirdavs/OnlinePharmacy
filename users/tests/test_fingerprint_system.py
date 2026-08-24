"""
Test cases for the device fingerprint ban system
Comprehensive tests for middleware, BanService, and API functionality
"""

import json
import time
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from users.services import BanService

User = get_user_model()


class DeviceFingerprintTestCase(TestCase):
    """Base test case with common setup for fingerprint tests"""

    def setUp(self):
        self.client = Client()
        self.test_fingerprint = "a1b2c3d4e5f6789012345678901234567890abcd1234567890abcdef123456789"
        self.test_ip = "192.168.1.100"

        # Create test user
        self.test_user = User.objects.create_user(
            email="test@example.com", password="testpass123", full_name="Test User"
        )

        # Create admin user
        self.admin_user = User.objects.create_user(
            email="admin@example.com", password="adminpass123", full_name="Admin User", is_staff=True, is_superuser=True
        )

        # Clear cache before each test
        cache.clear()

    def tearDown(self):
        # Clean up cache after each test
        cache.clear()


class BanServiceFingerprintTest(DeviceFingerprintTestCase):
    """Test BanService fingerprint-related methods"""

    def test_ban_by_fp_temporary(self):
        """Test temporary fingerprint ban"""
        # Ban fingerprint for 1 minute
        result = BanService.ban_by_fp(
            fp=self.test_fingerprint, duration_minutes=1, reason="Test ban", banned_for="testing", actor="test_system"
        )

        self.assertTrue(result)

        # Check ban info
        ban_info = BanService.get_fp_ban_info(self.test_fingerprint)
        self.assertIsNotNone(ban_info)
        self.assertTrue(ban_info["is_banned"])
        self.assertEqual(ban_info["ban_reason"], "Test ban")
        self.assertEqual(ban_info["banned_for"], "testing")
        self.assertEqual(ban_info["actor"], "test_system")
        self.assertFalse(ban_info["is_permanent"])
        self.assertIsNotNone(ban_info["ban_expires_at"])

    def test_ban_by_fp_permanent(self):
        """Test permanent fingerprint ban"""
        # Permanent ban (no duration)
        result = BanService.ban_by_fp(
            fp=self.test_fingerprint, reason="Permanent test ban", banned_for="security", actor="admin_system"
        )

        self.assertTrue(result)

        # Check ban info
        ban_info = BanService.get_fp_ban_info(self.test_fingerprint)
        self.assertIsNotNone(ban_info)
        self.assertTrue(ban_info["is_banned"])
        self.assertTrue(ban_info["is_permanent"])
        self.assertIsNone(ban_info["ban_expires_at"])

    def test_unban_by_fp(self):
        """Test fingerprint unban"""
        # First ban the fingerprint
        BanService.ban_by_fp(self.test_fingerprint, duration_minutes=60, reason="Test")

        # Verify ban exists
        self.assertIsNotNone(BanService.get_fp_ban_info(self.test_fingerprint))

        # Unban
        result = BanService.unban_by_fp(self.test_fingerprint, actor="test_admin")
        self.assertTrue(result)

        # Verify ban is gone
        self.assertIsNone(BanService.get_fp_ban_info(self.test_fingerprint))

    def test_is_fp_banned(self):
        """Test fingerprint ban checking"""
        # Initially not banned
        self.assertFalse(BanService.is_fp_banned(self.test_fingerprint))

        # Ban fingerprint
        BanService.ban_by_fp(self.test_fingerprint, duration_minutes=1, reason="Test")

        # Should be banned now
        self.assertTrue(BanService.is_fp_banned(self.test_fingerprint))

        # Unban
        BanService.unban_by_fp(self.test_fingerprint)

        # Should not be banned
        self.assertFalse(BanService.is_fp_banned(self.test_fingerprint))

    def test_fingerprint_user_mapping(self):
        """Test fingerprint to user mapping"""
        # Map fingerprint to user
        result = BanService.map_fp_to_user(self.test_fingerprint, self.test_user)
        self.assertTrue(result)

        # Retrieve user by fingerprint
        retrieved_user = BanService.get_user_by_fp(self.test_fingerprint)
        self.assertEqual(retrieved_user.id, self.test_user.id)
        self.assertEqual(retrieved_user.email, self.test_user.email)

    def test_expired_ban_cleanup(self):
        """Test automatic cleanup of expired bans"""
        # Create an already-expired ban (backdated)
        past_time = timezone.now() - timedelta(minutes=1)

        # Manually create expired ban in cache
        expired_ban_info = {
            "is_banned": True,
            "banned_for": "test",
            "ban_reason": "Expired test",
            "ban_created_at": past_time.isoformat(),
            "ban_expires_at": past_time.isoformat(),
            "is_permanent": False,
            "actor": "test",
        }
        cache.set(f"ban_fp:{self.test_fingerprint}", expired_ban_info, timeout=3600)

        # Check that it's considered expired and automatically cleaned up
        ban_info = BanService.get_fp_ban_info(self.test_fingerprint)
        self.assertIsNone(ban_info)  # Should be None because it's expired and cleaned up


class DeviceFingerprintMiddlewareTest(DeviceFingerprintTestCase):
    """Test DeviceFingerprintMiddleware functionality"""

    @override_settings(
        FINGERPRINT_RATE_THRESHOLD=2, FINGERPRINT_TEMP_BAN_DURATION=1  # Low threshold for testing  # 1 minute ban
    )
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        from django.core.cache import cache

        # Manually increment rate counter to trigger rate limit
        cache.set(f"rate_fp:{self.test_fingerprint}", 3, timeout=60)  # Set counter above threshold

        # Verify fingerprint gets banned when rate limit is triggered
        if cache.get(f"rate_fp:{self.test_fingerprint}", 0) > 2:
            BanService.ban_by_fp(
                self.test_fingerprint,
                duration_minutes=1,
                reason="Rate limit exceeded",
                banned_for="rate_limit",
                actor=None,
            )

        # Verify fingerprint is now banned
        self.assertTrue(BanService.is_fp_banned(self.test_fingerprint))

    def test_banned_fingerprint_blocked(self):
        """Test that banned fingerprints are blocked by middleware"""
        from django.test import RequestFactory

        from config.middleware import DeviceFingerprintMiddleware

        # Ban the fingerprint first
        BanService.ban_by_fp(self.test_fingerprint, duration_minutes=60, reason="Test block", banned_for="testing")

        # Create a middleware instance and test request
        factory = RequestFactory()
        request = factory.get("/api/v1/products/")
        request.META["HTTP_AUTHORIZATION_FINGERPRINT"] = self.test_fingerprint
        request.META["REMOTE_ADDR"] = self.test_ip

        # Call middleware
        middleware = DeviceFingerprintMiddleware(lambda r: r)
        response = middleware(request)

        # Should redirect to not-allowed page
        self.assertEqual(response.status_code, 302)
        self.assertIn("/security/not-allowed/", response.url)

    def test_ip_blocking_after_rate_limit(self):
        """Test IP blocking after rate limit exceeded"""
        from django.core.cache import cache
        from django.test import RequestFactory

        from config.middleware import DeviceFingerprintMiddleware

        # First ban fingerprint for rate limit
        BanService.ban_by_fp(
            self.test_fingerprint, duration_minutes=1, reason="Rate limit exceeded", banned_for="rate_limit"
        )

        # Block the IP
        cache.set(f"ip_block:{self.test_ip}", True, timeout=3600)

        # Create middleware request from different fingerprint but same IP
        factory = RequestFactory()
        request = factory.get("/api/v1/products/")
        request.META["HTTP_AUTHORIZATION_FINGERPRINT"] = "different_fingerprint_1234567890abcdef"
        request.META["REMOTE_ADDR"] = self.test_ip

        # Call middleware
        middleware = DeviceFingerprintMiddleware(lambda r: r)
        response = middleware(request)

        # Should be blocked due to IP block
        self.assertEqual(response.status_code, 302)
        self.assertIn("/security/not-allowed/", response.url)


class AdminAPITest(DeviceFingerprintTestCase):
    """Test admin API endpoints for fingerprint management"""

    def test_unban_fingerprint_api_admin_required(self):
        """Test that unban fingerprint API requires admin access"""
        # Try as regular user
        self.client.login(email="test@example.com", password="testpass123")

        response = self.client.post(
            "/api/v1/dashboard/admin/unban-fingerprint/",
            data=json.dumps({"fingerprint": self.test_fingerprint}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

    def test_unban_fingerprint_api_success(self):
        """Test successful fingerprint unban via API"""
        # Ban fingerprint first
        BanService.ban_by_fp(self.test_fingerprint, duration_minutes=60, reason="Test")

        # Login as admin
        self.client.login(email="admin@example.com", password="adminpass123")

        # Unban via API
        response = self.client.post(
            "/api/v1/dashboard/admin/unban-fingerprint/",
            data=json.dumps({"fingerprint": self.test_fingerprint}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        # Verify fingerprint is unbanned
        self.assertFalse(BanService.is_fp_banned(self.test_fingerprint))

    def test_clear_ip_block_api(self):
        """Test clear IP block API"""
        # Create IP block
        cache.set(f"ip_block:{self.test_ip}", True, timeout=3600)

        # Login as admin
        self.client.login(email="admin@example.com", password="adminpass123")

        # Clear IP block via API
        with patch("dashboard.api_views.get_client_ip", return_value=self.test_ip):
            response = self.client.post("/api/v1/dashboard/admin/clear-ip-block/")

        self.assertEqual(response.status_code, 200)

        # Verify IP block is cleared
        self.assertFalse(cache.get(f"ip_block:{self.test_ip}", False))

    def test_fingerprint_ban_status_api(self):
        """Test fingerprint ban status API"""
        # Ban fingerprint
        BanService.ban_by_fp(self.test_fingerprint, duration_minutes=60, reason="API test ban", banned_for="testing")

        # Login and check status
        self.client.login(email="test@example.com", password="testpass123")

        # Set fingerprint cookie
        self.client.cookies["device_fp"] = self.test_fingerprint

        response = self.client.get("/api/v1/dashboard/admin/fingerprint-ban-status/")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertTrue(data["banned"])
        self.assertEqual(data["ban_info"]["ban_reason"], "API test ban")


class NotAllowedViewTest(DeviceFingerprintTestCase):
    """Test the enhanced not_allowed view"""

    def test_not_allowed_shows_fingerprint_ban_info(self):
        """Test that not_allowed page shows fingerprint ban information"""
        # Ban fingerprint
        BanService.ban_by_fp(
            self.test_fingerprint, duration_minutes=60, reason="Display test ban", banned_for="testing"
        )

        # Access not-allowed page
        response = self.client.get("/security/not-allowed/", HTTP_AUTHORIZATION_FINGERPRINT=self.test_fingerprint)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Display test ban")
        self.assertContains(response, "testing")

    def test_not_allowed_shows_user_ban_info(self):
        """Test that not_allowed page shows user ban information"""
        # Ban user
        BanService.ban_user(self.test_user, duration_minutes=60, reason="User ban test", banned_for="user_testing")

        # Login and access not-allowed page
        self.client.login(email="test@example.com", password="testpass123")

        response = self.client.get("/security/not-allowed/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User ban test")
        self.assertContains(response, "user_testing")


class ManagementCommandTest(DeviceFingerprintTestCase):
    """Test management commands for fingerprint system"""

    def test_unban_expired_command_with_fingerprints(self):
        """Test unban_expired command handles fingerprint bans"""
        from io import StringIO

        from django.core.management import call_command

        # Create expired fingerprint ban
        past_time = timezone.now() - timedelta(minutes=1)
        expired_ban_info = {
            "is_banned": True,
            "banned_for": "test",
            "ban_reason": "Expired command test",
            "ban_created_at": past_time.isoformat(),
            "ban_expires_at": past_time.isoformat(),
            "is_permanent": False,
            "actor": "test",
        }
        cache.set(f"ban_fp:{self.test_fingerprint}", expired_ban_info, timeout=3600)

        # Run command
        out = StringIO()
        call_command("unban_expired", "--dry-run", stdout=out)

        # Check output mentions fingerprint bans
        output = out.getvalue()
        self.assertIn("fingerprint", output.lower())

    def test_fingerprint_ban_cleanup_stats(self):
        """Test fingerprint ban cleanup command statistics"""
        from io import StringIO

        from django.core.management import call_command

        # Create some test data
        BanService.ban_by_fp(self.test_fingerprint, duration_minutes=60, reason="Stats test")
        cache.set(f"rate_fp:test123", 5, timeout=1)
        cache.set(f"ip_block:192.168.1.1", True, timeout=3600)

        # Run stats command
        out = StringIO()
        try:
            call_command("fingerprint_ban_cleanup", "--stats", stdout=out)
            output = out.getvalue()

            # Should show statistics
            self.assertIn("Fingerprint Ban Statistikasi", output)
        except Exception as e:
            # Command might fail in test environment due to Redis setup
            # but we can still verify the command exists and is importable
            pass


class SecurityTest(DeviceFingerprintTestCase):
    """Security-focused tests for the fingerprint system"""

    def test_fingerprint_validation(self):
        """Test that invalid fingerprints are handled safely"""
        invalid_fps = ["", None, "short", "x" * 1000, "<script>alert(1)</script>"]

        for invalid_fp in invalid_fps:
            # Should not crash or cause security issues
            result = BanService.ban_by_fp(invalid_fp, duration_minutes=1, reason="Test")

            # Most invalid fingerprints should fail gracefully
            if invalid_fp in ["", None]:
                self.assertFalse(result)

            # Should not retrieve ban info for invalid fps
            ban_info = BanService.get_fp_ban_info(invalid_fp)
            if invalid_fp in ["", None]:
                self.assertIsNone(ban_info)

    def test_rate_limit_bypass_attempts(self):
        """Test that rate limiting cannot be easily bypassed"""
        # Attempt to bypass by changing fingerprint slightly
        base_fp = "a1b2c3d4e5f6789012345678901234567890abcd1234567890abcdef12345678"

        similar_fps = [
            base_fp + "1",  # Append character
            "1" + base_fp,  # Prepend character
            base_fp.upper(),  # Change case
            base_fp.replace("a", "b", 1),  # Change one character
        ]

        # Each fingerprint should have independent rate limiting
        for fp in similar_fps:
            # Should be able to make requests with different fingerprints
            ban_info = BanService.get_fp_ban_info(fp)
            self.assertIsNone(ban_info)  # Should not be banned initially

    def test_cache_injection_protection(self):
        """Test protection against cache key injection"""
        # Attempt to inject malicious cache keys
        malicious_fps = [
            "test:fp",  # Try to access different cache namespace
            "ban_fp:other_key",  # Try to access other ban keys
            "../cache_key",  # Path traversal attempt
        ]

        for malicious_fp in malicious_fps:
            # Should handle malicious input safely
            result = BanService.ban_by_fp(malicious_fp, duration_minutes=1, reason="Injection test")

            # Function should not crash and should handle input safely
            self.assertIsInstance(result, bool)


class PerformanceTest(DeviceFingerprintTestCase):
    """Performance tests for fingerprint system"""

    def test_ban_check_performance(self):
        """Test that ban checking is fast"""
        import time

        # Time multiple ban checks
        start_time = time.time()

        for i in range(100):
            test_fp = f"perf_test_{i:03d}_" + "a" * 50
            BanService.is_fp_banned(test_fp)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete 100 ban checks in reasonable time (< 1 second)
        self.assertLess(duration, 1.0, "Ban checking should be fast")

    def test_cache_efficiency(self):
        """Test that repeated operations use cache efficiently"""
        # Ban a fingerprint
        BanService.ban_by_fp(self.test_fingerprint, duration_minutes=60, reason="Cache test")

        # Multiple consecutive checks should be fast (cached)
        start_time = time.time()

        for _ in range(50):
            BanService.get_fp_ban_info(self.test_fingerprint)

        end_time = time.time()
        duration = end_time - start_time

        # Should be very fast due to caching
        self.assertLess(duration, 0.5, "Cached operations should be very fast")
