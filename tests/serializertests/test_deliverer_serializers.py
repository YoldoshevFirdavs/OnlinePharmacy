from rest_framework.test import APITestCase
from users.serializers import DriverSerializer, DelivererOnboardingSerializer
from users.models import Deliverer, CustomUser
import pytest

pytestmark = pytest.mark.django_db

class DelivererSerializerTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="deliverer@example.com",
            password="password123",
            full_name="Test Deliverer"
        )
        self.deliverer = Deliverer.objects.create(
            user=self.user,
            phone_number="+998901234567",
            license_number="DL12345",
            vehicle_type="Motorcycle"
        )

    def test_driver_serializer(self):
        serializer = DriverSerializer(instance=self.deliverer)
        data = serializer.data
        self.assertEqual(data["user"]["email"], self.user.email)
        self.assertEqual(data["license_number"], "DL12345")
        self.assertEqual(data["vehicle_type"], "Motorcycle")

    def test_deliverer_onboarding_serializer(self):
        # This serializer is for onboarding, so it doesn't take a Deliverer instance
        data = {
            "token": "some_onboarding_token",
            "full_name": "New Deliverer",
            "password": "newpassword123"
        }
        serializer = DelivererOnboardingSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["full_name"], "New Deliverer")
