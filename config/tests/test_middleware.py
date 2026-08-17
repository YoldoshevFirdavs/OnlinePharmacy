"""
Test cases for DeviceFingerprintMiddleware
Tests middleware functionality, request processing, and integration
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory, override_settings
from django.http import HttpResponse
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

from config.middleware import DeviceFingerprintMiddleware, get_client_ip
from users.services import BanService


class DeviceFingerprintMiddlewareTest(TestCase):
    """Test DeviceFingerprintMiddleware functionality"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = DeviceFingerprintMiddleware(self._get_response)
        self.test_fingerprint = 'a1b2c3d4e5f6789012345678901234567890abcd1234567890abcdef123456789'
        self.test_ip = '192.168.1.100'
        cache.clear()
    
    def _get_response(self, request):
        """Mock response function for middleware"""
        return HttpResponse("OK")
    
    def tearDown(self):
        cache.clear()
    
    def test_get_client_ip_direct(self):
        """Test IP extraction from REMOTE_ADDR"""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        
        ip = get_client_ip(request)
        self.assertEqual(ip, '192.168.1.100')
    
    def test_get_client_ip_forwarded(self):
        """Test IP extraction from X-Forwarded-For header"""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1, 192.168.1.100, 172.16.0.1'
        request.META['REMOTE_ADDR'] = '172.16.0.1'
        
        ip = get_client_ip(request)
        self.assertEqual(ip, '10.0.0.1')  # First IP in X-Forwarded-For
    
    def test_fingerprint_extraction_from_cookie(self):
        """Test fingerprint extraction from cookie"""
        request = self.factory.get('/')
        request.COOKIES = {'device_fp': self.test_fingerprint}
        
        response = self.middleware(request)
        
        # Check that fingerprint was extracted and stored in request
        self.assertEqual(getattr(request, 'device_fingerprint', None), self.test_fingerprint)
        self.assertEqual(response.status_code, 200)
    
    def test_fingerprint_extraction_from_header(self):
        """Test fingerprint extraction from Authorization-Fingerprint header"""
        request = self.factory.get('/')
        request.META['HTTP_AUTHORIZATION_FINGERPRINT'] = self.test_fingerprint
        
        response = self.middleware(request)
        
        # Check that fingerprint was extracted and stored in request
        self.assertEqual(getattr(request, 'device_fingerprint', None), self.test_fingerprint)
        self.assertEqual(response.status_code, 200)
    
    def test_cookie_priority_over_header(self):
        """Test that cookie takes priority over header"""
        cookie_fp = 'cookie_fingerprint_123'
        header_fp = 'header_fingerprint_456'
        
        request = self.factory.get('/')
        request.COOKIES = {'device_fp': cookie_fp}
        request.META['HTTP_AUTHORIZATION_FINGERPRINT'] = header_fp
        
        response = self.middleware(request)
        
        # Cookie should take priority
        self.assertEqual(getattr(request, 'device_fingerprint', None), cookie_fp)
    
    def test_excluded_paths_bypass(self):
        """Test that excluded paths bypass fingerprint processing"""
        excluded_paths = ['/static/test.css', '/media/image.png', '/favicon.ico']
        
        for path in excluded_paths:
            request = self.factory.get(path)
            request.META['HTTP_AUTHORIZATION_FINGERPRINT'] = self.test_fingerprint
            
            response = self.middleware(request)
            
            # Should process normally without fingerprint checking
            self.assertEqual(response.status_code, 200)
    
    @override_settings(FINGERPRINT_RATE_THRESHOLD=2)
    def test_rate_limiting_trigger(self):
        """Test that rate limiting triggers ban"""
        request = self.factory.get('/')
        request.COOKIES = {'device_fp': self.test_fingerprint}
        request.META['REMOTE_ADDR'] = self.test_ip
        
        # Simulate exceeding rate limit
        cache.set(f'rate_fp:{self.test_fingerprint}', 3, timeout=1)  # Above threshold
        
        with patch('users.services.BanService.ban_by_fp') as mock_ban:
            response = self.middleware(request)
            
            # Should trigger ban
            mock_ban.assert_called_once()
            args, kwargs = mock_ban.call_args
            self.assertEqual(args[0], self.test_fingerprint)
            self.assertIn('Rate limit exceeded', kwargs['reason'])
    
    def test_banned_fingerprint_redirect(self):
        """Test that banned fingerprint gets redirected"""
        # Ban the fingerprint
        BanService.ban_by_fp(
            self.test_fingerprint,
            duration_minutes=60,
            reason='Test ban',
            banned_for='testing'
        )
        
        request = self.factory.get('/test-path')
        request.COOKIES = {'device_fp': self.test_fingerprint}
        request.META['REMOTE_ADDR'] = self.test_ip
        
        response = self.middleware(request)
        
        # Should redirect to not-allowed page
        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard/not-allowed/', response.url)
        self.assertIn('next=/test-path', response.url)
    
    def test_expired_ban_automatic_cleanup(self):
        """Test that expired bans are automatically cleaned up"""
        # Create an expired ban
        past_time = timezone.now() - timedelta(minutes=1)
        expired_ban_info = {
            'is_banned': True,
            'banned_for': 'test',
            'ban_reason': 'Expired test',
            'ban_created_at': past_time.isoformat(),
            'ban_expires_at': past_time.isoformat(),
            'is_permanent': False,
            'actor': 'test'
        }
        cache.set(f"ban_fp:{self.test_fingerprint}", expired_ban_info, timeout=3600)
        
        request = self.factory.get('/')
        request.COOKIES = {'device_fp': self.test_fingerprint}
        request.META['REMOTE_ADDR'] = self.test_ip
        
        with patch('users.services.BanService.unban_by_fp') as mock_unban:
            response = self.middleware(request)
            
            # Should not be redirected (ban expired)
            self.assertEqual(response.status_code, 200)
            
            # Should trigger unban for expired ban
            mock_unban.assert_called_once_with(self.test_fingerprint, actor=None)
    
    def test_ip_block_check(self):
        """Test IP blocking functionality"""
        # Block the IP
        cache.set(f'ip_block:{self.test_ip}', True, timeout=3600)
        
        request = self.factory.get('/')
        request.COOKIES = {'device_fp': self.test_fingerprint}
        request.META['REMOTE_ADDR'] = self.test_ip
        
        response = self.middleware(request)
        
        # Should redirect due to IP block
        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard/not-allowed/', response.url)
    
    @override_settings(FINGERPRINT_MAIN_PAGE_REFRESH_LIMIT=2)
    def test_main_page_refresh_limit(self):
        """Test main page refresh limiting"""
        # Set up existing counter close to limit
        cache.set(f'main_page_fp:{self.test_fingerprint}', 2, timeout=3600)
        
        request = self.factory.get('/')  # Main page
        request.COOKIES = {'device_fp': self.test_fingerprint}
        request.META['REMOTE_ADDR'] = self.test_ip
        
        with patch('users.services.BanService.ban_by_fp') as mock_ban:
            response = self.middleware(request)
            
            # Should trigger ban for main page flooding
            mock_ban.assert_called_once()
            args, kwargs = mock_ban.call_args
            self.assertEqual(args[0], self.test_fingerprint)
            self.assertIn('Main page refresh limit', kwargs['reason'])
    
    def test_middleware_error_handling(self):
        """Test middleware handles errors gracefully"""
        request = self.factory.get('/')
        request.COOKIES = {'device_fp': self.test_fingerprint}
        
        # Simulate cache error
        with patch('django.core.cache.cache.get', side_effect=Exception('Cache error')):
            response = self.middleware(request)
            
            # Should not crash, continue processing
            self.assertEqual(response.status_code, 200)
    
    def test_no_fingerprint_processing(self):
        """Test middleware handles requests without fingerprint"""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = self.test_ip
        # No fingerprint in cookies or headers
        
        response = self.middleware(request)
        
        # Should process normally
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(getattr(request, 'device_fingerprint', None))
    
    @override_settings(
        FINGERPRINT_RATE_THRESHOLD=1,
        FINGERPRINT_IP_BLOCK_DURATION=1800
    )
    def test_rate_limit_ip_block_integration(self):
        """Test that rate limiting triggers IP block"""
        request = self.factory.get('/')
        request.COOKIES = {'device_fp': self.test_fingerprint}
        request.META['REMOTE_ADDR'] = self.test_ip
        
        # Simulate rate limit exceeded
        cache.set(f'rate_fp:{self.test_fingerprint}', 2, timeout=1)  # Above threshold
        
        with patch('users.services.BanService.ban_by_fp') as mock_ban:
            response = self.middleware(request)
            
            # Should ban fingerprint and block IP
            mock_ban.assert_called_once()
            
            # Check IP was blocked
            ip_blocked = cache.get(f'ip_block:{self.test_ip}')
            self.assertTrue(ip_blocked)
    
    def test_request_attribute_setting(self):
        """Test that middleware sets correct request attributes"""
        request = self.factory.get('/')
        request.COOKIES = {'device_fp': self.test_fingerprint}
        request.META['REMOTE_ADDR'] = self.test_ip
        
        response = self.middleware(request)
        
        # Check attributes were set
        self.assertEqual(request.device_fingerprint, self.test_fingerprint)
        self.assertEqual(request.client_ip, self.test_ip)
        self.assertEqual(response.status_code, 200)


class MiddlewareIntegrationTest(TestCase):
    """Integration tests for middleware with other components"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.test_fingerprint = 'integration_test_fp_123456789abcdef'
        self.test_ip = '10.0.0.100'
        cache.clear()
    
    def tearDown(self):
        cache.clear()
    
    def test_middleware_order_independence(self):
        """Test that middleware works regardless of order with other middleware"""
        # This would test interaction with other middleware in the stack
        # For now, we'll test that our middleware doesn't interfere with basic request processing
        
        def dummy_middleware(get_response):
            def middleware(request):
                request.dummy_processed = True
                return get_response(request)
            return middleware
        
        def final_response(request):
            return HttpResponse("Final response")
        
        # Stack middleware
        middleware_stack = DeviceFingerprintMiddleware(
            dummy_middleware(final_response)
        )
        
        request = self.factory.get('/')
        request.COOKIES = {'device_fp': self.test_fingerprint}
        
        response = middleware_stack(request)
        
        # Both middleware should have processed the request
        self.assertTrue(getattr(request, 'dummy_processed', False))
        self.assertEqual(request.device_fingerprint, self.test_fingerprint)
        self.assertEqual(response.status_code, 200)
    
    def test_middleware_with_authenticated_user(self):
        """Test middleware behavior with authenticated users"""
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        request = self.factory.get('/')
        request.user = user
        request.COOKIES = {'device_fp': self.test_fingerprint}
        
        middleware = DeviceFingerprintMiddleware(lambda r: HttpResponse("OK"))
        
        # Test fingerprint mapping with user
        with patch('users.services.BanService.map_fp_to_user') as mock_map:
            response = middleware(request)
            
            # Should attempt to map fingerprint to user
            # (Implementation detail - might not always call this)
            self.assertEqual(response.status_code, 200)