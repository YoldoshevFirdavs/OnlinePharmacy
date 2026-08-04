import sys
import os
import django

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import TestCase, Client
from users import otp_service
from users.models import CustomUser

class AdminLoginFlowTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = CustomUser.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="securepass",
            is_staff=True
        )

    def test_admin_login_flow(self):
        print("=== START ADMIN LOGIN FLOW TEST ===")

        # Step 1: Request OTP
        otp = otp_service.generate_numeric_code()
        print(f"Generated OTP: {otp}")

        session = otp_service.create_admin_session(identifier=self.admin.email, user_id=self.admin.id)
        print(f"Created admin session: {session}")

        hashed, salt = otp_service.hash_otp_with_salt(otp)
        otp_hash_obj = otp_service.OtpHash(hash=hashed, salt=salt)
        otp_service.store_otp_hash(self.admin.email, otp_hash_obj)
        print("Stored OTP hash in cache")

        # Step 2: Verify OTP
        otp_hash_obj = otp_service.get_otp_hash(self.admin.email)
        print(f"Retrieved OTP hash: {otp_hash_obj}")

        is_valid = otp_service.verify_otp_code(otp, otp_hash_obj)
        print(f"OTP verification result: {is_valid}")

        # Step 3: Simulate login
        if is_valid:
            logged_in = self.client.login(username="adminuser", password="securepass")
            print(f"Login attempt result: {logged_in}")
        else:
            print("Login failed due to invalid OTP")

        print("=== END ADMIN LOGIN FLOW TEST ===")
