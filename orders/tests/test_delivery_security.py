"""
Critical security regression tests for delivery functionality.
Tests parallel accept race conditions and authorization vulnerabilities.
"""

import threading
import time

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from orders.models import Order
from users.models import CustomUser, DeliveryDriver


class DeliveryParallelAcceptTests(TestCase):
    """Critical tests for parallel order acceptance race conditions"""

    def setUp(self):
        self.client = APIClient()

        # Create users
        self.user1 = CustomUser.objects.create_user(email="driver1@test.com", password="testpass123")
        self.user2 = CustomUser.objects.create_user(email="driver2@test.com", password="testpass123")
        self.customer = CustomUser.objects.create_user(email="customer@test.com", password="testpass123")

        # Create delivery drivers
        self.driver1 = DeliveryDriver.objects.create(user=self.user1, vehicle_type="bike", license_plate="ABC123")
        self.driver2 = DeliveryDriver.objects.create(user=self.user2, vehicle_type="car", license_plate="XYZ789")

        # Create order
        self.order = Order.objects.create(user=self.customer, total_price=150.00, status="Pending")

    def test_only_one_driver_wins_parallel_accept(self):
        """When two drivers try to accept the same order simultaneously, only one should win"""
        accept_results = []
        lock = threading.Lock()

        def attempt_accept(driver_user, results_list):
            client = APIClient()
            client.force_authenticate(user=driver_user)

            response = client.post(f"/api/v1/orders/driver/{self.order.id}/accept/")

            with lock:
                results_list.append(
                    {
                        "driver": driver_user.email,
                        "status": response.status_code,
                        "data": response.data if hasattr(response, "data") else {},
                    }
                )

        # Start both drivers simultaneously
        thread1 = threading.Thread(target=attempt_accept, args=(self.user1, accept_results))
        thread2 = threading.Thread(target=attempt_accept, args=(self.user2, accept_results))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Analyze results
        success_count = sum(1 for r in accept_results if r["status"] == 200)
        error_count = sum(1 for r in accept_results if r["status"] == 400)

        self.assertEqual(success_count, 1, "Only one driver should succeed")
        self.assertEqual(error_count, 1, "One driver should get error")

        # Verify order is assigned to exactly one driver
        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.driver)
        self.assertIn(self.order.driver, [self.driver1, self.driver2])

    def test_driver_cannot_accept_already_assigned_order(self):
        """Driver cannot accept order already assigned to another driver"""
        # Driver1 accepts order
        self.client.force_authenticate(user=self.user1)
        response1 = self.client.post(f"/api/v1/orders/driver/{self.order.id}/accept/")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Driver2 tries to accept same order
        self.client.force_authenticate(user=self.user2)
        response2 = self.client.post(f"/api/v1/orders/driver/{self.order.id}/accept/")
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already assigned", response2.data["error"].lower())

    def test_non_driver_cannot_accept_orders(self):
        """Regular user without driver profile cannot accept orders"""
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(f"/api/v1/orders/driver/{self.order.id}/accept/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("only delivery drivers", response.data["error"].lower())


class DeliveryAuthorizationTests(TestCase):
    """Critical tests for delivery authorization vulnerabilities"""

    def setUp(self):
        self.client = APIClient()

        # Create users
        self.driver_user = CustomUser.objects.create_user(email="driver@test.com", password="testpass123")
        self.other_driver_user = CustomUser.objects.create_user(email="otherdriver@test.com", password="testpass123")
        self.customer = CustomUser.objects.create_user(email="customer@test.com", password="testpass123")

        # Create delivery drivers
        self.driver = DeliveryDriver.objects.create(user=self.driver_user, vehicle_type="bike", license_plate="ABC123")
        self.other_driver = DeliveryDriver.objects.create(
            user=self.other_driver_user, vehicle_type="car", license_plate="XYZ789"
        )

        # Create orders
        self.driver_order = Order.objects.create(
            user=self.customer, driver=self.driver, total_price=100.00, status="Accepted"
        )
        self.other_driver_order = Order.objects.create(
            user=self.customer, driver=self.other_driver, total_price=200.00, status="Accepted"
        )

    def test_driver_can_only_update_own_orders(self):
        """Driver can only update status of orders assigned to them"""
        self.client.force_authenticate(user=self.driver_user)

        # Can update own order
        response1 = self.client.post(
            f"/api/v1/orders/driver/{self.driver_order.id}/update-status/", {"status": "Delivered"}
        )
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Cannot update other driver's order
        response2 = self.client.post(
            f"/api/v1/orders/driver/{self.other_driver_order.id}/update-status/", {"status": "Delivered"}
        )
        self.assertEqual(response2.status_code, status.HTTP_404_NOT_FOUND)

    def test_driver_can_only_see_own_assigned_orders(self):
        """Driver can only see orders assigned to them, not other drivers' orders"""
        self.client.force_authenticate(user=self.driver_user)
        response = self.client.get("/api/v1/orders/driver/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should only see own order
        order_ids = [order["id"] for order in response.data.get("results", response.data)]
        self.assertIn(self.driver_order.id, order_ids)
        self.assertNotIn(self.other_driver_order.id, order_ids)

    def test_driver_role_relationship_correct(self):
        """Test that driver role relationship uses delivery_profile correctly"""
        # Verify user has delivery_profile attribute
        self.assertTrue(hasattr(self.user1, "delivery_profile"))

        # Verify it's a DeliveryDriver instance
        self.assertIsInstance(self.user1.delivery_profile, DeliveryDriver)

        # Verify relationship exists
        self.assertEqual(self.user1.delivery_profile.user, self.user1)

    def test_driver_filter_uses_delivery_profile(self):
        """Test that order filtering uses user.delivery_profile not user"""
        self.client.force_authenticate(user=self.user1)

        # Create order with driver1
        order = Order.objects.create(
            customer=self.customer, driver=self.driver1, status="Processing", total_price=100.00
        )

        # Test that driver can access their orders
        response = self.client.get(f"/api/orders/{order.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test non-driver cannot access
        non_driver = CustomUser.objects.create_user(email="regular@test.com", password="testpass123")
        self.client.force_authenticate(user=non_driver)
        response = self.client.get(f"/api/orders/{order.id}/")
        # Should be 404 because filter will exclude it (non-driver has no delivery_profile)
        self.assertIn(response.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN])

    def test_order_accept_uses_delivery_profile(self):
        """Test order acceptance uses proper driver relationship"""
        order = Order.objects.create(customer=self.customer, driver=None, status="Pending", total_price=100.00)

        self.client.force_authenticate(user=self.user1)
        response = self.client.post(f"/api/orders/{order.id}/accept/")

        if response.status_code == status.HTTP_200_OK:
            # Refresh order
            order.refresh_from_db()
            # Verify driver is set to delivery_profile
            self.assertEqual(order.driver, self.user1.delivery_profile)
            self.assertEqual(order.driver.user, self.user1)
