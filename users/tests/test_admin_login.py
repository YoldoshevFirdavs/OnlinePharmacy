from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, date
from unittest.mock import patch, MagicMock

from users.models import CustomUser, AdminLoginToken, AdminLoginAttempt, Deliverer, SalaryRecord, PayrollStats, OnboardToken
from rest_framework import status
from django.conf import settings

class AdminLoginFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.email = "admin@example.com"
        self.full_name = "Test Admin"
        self.password = "testpassword123" # Not used in passwordless flow, but good practice for user creation
        self.user = CustomUser.objects.create_user(email=self.email, full_name=self.full_name, is_staff=True, is_active=True)
        self.request_login_url = reverse('admin_request_login')
        self.verify_login_url = reverse('admin_verify_login')
        self.check_admin_url = '/api/v1/users/admin/check/' # Not using reverse as it's a direct path for frontend
        self.confirm_login_url = reverse('admin_confirm_login')

    @patch('users.tasks.send_admin_login_email.delay')
    def test_request_creates_token_and_sends_email(self, mock_send_email_delay):
        response = self.client.post(self.request_login_url, {'email': self.email, 'full_name': self.full_name}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()['ok'])
        self.assertIn('message', response.json())

        self.assertTrue(AdminLoginToken.objects.filter(user=self.user).exists())
        mock_send_email_delay.assert_called_once()

        # Test with a new email, should create a new user and send email
        new_email = "newadmin@example.com"
        new_name = "New Admin"
        response = self.client.post(self.request_login_url, {'email': new_email, 'full_name': new_name}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(CustomUser.objects.filter(email=new_email).exists())
        self.assertEqual(mock_send_email_delay.call_count, 2)

    def test_request_login_rate_limiting_and_blocking(self):
        # Simulate multiple failed attempts
        for i in range(AdminLoginAttempt.MAX_ATTEMPTS):
            response = self.client.post(self.request_login_url, {'email': 'nonexistent@example.com'}, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK) # Still returns 200, but increments attempt

        # Next attempt should block
        response = self.client.post(self.request_login_url, {'email': 'nonexistent@example.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('Too many attempts. Temporarily blocked.', response.json()['detail'])

        # Check if blocked_until is set
        attempt = AdminLoginAttempt.objects.get(fingerprint=self.client.session.session_key) # Fingerprint is based on session_key in test client
        self.assertIsNotNone(attempt.blocked_until)
        self.assertTrue(attempt.blocked_until > timezone.now())

        # Attempt while blocked
        response = self.client.post(self.request_login_url, {'email': self.email}, format='json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_verify_redirects_to_check(self):
        token = AdminLoginToken.objects.create(user=self.user, token="validtoken", expires_at=timezone.now() + timedelta(minutes=15))
        response = self.client.get(f"{self.verify_login_url}?token={token.token}")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND) # Redirect
        self.assertIn(f"/admin/check/?token={token.token}", response.url)

    def test_verify_invalid_token(self):
        response = self.client.get(f"{self.verify_login_url}?token=invalid")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid or used token', response.json()['detail'])

    def test_verify_expired_token(self):
        token = AdminLoginToken.objects.create(user=self.user, token="expiredtoken", expires_at=timezone.now() - timedelta(minutes=1))
        response = self.client.get(f"{self.verify_login_url}?token={token.token}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Token expired', response.json()['detail'])

    def test_check_returns_user_info(self):
        token = AdminLoginToken.objects.create(user=self.user, token="checktoken", expires_at=timezone.now() + timedelta(minutes=15))
        response = self.client.get(f"{self.check_admin_url}?token={token.token}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['email'], self.email)
        self.assertEqual(response.json()['full_name'], self.full_name)

    def test_check_blocked_fingerprint(self):
        # Block the fingerprint
        fp = self.client.session.session_key # Test client uses session_key as fingerprint
        AdminLoginAttempt.objects.create(fingerprint=fp, blocked_until=timezone.now() + timedelta(minutes=30))
        token = AdminLoginToken.objects.create(user=self.user, token="blockedtoken", expires_at=timezone.now() + timedelta(minutes=15))
        response = self.client.get(f"{self.check_admin_url}?token={token.token}")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Blocked', response.json()['detail'])

    def test_confirm_logs_in_and_redirects(self):
        token = AdminLoginToken.objects.create(user=self.user, token="confirmtoken", expires_at=timezone.now() + timedelta(minutes=15))
        response = self.client.post(self.confirm_login_url, {'token': token.token, 'full_name': 'Updated Name', 'phone_number': '+998901234567'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()['ok'])
        self.assertEqual(response.json()['next'], '/dashboard/admin')

        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, 'Updated Name')
        self.assertEqual(self.user.phone_number, '+998901234567')
        self.assertTrue(AdminLoginToken.objects.get(token=token.token).used)
        self.assertTrue(self.client.session.get('_auth_user_id')) # Check if user is logged in

    def test_confirm_invalid_token(self):
        response = self.client.post(self.confirm_login_url, {'token': 'invalid', 'full_name': 'Test'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid or used token', response.json()['detail'])

    def test_confirm_expired_token(self):
        token = AdminLoginToken.objects.create(user=self.user, token="expiredconfirm", expires_at=timezone.now() - timedelta(minutes=1))
        response = self.client.post(self.confirm_login_url, {'token': token.token, 'full_name': 'Test'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Token expired', response.json()['detail'])

    def test_confirm_blocked_fingerprint(self):
        # Block the fingerprint
        fp = self.client.session.session_key
        AdminLoginAttempt.objects.create(fingerprint=fp, blocked_until=timezone.now() + timedelta(minutes=30))
        token = AdminLoginToken.objects.create(user=self.user, token="blockedconfirm", expires_at=timezone.now() + timedelta(minutes=15))
        response = self.client.post(self.confirm_login_url, {'token': token.token, 'full_name': 'Test'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Blocked', response.json()['detail'])

    def test_block_after_many_attempts_on_confirm(self):
        # Simulate multiple failed attempts on confirm
        token = AdminLoginToken.objects.create(user=self.user, token="temp_token", expires_at=timezone.now() + timedelta(minutes=15))
        for i in range(AdminLoginAttempt.MAX_ATTEMPTS):
            # Use a non-existent token to simulate invalid attempts
            response = self.client.post(self.confirm_login_url, {'token': 'wrongtoken', 'full_name': 'Test'}, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Next attempt should block
        response = self.client.post(self.confirm_login_url, {'token': 'wrongtoken', 'full_name': 'Test'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # Should be 403 because it's blocked
        self.assertIn('Blocked', response.json()['detail'])

        # Check if blocked_until is set
        fp = self.client.session.session_key
        attempt = AdminLoginAttempt.objects.get(fingerprint=fp)
        self.assertIsNotNone(attempt.blocked_until)
        self.assertTrue(attempt.blocked_until > timezone.now())