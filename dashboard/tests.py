from django.test import TestCase
from django.urls import reverse, NoReverseMatch
from django.contrib.auth import get_user_model

User = get_user_model()

class DashboardURLReverseTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            # username='testadmin', # Removed username as CustomUser does not have this field
            email='testadmin@example.com',
            password='testpassword',
            is_staff=True
        )
        self.client.login(email='testadmin@example.com', password='testpassword') # Changed login to use email

    def test_admin_settings_reverse(self):
        # Test that 'dashboard:admin_settings' resolves correctly
        url = reverse('dashboard:admin_settings')
        self.assertEqual(url, '/dashboard/settings/')

    def test_admin_account_reverse(self):
        # Test that 'dashboard:admin_account' resolves correctly
        url = reverse('dashboard:admin_account')
        self.assertEqual(url, '/dashboard/account/')

    def test_auth_reverse_for_logout(self):
        # Test that 'dashboard:auth' resolves correctly to logout_page
        url = reverse('dashboard:auth')
        self.assertEqual(url, '/dashboard/auth/')

    def test_admin_dashboard_access(self):
        # Test that the admin dashboard page can be accessed
        response = self.client.get(reverse('dashboard:admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard Overview") # Check for content from admin.html
