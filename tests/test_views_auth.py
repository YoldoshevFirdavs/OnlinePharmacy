from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from users.otp_service import get_session_meta, get_otp_hash, OtpHash, store_otp_hash, \
    check_rate_limit  # Updated import
from django.conf import settings
import json

User = get_user_model()


class AuthAPITests(APITestCase):

    def setUp(self):
        self.email = "test@example.com"
        self.password = "StrongPassword123"
        self.user = User.objects.create_user(email=self.email, password=self.password)
        self.login_email_url = reverse('login-email')
        self.verify_otp_url = reverse('verify-otp')

    @patch('custom_auth.tasks.send_otp_email.delay')
    def test_email_login_sends_otp_and_creates_session(self, mock_send_otp_email_delay):
        """
        Ensure we can request an OTP via email and a session is created.
        """
        data = {'email': self.email}
        response = self.client.post(self.login_email_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('session_id', response.data)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'], 'Email queued')

        session_id = response.data['session_id']
        session_meta = get_session_meta(session_id)  # Changed from get_otp_session
        self.assertIsNotNone(session_meta)
        self.assertEqual(session_meta['user_id'], self.user.id)
        self.assertEqual(session_meta['identifier'], self.email)
        self.assertEqual(session_meta['purpose'], 'email')

        # Check if OTP was stored
        otp_hash_obj = get_otp_hash(self.email)
        self.assertIsNotNone(otp_hash_obj)
        self.assertIsInstance(otp_hash_obj, OtpHash)

        # Check if email task was called
        mock_send_otp_email_delay.assert_called_once()
        args, kwargs = mock_send_otp_email_delay.call_args
        self.assertEqual(args[0], self.email)
        self.assertRegex(args[1], r'^\d{6}$')  # OTP is a 6-digit number

        # Check if OTP is returned in DEBUG mode
        if settings.DEBUG:
            self.assertIn('otp_code', response.data)
            self.assertRegex(response.data['otp_code'], r'^\d{6}$')
        else:
            self.assertNotIn('otp_code', response.data)

    @patch('custom_auth.tasks.send_otp_email.delay')
    def test_email_login_creates_user_if_not_exists(self, mock_send_otp_email_delay):
        """
        Ensure a new user is created if the email does not exist.
        """
        new_email = "newuser@example.com"
        data = {'email': new_email}
        response = self.client.post(self.login_email_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('session_id', response.data)
        self.assertTrue(User.objects.filter(email=new_email).exists())
        new_user = User.objects.get(email=new_email)
        self.assertFalse(new_user.is_verified)  # New user should not be verified yet

        session_id = response.data['session_id']
        session_meta = get_session_meta(session_id)  # Changed from get_otp_session
        self.assertEqual(session_meta['user_id'], new_user.id)

    def test_verify_otp_success(self):
        """
        Ensure OTP verification works with a valid code and session.
        """
        # Simulate OTP request
        data = {'email': self.email}
        response = self.client.post(self.login_email_url, data, format='json')
        session_id = response.data['session_id']

        # Manually get the OTP (only possible in test/debug)
        otp_hash_obj = get_otp_hash(self.email)
        # In a real scenario, the OTP would be sent to the user's email.
        # For testing, we need to know the OTP that was generated.
        # Since we're using a mocked send_otp_email, we can't easily get it from there.
        # The `EmailLoginView` returns `otp_code` in DEBUG mode, so we'll use that.
        otp_code = response.data['otp_code'] if settings.DEBUG else '123456'  # Fallback for non-DEBUG tests

        # Verify OTP
        verify_data = {'session_id': session_id, 'code': otp_code}
        response = self.client.post(self.verify_otp_url, verify_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertTrue(User.objects.get(email=self.email).is_verified)
        self.assertIn('refresh_token', self.client.cookies)

        # Ensure session is cleared
        self.assertIsNone(get_session_meta(session_id))  # Changed from get_otp_session
        self.assertIsNone(get_otp_hash(self.email))

    def test_verify_otp_invalid_code(self):
        """
        Ensure OTP verification fails with an invalid code.
        """
        # Simulate OTP request
        data = {'email': self.email}
        response = self.client.post(self.login_email_url, data, format='json')
        session_id = response.data['session_id']

        # Attempt to verify with wrong code
        verify_data = {'session_id': session_id, 'code': '999999'}
        response = self.client.post(self.verify_otp_url, verify_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
        self.assertEqual(response.data['detail'], 'Invalid OTP')
        self.assertFalse(User.objects.get(email=self.email).is_verified)  # User should not be verified

    def test_verify_otp_expired_session(self):
        """
        Ensure OTP verification fails with an expired session.
        """
        # Simulate OTP request
        data = {'email': self.email}
        response = self.client.post(self.login_email_url, data, format='json')
        session_id = response.data['session_id']
        otp_code = response.data['otp_code'] if settings.DEBUG else '123456'

        # Manually expire the session (or let it expire if TTL is very short in test config)
        # For testing, we can directly manipulate the cache or mock otp_service.verify_otp_once
        with patch('users.otp_service.verify_otp_once', return_value=(False, 'Session expired', None)):
            verify_data = {'session_id': session_id, 'code': otp_code}
            response = self.client.post(self.verify_otp_url, verify_data, format='json')

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('detail', response.data)
            self.assertEqual(response.data['detail'], 'Session expired')

    def test_verify_otp_missing_data(self):
        """
        Ensure OTP verification fails with missing session_id or code.
        """
        response = self.client.post(self.verify_otp_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
        self.assertEqual(response.data['detail'], 'session_id and code required')

        response = self.client.post(self.verify_otp_url, {'session_id': '123'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
        self.assertEqual(response.data['detail'], 'session_id and code required')

        response = self.client.post(self.verify_otp_url, {'code': '123456'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
        self.assertEqual(response.data['detail'], 'session_id and code required')

    def test_email_login_rate_limiting(self):
        """
        Ensure rate limiting is applied to email login requests.
        """
        # This test requires actual rate limiting to be configured and active.
        # For simplicity, we'll mock the check_rate_limit function.
        with patch('users.otp_service.check_rate_limit', return_value=(False, 60)):
            data = {'email': self.email}
            response = self.client.post(self.login_email_url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
            self.assertIn('detail', response.data)
            self.assertEqual(response.data['detail'], 'Too many requests.')

    def test_verify_otp_rate_limiting(self):
        """
        Ensure rate limiting is applied to OTP verification attempts.
        """
        # Simulate OTP request to get a valid session_id
        data = {'email': self.email}
        response = self.client.post(self.login_email_url, data, format='json')
        session_id = response.data['session_id']
        otp_code = response.data['otp_code'] if settings.DEBUG else '123456'

        with patch('users.otp_service.check_rate_limit', return_value=(False, 60)):
            verify_data = {'session_id': session_id, 'code': otp_code}
            response = self.client.post(self.verify_otp_url, verify_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
            self.assertIn('detail', response.data)
            self.assertEqual(response.data['detail'], 'Too many attempts, try later')

    def test_admin_redirect_after_verification(self):
        """
        Ensure admin users are redirected to the admin dashboard after successful OTP verification.
        """
        admin_email = "admin@example.com"
        admin_user = User.objects.create_user(email=admin_email, password=self.password, is_staff=True)

        # Simulate OTP request for admin user
        data = {'email': admin_email}
        response = self.client.post(self.login_email_url, data, format='json')
        session_id = response.data['session_id']
        otp_code = response.data['otp_code'] if settings.DEBUG else '123456'

        # Verify OTP
        verify_data = {'session_id': session_id, 'code': otp_code}
        response = self.client.post(self.verify_otp_url, verify_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('redirect_url', response.data)
        self.assertEqual(response.data['redirect_url'], reverse('admin_dashboard'))
        self.assertTrue(User.objects.get(email=admin_email).is_verified)
