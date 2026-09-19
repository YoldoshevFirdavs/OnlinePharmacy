"""
Critical security regression tests for billing functionality.
These tests simulate real attack scenarios and must pass in CI/CD pipeline.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from billing.models import Payment
from orders.models import Order
from users.models import CustomUser


class StripeWebhookSecurityTests(TestCase):
    """Critical negative tests for Stripe webhook security vulnerabilities"""

    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(email="user1@test.com", password="testpass123")
        self.other_user = CustomUser.objects.create_user(email="user2@test.com", password="testpass123")
        self.order = Order.objects.create(user=self.user, total_price=100.00, status="Pending")
        self.other_order = Order.objects.create(user=self.other_user, total_price=200.00, status="Pending")

    def test_missing_webhook_signature_returns_400(self):
        """Webhook without signature must be rejected"""
        response = self.client.post(
            "/api/v1/payments/webhook/", data={"type": "checkout.session.completed"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    @override_settings(STRIPE_WEBHOOK_SECRET="test_secret")
    def test_invalid_signature_returns_400(self):
        """Webhook with invalid signature must be rejected"""
        response = self.client.post(
            "/api/v1/payments/webhook/",
            data={"type": "checkout.session.completed"},
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="invalid_sig",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_webhook_secret_configured_rejects(self):
        """System must validate STRIPE_WEBHOOK_SECRET is configured"""
        with override_settings(STRIPE_WEBHOOK_SECRET=""):
            response = self.client.post(
                "/api/v1/payments/webhook/",
                data={"type": "checkout.session.completed"},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("not configured", response.data["error"].lower())


class LegacyChargeSecurityTests(TestCase):
    """Critical tests for legacy charge endpoint authorization"""

    def setUp(self):
        self.client = APIClient()
        self.user1 = CustomUser.objects.create_user(email="user1@test.com", password="testpass123")
        self.user2 = CustomUser.objects.create_user(email="user2@test.com", password="testpass123")
        self.order_user1 = Order.objects.create(user=self.user1, total_price=100.00, status="Pending")
        self.order_user2 = Order.objects.create(user=self.user2, total_price=200.00, status="Pending")

    def test_cannot_charge_another_users_order(self):
        """User cannot pay for another user's order"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            "/api/v1/payments/charge/",
            {"stripeToken": "tok_test_123", "order_id": self.order_user2.id},  # Belongs to user2
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not owned", response.data["error"].lower())
        self.assertEqual(Payment.objects.count(), 0)

    def test_charge_nonexistent_order_returns_400(self):
        """Charging non-existent order returns error"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            "/api/v1/payments/charge/", {"stripeToken": "tok_test_123", "order_id": 99999}  # Non-existent order
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not found", response.data["error"].lower())


class PaymentIdempotencyTests(TestCase):
    """Test idempotent payment processing"""

    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(email="user@test.com", password="testpass123")
        self.order = Order.objects.create(user=self.user, total_price=100.00, status="Pending")

    @override_settings(STRIPE_WEBHOOK_SECRET="")
    def test_duplicate_webhook_does_not_create_multiple_payments(self):
        """Duplicate webhook should not create multiple payments - test with empty webhook secret (skip signature verification)"""
        # Skip this test in CI/CD since signature verification requires real webhook secret
        self.skipTest("Skip webhook signature test in CI/CD - requires real STRIPE_WEBHOOK_SECRET")


class PaymentIdempotencyTests(TestCase):
    """Test idempotent payment processing - duplicate webhooks should not create duplicate payments"""

    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(email="user@test.com", password="testpass123")
        self.order = Order.objects.create(user=self.user, total_price=100.00, status="Pending")

    @override_settings(STRIPE_WEBHOOK_SECRET="test_secret_key")
    def test_duplicate_webhook_does_not_create_duplicate_payment(self):
        """Duplicate webhook with same session_id should not create multiple payments"""
        from unittest.mock import MagicMock, patch

        import stripe

        # Create a valid webhook event
        webhook_event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_12345",
                    "payment_intent": "pi_test_67890",
                    "metadata": {"order_id": str(self.order.id), "user_id": str(self.user.id)},
                }
            },
        }

        # Mock Stripe webhook construction
        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = webhook_event

            # Send webhook first time
            response1 = self.client.post(
                "/api/v1/payments/webhook/",
                data=webhook_event,
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="valid_signature",
            )
            self.assertEqual(response1.status_code, 200)

            # Verify payment created
            payment_count_after_first = Payment.objects.filter(order=self.order).count()
            self.assertEqual(payment_count_after_first, 1)

            # Send SAME webhook second time (duplicate)
            response2 = self.client.post(
                "/api/v1/payments/webhook/",
                data=webhook_event,
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="valid_signature",
            )
            self.assertEqual(response2.status_code, 200)

            # Verify ONLY ONE payment exists (not 2!)
            payment_count_after_second = Payment.objects.filter(order=self.order).count()
            self.assertEqual(payment_count_after_second, 1, "Duplicate webhook should not create duplicate payment")

            # Verify order status is still "Paid"
            self.order.refresh_from_db()
            self.assertEqual(self.order.status, "Paid")
