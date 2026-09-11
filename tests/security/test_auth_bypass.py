"""
Authentication Bypass Security Tests
Tests various authentication bypass techniques
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class AuthenticationBypassTests(TestCase):
    """Test authentication bypass vulnerabilities"""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email="admin@test.com", password="adminpass123", phone_number="+998901234567"
        )
        self.user = User.objects.create_user(
            email="user@test.com", password="userpass123", phone_number="+998907654321"
        )

    def test_direct_object_reference_bypass(self):
        """Test IDOR (Insecure Direct Object Reference)"""
        # Create orders for different users
        order_admin = User.objects.create_user(
            email="orderadmin@test.com", password="pass123", phone_number="+998901112233"
        )
        order_user = User.objects.create_user(
            email="orderuser@test.com", password="pass123", phone_number="+998904445566"
        )

        from orders.models import Order

        admin_order = Order.objects.create(user=order_admin, total_price=100.00, status="Pending")
        user_order = Order.objects.create(user=order_user, total_price=200.00, status="Pending")

        # User tries to access admin's order
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/v1/orders/orders/{admin_order.id}/")

        # Should get 404 (user can't see other users' orders)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, "IDOR vulnerability detected!")

    def test_jwt_token_manipulation(self):
        """Test JWT token manipulation"""
        from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

        # Try to use expired token
        expired_token = AccessToken()
        expired_token.set_exp(from_time=timezone.now() - timezone.timedelta(hours=1))

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(expired_token)}")
        response = self.client.get("/api/v1/users/profile/")

        # Should reject expired token
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Try to tamper with token
        tampered_token = str(expired_token)[:-5] + "XXXXX"
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tampered_token}")
        response = self.client.get("/api/v1/users/profile/")

        # Should reject tampered token
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_session_hijacking_prevention(self):
        """Test session hijacking prevention"""
        # Create two sessions for same user
        self.client.force_authenticate(user=self.user)

        # First request
        response1 = self.client.get("/api/v1/users/profile/")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Try to use session from another user
        self.client.force_authenticate(user=self.admin)
        response2 = self.client.get(f"/api/v1/orders/orders/{self.user.id}/")

        # Admin should NOT be able to access user's orders directly
        # (orders are accessed by user relationship, not ID)
        self.assertIn(response2.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_role_escalation(self):
        """Test role escalation prevention"""
        # Regular user tries to login as admin
        response = self.client.post(
            "/api/v1/users/login/credentials/",
            {"email": self.admin.email, "password": self.user.password},  # Wrong password
        )

        # Should fail
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify user cannot access admin endpoints
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/dashboard/stats/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_password_reset_token_bypass(self):
        """Test password reset token security"""
        from django.contrib.auth.tokens import default_token_generator

        # Generate a valid token
        token = default_token_generator.make_token(self.user)

        # Verify token works
        self.assertTrue(default_token_generator.check_token(self.user, token))

        # Try to use expired token (manually expired)
        # This would be done in a real attack with modified token

        # Django's default_token_generator has built-in expiry
        # Test that invalid tokens are rejected
        self.assertFalse(default_token_generator.check_token(self.user, "invalid-token"))
        self.assertFalse(default_token_generator.check_token(self.user, ""))


class AuthorizationTests(TestCase):
    """Test authorization controls"""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email="admin@test.com", password="adminpass123", phone_number="+998901234567"
        )
        self.user = User.objects.create_user(
            email="user@test.com", password="userpass123", phone_number="+998907654321"
        )

    def test_admin_only_endpoints(self):
        """Test that admin endpoints require admin access"""
        from pharmacy.models.medicine import Category

        # Create a category as admin
        self.client.force_authenticate(user=self.admin)
        response = self.client.post("/api/v1/products/categories/", {"name": "Test Category", "slug": "test-category"})

        # Should succeed for admin
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Regular user tries to create category
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/products/categories/", {"name": "Hacked Category", "slug": "hacked-category"}
        )

        # Should fail for regular user
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_order_payment_authorization(self):
        """Test that users can only pay for their own orders"""
        from billing.models import Payment
        from orders.models import Order

        other_user = User.objects.create_user(email="other@test.com", password="pass123", phone_number="+998908887766")

        other_order = Order.objects.create(user=other_user, total_price=150.00, status="Pending")

        self.client.force_authenticate(user=self.user)

        # User tries to pay for other user's order
        response = self.client.post("/api/v1/payments/charge/", {"stripeToken": "tok_visa", "order_id": other_order.id})

        # Should fail - user can only pay for their own orders
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify no payment was created
        self.assertEqual(Payment.objects.count(), 0)

    def test_review_authorization(self):
        """Test that users can only edit their own reviews"""
        from pharmacy.models.medicine import Medicine

        medicine = Medicine.objects.create(
            name="Test Medicine", slug="test-medicine", price=100.00, stock=10, category=None
        )

        # User1 creates a review
        self.client.force_authenticate(user=self.user)
        response1 = self.client.post(
            "/api/v1/products/reviews/", {"medicine": medicine.id, "rating": 5, "content": "User1 review"}
        )

        review_id = response1.data["id"]
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # User2 tries to edit User1's review
        other_user = User.objects.create_user(email="other@test.com", password="pass123", phone_number="+998908887766")
        self.client.force_authenticate(user=other_user)
        response2 = self.client.patch(
            f"/api/v1/products/reviews/{review_id}/", {"rating": 1, "content": "Hacked review"}
        )

        # Should fail - User2 can't edit User1's review
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

        # Verify content wasn't changed
        response3 = self.client.get(f"/api/v1/products/reviews/{review_id}/")
        self.assertEqual(response3.data["content"], "User1 review")
