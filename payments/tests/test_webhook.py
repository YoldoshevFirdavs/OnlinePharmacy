from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model

from payments.models import Payout
import json
from unittest.mock import patch

User = get_user_model()

class WebhookTests(APITestCase):
    def setUp(self):
        self.webhook_url = reverse('stripe-webhook')
        self.admin_user = User.objects.create_user(phone_number='+998901234567', password='adminpassword', is_staff=True)
        self.driver_user = User.objects.create_user(phone_number='+998907654321', password='driverpassword')
        self.driver_profile = DeliveryDriver.objects.create(
            user=self.driver_user,
            phone='+998907654321',
            vehicle_type='motorbike',
            license_plate='ABC123DEF'
        )
        self.admin_payout_create_url = reverse('admin-payout-create')

    def get_admin_token(self):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.admin_user)
        return str(refresh.access_token)

    def test_stripe_webhook_receives_post_request(self):
        payload = {'id': 'evt_test', 'type': 'payment_intent.succeeded', 'data': {'object': {'id': 'pi_test'}}}
        response = self.client.post(self.webhook_url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_stripe_webhook_invalid_json(self):
        payload = "this is not json"
        response = self.client.post(self.webhook_url, payload, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('payments.views.stripe.Webhook.construct_event')
    def test_stripe_webhook_with_signature_verification(self, mock_construct_event):
        mock_construct_event.return_value = {'id': 'evt_test', 'type': 'transfer.succeeded', 'data': {'object': {'id': 'tr_test'}}}
        payload = {'id': 'evt_test', 'type': 'transfer.succeeded', 'data': {'object': {'id': 'tr_test'}}}
        headers = {'HTTP_STRIPE_SIGNATURE': 't=123,v1=abc'}
        response = self.client.post(self.webhook_url, json.dumps(payload), content_type='application/json', **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_payout_create_success(self):
        token = self.get_admin_token()
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        data = {
            'driver_id': self.driver_profile.id,
            'amount_gross': '100.00',
            'tax_amount': '10.00',
            'commission_amount': '5.00',
            'period_start': '2023-01-01',
            'period_end': '2023-01-31'
        }
        response = self.client.post(self.admin_payout_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Payout.objects.count(), 1)
        payout = Payout.objects.first()
        self.assertEqual(payout.driver, self.driver_profile)
        self.assertEqual(float(payout.net_amount), 85.00)

    def test_admin_payout_create_not_admin(self):
        # Assuming get_driver_token exists or creating a driver token for this test
        # For now, let's use a placeholder if get_driver_token is not defined
        # In a real test, you would have a method to get a driver's token
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.driver_user)
        token = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        data = {
            'driver_id': self.driver_profile.id,
            'amount_gross': '100.00',
            'tax_amount': '10.00',
            'commission_amount': '5.00'
        }
        response = self.client.post(self.admin_payout_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_payout_create_invalid_data(self):
        token = self.get_admin_token()
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        data = {
            'driver_id': self.driver_profile.id,
            'amount_gross': '-100.00',
        }
        response = self.client.post(self.admin_payout_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount_gross', response.data)

    def test_admin_payout_create_net_amount_negative(self):
        token = self.get_admin_token()
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        data = {
            'driver_id': self.driver_profile.id,
            'amount_gross': '10.00',
            'tax_amount': '5.00',
            'commission_amount': '10.00',
        }
        response = self.client.post(self.admin_payout_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Net amount cannot be negative.', response.data['detail'])