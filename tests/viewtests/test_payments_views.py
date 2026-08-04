from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
import pytest

User = get_user_model()

pytestmark = pytest.mark.django_db

class PaymentViewTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="test@example.com", password="password")
        self.create_payment_intent_url = reverse("create-payment-intent") # Assuming 'create-payment-intent' URL name
        self.confirm_payment_url = reverse("confirm-payment") # Assuming 'confirm-payment' URL name

    @patch("stripe.PaymentIntent.create")
    def test_create_payment_intent(self, mock_stripe_create):
        mock_stripe_create.return_value = MagicMock(id="pi_test123", client_secret="cs_test123")
        self.client.force_authenticate(user=self.user)
        data = {"order_id": 1, "amount": 100.00}
        response = self.client.post(self.create_payment_intent_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("client_secret", response.data)
        mock_stripe_create.assert_called_once_with(
            amount=10000, # amount in cents
            currency="usd",
            metadata={"order_id": 1, "user_id": self.user.id}
        )

    @patch("stripe.PaymentIntent.confirm")
    def test_confirm_payment(self, mock_stripe_confirm):
        mock_stripe_confirm.return_value = MagicMock(status="succeeded")
        self.client.force_authenticate(user=self.user)
        data = {"payment_intent_id": "pi_test123", "payment_method_id": "pm_test123"}
        response = self.client.post(self.confirm_payment_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "succeeded")
        mock_stripe_confirm.assert_called_once_with(
            "pi_test123",
            payment_method="pm_test123"
        )

    def test_unauthenticated_create_payment_intent(self):
        data = {"order_id": 1, "amount": 100.00}
        response = self.client.post(self.create_payment_intent_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
