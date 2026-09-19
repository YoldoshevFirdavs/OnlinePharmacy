"""
Concurrent delivery tests - verify race condition handling with select_for_update
Tests driver parallel accept of same order
"""

from django.db import transaction
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from orders.models import Order
from users.models import CustomUser, DeliveryDriver


class ParallelDriverAcceptTests(TestCase):
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

    def test_parallel_driver_accept_only_one_wins(self):
        """Two drivers trying to accept same order simultaneously - only one should win"""
        from threading import Thread

        from django.db.utils import OperationalError

        results = {}

        def driver_accept(driver_user, driver_profile, driver_name):
            """Simulate driver accepting order"""
            try:
                # Use select_for_update to lock the order with timeout
                with transaction.atomic():
                    order = Order.objects.select_for_update(nowait=True).get(id=self.order.id)

                    # Check if order already assigned
                    if order.driver is not None:
                        results[driver_name] = {"status": "FAILED", "reason": "Already assigned"}
                        return

                    # Assign to this driver
                    order.driver = driver_profile
                    order.status = "Accepted"
                    order.save()

                    results[driver_name] = {"status": "SUCCESS", "driver_id": driver_profile.id}
            except OperationalError as e:
                # Database lock timeout - another transaction holds the lock
                results[driver_name] = {"status": "FAILED", "reason": "Database locked"}
            except Exception as e:
                results[driver_name] = {"status": "ERROR", "error": str(e)}

        # Simulate two drivers accepting in parallel
        thread1 = Thread(target=driver_accept, args=(self.driver1_user, self.driver1, "driver1"))
        thread2 = Thread(target=driver_accept, args=(self.driver2_user, self.driver2, "driver2"))

        # Start threads simultaneously
        thread1.start()
        thread2.start()

        # Wait for completion
        thread1.join()
        thread2.join()

        # Verify results
        success_count = sum(1 for r in results.values() if r["status"] == "SUCCESS")
        failed_count = sum(1 for r in results.values() if r["status"] == "FAILED")

        # Exactly ONE should succeed, ONE should fail
        self.assertEqual(success_count, 1, f"Exactly one driver should succeed. Results: {results}")
        self.assertEqual(failed_count, 1, f"Exactly one driver should fail. Results: {results}")

        # Verify order is assigned to only one driver
        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.driver)
        self.assertEqual(self.order.status, "Accepted")

        # Verify the winning driver
        winner = [r for r in results.values() if r["status"] == "SUCCESS"][0]
        self.assertEqual(self.order.driver.id, winner["driver_id"])
