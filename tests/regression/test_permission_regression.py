"""
Permission regression tests for CI/CD.
Tests category admin flow, review ownership, and cookie refresh.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from orders.models import Order
from pharmacy.models.medicine import Category, Medicine
from users.models import CustomUser, DeliveryDriver

User = get_user_model()


class CategoryAdminFlowTests(TestCase):
    """Category admin operations must return 2xx for authorized admins"""

    def setUp(self):
        self.client = APIClient()

        # Create admin user
        self.admin = User.objects.create_superuser(
            email="admin@test.com", password="adminpass123", phone_number="+998901234567"
        )

        # Create regular user
        self.user = User.objects.create_user(
            email="user@test.com", password="userpass123", phone_number="+998907654321"
        )

        # Create category
        self.category = Category.objects.create(name="Test Category", slug="test-category")

    def test_admin_can_create_category(self):
        """Admin user can create new category (2xx response)"""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post("/api/v1/dashboard/categories/", {"name": "New Category", "slug": "new-category"})
        # Should return 2xx for successful creation
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])

    def test_admin_can_update_category(self):
        """Admin user can update category (2xx response)"""
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(f"/api/v1/dashboard/categories/{self.category.id}/", {"name": "Updated Category"})
        # Should return 2xx for successful update
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])

    def test_admin_can_delete_category(self):
        """Admin user can delete category (2xx response)"""
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f"/api/v1/dashboard/categories/{self.category.id}/")
        # Should return 2xx for successful deletion
        self.assertIn(response.status_code, [status.HTTP_204_NO_CONTENT, status.HTTP_200_OK])

    def test_regular_user_cannot_create_category(self):
        """Regular user attempting to create category gets 403"""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/dashboard/categories/", {"name": "Hacked Category", "slug": "hacked-category"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ReviewOwnershipTests(TestCase):
    """Review creation and modification must respect ownership"""

    def setUp(self):
        self.client = APIClient()

        self.user1 = User.objects.create_user(
            email="user1@test.com", password="testpass123", phone_number="+998901234567"
        )
        self.user2 = User.objects.create_user(
            email="user2@test.com", password="testpass123", phone_number="+998907654321"
        )

        self.medicine = Medicine.objects.create(name="Test Medicine", slug="test-medicine", price=100.00, stock=10)

    def test_user_can_create_review(self):
        """Authenticated user can create review"""
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(
            "/api/v1/products/reviews/", {"medicine": self.medicine.id, "rating": 5, "content": "Great product!"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_user_can_only_edit_own_review(self):
        """User can only edit their own review"""
        self.client.force_authenticate(user=self.user1)
        create_response = self.client.post(
            "/api/v1/products/reviews/", {"medicine": self.medicine.id, "rating": 4, "content": "Initial review"}
        )
        review_id = create_response.data["id"]

        # User2 tries to edit User1's review
        self.client.force_authenticate(user=self.user2)
        edit_response = self.client.patch(
            f"/api/v1/products/reviews/{review_id}/", {"rating": 1, "content": "Hacked review"}
        )
        self.assertEqual(edit_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_can_delete_own_review(self):
        """User can delete their own review"""
        self.client.force_authenticate(user=self.user1)
        create_response = self.client.post(
            "/api/v1/products/reviews/", {"medicine": self.medicine.id, "rating": 5, "content": "My review"}
        )
        review_id = create_response.data["id"]

        delete_response = self.client.delete(f"/api/v1/products/reviews/{review_id}/")
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_user_cannot_delete_others_review(self):
        """User cannot delete another user's review"""
        self.client.force_authenticate(user=self.user1)
        create_response = self.client.post(
            "/api/v1/products/reviews/", {"medicine": self.medicine.id, "rating": 5, "content": "User1 review"}
        )
        review_id = create_response.data["id"]

        # User2 tries to delete
        self.client.force_authenticate(user=self.user2)
        delete_response = self.client.delete(f"/api/v1/products/reviews/{review_id}/")
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)


class CookieRefreshTokenTests(TestCase):
    """Cookie-based token refresh must return new tokens"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@test.com", password="testpass123", phone_number="+998901234567"
        )

    @override_settings(
        SIMPLE_JWT={
            "ROTATE_REFRESH_TOKENS": True,
            "BLACKLIST_AFTER_ROTATION": True,
            "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
            "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
        }
    )
    def test_valid_refresh_token_returns_new_tokens(self):
        """Valid refresh token in cookie should return new access and refresh tokens"""
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(self.user)
        refresh_token_str = str(refresh)

        # Set refresh token in cookie
        response = self.client.post(
            "/api/v1/users/token/refresh/cookie/", {}, cookies={"refresh_token": refresh_token_str}
        )

        # Should return 200 with new tokens
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        # Tokens should be different from original
        self.assertNotEqual(response.data["access"], str(refresh.access_token))
        self.assertNotEqual(response.data["refresh"], refresh_token_str)

    def test_invalid_refresh_token_returns_401(self):
        """Invalid refresh token returns 401 Unauthorized"""
        response = self.client.post(
            "/api/v1/users/token/refresh/cookie/", {}, cookies={"refresh_token": "invalid.token.here"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_refresh_token_returns_401(self):
        """Request without refresh token cookie returns 401"""
        response = self.client.post("/api/v1/users/token/refresh/cookie/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
