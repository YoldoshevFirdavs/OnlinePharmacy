from django.urls import reverse
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from pharmacy.models.medicine import Medicine, Category
from orders.models import Order
from users.models import Deliverer
import pytest

User = get_user_model()

pytestmark = pytest.mark.django_db

class DashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="adminpassword",
            full_name="Admin User",
            is_staff=True,
            is_superuser=True
        )
        self.deliverer_user = User.objects.create_user(
            email="deliverer@example.com",
            password="delivererpassword",
            full_name="Deliverer User"
        )
        self.deliverer_profile = Deliverer.objects.create(
            user=self.deliverer_user,
            phone_number="+998901234567",
            license_number="DL123",
            vehicle_type="Car"
        )
        self.normal_user = User.objects.create_user(
            email="user@example.com",
            password="userpassword",
            full_name="Normal User"
        )

        self.category = Category.objects.create(name="Test Category", slug="test-category")
        self.medicine = Medicine.objects.create(name="Test Medicine", slug="test-medicine", category=self.category, price=10, stock=10)
        self.order = Order.objects.create(customer=self.normal_user, address="Some Address", status="Pending")
        self.deliverer_order = Order.objects.create(customer=self.normal_user, address="Another Address", status="Assigned", driver=self.deliverer_profile)

        self.login_url = reverse("dashboard:login_page")
        self.main_dashboard_url = reverse("dashboard:main_dashboard")
        self.deliverer_dashboard_url = reverse("dashboard:deliverer_dashboard")
        self.category_list_url = reverse("dashboard:category_list")
        self.medicine_list_url = reverse("dashboard:medicine_list")
        self.user_list_url = reverse("dashboard:user_list")
        self.order_list_url = reverse("dashboard:order_list")
        self.account_settings_url = reverse("dashboard:account_settings")
        self.not_allowed_url = reverse("dashboard:not_allowed")

    def test_admin_login_redirects_to_main_dashboard(self):
        self.client.login(email="admin@example.com", password="adminpassword")
        response = self.client.get(self.login_url, follow=True)
        self.assertRedirects(response, self.main_dashboard_url)

    def test_deliverer_login_redirects_to_deliverer_dashboard(self):
        self.client.login(email="deliverer@example.com", password="delivererpassword")
        response = self.client.get(self.login_url, follow=True)
        self.assertRedirects(response, self.deliverer_dashboard_url)

    def test_normal_user_login_redirects_to_auth_and_logs_out(self):
        self.client.login(email="user@example.com", password="userpassword")
        response = self.client.get(self.login_url, follow=True)
        self.assertRedirects(response, "/auth/") # Assuming /auth/ is the base auth URL

    def test_admin_main_dashboard_access(self):
        self.client.login(email="admin@example.com", password="adminpassword")
        response = self.client.get(self.main_dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Total Categories")

    def test_deliverer_dashboard_access(self):
        self.client.login(email="deliverer@example.com", password="delivererpassword")
        response = self.client.get(self.deliverer_dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Deliverer Dashboard")

    def test_normal_user_access_to_admin_dashboard_redirects_to_not_allowed(self):
        self.client.login(email="user@example.com", password="userpassword")
        response = self.client.get(self.main_dashboard_url, follow=True)
        self.assertRedirects(response, self.not_allowed_url + "?from=/dashboard/")

    def test_admin_category_list(self):
        self.client.login(email="admin@example.com", password="adminpassword")
        response = self.client.get(self.category_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Category")

    def test_admin_medicine_list(self):
        self.client.login(email="admin@example.com", password="adminpassword")
        response = self.client.get(self.medicine_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Medicine")

    def test_admin_user_list(self):
        self.client.login(email="admin@example.com", password="adminpassword")
        response = self.client.get(self.user_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test User") # Admin user itself
        self.assertContains(response, "Deliverer User")
        self.assertContains(response, "Normal User")

    def test_admin_order_list(self):
        self.client.login(email="admin@example.com", password="adminpassword")
        response = self.client.get(self.order_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Some Address")
        self.assertContains(response, "Another Address")

    def test_account_settings_admin_access(self):
        self.client.login(email="admin@example.com", password="adminpassword")
        response = self.client.get(self.account_settings_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Account Settings")

    def test_account_settings_deliverer_access(self):
        self.client.login(email="deliverer@example.com", password="delivererpassword")
        response = self.client.get(self.account_settings_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Account Settings")

    def test_deliverer_order_update(self):
        self.client.login(email="deliverer@example.com", password="delivererpassword")
        update_url = reverse("dashboard:deliverer_order_update", kwargs={"pk": self.deliverer_order.pk})
        response = self.client.post(update_url, {"status": "Accepted"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.deliverer_order.refresh_from_db()
        self.assertEqual(self.deliverer_order.status, "Accepted")
        self.assertContains(response, "statusi muvaffaqiyatli yangilandi.")
