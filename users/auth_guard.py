"""
users/auth_guard.py
-------------------
Centralized authentication & authorization guard for all API views.

Muammo: so'rov yuborgan foydalanuvchi identifikatori yetarlicha tekshirilmaydi;
bu boshqa foydalanuvchi nomidan harakat qilish (impersonation) imkonini beradi.

Yechim: barcha kiruvchi so'rovlarda autentifikatsiya va autorizatsiya tekshiruvini
qat'iy joriy qilish, noto'g'ri holatda mos HTTP status kodlari bilan rad etish,
va xavfsizlik loglarini yozish.
"""

import logging
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger("security.auth_guard")

# ── Audit log format ──────────────────────────────────────────────────────────
# FORMAT: [SECURITY] timestamp=... event=... requester_id=... target_id=... ip=... reason=...
# ─────────────────────────────────────────────────────────────────────────────


def _get_client_ip(request):
    """Extract real client IP, respecting X-Forwarded-For if set."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _log_rejection(event, request, target_id=None, reason=""):
    """Write structured security log entry for every rejected request."""
    requester_id = (
        str(request.user.id)
        if request.user and request.user.is_authenticated
        else "anonymous"
    )
    ip = _get_client_ip(request)
    ts = timezone.now().isoformat()
    logger.warning(
        "[SECURITY] timestamp=%s event=%s requester_id=%s target_id=%s ip=%s reason=%s",
        ts,
        event,
        requester_id,
        str(target_id) if target_id is not None else "N/A",
        ip,
        reason,
    )


def _normalize_id(value):
    """Normalize user ID to string for safe comparison (handles int/str/UUID)."""
    if value is None:
        return None
    return str(value).strip()


# ── Public API ────────────────────────────────────────────────────────────────


def require_authenticated(request):
    """
    Check that request.user is authenticated.

    Returns:
        None  — if authenticated (caller may proceed)
        Response(401) — if not authenticated
    """
    if not request.user or not request.user.is_authenticated:
        _log_rejection(
            event="UNAUTHENTICATED_REQUEST",
            request=request,
            reason="request.user is missing or not authenticated",
        )
        return Response(
            {"detail": "Authentication credentials were not provided."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    return None


def require_self_or_admin(request, target_user_id):
    """
    Enforce that the authenticated user may only act on their own resource,
    unless they are staff (admin) AND the request carries an explicit
    X-Acting-As: true header (audit flag).

    Args:
        request:        DRF Request object
        target_user_id: The user ID extracted from URL param / query / body

    Returns:
        None        — access granted
        Response(401) — not authenticated
        Response(403) — authenticated but not authorized
    """
    # Step 1: authentication check
    auth_error = require_authenticated(request)
    if auth_error is not None:
        return auth_error

    requester_id = _normalize_id(request.user.id)
    target_id = _normalize_id(target_user_id)

    # Step 2: own-resource check
    if requester_id == target_id:
        return None  # ✓ user acting on their own resource

    # Step 3: admin acting-as check (requires explicit audit flag)
    if request.user.is_staff or request.user.is_superuser:
        acting_as = request.headers.get("X-Acting-As", "").strip().lower()
        if acting_as == "true":
            # Permitted — log for audit trail
            logger.info(
                "[SECURITY] timestamp=%s event=ADMIN_ACTING_AS requester_id=%s "
                "target_id=%s ip=%s",
                timezone.now().isoformat(),
                requester_id,
                target_id,
                _get_client_ip(request),
            )
            return None

        # Admin without explicit acting-as flag — still reject and log
        _log_rejection(
            event="ADMIN_MISSING_ACTING_AS_FLAG",
            request=request,
            target_id=target_id,
            reason="Admin tried to act on behalf of another user without X-Acting-As header",
        )
        return Response(
            {"detail": "Forbidden. Use X-Acting-As: true header for admin delegation."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Step 4: impersonation attempt by regular user
    _log_rejection(
        event="IMPERSONATION_ATTEMPT",
        request=request,
        target_id=target_id,
        reason="Authenticated user attempted to act on behalf of another user",
    )
    return Response(
        {"detail": "You do not have permission to perform this action."},
        status=status.HTTP_403_FORBIDDEN,
    )
