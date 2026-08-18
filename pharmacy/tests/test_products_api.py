"""
Unit and integration tests for Products API
Tests: Filtering, pagination, search suggestions, serializers
"""

from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from pharmacy.models.medicine import Medicine, Category
from users.models import CustomUser, Seller


class ProductFilterTestCase(APITestCase):
    """Test product filtering and search"""
    
    @classmethod
    def setUpTestData(cls):
        cls.cat1 = Category.objects.create(name="Vitaminlar", slug="vitaminlar")
        cls.cat2 = Category.objects.create(name="Antibiotiklar", slug="antibiotiklar")
        
        cls.seller_user = CustomUser.objects.create_user(
            phone_number="+998901234567",
            password="test123"
        )
        cls.seller = Seller.objects.create(
            user=cls.seller_user,
            shop_name="Test Shop",
            description="Test"
        )
        
        # Create test products
        Medicine.objects.create(
            name="Vitamin C",
            slug="vitamin-c",
            category=cls.cat1,
            price=50.0,
            brand="GenericBrand",
            is_active=True,
            average_rating=4.5,
            reviews_count=10,
            seller=cls.seller
        )
        Medicine.objects.create(
            name="Vitamin D",
            slug="vitamin-d",
            category=cls.cat1,
            price=75.0,
            brand="GenericBrand",
            is_active=True,
            average_rating=4.8,
            reviews_count=25,
            seller=cls.seller
        )
        Medicine.objects.create(
            name="Amoxicillin",
            slug="amoxicillin",
            category=cls.cat2,
            price=200.0,
            brand="Pharma",
            is_active=True,
            average_rating=4.9,
            reviews_count=50,
            seller=cls.seller
        )
    
    def setUp(self):
        self.client = APIClient()
    
    def test_get_all_products(self):
        """Test getting all products"""
        response = self.client.get('/api/v1/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
    
    def test_filter_by_category(self):
        """Test filtering products by category"""
        response = self.client.get(f'/api/v1/products/?category={self.cat1.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
    
    def test_filter_by_price_range(self):
        """Test filtering products by price"""
        response = self.client.get('/api/v1/products/?price_min=50&price_max=100')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)  # C and D vitamins
    
    def test_filter_by_brand(self):
        """Test filtering products by brand"""
        response = self.client.get('/api/v1/products/?brand=GenericBrand')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
    
    def test_filter_by_rating(self):
        """Test filtering products by rating"""
        response = self.client.get('/api/v1/products/?rating_min=4.8')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 2)
    
    def test_search_products(self):
        """Test searching products by name"""
        response = self.client.get('/api/v1/products/?search=Vitamin')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
    
    def test_pagination(self):
        """Test product pagination"""
        response = self.client.get('/api/v1/products/?page_size=2')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertTrue(response.data['next'] is not None)
    
    def test_sorting_by_price_asc(self):
        """Test sorting products by price ascending"""
        response = self.client.get('/api/v1/products/?ordering=price')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prices = [p['price'] for p in response.data['results']]
        self.assertEqual(prices, sorted(prices))
    
    def test_sorting_by_rating_desc(self):
        """Test sorting products by rating descending"""
        response = self.client.get('/api/v1/products/?ordering=-average_rating')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ratings = [p['average_rating'] for p in response.data['results']]
        self.assertEqual(ratings, sorted(ratings, reverse=True))


class ProductSuggestionsTestCase(APITestCase):
    """Test product search suggestions endpoint"""
    
    @classmethod
    def setUpTestData(cls):
        cat = Category.objects.create(name="Test", slug="test")
        seller_user = CustomUser.objects.create_user(
            phone_number="+998901234567",
            password="test123"
        )
        seller = Seller.objects.create(
            user=seller_user,
            shop_name="Shop",
            description="Test"
        )
        
        for name in ["Aspirin", "Aspirin Plus", "Acetaminophen", "Ibuprofen"]:
            Medicine.objects.create(
                name=name,
                slug=name.lower().replace(' ', '-'),
                category=cat,
                price=50.0,
                is_active=True,
                average_rating=4.5,
                reviews_count=10,
                seller=seller
            )
    
    def setUp(self):
        self.client = APIClient()
    
    def test_get_suggestions(self):
        """Test getting search suggestions"""
        response = self.client.get('/api/v1/products/suggest/?query=asp')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
    
    def test_suggestions_return_top_10(self):
        """Test suggestions return top 10 results"""
        # Create 15 products starting with 'A'
        cat = Category.objects.first()
        seller = Seller.objects.first()
        for i in range(15):
            Medicine.objects.create(
                name=f"Aspirin {i}",
                slug=f"aspirin-{i}",
                category=cat,
                price=50.0,
                is_active=True,
                average_rating=4.5,
                reviews_count=10,
                seller=seller
            )
        
        response = self.client.get('/api/v1/products/suggest/?query=asp')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data), 10)
    
    def test_suggestions_include_basic_info(self):
        """Test suggestions include id, name, rating, price"""
        response = self.client.get('/api/v1/products/suggest/?query=asp')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        if len(response.data) > 0:
            suggestion = response.data[0]
            self.assertIn('id', suggestion)
            self.assertIn('name', suggestion)
            self.assertIn('rating', suggestion)
            self.assertIn('price', suggestion)


class ProductSerializerTestCase(TestCase):
    """Test product serializers"""
    
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Test", slug="test")
        seller_user = CustomUser.objects.create_user(
            phone_number="+998901234567",
            password="test123",
            full_name="Seller Name"
        )
        cls.seller = Seller.objects.create(
            user=seller_user,
            shop_name="Test Shop",
            description="Test seller"
        )
        
        cls.product = Medicine.objects.create(
            name="Test Product",
            slug="test-product",
            category=cls.cat,
            price=100.0,
            brand="TestBrand",
            is_active=True,
            average_rating=4.5,
            reviews_count=10,
            seller=cls.seller
        )
    
    def test_product_list_serializer(self):
        """Test product list serializer includes seller info"""
        from pharmacy.serializers.misc import MedicineListSerializer
        serializer = MedicineListSerializer(self.product)
        data = serializer.data
        
        self.assertEqual(data['name'], 'Test Product')
        self.assertEqual(data['price'], 100.0)
        self.assertIn('seller', data)
        self.assertEqual(data['seller']['shop_name'], 'Test Shop')
