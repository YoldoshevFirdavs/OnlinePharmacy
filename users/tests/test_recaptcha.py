import os
from django.test import TestCase, override_settings
from unittest.mock import patch, MagicMock
from users.otp_service import verify_recaptcha
import requests # requests.exceptions.RequestException uchun

# Test uchun dummy reCAPTCHA kalitlari
# Bularni o'zingizning haqiqiy kalitlaringiz bilan almashtiring!
TEST_RECAPTCHA_SITE_KEY = "6LdboSstAAAAAEzddn7S_3RXOTxjsDPOGt-qXdru" # Bu sizning frontend kalitingizga mos bo'lishi kerak
TEST_RECAPTCHA_SECRET_KEY = "6LdboSstAAAAAP-XhQgRwg1jAxSk2SGBf_vW60RX" # Bu sizning backend secret kalitingizga mos bo'lishi kerak

@override_settings(RECAPTCHA_SECRET_KEY=TEST_RECAPTCHA_SECRET_KEY, RECAPTCHA_THRESHOLD=0.5)
class RecaptchaServiceTest(TestCase):

    @patch('requests.post')
    def test_verify_recaptcha_success(self, mock_post):
        """
        reCAPTCHA muvaffaqiyatli tekshirilganda.
        """
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "success": True,
            "score": 0.9,
            "action": "login_telegram",
            "hostname": "127.0.0.1"
        }
        mock_post.return_value = mock_response

        # Google'dan kelgan haqiqiy token o'rniga test token ishlatamiz
        test_token = "test_recaptcha_token_success"
        result = verify_recaptcha(test_token, action='login_telegram')

        self.assertTrue(result['success'])
        self.assertEqual(result['score'], 0.9)
        self.assertEqual(result['action'], 'login_telegram')
        mock_post.assert_called_once_with(
            'https://www.google.com/recaptcha/api/siteverify',
            data={'secret': TEST_RECAPTCHA_SECRET_KEY, 'response': test_token, 'action': 'login_telegram'}
        )

    @patch('requests.post')
    def test_verify_recaptcha_failure_invalid_token(self, mock_post):
        """
        reCAPTCHA noto'g'ri token bilan tekshirilganda.
        """
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "success": False,
            "error-codes": ["invalid-input-response"]
        }
        mock_post.return_value = mock_response

        test_token = "test_recaptcha_token_failure"
        result = verify_recaptcha(test_token, action='login_telegram')

        self.assertFalse(result['success'])
        self.assertIn("invalid-input-response", result['error-codes'])
        mock_post.assert_called_once()

    @patch('requests.post')
    def test_verify_recaptcha_api_error(self, mock_post):
        """
        reCAPTCHA API bilan bog'lanishda xato yuz berganda.
        """
        mock_post.side_effect = requests.exceptions.RequestException("Test API error")

        test_token = "any_token"
        result = verify_recaptcha(test_token)

        self.assertFalse(result['success'])
        self.assertIn("recaptcha-api-error", result['error-codes'])
        mock_post.assert_called_once()

    def test_verify_recaptcha_missing_secret_key(self):
        """
        RECAPTCHA_SECRET_KEY sozlamalarda mavjud bo'lmaganda.
        """
        with self.settings(RECAPTCHA_SECRET_KEY=None): # Test uchun secret keyni o'chiramiz
            test_token = "any_token"
            result = verify_recaptcha(test_token)
            self.assertFalse(result['success'])
            self.assertIn("missing-secret-key", result['error-codes'])

    def test_verify_recaptcha_missing_token(self):
        """
        reCAPTCHA tokeni berilmaganda.
        """
        result = verify_recaptcha(None)
        self.assertFalse(result['success'])
        self.assertIn("missing-input-response", result['error-codes'])
