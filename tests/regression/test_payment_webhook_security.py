"""
Critical regression tests for Stripe webhook security and idempotency.
Run with: pytest tests/regression/test_payment_webhook_security.py -v
"""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from billing.models import Payment
from orders.models import Order
from users.models import CustomUser

User = get_user_model()


class StripeWebhookSignatureTests(TestCase):
    """Critical security tests: Webhook signature must be validated"""

    def setUp(self):
        self.client = APIClient()
        self.webhook_url = "/api/v1/payments/webhook/"

    def test_missing_signature_header_returns_400(self):
        """Webhook without Stripe-Signature header must be rejected (400)"""
        response = self.client.post(
            self.webhook_url, data={"type": "checkout.session.completed"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    @override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
    def test_invalid_signature_returns_400(self):
        """Webhook with malformed/invalid signature must be rejected (400)"""
        response = self.client.post(
            self.webhook_url,
            data={"type": "checkout.session.completed"},
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="v1,invalid_signature_here",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(STRIPE_WEBHOOK_SECRET="")
    def test_no_webhook_secret_raises_error(self):
        """System must validate STRIPE_WEBHOOK_SECRET configuration"""
        response = self.client.post(
            self.webhook_url, data={"type": "checkout.session.completed"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not configured", response.data.get("error", "").lower())


class PaymentAuthorizationTests(TestCase):
    """Critical tests: Users can only pay for their own orders"""

    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            email="user1@test.com", password="testpass123", phone_number="+998901234567"
        )
        self.user2 = User.objects.create_user(
            email="user2@test.com", password="testpass123", phone_number="+998907654321"
        )
        self.order1 = Order.objects.create(user=self.user1, total_price=100.00, status="Pending")
        self.order2 = Order.objects.create(user=self.user2, total_price=200.00, status="Pending")

    def test_cannot_pay_another_users_order(self):
        """Payment for another user's order must be rejected (400)"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.post("/api/v1/payments/charge/", {"stripeToken": "tok_visa", "order_id": self.order2.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not owned", response.data["error"].lower())

    def test_can_only_pay_own_orders(self):
        """User can only pay for their own orders"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.post("/api/v1/payments/charge/", {"stripeToken": "tok_visa", "order_id": self.order1.id})
        # Should either succeed or fail due to Stripe API (not permission error)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_nonexistent_order_returns_400(self):
        """Charging non-existent order returns error"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.post("/api/v1/payments/charge/", {"stripeToken": "tok_visa", "order_id": 999999})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PaymentIdempotencyTests(TestCase):
    """Test idempotent payment processing - duplicate webhooks don't create duplicate payments"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@test.com", password="testpass123", phone_number="+998901112233"
        )
        self.order = Order.objects.create(user=self.user, total_price=150.00, status="Pending")

    @override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_1234567890")
    @patch("stripe.Webhook.construct_event")
    def test_duplicate_webhook_does_not_create_duplicate_payment(self, mock_construct):
        """Sending same webhook twice should not create duplicate Payment records"""
        # Mock successful Stripe event
        mock_event = MagicMock()
        mock_event.type = "checkout.session.completed"
        mock_event.data.object = {
            "id": "cs_test_123456",
            "payment_intent": "pi_test_123456",
            "metadata": {"order_id": str(self.order.id)},
            "amount_total": 15000,  # cents
        }
        mock_construct.return_value = mock_event

        webhook_data = {"type": "checkout.session.completed", "data": {"object": mock_event.data.object}}

        # First webhook call
        response1 = self.client.post(
            "/api/v1/payments/webhook/",
            data=webhook_data,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig_test_1",
        )
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        initial_payments = Payment.objects.filter(order=self.order).count()
        self.assertEqual(initial_payments, 1)

        # Second identical webhook call
        response2 = self.client.post(
            "/api/v1/payments/webhook/",
            data=webhook_data,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig_test_1",
        )
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        final_payments = Payment.objects.filter(order=self.order).count()
        self.assertEqual(final_payments, 1, "Duplicate webhook created second payment!")

    @override_settings(STRIPE_WEBHOOK_SECRET="whsec_test_1234567890")
    @patch("stripe.Webhook.construct_event")
    def test_webhook_only_updates_pending_orders(self, mock_construct):
        """Webhook should not update already paid orders"""
        # Create order that's already paid
        paid_order = Order.objects.create(user=self.user, total_price=200.00, status="Paid")

        mock_event = MagicMock()
        mock_event.type = "checkout.session.completed"
        mock_event.data.object = {
            "id": "cs_test_paid",
            "payment_intent": "pi_test_paid",
            "metadata": {"order_id": str(paid_order.id)},
            "amount_total": 20000,
        }
        mock_construct.return_value = mock_event

        webhook_data = {"type": "checkout.session.completed", "data": {"object": mock_event.data.object}}

        response = self.client.post(
            "/api/v1/payments/webhook/",
            data=webhook_data,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig_test_paid",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Order should still be "Paid"
        paid_order.refresh_from_db()
        self.assertEqual(paid_order.status, "Paid")


class OrderAcceptanceTests(TestCase):
    """Test driver order acceptance logic"""

    def setUp(self):
        self.client = APIClient()
        from users.models import DeliveryDriver

        self.user1 = User.objects.create_user(
            email="driver1@test.com", password="testpass123", phone_number="+998901234567", role="driver"
        )
        self.driver1 = DeliveryDriver.objects.create(user=self.user1, vehicle_type="car")

        self.user2 = User.objects.create_user(
            email="driver2@test.com", password="testpass123", phone_number="+998907654321", role="driver"
        )
        self.driver2 = DeliveryDriver.objects.create(user=self.user2, vehicle_type="motorcycle")

        self.order = Order.objects.create(user=self.user1, total_price=100.00, status="Pending")

    def test_only_one_driver_can_accept_order(self):
        """Parallel accept attempts - only first driver should succeed"""
        from orders.models import Order

        self.client.force_authenticate(user=self.user1)
        response1 = self.client.post(f"/api/v1/orders/orders/{self.order.id}/accept/", format="json")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Second driver tries to accept same order
        self.client.force_authenticate(user=self.user2)
        response2 = self.client.post(f"/api/v1/orders/orders/{self.order.id}/accept/", format="json")

        # Should fail - order already assigned
        self.assertIn(response2.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN])

        # Verify only one driver is assigned
        self.order.refresh_from_db()
        self.assertEqual(self.order.driver, self.driver1)
