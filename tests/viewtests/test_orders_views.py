from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from orders.models import Order, OrderItem, Cart, CartItem, OrderDelivery
from pharmacy.models.medicine import Medicine, Category
from users.models import Deliverer
from django.utils import timezone
from unittest.mock import patch
import pytest

User = get_user_model()

pytestmark = pytest.mark.django_db

class OrderViewTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="customer@example.com", password="password")
        self.driver_user = User.objects.create_user(email="driver@example.com", password="password")
        self.driver = Deliverer.objects.create(user=self.driver_user, phone_number="+998901234567", license_number="DL123", vehicle_type="Car")
        self.category = Category.objects.create(name="Painkillers", slug="painkillers")
        self.medicine1 = Medicine.objects.create(name="Paracetamol", slug="paracetamol", category=self.category, price=10.00, stock=100)
        self.medicine2 = Medicine.objects.create(name="Ibuprofen", slug="ibuprofen", category=self.category, price=15.00, stock=50)

        self.cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=self.cart, product=self.medicine1, quantity=2)
        CartItem.objects.create(cart=self.cart, product=self.medicine2, quantity=1)

        self.order = Order.objects.create(customer=self.user, address="123 Main St", status="Pending")
        OrderItem.objects.create(order=self.order, product=self.medicine1, quantity=2, price_at_order=10.00)
        self.assigned_order = Order.objects.create(customer=self.user, address="456 Oak Ave", status="Assigned", driver=self.driver)

        self.cart_list_url = reverse("cart-list") # Assuming 'cart-list' URL name
        self.order_list_url = reverse("order-list") # Assuming 'order-list' URL name
        self.order_detail_url = reverse("order-detail", kwargs={"pk": self.order.pk}) # Assuming 'order-detail'
        self.driver_order_list_url = reverse("driver-orders-list") # Assuming 'driver-orders-list' URL name
        self.driver_order_detail_url = reverse("driver-orders-detail", kwargs={"pk": self.assigned_order.pk}) # Assuming 'driver-orders-detail'
        self.driver_order_accept_url = reverse("driver-orders-accept", kwargs={"pk": self.assigned_order.pk}) # Assuming 'driver-orders-accept'
        self.driver_order_status_url = reverse("driver-orders-status", kwargs={"pk": self.assigned_order.pk}) # Assuming 'driver-orders-status'
        self.driver_order_arrival_url = reverse("driver-orders-arrival", kwargs={"pk": self.assigned_order.pk}) # Assuming 'driver-orders-arrival'


    def test_list_cart_items(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.cart_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["items"]), 2)

    def test_add_item_to_cart(self):
        self.client.force_authenticate(user=self.user)
        new_medicine = Medicine.objects.create(name="Vitamin C", slug="vitaminc", category=self.category, price=5.00, stock=200)
        response = self.client.post(reverse("cart-add-item"), {"product_id": new_medicine.pk, "quantity": 3}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CartItem.objects.filter(cart__user=self.user, product=new_medicine).first().quantity, 3)

    def test_create_order_from_cart(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.order_list_url, {"address": "789 Pine St"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Order.objects.filter(customer=self.user, address="789 Pine St").exists())
        self.assertEqual(CartItem.objects.filter(cart__user=self.user).count(), 0) # Cart should be empty after order creation

    def test_cancel_order(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("order-cancel", kwargs={"pk": self.order.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "Canceled")

    def test_driver_list_assigned_orders(self):
        self.client.force_authenticate(user=self.driver_user)
        response = self.client.get(self.driver_order_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.assigned_order.pk)

    def test_driver_retrieve_order_detail(self):
        self.client.force_authenticate(user=self.driver_user)
        response = self.client.get(self.driver_order_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.assigned_order.pk)

    def test_driver_accept_order(self):
        self.client.force_authenticate(user=self.driver_user)
        response = self.client.post(self.driver_order_accept_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assigned_order.refresh_from_db()
        self.assertEqual(self.assigned_order.status, "Accepted")
        self.assertIsNotNone(self.assigned_order.accepted_at)

    def test_driver_update_order_status_picked_up(self):
        self.client.force_authenticate(user=self.driver_user)
        self.assigned_order.status = "Accepted"
        self.assigned_order.save()
        response = self.client.post(self.driver_order_status_url, {"status": "Picked Up"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assigned_order.refresh_from_db()
        self.assertEqual(self.assigned_order.status, "Picked Up")
        self.assertIsNotNone(self.assigned_order.picked_up_at)

    def test_driver_record_arrival(self):
        self.client.force_authenticate(user=self.driver_user)
        self.assigned_order.status = "On The Way"
        self.assigned_order.save()
        response = self.client.post(self.driver_order_arrival_url, {"wait_seconds": 60}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assigned_order.refresh_from_db()
        self.assertEqual(self.assigned_order.status, "Arrived")
        self.assertEqual(OrderDelivery.objects.get(order=self.assigned_order).wait_seconds, 60)
