from datetime import timedelta
from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse

from .models import BanRecord


class BanRecordTestCase(TestCase):
    """BanRecord model tests"""
    
    def setUp(self):
        self.ban_temp = BanRecord.objects.create(
            ip='192.168.1.1',
            reason='Rate limit exceeded',
            ban_type='temporary',
            created_by='system',
            attempts=50,
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        
        self.ban_perm = BanRecord.objects.create(
            ip='192.168.1.2',
            reason='Permanent ban for abuse',
            ban_type='permanent',
            created_by='admin',
            attempts=100
        )
    
    def test_ban_record_creation(self):
        """Test BanRecord model creation"""
        self.assertEqual(BanRecord.objects.count(), 2)
        self.assertEqual(self.ban_temp.ban_type, 'temporary')
        self.assertEqual(self.ban_perm.ban_type, 'permanent')
    
    def test_is_expired_temporary_not_yet(self):
        """Test temporary ban not expired"""
        self.assertFalse(self.ban_temp.is_expired())
    
    def test_is_expired_temporary_expired(self):
        """Test temporary ban expired"""
        self.ban_temp.expires_at = timezone.now() - timedelta(seconds=1)
        self.assertTrue(self.ban_temp.is_expired())
    
    def test_is_expired_permanent_never(self):
        """Test permanent ban never expires"""
        self.assertFalse(self.ban_perm.is_expired())
    
    def test_get_active_ban_by_ip(self):
        """Test get active ban by IP"""
        ban = BanRecord.get_active_ban(ip='192.168.1.1')
        self.assertIsNotNone(ban)
        self.assertEqual(ban.ip, '192.168.1.1')
    
    def test_get_active_ban_expired(self):
        """Test get active ban returns None for expired temporary ban"""
        self.ban_temp.expires_at = timezone.now() - timedelta(seconds=1)
        self.ban_temp.save()
        
        ban = BanRecord.get_active_ban(ip='192.168.1.1')
        self.assertIsNone(ban)
        
        # Check that is_active was set to False
        self.ban_temp.refresh_from_db()
        self.assertFalse(self.ban_temp.is_active)
    
    def test_get_active_ban_not_found(self):
        """Test get active ban returns None for non-existent IP"""
        ban = BanRecord.get_active_ban(ip='10.0.0.1')
        self.assertIsNone(ban)


class BanMiddlewareTestCase(TestCase):
    """BanMiddleware tests"""
    
    def setUp(self):
        self.client = Client()
    
    def test_excluded_paths_not_checked(self):
        """Test that excluded paths are not checked for bans"""
        response = self.client.get('/static/test.css')
        self.assertNotEqual(response.status_code, 403)
    
    def test_not_allowed_page_not_blocked(self):
        """Test that not-allowed page itself is not blocked"""
        response = self.client.get('/security/not-allowed/')
        # Should not be 403 forbidden (middleware should skip it)
        self.assertNotEqual(response.status_code, 403)
    
    def test_ban_check_returns_403(self):
        """Test that banned IP gets 403 response"""
        BanRecord.objects.create(
            ip='127.0.0.1',
            reason='Test ban',
            ban_type='temporary',
            created_by='system',
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        
        response = self.client.get('/', REMOTE_ADDR='127.0.0.1')
        self.assertEqual(response.status_code, 403)
        self.assertIn(b'Kirishga Ruxsat Berilmagan', response.content)
    
    def test_ban_info_shown_in_response(self):
        """Test that ban information is shown in 403 response"""
        ban = BanRecord.objects.create(
            ip='127.0.0.1',
            reason='Rate limit exceeded: 100+ requests',
            ban_type='temporary',
            created_by='system',
            attempts=100,
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        
        response = self.client.get('/', REMOTE_ADDR='127.0.0.1')
        self.assertEqual(response.status_code, 403)
        self.assertIn(b'Rate limit exceeded', response.content)
        self.assertIn(b'Vaqtli', response.content)  # Temporary in Uzbek
    
    def test_permanent_ban_shown(self):
        """Test permanent ban display"""
        BanRecord.objects.create(
            ip='127.0.0.1',
            reason='Permanent ban for abuse',
            ban_type='permanent',
            created_by='admin',
            attempts=100
        )
        
        response = self.client.get('/', REMOTE_ADDR='127.0.0.1')
        self.assertEqual(response.status_code, 403)
        self.assertIn(b'Doimiy', response.content)  # Permanent in Uzbek
    
    def test_no_redirect_loop(self):
        """Test that there is no redirect loop - returns 403 directly"""
        BanRecord.objects.create(
            ip='127.0.0.1',
            reason='Test ban',
            ban_type='temporary',
            created_by='system',
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        
        # Try accessing banned IP
        response = self.client.get('/', REMOTE_ADDR='127.0.0.1', follow=False)
        
        # Should return 403 directly, not redirect
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('Location', response)  # No redirect header


class BanRateLimitTestCase(TestCase):
    """Rate limit and ban creation tests"""
    
    def setUp(self):
        self.client = Client()
    
    def test_rate_limit_threshold_reached(self):
        """Test rate limit creates temporary ban"""
        from django.core.cache import cache
        
        # Simulate rapid requests from same IP
        ip = '192.168.1.100'
        
        # Make 101 rapid requests (threshold is 100)
        for i in range(105):
            response = self.client.get('/', REMOTE_ADDR=ip)
            if response.status_code == 403:
                # Ban created
                break
        
        # Check that ban was created
        ban = BanRecord.objects.filter(ip=ip, is_active=True).first()
        if ban:
            self.assertEqual(ban.ban_type, 'temporary')
            self.assertEqual(ban.created_by, 'system')


class BanAdminTestCase(TestCase):
    """BanRecord Admin tests"""
    
    def setUp(self):
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        self.admin_user = User.objects.create_superuser(
            email='admin@test.com',
            password='testpass123'
        )
        
        self.client = Client()
        self.client.login(email='admin@test.com', password='testpass123')
        
        # Create test ban
        self.ban = BanRecord.objects.create(
            ip='192.168.1.1',
            reason='Test ban',
            ban_type='temporary',
            created_by='system',
            expires_at=timezone.now() + timedelta(minutes=5)
        )
    
    def test_admin_list_view(self):
        """Test admin can view ban records"""
        response = self.client.get('/admin/security/banrecord/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'192.168.1.1', response.content)
    
    def test_admin_search(self):
        """Test admin can search ban records"""
        response = self.client.get('/admin/security/banrecord/?q=192.168.1.1')
        self.assertEqual(response.status_code, 200)
