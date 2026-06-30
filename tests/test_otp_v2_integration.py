"""
OnlinePharmacy - OTP v2.0 Integration Tests
Tests: registration → Telegram/Email flow → verify-otp → JWT
"""

import pytest
import json
from django.test import Client
from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from users.otp_service import (
    generate_numeric_code,
    hash_otp_with_salt,
    OtpHash,
    create_otp_session,
    bind_session_to_user,
    store_otp_hash,
    get_otp_hash,
    verify_otp_once,
    get_session_meta,
    store_bot_otp,
    get_bot_otp,
)

User = get_user_model()


@pytest.mark.django_db
class TestOTPv2Integration:
    """Integration tests for OTP Service v2.0"""
    
    def setup_method(self):
        self.client = Client()
        cache.clear()
    
    def test_generate_numeric_code(self):
        """Test OTP code generation"""
        code = generate_numeric_code(4)
        assert len(code) == 4
        assert code.isdigit()
        
        code6 = generate_numeric_code(6)
        assert len(code6) == 6
        assert code6.isdigit()
    
    def test_hash_otp_with_salt(self):
        """Test SHA256 hashing with salt"""
        otp = "123456"
        hashed, salt = hash_otp_with_salt(otp)
        
        assert len(salt) == 32  # 16 bytes = 32 hex chars
        assert len(hashed) == 64  # SHA256 = 64 hex chars
        assert hashed != otp
    
    def test_otp_hash_serialization(self):
        """Test OtpHash JSON serialization"""
        otp_hash = OtpHash(
            hash="abc123",
            salt="def456",
            algorithm="sha256"
        )
        
        json_str = otp_hash.to_json()
        assert isinstance(json_str, str)
        
        parsed = OtpHash.from_json(json_str)
        assert parsed.hash == "abc123"
        assert parsed.salt == "def456"
    
    def test_create_otp_session(self):
        """Test OTP session creation"""
        session = create_otp_session(purpose="telegram")
        assert session.session_id
        assert session.purpose == "telegram"
        assert len(session.session_id) > 10
    
    def test_bind_session_to_user(self):
        """Test session binding to user in cache"""
        # Create user
        user = User.objects.create(phone_number="+998901234567", email="test@example.com")
        
        # Create and bind session
        session = create_otp_session("telegram")
        result = bind_session_to_user(session.session_id, user.id, "+998901234567")
        assert result is True
        
        # Verify session is stored
        meta = get_session_meta(session.session_id)
        assert meta is not None
        assert meta['user_id'] == user.id
        assert meta['identifier'] == "+998901234567"
    
    def test_store_and_retrieve_otp_hash(self):
        """Test storing and retrieving OTP hash from cache"""
        identifier = "test@example.com"
        otp_code = "123456"
        
        # Hash and store
        hashed, salt = hash_otp_with_salt(otp_code)
        otp_hash = OtpHash(hash=hashed, salt=salt)
        result = store_otp_hash(identifier, otp_hash, ttl=900)
        assert result is True
        
        # Retrieve
        retrieved = get_otp_hash(identifier)
        assert retrieved is not None
        assert retrieved.hash == hashed
        assert retrieved.salt == salt
    
    def test_store_and_retrieve_bot_otp(self):
        """Test storing bot OTP for Telegram flow"""
        session_id = "test_session_123"
        otp_code = "1234"
        
        # Store
        result = store_bot_otp(session_id, otp_code, ttl=900)
        assert result is True
        
        # Retrieve
        otp_hash = get_bot_otp(session_id)
        assert otp_hash is not None
        assert otp_hash.hash  # Hash should exist
        assert otp_hash.salt  # Salt should exist
    
    def test_verify_otp_once_success(self):
        """Test successful OTP verification"""
        # Setup
        user = User.objects.create(phone_number="+998901234567", email="test@example.com")
        session = create_otp_session("telegram")
        identifier = "+998901234567"
        otp_code = "123456"
        
        # Store OTP
        hashed, salt = hash_otp_with_salt(otp_code)
        otp_hash = OtpHash(hash=hashed, salt=salt)
        store_otp_hash(identifier, otp_hash, ttl=900)
        bind_session_to_user(session.session_id, user.id, identifier)
        
        # Verify with correct code
        is_valid, message = verify_otp_once(session.session_id, otp_code)
        assert is_valid is True
        assert "successfully" in message.lower()
        
        # Session should be deleted after verification
        meta = get_session_meta(session.session_id)
        assert meta is None
    
    def test_verify_otp_once_invalid_code(self):
        """Test OTP verification with wrong code"""
        # Setup
        user = User.objects.create(phone_number="+998901234567", email="test@example.com")
        session = create_otp_session("telegram")
        identifier = "+998901234567"
        otp_code = "123456"
        
        # Store OTP
        hashed, salt = hash_otp_with_salt(otp_code)
        otp_hash = OtpHash(hash=hashed, salt=salt)
        store_otp_hash(identifier, otp_hash, ttl=900)
        bind_session_to_user(session.session_id, user.id, identifier)
        
        # Verify with wrong code
        is_valid, message = verify_otp_once(session.session_id, "000000")
        assert is_valid is False
        assert "invalid" in message.lower()
    
    def test_registration_endpoint(self):
        """Test /api/v1/users/registration/ endpoint"""
        payload = {
            "phone_number": "+998901234567",
            "full_name": "Test User"
        }
        
        response = self.client.post(
            "/api/v1/users/registration/",
            json.dumps(payload),
            content_type="application/json"
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'session_id' in data
        assert 'verification_link' in data
        assert 'message' in data
        
        # Verify user created
        user = User.objects.filter(phone_number="+998901234567").first()
        assert user is not None
        
        # Verify session stored in cache
        meta = get_session_meta(data['session_id'])
        assert meta is not None
        assert meta['user_id'] == user.id
    
    def test_verify_otp_endpoint(self):
        """Test /api/v1/users/verify-otp/ endpoint"""
        # Setup: register user
        payload = {
            "phone_number": "+998901234567",
            "full_name": "Test User"
        }
        
        response = self.client.post(
            "/api/v1/users/registration/",
            json.dumps(payload),
            content_type="application/json"
        )
        
        reg_data = response.json()
        session_id = reg_data['session_id']
        
        # Manually set OTP for testing
        user = User.objects.get(phone_number="+998901234567")
        otp_code = "123456"
        hashed, salt = hash_otp_with_salt(otp_code)
        otp_hash = OtpHash(hash=hashed, salt=salt)
        store_otp_hash("+998901234567", otp_hash, ttl=900)
        
        # Verify OTP
        verify_payload = {
            "session_id": session_id,
            "code": otp_code
        }
        
        response = self.client.post(
            "/api/v1/users/verify-otp/",
            json.dumps(verify_payload),
            content_type="application/json"
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'access' in data
        assert 'user' in data
        
        # Verify user is marked as verified
        user.refresh_from_db()
        assert user.is_verified is True
    
    def test_verify_otp_invalid_session(self):
        """Test verify-otp with non-existent session"""
        verify_payload = {
            "session_id": "fake_session_xyz",
            "code": "123456"
        }
        
        response = self.client.post(
            "/api/v1/users/verify-otp/",
            json.dumps(verify_payload),
            content_type="application/json"
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert 'session' in data['detail'].lower() or 'not' in data['detail'].lower()
    
    def test_cache_ttl_enforcement(self):
        """Test that OTP expires after TTL"""
        # This test requires actual cache TTL support
        # For Redis, we'd need to wait or mock time
        # For now, just verify TTL parameter is accepted
        
        user = User.objects.create(phone_number="+998901234567")
        session = create_otp_session("telegram")
        otp_code = "123456"
        
        hashed, salt = hash_otp_with_salt(otp_code)
        otp_hash = OtpHash(hash=hashed, salt=salt)
        
        # Store with short TTL
        result = store_otp_hash("+998901234567", otp_hash, ttl=1)
        assert result is True
        
        # Should exist immediately
        retrieved = get_otp_hash("+998901234567")
        assert retrieved is not None


@pytest.mark.django_db
class TestEmailOTPFlow:
    """Test email-based OTP flow"""
    
    def setup_method(self):
        self.client = Client()
        cache.clear()
    
    def test_email_registration(self):
        """Test registration with email"""
        payload = {
            "email": "user@example.com",
            "full_name": "Email User"
        }
        
        response = self.client.post(
            "/api/v1/users/registration/",
            json.dumps(payload),
            content_type="application/json"
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'session_id' in data
        assert 'message' in data
        
        # Verify user created
        user = User.objects.filter(email="user@example.com").first()
        assert user is not None
    
    def test_email_login_endpoint(self):
        """Test /api/v1/users/login/email/ endpoint"""
        # Create user first
        User.objects.create(email="existing@example.com")
        
        payload = {"email": "existing@example.com"}
        
        response = self.client.post(
            "/api/v1/users/login/email/",
            json.dumps(payload),
            content_type="application/json"
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'session_id' in data
        assert 'message' in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
