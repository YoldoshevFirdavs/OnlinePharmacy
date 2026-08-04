from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from users.models import Deliverer, CustomUser
import pytest

pytestmark = pytest.mark.django_db

class DelivererViewTests(APITestCase):
    def setUp(self):
        self.admin_user = CustomUser.objects.create_user(
            email="admin@example.com",
            password="adminpassword",
            full_name="Admin User",
            is_staff=True,
            is_superuser=True
        )
        self.deliverer_user = CustomUser.objects.create_user(
            email="deliverer@example.com",
            password="delivererpassword",
            full_name="Test Deliverer"
        )
        self.deliverer = Deliverer.objects.create(
            user=self.deliverer_user,
            phone_number="+998901234567",
            license_number="DL12345",
            vehicle_type="Motorcycle"
        )
        self.client = APIClient()
        self.list_url = reverse("deliverer-list") # Assuming a 'deliverer-list' URL name
        self.detail_url = reverse("deliverer-detail", kwargs={"pk": self.deliverer.pk}) # Assuming 'deliverer-detail'

    def test_list_deliverers_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["user"]["email"], self.deliverer_user.email)

    def test_retrieve_deliverer_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["email"], self.deliverer_user.email)

    def test_create_deliverer_onboarding(self):
        # This test assumes an onboarding endpoint for new deliverers
        # and that the user is not authenticated or uses a specific onboarding token
        onboarding_url = reverse("deliverer-onboard") # Hypothetical onboarding URL
        data = {
            "token": "valid_onboarding_token", # This token would link to a pre-registered user or invite
            "full_name": "New Onboarded Deliverer",
            "password": "securepassword123"
        }
        response = self.client.post(onboarding_url, data, format="json")
        # Assuming successful onboarding creates a user and deliverer, and returns success
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Deliverer.objects.filter(user__full_name="New Onboarded Deliverer").exists())

    def test_unauthenticated_access_to_list(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
