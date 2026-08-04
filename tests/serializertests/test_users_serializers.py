from rest_framework import serializers
from rest_framework.test import APITestCase
from users.serializers import UserSerializer, RegisterSerializer, VerifySerializer, TelegramLoginSerializer, SubscribedUserSerializer, AdminLoginSerializer
from users.models import CustomUser, Seller, SubscribedUser, Deliverer
from django.urls import reverse
from unittest.mock import patch
import pytest
import phonenumbers
from phonenumbers import PhoneNumberFormat

pytestmark = pytest.mark.django_db

class UserSerializerTests(APITestCase):
    def setUp(self):
        self.user_data = {
            "full_name": "Test User",
            "email": "test@example.com",
            "phone_number": "+998901234567",
            "password": "StrongPassword123"
        }
        self.user = CustomUser.objects.create_user(**self.user_data)

    def test_user_serializer(self):
        serializer = UserSerializer(instance=self.user)
        data = serializer.data
        self.assertEqual(data["full_name"], self.user_data["full_name"])
        self.assertEqual(data["email"], self.user_data["email"])
        self.assertEqual(data["phone_number"], self.user_data["phone_number"])
        self.assertIn("avatar_url", data)

    def test_register_serializer_valid(self):
        data = {
            "phone_number": "+998907654321",
            "email": "newuser@example.com",
            "full_name": "New User"
        }
        serializer = RegisterSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_register_serializer_invalid_no_identifier(self):
        data = {"full_name": "New User"}
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_verify_serializer_valid(self):
        data = {"session_id": "some_session_id", "code": "123456"}
        serializer = VerifySerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_telegram_login_serializer_valid(self):
        data = {"phone_number": "+998901112233", "full_name": "Telegram User"}
        serializer = TelegramLoginSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_subscribed_user_serializer_valid_gmail(self):
        data = {"email": "test@gmail.com"}
        serializer = SubscribedUserSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        subscriber = serializer.save()
        self.assertIsInstance(subscriber, SubscribedUser)
        self.assertEqual(subscriber.email, "test@gmail.com")

    def test_subscribed_user_serializer_invalid_email_format(self):
        data = {"email": "test@example.com"} # Not gmail.com
        serializer = SubscribedUserSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_admin_login_serializer_credentials_valid(self):
        data = {"username": "admin", "password": "password", "action": "credentials"}
        serializer = AdminLoginSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_phone_number_field_valid(self):
        field = PhoneNumberField()
        valid_number = "+998901234567"
        internal_value = field.to_internal_value(valid_number)
        self.assertEqual(internal_value, valid_number)

    def test_phone_number_field_invalid(self):
        field = PhoneNumberField()
        invalid_number = "123"
        with self.assertRaises(serializers.ValidationError):
            field.to_internal_value(invalid_number)

    def test_role_determine_serializer_valid(self):
        data = {"phone_number": "+998901234567"}
        serializer = RoleDetermineSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_payout_serializer(self):
        deliverer_user = CustomUser.objects.create_user(email="driver@example.com", password="password")
        deliverer = Deliverer.objects.create(user=deliverer_user, phone_number="+998901234567", license_number="123", vehicle_type="Car")
        # Assuming a Payout model exists
        # payout = Payout.objects.create(driver=deliverer, amount=100.00, status="completed")
        # serializer = PayoutSerializer(instance=payout)
        # self.assertEqual(serializer.data["amount"], "100.00")
        # self.assertEqual(serializer.data["driver_full_name"], deliverer_user.full_name)
        pass # Placeholder as Payout model is not defined here
