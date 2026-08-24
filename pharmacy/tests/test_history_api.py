"""
Unit and integration tests for CustomerUserHistory (immutable audit log)
Tests: Model immutability, API endpoints, action logging
"""

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from pharmacy.models.history import CustomerUserHistory
from pharmacy.models.medicine import Category, Medicine
from users.models import CustomUser


class CustomerUserHistoryModelTestCase(TestCase):
    """Test CustomerUserHistory model immutability"""

    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(phone_number="+998901234567", password="test123")
        cls.category = Category.objects.create(name="Test", slug="test")
        cls.product = Medicine.objects.create(
            name="Test Product", slug="test-product", category=cls.category, price=100.0
        )

    def test_create_history_record(self):
        """Test creating a history record"""
        history = CustomerUserHistory.objects.create(
            user=self.user,
            product=self.product,
            action="view_product",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0",
        )

        self.assertEqual(history.user.id, self.user.id)
        self.assertEqual(history.product.id, self.product.id)
        self.assertEqual(history.action, "view_product")

    def test_history_record_immutable_on_save(self):
        """Test that history records cannot be modified after creation"""
        history = CustomerUserHistory.objects.create(
            user=self.user, product=self.product, action="view_product", ip_address="127.0.0.1"
        )

        # Try to update - should raise ValueError
        history.action = "add_to_cart"
        with self.assertRaises(ValueError):
            history.save()

    def test_history_record_immutable_on_delete(self):
        """Test that history records cannot be deleted"""
        history = CustomerUserHistory.objects.create(
            user=self.user, product=self.product, action="view_product", ip_address="127.0.0.1"
        )

        # Try to delete - should raise ValueError
        with self.assertRaises(ValueError):
            history.delete()

    def test_history_with_meta(self):
        """Test creating history with JSON metadata"""
        meta = {"quantity": 2, "variant": "large"}
        history = CustomerUserHistory.objects.create(
            user=self.user, product=self.product, action="add_to_cart", meta=meta, ip_address="127.0.0.1"
        )

        self.assertEqual(history.meta["quantity"], 2)
        self.assertEqual(history.meta["variant"], "large")

    def test_history_ordering(self):
        """Test history records are ordered by timestamp (newest first)"""
        h1 = CustomerUserHistory.objects.create(
            user=self.user, product=self.product, action="view_product", ip_address="127.0.0.1"
        )
        h2 = CustomerUserHistory.objects.create(
            user=self.user, product=self.product, action="add_to_cart", ip_address="127.0.0.1"
        )

        histories = CustomerUserHistory.objects.filter(user=self.user)
        self.assertEqual(histories[0].id, h2.id)
        self.assertEqual(histories[1].id, h1.id)


class CustomerUserHistoryAPITestCase(APITestCase):
    """Integration tests for UserHistory API endpoints"""

    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(
            phone_number="+998901234567", password="test123", full_name="Test User"
        )
        cls.admin = CustomUser.objects.create_user(phone_number="+998909999999", password="admin123", is_staff=True)
        cls.category = Category.objects.create(name="Test", slug="test")
        cls.product = Medicine.objects.create(
            name="Test Product", slug="test-product", category=cls.category, price=100.0
        )

    def setUp(self):
        self.client = APIClient()

    def test_get_user_history_list(self):
        """Test getting paginated user history"""
        # Create some history records
        for i in range(5):
            CustomerUserHistory.objects.create(
                user=self.user, product=self.product, action="view_product", ip_address="127.0.0.1"
            )

        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/user/history/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 5)

    def test_log_action_endpoint(self):
        """Test logging action via API"""
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/v1/user/history/log/", {"action": "view_product", "product_id": self.product.id}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        history = CustomerUserHistory.objects.filter(user=self.user).first()
        self.assertEqual(history.action, "view_product")
        self.assertEqual(history.product.id, self.product.id)

    def test_history_pagination(self):
        """Test history pagination"""
        # Create 60 records (more than default page size)
        for i in range(60):
            CustomerUserHistory.objects.create(
                user=self.user, product=self.product, action="view_product", ip_address="127.0.0.1"
            )

        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/user/history/?page_size=50")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 50)
        self.assertTrue(response.data["next"] is not None)  # Should have next page

    def test_history_read_only(self):
        """Test that history is read-only via API"""
        history = CustomerUserHistory.objects.create(
            user=self.user, product=self.product, action="view_product", ip_address="127.0.0.1"
        )

        self.client.force_authenticate(user=self.user)
        # Try to update - should fail
        response = self.client.patch(f"/api/v1/user/history/{history.id}/", {"action": "add_to_cart"})

        # Should be method not allowed or forbidden
        self.assertIn(response.status_code, [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_403_FORBIDDEN])

    def test_unauthenticated_cannot_access_history(self):
        """Test that unauthenticated users can't access history"""
        response = self.client.get("/api/v1/user/history/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_different_users_see_own_history(self):
        """Test that users see only their own history"""
        other_user = CustomUser.objects.create_user(phone_number="+998901234568", password="test123")

        # Create history for user 1
        CustomerUserHistory.objects.create(
            user=self.user, product=self.product, action="view_product", ip_address="127.0.0.1"
        )

        # Create history for user 2
        CustomerUserHistory.objects.create(
            user=other_user, product=self.product, action="add_to_cart", ip_address="127.0.0.1"
        )

        # User 1 should only see their own history
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/user/history/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["action"], "view_product")
