"""
Pytest configuration and shared fixtures
"""

import os
import django
import pytest
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_test')
django.setup()


@pytest.fixture(scope='session')
def django_db_setup():
    """Configure Django database for tests"""
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }


@pytest.fixture
def api_client():
    """Provide API client for tests"""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, django_user_model):
    """Provide authenticated API client"""
    user = django_user_model.objects.create_user(
        phone_number='+998901234567',
        password='testpass123'
    )
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.fixture
def test_user(django_user_model):
    """Create a test user"""
    return django_user_model.objects.create_user(
        phone_number='+998901234567',
        password='testpass123',
        full_name='Test User'
    )


@pytest.fixture
def test_admin(django_user_model):
    """Create a test admin user"""
    return django_user_model.objects.create_user(
        phone_number='+998909999999',
        password='adminpass123',
        is_staff=True,
        is_superuser=True,
        full_name='Admin User'
    )


@pytest.fixture
def test_product():
    """Create a test product"""
    from pharmacy.models.medicine import Medicine, Category
    
    category = Category.objects.create(name='Test', slug='test')
    return Medicine.objects.create(
        name='Test Product',
        slug='test-product',
        category=category,
        price=100.0,
        is_active=True
    )


@pytest.fixture
def test_seller(test_user):
    """Create a test seller"""
    from users.models import Seller
    
    seller_user = test_user
    return Seller.objects.create(
        user=seller_user,
        shop_name='Test Shop',
        description='Test seller shop'
    )


@pytest.fixture
def test_order(test_user, test_product):
    """Create a test order"""
    from orders.models import Order, OrderItem
    
    order = Order.objects.create(
        customer=test_user,
        status='Pending',
        total_price=100.0
    )
    
    OrderItem.objects.create(
        order=order,
        product=test_product,
        quantity=1,
        price=100.0
    )
    
    return order
