import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user_factory():
    def _user_factory(**kwargs):
        return User.objects.create_user(**kwargs)
    return _user_factory

@pytest.fixture
def create_admin_user(user_factory):
    return user_factory(email="admin@example.com", password="adminpassword", role="admin", is_staff=True, is_superuser=True, is_verified=True)

@pytest.fixture
def create_customer_user(user_factory):
    return user_factory(email="customer@example.com", password="customerpassword", role="customer", is_verified=True)

@pytest.fixture
def create_seller_user(user_factory):
    user = user_factory(email="seller@example.com", password="sellerpassword", role="seller", is_verified=True)
    # Assuming Seller profile is created separately or via signal
    from users.models import Seller
    Seller.objects.create(user=user, shop_name="Test Seller Shop", is_verified=True)
    return user

@pytest.fixture
def create_deliverer_user(user_factory):
    user = user_factory(email="deliverer@example.com", password="delivererpassword", role="deliverer", is_verified=True)
    # Assuming Deliverer profile is created separately or via signal
    from users.models import Deliverer
    Deliverer.objects.create(user=user, phone_number="+998901234567", vehicle_info="Bike", status="active")
    return user

@pytest.fixture
def get_auth_token():
    def _get_auth_token(user):
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }
    return _get_auth_token

@pytest.fixture
def authenticated_client(api_client, create_customer_user, get_auth_token):
    user = create_customer_user
    tokens = get_auth_token(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    api_client.cookies[settings.SIMPLE_JWT['AUTH_COOKIE']] = tokens['refresh']
    return api_client

@pytest.fixture
def authenticated_admin_client(api_client, create_admin_user, get_auth_token):
    user = create_admin_user
    tokens = get_auth_token(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    api_client.cookies[settings.SIMPLE_JWT['AUTH_COOKIE']] = tokens['refresh']
    return api_client

@pytest.fixture
def authenticated_seller_client(api_client, create_seller_user, get_auth_token):
    user = create_seller_user
    tokens = get_auth_token(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    api_client.cookies[settings.SIMPLE_JWT['AUTH_COOKIE']] = tokens['refresh']
    return api_client

@pytest.fixture
def authenticated_deliverer_client(api_client, create_deliverer_user, get_auth_token):
    user = create_deliverer_user
    tokens = get_auth_token(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    api_client.cookies[settings.SIMPLE_JWT['AUTH_COOKIE']] = tokens['refresh']
    return api_client