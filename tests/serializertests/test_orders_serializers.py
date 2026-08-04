from rest_framework.test import APITestCase
from orders.serializers import OrderItemSerializer, OrderSerializer, CartItemSerializer, CartSummarySerializer, OrderDeliverySerializer, DriverOrderSerializer, OrderListSerializer, OrderDetailSerializer, OrderStatusUpdateSerializer, ArrivalSerializer, LocationSerializer
from orders.models import Order, OrderItem, Cart, CartItem, OrderDelivery
from pharmacy.models.medicine import Medicine, Category
from users.models import CustomUser, Deliverer
from django.urls import reverse
from django.utils import timezone
import pytest

pytestmark = pytest.mark.django_db

class OrderSerializerTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(email="customer@example.com", password="password")
        self.deliverer_user = CustomUser.objects.create_user(email="deliverer@example.com", password="password")
        self.deliverer = Deliverer.objects.create(user=self.deliverer_user, phone_number="+998901234567", license_number="DL123", vehicle_type="Car")
        self.category = Category.objects.create(name="Painkillers", slug="painkillers")
        self.medicine1 = Medicine.objects.create(name="Paracetamol", slug="paracetamol", category=self.category, price=10.00, stock=100)
        self.medicine2 = Medicine.objects.create(name="Ibuprofen", slug="ibuprofen", category=self.category, price=15.00, stock=50)

        self.cart = Cart.objects.create(user=self.user)
        self.cart_item1 = CartItem.objects.create(cart=self.cart, product=self.medicine1, quantity=2)
        self.cart_item2 = CartItem.objects.create(cart=self.cart, product=self.medicine2, quantity=1)

        self.order = Order.objects.create(customer=self.user, address="123 Main St", status="Pending")
        self.order_item1 = OrderItem.objects.create(order=self.order, product=self.medicine1, quantity=2, price_at_order=10.00)
        self.order_item2 = OrderItem.objects.create(order=self.order, product=self.medicine2, quantity=1, price_at_order=15.00)
        self.order_delivery = OrderDelivery.objects.create(order=self.order, driver=self.deliverer)


    def test_order_item_serializer(self):
        serializer = OrderItemSerializer(instance=self.order_item1)
        data = serializer.data
        self.assertEqual(data["product_name"], "Paracetamol")
        self.assertEqual(data["quantity"], 2)
        self.assertEqual(float(data["price_at_order"]), 10.00)

    def test_order_serializer_create(self):
        # Ensure cart is not empty for this test
        CartItem.objects.create(cart=self.cart, product=self.medicine1, quantity=1)
        
        serializer = OrderSerializer(data={"address": "456 New St"}, context={"request": self.client.request()._request})
        serializer.context["request"].user = self.user # Manually set user for serializer context
        self.assertTrue(serializer.is_valid())
        order = serializer.save()
        self.assertIsInstance(order, Order)
        self.assertEqual(order.customer, self.user)
        self.assertEqual(order.order_items.count(), 1) # Only one item from the cart created in this test
        self.assertEqual(order.total_price, 10.00) # Price of the single item

    def test_order_serializer_create_empty_cart(self):
        self.cart.cartitem_set.all().delete() # Empty the cart
        serializer = OrderSerializer(data={"address": "456 New St"}, context={"request": self.client.request()._request})
        serializer.context["request"].user = self.user
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_cart_item_serializer_validate_quantity(self):
        data = {"product": self.medicine1.pk, "quantity": 101} # More than stock
        serializer = CartItemSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("quantity", serializer.errors)

        data = {"product": self.medicine1.pk, "quantity": 50} # Valid quantity
        serializer = CartItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_cart_summary_serializer(self):
        serializer = CartSummarySerializer(instance=self.cart)
        data = serializer.data
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(float(data["grand_total"]), 35.00) # 2*10 + 1*15

    def test_order_delivery_serializer(self):
        serializer = OrderDeliverySerializer(instance=self.order_delivery)
        data = serializer.data
        self.assertEqual(data["order"], self.order.pk)
        self.assertEqual(data["driver"], self.deliverer.pk)

    def test_driver_order_serializer(self):
        serializer = DriverOrderSerializer(instance=self.order)
        data = serializer.data
        self.assertEqual(data["customer_full_name"], self.user.full_name)
        self.assertEqual(data["driver"], self.deliverer.pk)
        self.assertIn("order_items", data)
        self.assertIn("delivery_details", data)

    def test_order_list_serializer(self):
        serializer = OrderListSerializer(instance=self.order)
        data = serializer.data
        self.assertEqual(data["id"], self.order.pk)
        self.assertEqual(data["status"], "Pending")
        self.assertEqual(float(data["total_price"]), 35.00) # 2*10 + 1*15
        self.assertIn("short_address", data)

    def test_order_detail_serializer(self):
        serializer = OrderDetailSerializer(instance=self.order)
        data = serializer.data
        self.assertEqual(data["id"], self.order.pk)
        self.assertEqual(data["customer"], self.user.pk)
        self.assertIn("order_items", data)
        self.assertIn("delivery_details", data)

    def test_order_status_update_serializer(self):
        data = {"status": "Accepted"}
        serializer = OrderStatusUpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["status"], "Accepted")

        data = {"status": "InvalidStatus"}
        serializer = OrderStatusUpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("status", serializer.errors)

    def test_arrival_serializer(self):
        data = {"arrived_at": timezone.now()}
        serializer = ArrivalSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        data = {"arrived_at": timezone.now() + timedelta(days=1)} # Future date
        serializer = ArrivalSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("arrived_at", serializer.errors)

    def test_location_serializer(self):
        data = {"lat": 41.2995, "lng": 69.2401}
        serializer = LocationSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        data = {"lat": 41.2995, "lng": 69.2401, "timestamp": timezone.now() + timedelta(days=1)} # Future timestamp
        serializer = LocationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("timestamp", serializer.errors)
