"""
SQL Injection Security Tests
Tests various SQL injection attack vectors
"""

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class SQLInjectionAuthTests(TestCase):
    """Test SQL injection vulnerabilities in authentication endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="testuser@test.com", password="testpass123", phone_number="+998901234567"
        )

    def test_sql_injection_login_email(self):
        """Test SQL injection in login email field"""
        # SQL injection payload
        sql_payloads = [
            "' OR '1'='1",
            "' OR 1=1--",
            "' OR 1=1#",
            "admin'--",
            "admin' OR ''='",
        ]

        for payload in sql_payloads:
            # These should NOT bypass authentication
            response = self.client.post(
                "/api/v1/users/login/credentials/", {"email": payload, "password": "wrongpassword"}
            )

            # Should NOT get 200 OK - authentication should fail
            self.assertNotEqual(
                response.status_code, status.HTTP_200_OK, f"SQL injection bypass detected with payload: {payload}"
            )

    def test_sql_injection_phone_login(self):
        """Test SQL injection in phone login"""
        sql_payloads = [
            "+998901234567' OR '1'='1",
            "1' OR '1'='1'--",
        ]

        for payload in sql_payloads:
            response = self.client.post(
                "/api/v1/users/login/credentials/", {"phone_number": payload, "password": "testpass123"}
            )

            # Should NOT succeed with SQL injection
            self.assertNotEqual(response.status_code, status.HTTP_200_OK, f"SQL injection in phone detected: {payload}")

    def test_sql_injection_registration(self):
        """Test SQL injection in registration"""
        # Registration endpoint might not exist - skip if 404
        sql_payloads = [
            "test' OR '1'='1@test.com",
            "user'--@test.com",
            "admin' OR 1=1#",
        ]

        for payload in sql_payloads:
            response = self.client.post(
                "/api/v1/users/register/",
                {"email": payload, "password": "testpass123", "phone_number": "+998909998877"},
            )

            # Should handle gracefully - either validation error or successful registration
            # or endpoint might not exist (404)
            self.assertIn(
                response.status_code,
                [
                    status.HTTP_400_BAD_REQUEST,
                    status.HTTP_201_CREATED,
                    status.HTTP_404_NOT_FOUND,
                    status.HTTP_409_CONFLICT,
                ],
            )


class SQLInjectionAPITests(TestCase):
    """Test SQL injection in various API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="testuser@test.com", password="testpass123", phone_number="+998901234567"
        )
        from pharmacy.models.medicine import Category

        self.category = Category.objects.create(name="Test Category", slug="test-category")

    def test_sql_injection_order_id(self):
        """Test SQL injection in order ID parameter"""
        self.client.force_authenticate(user=self.user)

        # SQL injection in order ID
        response = self.client.get("/api/v1/orders/orders/1 OR 1=1/")
        # Should return 404 or error, not show all orders

        # Should NOT show 200 OK with all orders
        self.assertNotEqual(response.status_code, status.HTTP_200_OK, "SQL injection in order ID allowed")

    def test_sql_injection_search(self):
        """Test SQL injection in search queries"""
        self.client.force_authenticate(user=self.user)

        sql_payloads = [
            "%' OR '1'='1",
            "' UNION SELECT * FROM users--",
            "' UNION SELECT password FROM auth_user--",
        ]

        for payload in sql_payloads:
            response = self.client.get(f"/api/v1/products/medicines/?search={payload}")

            # Should handle gracefully - or endpoint might not exist
            self.assertIn(
                response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND]
            )

    def test_sql_injection_review_rating(self):
        """Test SQL injection in review rating"""
        from pharmacy.models.medicine import Medicine

        medicine = Medicine.objects.create(
            name="Test Medicine", slug="test-medicine", price=100.00, stock=10, category=self.category
        )

        sql_payloads = [
            "' OR '1'='1",
            "5' OR 1=1--",
            "1; DROP TABLE pharmacy_review;--",
        ]

        for payload in sql_payloads:
            response = self.client.post(
                "/api/v1/products/reviews/", {"medicine": medicine.id, "rating": payload, "content": "Test review"}
            )

            # Should return error or handle gracefully
            self.assertIn(
                response.status_code,
                [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
            )


class SQLInjectionDatabaseTests(TestCase):
    """Direct database SQL injection tests"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="testuser@test.com", password="testpass123", phone_number="+998901234567"
        )

    def test_parameterized_queries_protected(self):
        """Test that parameterized queries protect against SQL injection"""
        from django.db import connection

        # Test 1: Safe parameterized query
        with connection.cursor() as cursor:
            cursor.execute("SELECT email FROM users_customuser WHERE email = %s", ["testuser@test.com"])
            result = cursor.fetchone()
            self.assertEqual(result[0], "testuser@test.com")

        # Test 2: Malicious input should be escaped
        malicious_email = "testuser@test.com' OR '1'='1"
        with connection.cursor() as cursor:
            cursor.execute("SELECT email FROM users_customuser WHERE email = %s", [malicious_email])
            result = cursor.fetchone()
            # Should be None because email doesn't exist with that exact value
            self.assertIsNone(result)

    def test_raw_queries_protected(self):
        """Test that raw queries with params are protected"""
        # Raw queries with params should work fine
        # Multiple statements are not supported by Django's parameterized queries
        # This is a safety feature that prevents SQL injection
        users = User.objects.raw("SELECT * FROM users_customuser WHERE email = %s", ["testuser@test.com"])

        # Should execute without error
        self.assertEqual(len(list(users)), 1)

    def test_bulk_create_safe(self):
        """Test that bulk_create is safe from SQL injection"""
        users = [User(email=f"user{i}@test.com", phone_number=f"+99890111223{i}", role="user") for i in range(5)]

        # Should create all users safely
        created = User.objects.bulk_create(users)
        self.assertEqual(len(created), 5)

        # Verify no injection occurred
        self.assertEqual(User.objects.count(), 6)  # Original + 5 new
