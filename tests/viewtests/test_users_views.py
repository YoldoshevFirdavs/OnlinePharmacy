from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
import pytest

User = get_user_model()

pytestmark = pytest.mark.django_db

class UserViewTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_data = {
            "full_name": "Test User",
            "email": "test@example.com",
            "phone_number": "+998901234567",
            "password": "StrongPassword123"
        }
        self.user = User.objects.create_user(**self.user_data)
        self.register_url = reverse("register") # Assuming 'register' URL name
        self.login_url = reverse("login") # Assuming 'login' URL name
        self.profile_url = reverse("profile") # Assuming 'profile' URL name
        self.change_password_url = reverse("change-password") # Assuming 'change-password' URL name

    def test_user_registration(self):
        new_user_data = {
            "full_name": "New User",
            "email": "new@example.com",
            "phone_number": "+998907654321",
            "password": "NewStrongPassword123"
        }
        response = self.client.post(self.register_url, new_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="new@example.com").exists())

    def test_user_login(self):
        response = self.client.post(self.login_url, {"email": self.user_data["email"], "password": self.user_data["password"]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_retrieve_user_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user.email)

    def test_update_user_profile(self):
        self.client.force_authenticate(user=self.user)
        updated_data = {"full_name": "Updated Name", "address": "New Address"}
        response = self.client.patch(self.profile_url, updated_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Updated Name")
        self.assertEqual(self.user.address, "New Address")

    def test_change_password(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.change_password_url, {"old_password": self.user_data["password"], "new_password": "EvenStrongerPassword123"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("EvenStrongerPassword123"))

    def test_unauthenticated_access_to_profile(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
