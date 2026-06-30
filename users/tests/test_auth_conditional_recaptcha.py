from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from users.models import CustomUser
from users.otp_service import verify_recaptcha as otp_service_verify_recaptcha

# Mock reCAPTCHA settings for tests
@override_settings(
    RECAPTCHA_SECRET_KEY='test_secret_key',
    RECAPTCHA_THRESHOLD=0.5,
    DEBUG=True # Enable debug logging in tests
)
class ConditionalRecaptchaTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.phone_number = '+998901234567'
        self.email = 'test@example.com'
        self.name = 'Test User'
        self.login_telegram_url = '/api/v1/users/login/telegram/'
        self.login_email_url = '/api/v1/users/login/email/'
        self.verify_otp_url = '/api/v1/users/verify-otp/'

        # Create a user for OTP verification tests
        self.user = CustomUser.objects.create(phone_number=self.phone_number, email=self.email, full_name=self.name)

    @patch('users.otp_service.verify_recaptcha')
    @patch('users.otp_service.create_otp_session')
    @patch('users.otp_service.store_bot_otp')
    @patch('users.otp_service.bind_session_to_user')
    def test_telegram_login_incognito_recaptcha_success(self, mock_bind, mock_store_otp, mock_create_session, mock_verify_recaptcha):
        """
        Test Telegram login when in incognito mode and reCAPTCHA verification succeeds.
        """
        mock_verify_recaptcha.return_value = {'success': True, 'score': 0.9, 'action': 'login_telegram'}
        mock_create_session.return_value = MagicMock(session_id='test_session_id')

        payload = {
            'phone_number': self.phone_number,
            'name': self.name,
            'recaptcha_token': 'mock_recaptcha_token',
            'incognito': True,
        }
        headers = {'X-Incognito': 'true'}

        response = self.client.post(self.login_telegram_url, payload, format='json', headers=headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_verify_recaptcha.assert_called_once_with('mock_recaptcha_token', action='login_telegram')
        self.assertIn('session_id', response.data)
        self.assertIn('deeplink', response.data)

    @patch('users.otp_service.verify_recaptcha')
    @patch('users.otp_service.create_otp_session')
    @patch('users.otp_service.store_bot_otp')
    @patch('users.otp_service.bind_session_to_user')
    def test_telegram_login_incognito_recaptcha_fail(self, mock_bind, mock_store_otp, mock_create_session, mock_verify_recaptcha):
        """
        Test Telegram login when in incognito mode and reCAPTCHA verification fails.
        """
        mock_verify_recaptcha.return_value = {'success': False, 'error-codes': ['invalid-input-response']}

        payload = {
            'phone_number': self.phone_number,
            'name': self.name,
            'recaptcha_token': 'mock_recaptcha_token',
            'incognito': True,
        }
        headers = {'X-Incognito': 'true'}

        response = self.client.post(self.login_telegram_url, payload, format='json', headers=headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('reCAPTCHA tekshiruvi muvaffaqiyatsiz tugadi.', response.data['detail'])
        mock_verify_recaptcha.assert_called_once_with('mock_recaptcha_token', action='login_telegram')

    @patch('users.otp_service.verify_recaptcha')
    @patch('users.otp_service.create_otp_session')
    @patch('users.otp_service.store_bot_otp')
    @patch('users.otp_service.bind_session_to_user')
    def test_telegram_login_not_incognito_recaptcha_skipped(self, mock_bind, mock_store_otp, mock_create_session, mock_verify_recaptcha):
        """
        Test Telegram login when not in incognito mode, reCAPTCHA should be skipped.
        """
        mock_create_session.return_value = MagicMock(session_id='test_session_id')

        payload = {
            'phone_number': self.phone_number,
            'name': self.name,
            'incognito': False, # Explicitly set incognito to false
        }
        headers = {'X-Incognito': 'false'} # Explicitly set header to false

        response = self.client.post(self.login_telegram_url, payload, format='json', headers=headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_verify_recaptcha.assert_not_called() # reCAPTCHA should not be called
        self.assertIn('session_id', response.data)
        self.assertIn('deeplink', response.data)

    @patch('users.otp_service.verify_recaptcha')
    @patch('users.otp_service.create_otp_session')
    @patch('users.otp_service.store_bot_otp')
    @patch('users.otp_service.bind_session_to_user')
    def test_telegram_login_anonymous_user_recaptcha_required(self, mock_bind, mock_store_otp, mock_create_session, mock_verify_recaptcha):
        """
        Test Telegram login for an anonymous user (default client state), reCAPTCHA should be required.
        """
        mock_verify_recaptcha.return_value = {'success': True, 'score': 0.9, 'action': 'login_telegram'}
        mock_create_session.return_value = MagicMock(session_id='test_session_id')

        payload = {
            'phone_number': self.phone_number,
            'name': self.name,
            'recaptcha_token': 'mock_recaptcha_token',
        }
        # No login, so request.user.is_anonymous is True by default

        response = self.client.post(self.login_telegram_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_verify_recaptcha.assert_called_once_with('mock_recaptcha_token', action='login_telegram')
        self.assertIn('session_id', response.data)

    @patch('users.otp_service.verify_recaptcha')
    @patch('users.otp_service.create_otp_session')
    @patch('users.otp_service.store_bot_otp')
    @patch('users.otp_service.bind_session_to_user')
    def test_telegram_login_authenticated_user_recaptcha_skipped(self, mock_bind, mock_store_otp, mock_create_session, mock_verify_recaptcha):
        """
        Test Telegram login for an authenticated user, reCAPTCHA should be skipped.
        """
        mock_create_session.return_value = MagicMock(session_id='test_session_id')

        # Log in the user
        self.client.force_authenticate(user=self.user)

        payload = {
            'phone_number': self.phone_number,
            'name': self.name,
            'recaptcha_token': 'mock_recaptcha_token', # Even if provided, should be skipped
        }

        response = self.client.post(self.login_telegram_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_verify_recaptcha.assert_not_called() # reCAPTCHA should not be called
        self.assertIn('session_id', response.data)
        self.client.force_authenticate(user=None) # Log out for subsequent tests

    @patch('users.otp_service.verify_recaptcha')
    @patch('users.otp_service.verify_otp_once')
    @patch('users.otp_service.get_session_meta')
    def test_verify_otp_incognito_recaptcha_success(self, mock_get_session_meta, mock_verify_otp_once, mock_verify_recaptcha):
        """
        Test OTP verification when in incognito mode and reCAPTCHA succeeds.
        """
        mock_verify_recaptcha.return_value = {'success': True, 'score': 0.9, 'action': 'verify_otp'}
        mock_get_session_meta.return_value = {'user_id': self.user.id, 'identifier': self.phone_number}
        mock_verify_otp_once.return_value = (True, 'OTP verified successfully', {'user_id': self.user.id, 'identifier': self.phone_number})

        payload = {
            'session_id': 'mock_session_id',
            'code': '123456',
            'recaptcha_token': 'mock_recaptcha_token',
            'incognito': True,
        }
        headers = {'X-Incognito': 'true'}

        response = self.client.post(self.verify_otp_url, payload, format='json', headers=headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_verify_recaptcha.assert_called_once_with('mock_recaptcha_token', action='verify_otp')
        self.assertIn('access', response.data)

    @patch('users.otp_service.verify_recaptcha')
    @patch('users.otp_service.verify_otp_once')
    @patch('users.otp_service.get_session_meta')
    def test_verify_otp_incognito_recaptcha_fail(self, mock_get_session_meta, mock_verify_otp_once, mock_verify_recaptcha):
        """
        Test OTP verification when in incognito mode and reCAPTCHA fails.
        """
        mock_verify_recaptcha.return_value = {'success': False, 'error-codes': ['timeout-or-duplicate']}
        mock_get_session_meta.return_value = {'user_id': self.user.id, 'identifier': self.phone_number}

        payload = {
            'session_id': 'mock_session_id',
            'code': '123456',
            'recaptcha_token': 'mock_recaptcha_token',
            'incognito': True,
        }
        headers = {'X-Incognito': 'true'}

        response = self.client.post(self.verify_otp_url, payload, format='json', headers=headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('reCAPTCHA tekshiruvi muvaffaqiyatsiz tugadi.', response.data['detail'])
        mock_verify_recaptcha.assert_called_once_with('mock_recaptcha_token', action='verify_otp')
        mock_verify_otp_once.assert_not_called() # OTP verification should not proceed

    @patch('users.otp_service.verify_recaptcha')
    @patch('users.otp_service.verify_otp_once')
    @patch('users.otp_service.get_session_meta')
    def test_verify_otp_not_incognito_recaptcha_skipped(self, mock_get_session_meta, mock_verify_otp_once, mock_verify_recaptcha):
        """
        Test OTP verification when not in incognito mode, reCAPTCHA should be skipped.
        """
        mock_get_session_meta.return_value = {'user_id': self.user.id, 'identifier': self.phone_number}
        mock_verify_otp_once.return_value = (True, 'OTP verified successfully', {'user_id': self.user.id, 'identifier': self.phone_number})

        payload = {
            'session_id': 'mock_session_id',
            'code': '123456',
            'incognito': False,
        }
        headers = {'X-Incognito': 'false'}

        response = self.client.post(self.verify_otp_url, payload, format='json', headers=headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_verify_recaptcha.assert_not_called() # reCAPTCHA should not be called
        mock_verify_otp_once.assert_called_once() # OTP verification should proceed
        self.assertIn('access', response.data)

    @patch('users.otp_service.verify_recaptcha')
    @patch('users.otp_service.verify_otp_once')
    @patch('users.otp_service.get_session_meta')
    def test_verify_otp_anonymous_user_recaptcha_required(self, mock_get_session_meta, mock_verify_otp_once, mock_verify_recaptcha):
        """
        Test OTP verification for an anonymous user, reCAPTCHA should be required.
        """
        mock_verify_recaptcha.return_value = {'success': True, 'score': 0.9, 'action': 'verify_otp'}
        mock_get_session_meta.return_value = {'user_id': self.user.id, 'identifier': self.phone_number}
        mock_verify_otp_once.return_value = (True, 'OTP verified successfully', {'user_id': self.user.id, 'identifier': self.phone_number})

        payload = {
            'session_id': 'mock_session_id',
            'code': '123456',
            'recaptcha_token': 'mock_recaptcha_token',
        }
        # No login, so request.user.is_anonymous is True by default

        response = self.client.post(self.verify_otp_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_verify_recaptcha.assert_called_once_with('mock_recaptcha_token', action='verify_otp')
        self.assertIn('access', response.data)

    @patch('users.otp_service.verify_recaptcha')
    @patch('users.otp_service.verify_otp_once')
    @patch('users.otp_service.get_session_meta')
    def test_verify_otp_authenticated_user_recaptcha_skipped(self, mock_get_session_meta, mock_verify_otp_once, mock_verify_recaptcha):
        """
        Test OTP verification for an authenticated user, reCAPTCHA should be skipped.
        """
        mock_get_session_meta.return_value = {'user_id': self.user.id, 'identifier': self.phone_number}
        mock_verify_otp_once.return_value = (True, 'OTP verified successfully', {'user_id': self.user.id, 'identifier': self.phone_number})

        # Log in the user
        self.client.force_authenticate(user=self.user)

        payload = {
            'session_id': 'mock_session_id',
            'code': '123456',
            'recaptcha_token': 'mock_recaptcha_token', # Even if provided, should be skipped
        }

        response = self.client.post(self.verify_otp_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_verify_recaptcha.assert_not_called() # reCAPTCHA should not be called
        mock_verify_otp_once.assert_called_once() # OTP verification should proceed
        self.assertIn('access', response.data)
        self.client.force_authenticate(user=None) # Log out for subsequent tests

    @patch('users.otp_service.verify_recaptcha')
    @patch('users.otp_service.create_otp_session')
    @patch('users.otp_service.store_bot_otp')
    @patch('users.otp_service.bind_session_to_user')
    def test_telegram_login_incognito_missing_recaptcha_token(self, mock_bind, mock_store_otp, mock_create_session, mock_verify_recaptcha):
        """
        Test Telegram login when in incognito mode but reCAPTCHA token is missing.
        """
        payload = {
            'phone_number': self.phone_number,
            'name': self.name,
            'incognito': True,
        }
        headers = {'X-Incognito': 'true'}

        response = self.client.post(self.login_telegram_url, payload, format='json', headers=headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('reCAPTCHA required', response.data['detail']) # Updated error message
        mock_verify_recaptcha.assert_not_called() # reCAPTCHA verification should not be attempted
        mock_create_session.assert_not_called()

    @patch('users.otp_service.verify_recaptcha')
    @patch('users.otp_service.verify_otp_once')
    @patch('users.otp_service.get_session_meta')
    def test_verify_otp_incognito_missing_recaptcha_token(self, mock_get_session_meta, mock_verify_otp_once, mock_verify_recaptcha):
        """
        Test OTP verification when in incognito mode but reCAPTCHA token is missing.
        """
        mock_get_session_meta.return_value = {'user_id': self.user.id, 'identifier': self.phone_number}

        payload = {
            'session_id': 'mock_session_id',
            'code': '123456',
            'incognito': True,
        }
        headers = {'X-Incognito': 'true'}

        response = self.client.post(self.verify_otp_url, payload, format='json', headers=headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('reCAPTCHA required', response.data['detail']) # Updated error message
        mock_verify_recaptcha.assert_not_called() # reCAPTCHA verification should not be attempted
        mock_verify_otp_once.assert_not_called()