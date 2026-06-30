from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from .models import SubscribedUser, CustomUser, Deliverer
from unittest.mock import patch
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

User = get_user_model()

class SubscriberAPITest(TestCase):
	def setUp(self):
		patcher = patch('users.views.send_subscription_verification_email.delay')
		self.addCleanup(patcher.stop)
		self.mock_send = patcher.start()
		self.client = APIClient()
		self.url = reverse('subscribers-list')

	def test_create_non_gmail_rejected(self):
		resp = self.client.post(self.url, {'email': 'user@example.com'}, format='json')
		self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
		self.mock_send.assert_not_called()

	def test_create_gmail_created_and_linked(self):
		user = CustomUser.objects.create(email='tester@gmail.com')
		resp = self.client.post(self.url, {'email': 'TESTER@GMAIL.com'}, format='json')
		self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
		self.mock_send.assert_called_once()
		self.assertIn('email', resp.data)
		sub = SubscribedUser.objects.get(email='tester@gmail.com')
		self.assertIsNotNone(sub.user)
		self.assertEqual(sub.user.id, user.id)

class DeliveryDriverAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.driver_user = CustomUser.objects.create_user(
            phone_number='+998901234567',
            email='driver@example.com',
            password='driverpassword'
        )
        self.driver_profile = Deliverer.objects.create(
            user=self.driver_user,
            phone='+998901234567',
            vehicle_type='motorbike'
        )
        self.non_driver_user = CustomUser.objects.create_user(
            phone_number='+998907654321',
            email='user@example.com',
            password='userpassword'
        )

        self.login_url = reverse('driver-login')
        self.profile_url = reverse('driver-profile')
        self.location_url = reverse('driver-location-update')

    def get_driver_auth_headers(self):
        refresh = RefreshToken.for_user(self.driver_user)
        return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}

    def test_driver_login_success(self):
        response = self.client.post(self.login_url, {
            'phone_number': '+998901234567',
            'password': 'driverpassword'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_driver_login_fail_wrong_password(self):
        response = self.client.post(self.login_url, {
            'phone_number': '+998901234567',
            'password': 'wrongpassword'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Unable to log in with provided credentials.', str(response.data))

    def test_driver_login_fail_not_driver(self):
        response = self.client.post(self.login_url, {
            'phone_number': '+998907654321',
            'password': 'userpassword'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('User is not a delivery driver.', str(response.data))

    def test_driver_profile_access_success(self):
        headers = self.get_driver_auth_headers()
        response = self.client.get(self.profile_url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user'], str(self.driver_user))
        self.assertEqual(response.data['phone'], self.driver_profile.phone)

    def test_driver_profile_access_unauthorized(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_driver_location_update_success(self):
        headers = self.get_driver_auth_headers()
        new_lat = 41.2995
        new_lng = 69.2401
        response = self.client.post(self.location_url, {
            'lat': new_lat,
            'lng': new_lng
        }, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.driver_profile.refresh_from_db()
        self.assertEqual(float(self.driver_profile.current_lat), new_lat)
        self.assertEqual(float(self.driver_profile.current_lng), new_lng)
        self.assertIsNotNone(self.driver_profile.last_location_update)

    def test_driver_location_update_invalid_data(self):
        headers = self.get_driver_auth_headers()
        response = self.client.post(self.location_url, {
            'lat': 'invalid',
            'lng': 69.2401
        }, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Latitude and longitude must be valid numbers.', str(response.data))

    def test_driver_location_update_unauthorized(self):
        response = self.client.post(self.location_url, {
            'lat': 41.2995,
            'lng': 69.2401
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AdminLoginAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='adminpassword',
            is_staff=True
        )
        self.non_admin_user = User.objects.create_user(
            email='user@example.com',
            password='userpassword',
            is_staff=False
        )
        self.login_url = reverse('admin_login_alias')

    def test_admin_login_success_with_credentials(self):
        response = self.client.post(self.login_url, {
            'action': 'credentials',
            'email': 'admin@example.com',
            'password': 'adminpassword'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['redirect'], '/dashboard/')

    def test_admin_login_fail_invalid_credentials(self):
        response = self.client.post(self.login_url, {
            'action': 'credentials',
            'email': 'admin@example.com',
            'password': 'wrongpassword'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Login yoki parol noto‘g‘ri.', response.data['error'])

    def test_admin_login_fail_non_admin_user(self):
        response = self.client.post(self.login_url, {
            'action': 'credentials',
            'email': 'user@example.com',
            'password': 'userpassword'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Foydalanuvchi admin emas.', response.data['error'])

    def test_admin_login_fail_missing_action(self):
        response = self.client.post(self.login_url, {
            'email': 'admin@example.com',
            'password': 'adminpassword'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Noma\'lum action', response.data['error'])

    def test_admin_login_fail_invalid_action(self):
        response = self.client.post(self.login_url, {
            'action': 'invalid_action',
            'email': 'admin@example.com',
            'password': 'adminpassword'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Noma\'lum action', response.data['error'])