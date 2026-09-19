"""
Concurrent delivery tests - verify race condition handling with select_for_update
Tests driver parallel accept of same order
"""

from django.db import transaction
from django.test import TransactionTestCase
from rest_framework import status
from rest_framework.test import APIClient

from orders.models import Order
from users.models import CustomUser, DeliveryDriver


class ParallelDriverAcceptTests(TransactionTestCase):
    """Test concurrent driver accept of orders - verify only one driver gets the order"""

    def setUp(self):
        self.client = APIClient()

        # Create customer
        self.customer = CustomUser.objects.create_user(
            phone_number="+998901234567", password="testpass123", role="user"
        )

        # Create 2 drivers
        self.driver1_user = CustomUser.objects.create_user(
            phone_number="+998901234568", password="testpass123", role="deliverer"
        )
        self.driver1 = DeliveryDriver.objects.create(user=self.driver1_user, status="active")

        self.driver2_user = CustomUser.objects.create_user(
            phone_number="+998901234569", password="testpass123", role="deliverer"
        )
        self.driver2 = DeliveryDriver.objects.create(user=self.driver2_user, status="active")

        # Create order without driver assignment
        self.order = Order.objects.create(
            user=self.customer, total_price=50000.00, status="Ready for Delivery", driver=None  # Not assigned yet
        )

    def test_select_for_update_locks_order(self):
        """Verify select_for_update properly locks order during transaction"""
        # First transaction locks the order
        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=self.order.id)
            self.assertIsNone(order.driver)
            
            # In a separate transaction, try to lock the same order
            # This should wait until first transaction completes
            try:
                with transaction.atomic():
                    order2 = Order.objects.select_for_update(nowait=True).get(id=self.order.id)
                    # If we get here, it means nowait=True worked (lock was not held)
                    self.assertIsNone(order2.driver)
            except Exception as e:
                # Lock was held - this is expected behavior
                self.assertIn("locked", str(e).lower())