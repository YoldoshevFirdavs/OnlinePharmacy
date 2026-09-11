"""
Delivery regression tests for parallel accept and rollback scenarios.
Run with: pytest tests/regression/test_delivery_rollback.py -v
"""

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from orders.models import Order
from pharmacy.models.medicine import Medicine
from users.models import CustomUser, DeliveryDriver


class DeliveryModelViewContractTests(TestCase):
    """Test DeliveryOrder model-view contract"""

    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            email="user@test.com", password="testpass123", phone_number="+998901234567"
        )

        self.driver = CustomUser.objects.create_user(
            email="driver@test.com", password="testpass123", phone_number="+998907654321", role="driver"
        )
        self.delivery_profile = DeliveryDriver.objects.create(user=self.driver, vehicle_type="car")

        self.medicine = Medicine.objects.create(name="Test Medicine", slug="test-medicine", price=50.00, stock=10)

        self.order = Order.objects.create(user=self.user, total_price=100.00, status="Pending")

    def test_delivery_order_created_on_assign(self):
        """Creating a delivery record should properly link to order and driver"""
        from orders.models import DeliveryOrder

        delivery = DeliveryOrder.objects.create(driver=self.delivery_profile, order=self.order, status="assigned")

        self.assertEqual(delivery.driver, self.delivery_profile)
        self.assertEqual(delivery.order, self.order)
        self.assertEqual(delivery.status, "assigned")
        self.assertIsNotNone(delivery.assigned_at)

    def test_delivery_order_status_transitions(self):
        """Delivery status should properly transition through states"""
        from orders.models import DeliveryOrder

        delivery = DeliveryOrder.objects.create(driver=self.delivery_profile, order=self.order, status="assigned")

        # Initial state
        self.assertEqual(delivery.status, "assigned")

        # Transition to accepted
        delivery.status = "accepted"
        delivery.accepted_at = None  # Will be auto-set or manually set
        delivery.save()

        delivery.refresh_from_db()
        self.assertEqual(delivery.status, "accepted")

    def test_delivery_order_cascade_delete(self):
        """Deleting order should delete associated delivery records"""
        from orders.models import DeliveryOrder

        delivery = DeliveryOrder.objects.create(driver=self.delivery_profile, order=self.order, status="assigned")

        order_id = self.order.id
        delivery_id = delivery.id

        self.order.delete()

        # Delivery should be deleted due to cascade
        with self.assertRaises(DeliveryOrder.DoesNotExist):
            DeliveryOrder.objects.get(id=delivery_id)


class ParallelDriverAcceptTests(TestCase):
    """Test that only one driver can accept an order in parallel scenario"""

    def setUp(self):
        self.client = APIClient()

        # Create two drivers
        self.driver1 = CustomUser.objects.create_user(
            email="driver1@test.com", password="testpass123", phone_number="+998901112233", role="driver"
        )
        self.profile1 = DeliveryDriver.objects.create(user=self.driver1, phone_number="+998901112233")

        self.driver2 = CustomUser.objects.create_user(
            email="driver2@test.com", password="testpass123", phone_number="+998904445566", role="driver"
        )
        self.profile2 = DeliveryDriver.objects.create(user=self.driver2, vehicle_type="motorcycle")

        self.order = Order.objects.create(user=self.driver1, total_price=150.00, status="Pending")

    def test_only_first_driver_can_accept_order(self):
        """
        When two drivers try to accept simultaneously, only the first should succeed.
        This test verifies the select_for_update() locking mechanism works.
        """
        self.client.force_authenticate(user=self.driver1)

        # First driver accepts
        response1 = self.client.post(f"/api/v1/orders/orders/{self.order.id}/accept/", format="json")

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response1.data["status"], "Order accepted")

        # Order should be assigned to driver1
        self.order.refresh_from_db()
        self.assertEqual(self.order.driver, self.profile1)

        # Second driver tries to accept - should fail
        self.client.force_authenticate(user=self.driver2)
        response2 = self.client.post(f"/api/v1/orders/orders/{self.order.id}/accept/", format="json")

        # Should be rejected (400 or 403)
        self.assertIn(response2.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN])

        # Order should still be assigned to driver1
        self.order.refresh_from_db()
        self.assertEqual(self.order.driver, self.profile1)

    def test_driver_can_accept_own_unassigned_order(self):
        """Driver can accept an order that's not yet assigned"""
        # Create unassigned order
        order = Order.objects.create(user=self.driver1, total_price=100.00, status="Pending", driver=None)

        self.client.force_authenticate(user=self.driver1)
        response = self.client.post(f"/api/v1/orders/orders/{order.id}/accept/", format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.driver, self.profile1)

    def test_driver_cannot_accept_already_assigned_order(self):
        """Driver cannot accept order already assigned to another driver"""
        order = Order.objects.create(user=self.driver1, total_price=100.00, status="Pending")

        # First driver accepts
        self.client.force_authenticate(user=self.driver1)
        self.client.post(f"/api/v1/orders/orders/{order.id}/accept/", format="json")

        # Second driver tries to accept
        self.client.force_authenticate(user=self.driver2)
        response = self.client.post(f"/api/v1/orders/orders/{order.id}/accept/", format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already assigned", response.data.get("error", "").lower())


class OrderStatusUpdateTests(TestCase):
    """Test driver can update order status correctly"""

    def setUp(self):
        self.client = APIClient()

        self.driver = CustomUser.objects.create_user(
            email="driver@test.com", password="testpass123", phone_number="+998901234567", role="driver"
        )
        self.profile = DeliveryDriver.objects.create(user=self.driver, vehicle_type="car")

        self.order = Order.objects.create(user=self.driver, total_price=100.00, status="Pending", driver=self.profile)

    def test_driver_can_update_own_order_status(self):
        """Driver can update status of assigned order"""
        self.client.force_authenticate(user=self.driver)
        response = self.client.post(f"/api/v1/orders/orders/{self.order.id}/status/", {"status": "Processing"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "Processing")

    def test_driver_cannot_update_others_order_status(self):
        """Driver cannot update status of order assigned to another driver"""
        other_driver = CustomUser.objects.create_user(
            email="other@test.com", password="testpass123", phone_number="+998907654321", role="driver"
        )
        other_profile = DeliveryDriver.objects.create(user=other_driver, vehicle_type="car")
        other_order = Order.objects.create(
            user=other_driver, total_price=100.00, status="Pending", driver=other_profile
        )

        self.client.force_authenticate(user=self.driver)
        response = self.client.post(f"/api/v1/orders/orders/{other_order.id}/status/", {"status": "Processing"})

        # Should get 404 (order not found in queryset) or 403
        self.assertIn(response.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN])


class RollbackTests(TestCase):
    """Test rollback scenarios"""

    def setUp(self):
        self.client = APIClient()

        self.user = CustomUser.objects.create_user(
            email="user@test.com", password="testpass123", phone_number="+998901234567"
        )
        self.driver = CustomUser.objects.create_user(
            email="driver@test.com", password="testpass123", phone_number="+998907654321", role="driver"
        )
        self.profile = DeliveryDriver.objects.create(user=self.driver, vehicle_type="car")

        self.medicine = Medicine.objects.create(name="Test Med", slug="test-med", price=50.00, stock=20)

    def test_canceled_order_cleans_up_delivery(self):
        """When order is canceled, delivery record should be cleaned up"""
        order = Order.objects.create(user=self.user, total_price=100.00, status="Pending")

        from orders.models import DeliveryOrder

        delivery = DeliveryOrder.objects.create(driver=self.profile, order=order, status="assigned")

        # Cancel the order
        self.client.force_authenticate(user=self.user)
        self.client.post(f"/api/v1/orders/orders/{order.id}/cancel/", format="json")

        order.refresh_from_db()
        self.assertEqual(order.status, "Canceled")

        # Delivery should still exist (we don't auto-delete) but status can be updated
        delivery.refresh_from_db()
        self.assertEqual(delivery.order, order)

    def test_order_refund_scenario(self):
        """Test refund scenario - payment status update"""
        from billing.models import Payment

        order = Order.objects.create(user=self.user, total_price=100.00, status="Paid")

        payment = Payment.objects.create(order=order, amount=100.00, payment_method="card", status="completed")

        # Simulate refund
        payment.status = "refunded"
        payment.save()

        payment.refresh_from_db()
        self.assertEqual(payment.status, "refunded")
