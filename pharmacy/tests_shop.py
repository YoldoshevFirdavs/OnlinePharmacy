"""
Tests for Shop API endpoints
"""
from django.test import TestCase
from rest_framework.test import APIClient
from pharmacy.models.medicine import Medicine, Category


class ProductFilterTestCase(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        """Create test data"""
        # Create categories
        cls.cat1 = Category.objects.create(name="Vitaminlar", slug="vitaminlar-test")
        cls.cat2 = Category.objects.create(name="Antibiotiklar", slug="antibiotiklar-test")
        
        # Create medicines with unique slugs
        Medicine.objects.create(
            name="Aspirin",
            slug="aspirin-test-1",
            short_description="Pain relief",
            price=10.0,
            category=cls.cat1,
            is_active=True,
            average_rating=4.5,
            reviews_count=10
        )
        Medicine.objects.create(
            name="Paracetamol",
            slug="paracetamol-test-1",
            short_description="Fever reducer",
            price=50.0,
            category=cls.cat1,
            is_active=True,
            average_rating=4.8,
            reviews_count=25
        )
        Medicine.objects.create(
            name="Amoxicillin",
            slug="amoxicillin-test-1",
            short_description="Antibiotic",
            price=200.0,
            category=cls.cat2,
            is_active=True,
            average_rating=4.9,
            reviews_count=50
        )
    
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/v1/pharmacy/products/'
    
    def test_list_all_products(self):
        """Test basic list endpoint"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertEqual(response.data['count'], 3)
    
    def test_search_filter(self):
        """Test search by name"""
        response = self.client.get(f'{self.url}?q=aspirin')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Aspirin')
    
    def test_price_filter_min(self):
        """Test minimum price filter"""
        response = self.client.get(f'{self.url}?min_price=100')
        self.assertEqual(response.status_code, 200)
        # Should include Paracetamol (50 filtered out - wait, 50 < 100, check)
        # Actually: Amoxicillin (200) only
        results = response.data['results']
        for product in results:
            self.assertGreaterEqual(float(product['price']), 100)
    
    def test_price_filter_max(self):
        """Test maximum price filter"""
        response = self.client.get(f'{self.url}?max_price=100')
        self.assertEqual(response.status_code, 200)
        results = response.data['results']
        for product in results:
            self.assertLessEqual(float(product['price']), 100)
    
    def test_price_filter_range(self):
        """Test price range filter"""
        response = self.client.get(f'{self.url}?min_price=30&max_price=150')
        self.assertEqual(response.status_code, 200)
        results = response.data['results']
        # Should include Paracetamol (50)
        self.assertGreater(len(results), 0)
    
    def test_category_filter(self):
        """Test category filter"""
        response = self.client.get(f'{self.url}?category={self.cat1.id}')
        self.assertEqual(response.status_code, 200)
        results = response.data['results']
        for product in results:
            self.assertEqual(product['category'], self.cat1.id)
    
    def test_ordering_by_price_asc(self):
        """Test ordering by price ascending"""
        response = self.client.get(f'{self.url}?ordering=price')
        self.assertEqual(response.status_code, 200)
        results = response.data['results']
        prices = [float(p['price']) for p in results]
        self.assertEqual(prices, sorted(prices))
    
    def test_ordering_by_price_desc(self):
        """Test ordering by price descending"""
        response = self.client.get(f'{self.url}?ordering=-price')
        self.assertEqual(response.status_code, 200)
        results = response.data['results']
        prices = [float(p['price']) for p in results]
        self.assertEqual(prices, sorted(prices, reverse=True))
    
    def test_pagination(self):
        """Test pagination"""
        response = self.client.get(f'{self.url}?page=1')
        self.assertEqual(response.status_code, 200)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('count', response.data)
    
    def test_page_size(self):
        """Test custom page size"""
        response = self.client.get(f'{self.url}?page_size=2')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)
