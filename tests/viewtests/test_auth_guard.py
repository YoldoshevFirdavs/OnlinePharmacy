"""
tests/viewtests/test_auth_guard.py
-----------------------------------
Unit va integration testlar:
  (a) autentifikatsiyasiz so'rov → 401
  (b) foydalanuvchi o'z ID bilan → 200
  (c) foydalanuvchi boshqa ID bilan → 403
  (d) admin X-Acting-As: true bilan → 200 (ruxsatlangan)
  (e) admin X-Acting-As headersiz → 403
  (f) log yozilayotganini tekshirish
"""

import pytest
from unittest.mock import patch, MagicMock
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIClient, APITestCase
from rest_framework import status

from users.auth_guard import (
    require_authenticated,
    require_self_or_admin,
    _normalize_id,
    _get_client_ip,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


# ── Helper ────────────────────────────────────────────────────────────────────

def _make_request(user=None, headers=None):
    """Build a minimal mock request object."""
    req = MagicMock()
    req.user = user or AnonymousUser()
    req.META = {"REMOTE_ADDR": "127.0.0.1"}
    req.headers = headers or {}
    return req


# ── Unit tests: _normalize_id ─────────────────────────────────────────────────

class TestNormalizeId:
    def test_int_becomes_string(self):
        assert _normalize_id(42) == "42"

    def test_string_unchanged(self):
        assert _normalize_id("42") == "42"

    def test_none_returns_none(self):
        assert _normalize_id(None) is None

    def test_strips_whitespace(self):
        assert _normalize_id("  7  ") == "7"


# ── Unit tests: _get_client_ip ────────────────────────────────────────────────

class TestGetClientIp:
    def test_returns_remote_addr(self):
        req = MagicMock()
        req.META = {"REMOTE_ADDR": "10.0.0.1"}
        req.headers = {}
        assert _get_client_ip(req) == "10.0.0.1"

    def test_prefers_x_forwarded_for(self):
        req = MagicMock()
        req.META = {
            "HTTP_X_FORWARDED_FOR": "203.0.113.5, 10.0.0.1",
            "REMOTE_ADDR": "10.0.0.1",
        }
        req.headers = {}
        assert _get_client_ip(req) == "203.0.113.5"


# ── Unit tests: require_authenticated ────────────────────────────────────────

class TestRequireAuthenticated:
    def test_anonymous_returns_401(self):
        req = _make_request(user=AnonymousUser())
        response = require_authenticated(req)
        assert response is not None
        assert response.status_code == 401

    def test_authenticated_returns_none(self):
        user = MagicMock()
        user.is_authenticated = True
        req = _make_request(user=user)
        result = require_authenticated(req)
        assert result is None

    def test_missing_user_returns_401(self):
        req = _make_request(user=None)
        response = require_authenticated(req)
        assert response is not None
        assert response.status_code == 401

    def test_401_does_not_leak_user_info(self):
        req = _make_request(user=AnonymousUser())
        response = require_authenticated(req)
        data = response.data
        assert "password" not in str(data)
        assert "token" not in str(data)
        assert "detail" in data


# ── Unit tests: require_self_or_admin ────────────────────────────────────────

class TestRequireSelfOrAdmin:
    def _make_user(self, user_id, is_staff=False, is_superuser=False):
        user = MagicMock()
        user.id = user_id
        user.is_authenticated = True
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        return user

    # (a) unauthenticated → 401
    def test_unauthenticated_returns_401(self):
        req = _make_request(user=AnonymousUser())
        response = require_self_or_admin(req, target_user_id=1)
        assert response.status_code == 401

    # (b) user acting on own resource → None (allowed)
    def test_own_resource_returns_none(self):
        user = self._make_user(user_id=5)
        req = _make_request(user=user)
        result = require_self_or_admin(req, target_user_id=5)
        assert result is None

    # (b) type normalization: int vs string same ID
    def test_own_resource_int_vs_string(self):
        user = self._make_user(user_id=5)
        req = _make_request(user=user)
        result = require_self_or_admin(req, target_user_id="5")
        assert result is None

    # (c) regular user targeting another user → 403
    def test_impersonation_returns_403(self):
        user = self._make_user(user_id=5)
        req = _make_request(user=user)
        response = require_self_or_admin(req, target_user_id=99)
        assert response.status_code == 403

    # (c) 403 response must not leak sensitive info
    def test_403_no_sensitive_data(self):
        user = self._make_user(user_id=5)
        req = _make_request(user=user)
        response = require_self_or_admin(req, target_user_id=99)
        data = str(response.data)
        assert "password" not in data
        assert "token" not in data

    # (d) admin WITH X-Acting-As: true → None (allowed)
    def test_admin_with_acting_as_flag_returns_none(self):
        user = self._make_user(user_id=1, is_staff=True)
        req = _make_request(user=user, headers={"X-Acting-As": "true"})
        result = require_self_or_admin(req, target_user_id=99)
        assert result is None

    # (e) admin WITHOUT X-Acting-As header → 403
    def test_admin_without_acting_as_flag_returns_403(self):
        user = self._make_user(user_id=1, is_staff=True)
        req = _make_request(user=user, headers={})
        response = require_self_or_admin(req, target_user_id=99)
        assert response.status_code == 403

    # (e) admin with wrong acting-as value → 403
    def test_admin_wrong_acting_as_value_returns_403(self):
        user = self._make_user(user_id=1, is_staff=True)
        req = _make_request(user=user, headers={"X-Acting-As": "yes"})
        response = require_self_or_admin(req, target_user_id=99)
        assert response.status_code == 403

    # (f) impersonation attempt is logged
    def test_impersonation_is_logged(self):
        user = self._make_user(user_id=5)
        req = _make_request(user=user)
        with patch("users.auth_guard.logger") as mock_logger:
            require_self_or_admin(req, target_user_id=99)
            mock_logger.warning.assert_called_once()
            call_args = str(mock_logger.warning.call_args)
            assert "IMPERSONATION_ATTEMPT" in call_args

    # (f) unauthenticated rejection is logged
    def test_unauthenticated_is_logged(self):
        req = _make_request(user=AnonymousUser())
        with patch("users.auth_guard.logger") as mock_logger:
            require_authenticated(req)
            mock_logger.warning.assert_called_once()
            call_args = str(mock_logger.warning.call_args)
            assert "UNAUTHENTICATED_REQUEST" in call_args

    # (f) admin acting-as is logged at INFO level
    def test_admin_acting_as_is_audit_logged(self):
        user = self._make_user(user_id=1, is_staff=True)
        req = _make_request(user=user, headers={"X-Acting-As": "true"})
        with patch("users.auth_guard.logger") as mock_logger:
            require_self_or_admin(req, target_user_id=99)
            mock_logger.info.assert_called_once()
            call_args = str(mock_logger.info.call_args)
            assert "ADMIN_ACTING_AS" in call_args


# ── Integration tests: /api/v1/users/me/ ─────────────────────────────────────

class TestUserProfileEndpoint(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="Pass1234!",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="Pass1234!",
        )
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="Pass1234!",
            is_staff=True,
        )
        self.url = "/api/v1/users/me/"

    # (a) unauthenticated GET → 401
    def test_unauthenticated_get_returns_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # (a) unauthenticated PATCH → 401
    def test_unauthenticated_patch_returns_401(self):
        response = self.client.patch(self.url, {"full_name": "Hacker"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # (b) authenticated GET own profile → 200
    def test_authenticated_get_own_profile_returns_200(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("email"), self.user.email)

    # (b) authenticated PATCH own profile (no user_id param) → 200
    def test_authenticated_patch_own_profile_returns_200(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            self.url, {"full_name": "Updated"}, format="json"
        )
        self.assertIn(response.status_code, [status.HTTP_200_OK])

    # (b) authenticated PATCH with matching user_id → 200
    def test_patch_with_own_user_id_returns_200(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            self.url,
            {"full_name": "Updated", "user_id": str(self.user.id)},
            format="json",
        )
        self.assertIn(response.status_code, [status.HTTP_200_OK])

    # (c) authenticated PATCH with other user's ID → 403
    def test_patch_with_other_user_id_returns_403(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            self.url,
            {"full_name": "Hacker", "user_id": str(self.other_user.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # (d) admin PATCH with X-Acting-As: true → 200
    def test_admin_patch_with_acting_as_flag_returns_200(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            self.url,
            {"full_name": "Admin Edit", "user_id": str(self.other_user.id)},
            format="json",
            HTTP_X_ACTING_AS="true",
        )
        # Admin acts on own /me/ endpoint — still returns own profile
        self.assertIn(response.status_code, [status.HTTP_200_OK])

    # (e) admin PATCH without X-Acting-As → 403
    def test_admin_patch_without_acting_as_returns_403(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            self.url,
            {"full_name": "Admin Edit", "user_id": str(self.other_user.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ── Integration tests: /api/v1/users/login/check-session/ ────────────────────

class TestCheckSessionEndpoint(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="sess@example.com",
            password="Pass1234!",
        )
        self.other_user = User.objects.create_user(
            email="other2@example.com",
            password="Pass1234!",
        )
        self.url = "/api/v1/users/login/check-session/"

    # (a) unauthenticated → 401
    def test_unauthenticated_returns_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # (b) authenticated, no user_id param → 200
    def test_authenticated_no_param_returns_200(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("ok"))

    # (b) authenticated with own user_id → 200
    def test_authenticated_own_user_id_returns_200(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {"user_id": str(self.user.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # (c) authenticated with other user_id → 403
    def test_authenticated_other_user_id_returns_403(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {"user_id": str(self.other_user.id)})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
