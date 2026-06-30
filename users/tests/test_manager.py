from django.test import TestCase
from users.models import CustomUser

class CustomUserManagerTests(TestCase):
    def test_create_user_with_phone_only(self):
        u = CustomUser.objects.create_user(phone_number='+998901234567', password='testpass123')
        self.assertIsNotNone(u.pk)
        self.assertTrue(u.check_password('testpass123'))
        self.assertIsNone(u.email)

    def test_create_user_with_email_only(self):
        u = CustomUser.objects.create_user(email='test@example.com', password='testpass123')
        self.assertIsNotNone(u.pk)
        self.assertTrue(u.check_password('testpass123'))
        self.assertIsNone(u.phone_number)

    def test_create_user_with_email_and_phone(self):
        u = CustomUser.objects.create_user(email='test2@example.com', phone_number='+998901234568', password='testpass123')
        self.assertIsNotNone(u.pk)
        self.assertTrue(u.check_password('testpass123'))
        self.assertEqual(u.email, 'test2@example.com')
        self.assertEqual(u.phone_number, '+998901234568')

    def test_create_user_no_email_or_phone(self):
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(password='testpass123')

    def test_create_superuser_requires_email(self):
        with self.assertRaises(ValueError, msg="Superuser must have an email"):
            CustomUser.objects.create_superuser(email=None, password='adminpass123')

    def test_create_superuser_success(self):
        admin_user = CustomUser.objects.create_superuser(email='admin@example.com', password='adminpass123')
        self.assertIsNotNone(admin_user.pk)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.check_password('adminpass123'))
        self.assertEqual(admin_user.email, 'admin@example.com')
        self.assertIsNone(admin_user.phone_number) # Superuser should not have phone_number by default in this setup
