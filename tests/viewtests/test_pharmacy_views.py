from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from pharmacy.models.medicine import Medicine, Category
from pharmacy.models.misc import Review, FlashSale, MedicineImage
from datetime import timedelta
from django.utils import timezone
import pytest

User = get_user_model()

pytestmark = pytest.mark.django_db

class PharmacyViewTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="user@example.com", password="password")
        self.seller_user = User.objects.create_user(email="seller@example.com", password="password", is_staff=True) # Assuming is_staff implies seller for simplicity
        self.category = Category.objects.create(name="Painkillers", slug="painkillers")
        self.medicine = Medicine.objects.create(
            name="Paracetamol",
            slug="paracetamol",
            category=self.category,
            price=10.00,
            stock=100,
            short_description="Relieves pain",
            instruction="Take with water"
        )
        self.medicine_list_url = reverse("medicine-list") # Assuming 'medicine-list' URL name
        self.medicine_detail_url = reverse("medicine-detail", kwargs={"pk": self.medicine.pk}) # Assuming 'medicine-detail'
        self.category_list_url = reverse("category-list") # Assuming 'category-list' URL name
        self.review_list_url = reverse("review-list") # Assuming 'review-list' URL name
        self.flash_sale_list_url = reverse("flashsale-list") # Assuming 'flashsale-list' URL name

    def test_list_medicines(self):
        response = self.client.get(self.medicine_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Paracetamol")

    def test_retrieve_medicine(self):
        response = self.client.get(self.medicine_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Paracetamol")
        self.assertIn("reviews", response.data)

    def test_create_medicine_as_seller(self):
        self.client.force_authenticate(user=self.seller_user)
        new_medicine_data = {
            "name": "Ibuprofen",
            "slug": "ibuprofen",
            "category": self.category.pk,
            "price": 15.00,
            "stock": 50,
            "short_description": "Reduces inflammation",
            "instruction": "Take after food"
        }
        response = self.client.post(self.medicine_list_url, new_medicine_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Medicine.objects.filter(name="Ibuprofen").exists())

    def test_create_medicine_unauthenticated(self):
        new_medicine_data = {
            "name": "Aspirin",
            "slug": "aspirin",
            "category": self.category.pk,
            "price": 5.00,
            "stock": 200,
            "short_description": "Blood thinner",
            "instruction": "Consult doctor"
        }
        response = self.client.post(self.medicine_list_url, new_medicine_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_categories(self):
        response = self.client.get(self.category_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Painkillers")

    def test_create_review(self):
        self.client.force_authenticate(user=self.user)
        review_data = {
            "medicine": self.medicine.pk,
            "rating": 4,
            "content": "Good product."
        }
        response = self.client.post(self.review_list_url, review_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Review.objects.filter(content="Good product.").exists())

    def test_list_flash_sales(self):
        FlashSale.objects.create(
            product=self.medicine,
            discount_percentage=20,
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=1)
        )
        response = self.client.get(self.flash_sale_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["product_details"]["name"], "Paracetamol")
