"""
Critical security regression tests for object-level permissions.
Tests review ownership, category permissions, and authorization vulnerabilities.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from pharmacy.models.medicine import Category
from pharmacy.models.misc import Review
from users.models import CustomUser


class ReviewOwnershipSecurityTests(TestCase):
    """Critical tests for review ownership and object-level permissions"""

    def setUp(self):
        self.client = APIClient()

        # Create users
        self.user1 = CustomUser.objects.create_user(email="user1@test.com", password="testpass123")
        self.user2 = CustomUser.objects.create_user(email="user2@test.com", password="testpass123")
        self.admin = CustomUser.objects.create_user(email="admin@test.com", password="adminpass123", is_staff=True)

        # Create reviews
        self.review_user1 = Review.objects.create(
            user=self.user1, medicine=None, rating=5, content="Great product!", is_approved=True  # For testing only
        )
        self.review_user2 = Review.objects.create(
            user=self.user2, medicine=None, rating=3, content="Average product", is_approved=True
        )

    def test_user_cannot_update_another_users_review(self):
        """User cannot update or delete another user's review"""
        self.client.force_authenticate(user=self.user1)

        # Try to update user2's review
        response = self.client.patch(f"/api/v1/products/reviews/{self.review_user2.id}/", {"comment": "Hacked review!"})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Original review should remain unchanged
        self.review_user2.refresh_from_db()
        self.assertEqual(self.review_user2.comment, "Average product")

    def test_user_can_update_own_review(self):
        """User can update their own review"""
        self.client.force_authenticate(user=self.user1)

        response = self.client.patch(
            f"/api/v1/products/reviews/{self.review_user1.id}/", {"comment": "Updated my review"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.review_user1.refresh_from_db()
        self.assertEqual(self.review_user1.comment, "Updated my review")

    def test_user_cannot_delete_another_users_review(self):
        """User cannot delete another user's review"""
        self.client.force_authenticate(user=self.user1)

        response = self.client.delete(f"/api/v1/products/reviews/{self.review_user2.id}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Review should still exist
        self.assertTrue(Review.objects.filter(id=self.review_user2.id).exists())

    def test_anonymous_cannot_create_review(self):
        """Anonymous user cannot create review"""
        response = self.client.post("/api/v1/products/reviews/", {"rating": 5, "comment": "Anonymous review"})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CategoryPermissionSecurityTests(TestCase):
    """Critical tests for category permissions"""

    def setUp(self):
        self.client = APIClient()

        # Create users
        self.user = CustomUser.objects.create_user(email="user@test.com", password="testpass123")
        self.admin = CustomUser.objects.create_user(email="admin@test.com", password="adminpass123", is_staff=True)

        # Create category
        self.category = Category.objects.create(name="Test Category", slug="test-category")

    def test_anonymous_can_view_categories(self):
        """Anonymous user can view categories"""
        response = self.client.get("/api/v1/products/categories/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_cannot_create_category(self):
        """Anonymous user cannot create category"""
        response = self.client.post("/api/v1/products/categories/", {"name": "New Category", "slug": "new-category"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_create_category(self):
        """Regular user without admin privileges cannot create category"""
        self.client.force_authenticate(user=self.user)

        response = self.client.post("/api/v1/products/categories/", {"name": "New Category", "slug": "new-category"})

        # Should return 403 or 401 depending on implementation
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED])

    def test_admin_can_create_category(self):
        """Admin user can create category"""
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            "/api/v1/products/categories/", {"name": "Admin Category", "slug": "admin-category"}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify category was created
        self.assertTrue(Category.objects.filter(slug="admin-category").exists())


class RollbackTransactionTests(TestCase):
    """Critical tests for transaction rollback scenarios"""

    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(email="user@test.com", password="testpass123")
        self.client.force_authenticate(user=self.user)

    def test_failed_transaction_does_not_create_partial_data(self):
        """When transaction fails, no partial data should be created"""
        initial_category_count = Category.objects.count()

        # Try to create category with invalid data that will fail
        response = self.client.post(
            "/api/v1/products/categories/", {"name": "", "slug": "test-category"}  # Invalid - empty name
        )

        self.assertNotEqual(response.status_code, status.HTTP_201_CREATED)

        # No new category should be created
        final_category_count = Category.objects.count()
        self.assertEqual(initial_category_count, final_category_count)
