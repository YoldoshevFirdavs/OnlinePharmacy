from rest_framework.test import APITestCase
from pharmacy.serializers.misc import CategorySerializer, MedicineImageSerializer, ReviewSerializer, MedicineListSerializer, MedicineDetailSerializer, FlashSaleSerializer, ProductViewHistorySerializer, CartSerializer, CartItemSerializer
from pharmacy.models.medicine import Medicine, Category
from pharmacy.models.misc import MedicineImage, Review, FlashSale, ProductViewHistory
from orders.models import Cart, CartItem
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import timedelta
from django.utils import timezone
import pytest

User = get_user_model()

pytestmark = pytest.mark.django_db

class PharmacySerializerTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="password")
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
        self.image = MedicineImage.objects.create(medicine=self.medicine, image="path/to/image.jpg", is_primary=True)
        self.review = Review.objects.create(medicine=self.medicine, user=self.user, rating=5, content="Great medicine!")
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(cart=self.cart, product=self.medicine, quantity=2)
        self.flash_sale = FlashSale.objects.create(
            product=self.medicine,
            discount_percentage=10,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(days=1)
        )
        self.product_view = ProductViewHistory.objects.create(user=self.user, product=self.medicine)

    def test_category_serializer(self):
        serializer = CategorySerializer(instance=self.category)
        data = serializer.data
        self.assertEqual(data["name"], "Painkillers")
        self.assertEqual(data["slug"], "painkillers")

    def test_medicine_image_serializer(self):
        serializer = MedicineImageSerializer(instance=self.image)
        data = serializer.data
        self.assertEqual(data["image"], "/media/path/to/image.jpg") # Assuming MEDIA_URL is /media/
        self.assertTrue(data["is_primary"])

    def test_review_serializer(self):
        serializer = ReviewSerializer(instance=self.review)
        data = serializer.data
        self.assertEqual(data["user"], self.user.full_name)
        self.assertEqual(data["rating"], 5)
        self.assertEqual(data["content"], "Great medicine!")

    def test_medicine_list_serializer(self):
        serializer = MedicineListSerializer(instance=self.medicine)
        data = serializer.data
        self.assertEqual(data["name"], "Paracetamol")
        self.assertEqual(data["category"], "Painkillers")
        self.assertEqual(float(data["price"]), 10.00)

    def test_medicine_detail_serializer(self):
        serializer = MedicineDetailSerializer(instance=self.medicine)
        data = serializer.data
        self.assertEqual(data["name"], "Paracetamol")
        self.assertIn("images", data)
        self.assertIn("reviews", data)
        self.assertEqual(data["category"]["name"], "Painkillers")

    def test_flash_sale_serializer(self):
        serializer = FlashSaleSerializer(instance=self.flash_sale)
        data = serializer.data
        self.assertEqual(data["product_details"]["name"], "Paracetamol")
        self.assertEqual(data["discount_percentage"], 10)
        self.assertTrue(data["is_active"])

    def test_product_view_history_serializer(self):
        serializer = ProductViewHistorySerializer(instance=self.product_view)
        data = serializer.data
        self.assertEqual(data["product"]["name"], "Paracetamol")

    def test_cart_item_serializer(self):
        serializer = CartItemSerializer(instance=self.cart_item)
        data = serializer.data
        self.assertEqual(data["product_details"]["name"], "Paracetamol")
        self.assertEqual(data["quantity"], 2)
        self.assertEqual(float(data["total_price"]), 20.00)

    def test_cart_serializer(self):
        serializer = CartSerializer(instance=self.cart)
        data = serializer.data
        self.assertEqual(data["user"], self.user.id)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(float(data["grand_total"]), 20.00)
