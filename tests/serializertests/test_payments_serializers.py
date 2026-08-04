from rest_framework import serializers
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
import pytest

User = get_user_model()

# Assuming a simple Payment model and serializer for testing purposes
# In a real scenario, these would be defined in payments/models.py and payments/serializers.py
class MockPayment:
    def __init__(self, id, user, amount, status, transaction_id=None):
        self.id = id
        self.user = user
        self.amount = amount
        self.status = status
        self.transaction_id = transaction_id

class MockPaymentSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.CharField(max_length=50)
    transaction_id = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def create(self, validated_data):
        return MockPayment(id=1, **validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        return instance

class CreatePaymentIntentSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class ConfirmPaymentSerializer(serializers.Serializer):
    payment_intent_id = serializers.CharField(max_length=255)
    payment_method_id = serializers.CharField(max_length=255)


pytestmark = pytest.mark.django_db

class PaymentSerializerTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="password")
        self.payment_data = {
            "user": self.user.pk,
            "amount": "100.00",
            "status": "pending",
            "transaction_id": "pi_test123"
        }
        self.payment_instance = MockPayment(id=1, user=self.user, amount=100.00, status="pending", transaction_id="pi_test123")

    def test_mock_payment_serializer(self):
        serializer = MockPaymentSerializer(instance=self.payment_instance)
        data = serializer.data
        self.assertEqual(data["user"], self.user.pk)
        self.assertEqual(data["amount"], "100.00")
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["transaction_id"], "pi_test123")

    def test_create_payment_intent_serializer(self):
        data = {"order_id": 1, "amount": "50.00"}
        serializer = CreatePaymentIntentSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["order_id"], 1)

    def test_confirm_payment_serializer(self):
        data = {"payment_intent_id": "pi_abc123", "payment_method_id": "pm_def456"}
        serializer = ConfirmPaymentSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["payment_intent_id"], "pi_abc123")
