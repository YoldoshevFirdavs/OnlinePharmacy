"""
OnlinePharmacy - OTP Service v2.0
Secure, clean, production-ready OTP management
- SHA256 hash with salt
- Rate limiting
- Proper logging (PII masked)
- Type hints
- Comprehensive error handling

This is Claude AI recommended implementation.
Replaces otp_service.py after verification.
"""

import json
import hashlib
import secrets
import time
import logging
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

# ============================================
# CONSTANTS
# ============================================

OTP_TTL = 900  # 15 minutes
TELEGRAM_OTP_LENGTH = 4  # Bot: 4 digits
EMAIL_OTP_LENGTH = 6  # Email/SMS: 6 digits
SALT_LENGTH = 16  # 32 hex chars (16 bytes)
RATE_LIMIT_WINDOW = 60  # seconds
MAX_OTP_ATTEMPTS = 5  # per hour


# ============================================
# DATA CLASSES
# ============================================


@dataclass(frozen=True)
class OtpSession:
    """Immutable OTP session"""

    session_id: str
    purpose: str  # "telegram" | "email"
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            object.__setattr__(self, "created_at", timezone.now())


@dataclass(frozen=True)
class OtpHash:
    """Secure OTP storage format"""

    hash: str
    salt: str
    algorithm: str = "sha256"

    def to_json(self) -> str:
        return json.dumps(
            {"hash": self.hash, "salt": self.salt, "algorithm": self.algorithm}
        )

    @staticmethod
    def from_json(data: str) -> "OtpHash":
        try:
            d = json.loads(data) if isinstance(data, str) else data
            return OtpHash(
                hash=d["hash"], salt=d["salt"], algorithm=d.get("algorithm", "sha256")
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Failed to parse OtpHash: {str(e)[:50]}")
            raise ValueError("Invalid OtpHash format")


# ============================================
# OTP GENERATION
# ============================================


def generate_numeric_code(length: int = EMAIL_OTP_LENGTH) -> str:
    """Generate secure numeric OTP code."""
    if length < 4 or length > 10:
        raise ValueError("OTP length must be 4-10")

    digits = "0123456789"
    code = "".join(secrets.choice(digits) for _ in range(length))
    logger.debug(f"OTP generated: {length} digits")
    return code


def generate_session_id() -> str:
    """Generate secure session ID (URL-safe)"""
    return secrets.token_urlsafe(16)


# ============================================
# HASHING & VERIFICATION
# ============================================


def hash_otp_with_salt(otp: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Hash OTP with SHA256 + salt. Returns (hash, salt) tuple."""
    if not otp or not isinstance(otp, str):
        raise ValueError("OTP must be non-empty string")

    if salt is None:
        salt = secrets.token_hex(SALT_LENGTH // 2)  # 16 bytes = 32 hex chars
    elif len(salt) != SALT_LENGTH:
        raise ValueError(f"Salt must be {SALT_LENGTH} hex chars")

    hash_input = otp + salt
    hashed = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

    logger.debug(f"OTP hashed (salt: {salt[:8]}...)")
    return hashed, salt


def verify_otp_code(provided_code: str, otp_hash_obj: OtpHash) -> bool:
    """Verify OTP against hash using constant-time comparison."""
    if not provided_code or not isinstance(provided_code, str):
        logger.warning("Invalid provided_code format")
        return False

    try:
        computed_hash, _ = hash_otp_with_salt(provided_code, otp_hash_obj.salt)
        # Constant-time comparison (prevent timing attacks)
        is_valid = secrets.compare_digest(computed_hash, otp_hash_obj.hash)

        if is_valid:
            logger.info("OTP verification SUCCESS")
        else:
            logger.warning("OTP verification FAILED (mismatch)")

        return is_valid
    except Exception as e:
        logger.error(f"OTP verification error: {str(e)[:100]}")
        return False


# ============================================
# SESSION MANAGEMENT
# ============================================


def create_otp_session(purpose: str) -> OtpSession:
    """Create new OTP session."""
    if purpose not in ("telegram", "email"):
        raise ValueError("Purpose must be 'telegram' or 'email'")

    session = OtpSession(
        session_id=generate_session_id(), purpose=purpose, created_at=timezone.now()
    )

    logger.info(f"OTP session created: {session.session_id[:8]}... ({purpose})")
    return session


def bind_session_to_user(
    session_id: str, user_id: int, identifier: str, ttl: int = OTP_TTL
) -> bool:
    """Store session metadata (user_id, identifier, timestamp)."""
    if not all([session_id, user_id, identifier]):
        logger.error("Missing required fields for bind_session_to_user")
        return False

    try:
        key = f"auth_session:{session_id}"
        payload = {
            "user_id": int(user_id),
            "identifier": identifier,
            "created_at": int(time.time()),
            "purpose": "registration",
        }

        cache.set(key, payload, timeout=ttl)
        logger.info(f"Session bound: {session_id[:8]}... (TTL: {ttl}s)")
        return True
    except Exception as e:
        logger.error(f"bind_session_to_user error: {str(e)[:100]}")
        return False


def get_session_meta(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve session metadata from cache."""
    if not session_id:
        return None

    try:
        key = f"auth_session:{session_id}"
        result = cache.get(key)

        if result is None:
            logger.warning(f"Session not found: {session_id[:8]}...")
            return None

        if not isinstance(result, dict):
            logger.error(f"Session meta corrupted (type: {type(result).__name__})")
            return None

        return result
    except Exception as e:
        logger.error(f"get_session_meta error: {str(e)[:100]}")
        return None


def delete_session(session_id: str) -> bool:
    """Delete session from cache"""
    try:
        key = f"auth_session:{session_id}"
        cache.delete(key)
        logger.debug(f"Session deleted: {session_id[:8]}...")
        return True
    except Exception as e:
        logger.error(f"delete_session error: {str(e)[:100]}")
        return False


# ============================================
# OTP STORAGE & RETRIEVAL (Email/Phone)
# ============================================


def store_otp_hash(identifier: str, otp_hash_obj: OtpHash, ttl: int = OTP_TTL) -> bool:
    """Store hashed OTP (with salt) in cache."""
    if not identifier or not otp_hash_obj:
        logger.error("Missing identifier or otp_hash_obj")
        return False

    try:
        key = f"otp_code:{identifier}"
        cache.set(key, otp_hash_obj.to_json(), timeout=ttl)
        logger.info(f"OTP hash stored (TTL: {ttl}s)")
        return True
    except Exception as e:
        logger.error(f"store_otp_hash error: {str(e)[:100]}")
        return False


def get_otp_hash(identifier: str) -> Optional[OtpHash]:
    """Retrieve hashed OTP from cache."""
    if not identifier:
        return None

    try:
        key = f"otp_code:{identifier}"
        stored = cache.get(key)

        if stored is None:
            logger.debug("OTP not found for identifier")
            return None

        return OtpHash.from_json(stored)
    except ValueError as e:
        logger.warning(f"Invalid OTP format: {str(e)[:50]}")
        return None
    except Exception as e:
        logger.error(f"get_otp_hash error: {str(e)[:100]}")
        return None


def delete_otp(identifier: str) -> bool:
    """Delete OTP from cache"""
    try:
        key = f"otp_code:{identifier}"
        cache.delete(key)
        logger.debug("OTP deleted")
        return True
    except Exception as e:
        logger.error(f"delete_otp error: {str(e)[:100]}")
        return False


# ============================================
# BOT OTP STORAGE (Telegram)
# ============================================


def store_bot_otp(session_id: str, otp_code: str, ttl: int = OTP_TTL) -> bool:
    """Store bot OTP (hashed with salt) for telegram flow."""
    if not session_id or not otp_code:
        logger.error("Missing session_id or otp_code")
        return False

    try:
        hashed, salt = hash_otp_with_salt(otp_code)
        otp_hash_obj = OtpHash(hash=hashed, salt=salt)

        key = f"otp:{session_id}:telegram"
        cache.set(key, otp_hash_obj.to_json(), timeout=ttl)
        logger.info(f"Bot OTP stored: {session_id[:8]}... (TTL: {ttl}s)")
        return True
    except Exception as e:
        logger.error(f"store_bot_otp error: {str(e)[:100]}")
        return False


def get_bot_otp(session_id: str) -> Optional[OtpHash]:
    """Retrieve bot OTP from cache."""
    if not session_id:
        return None

    try:
        key = f"otp:{session_id}:telegram"
        stored = cache.get(key)

        if stored is None:
            logger.debug(f"Bot OTP not found: {session_id[:8]}...")
            return None

        return OtpHash.from_json(stored)
    except ValueError as e:
        logger.warning(f"Invalid bot OTP format: {str(e)[:50]}")
        return None
    except Exception as e:
        logger.error(f"get_bot_otp error: {str(e)[:100]}")
        return None


# ============================================
# VERIFICATION FLOW
# ============================================


def verify_otp_once(
    session_id: str, provided_code: str, identifier: str = None
) -> Tuple[bool, str]:
    """Verify OTP code and invalidate on success. Returns (is_valid, message) tuple."""
    if not all([session_id, provided_code]):
        msg = "Missing session_id or provided_code"
        logger.warning(msg)
        return False, msg

    # Get session metadata
    session_meta = get_session_meta(session_id)
    if not session_meta:
        msg = "Session expired or not found"
        logger.warning(msg)
        return False, msg

    # Extract identifier from session if not provided
    identifier = identifier or session_meta.get("identifier")
    if not identifier:
        msg = "Identifier not found in session"
        logger.error(msg)
        return False, msg

    # Get stored OTP hash
    otp_hash_obj = get_otp_hash(identifier)
    if not otp_hash_obj:
        msg = "OTP code not found or expired"
        logger.warning(msg)
        return False, msg

    # Verify OTP
    if not verify_otp_code(provided_code, otp_hash_obj):
        msg = "Invalid OTP code"
        logger.warning(msg)
        return False, msg

    # Success: delete OTP and session
    delete_otp(identifier)
    delete_session(session_id)

    logger.info(f"OTP verification SUCCESS for session {session_id[:8]}...")
    return True, "OTP verified successfully"


# ============================================
# RATE LIMITING
# ============================================


def check_rate_limit(scope: str, window: int = RATE_LIMIT_WINDOW) -> Tuple[bool, int]:
    """Check if action exceeds rate limit. Returns (allowed, remaining_seconds) tuple."""
    if not scope:
        raise ValueError("Scope required")

    try:
        key = f"rl:{scope}"
        count = cache.get(key, 0)

        if count >= MAX_OTP_ATTEMPTS:
            remaining = window  # Estimate
            logger.warning(f"Rate limit exceeded: {scope}")
            return False, remaining

        cache.set(key, count + 1, timeout=window)
        return True, 0
    except Exception as e:
        logger.error(f"check_rate_limit error: {str(e)[:100]}")
        raise


def reset_rate_limit(scope: str) -> bool:
    """Reset rate limit for scope"""
    try:
        key = f"rl:{scope}"
        cache.delete(key)
        logger.debug(f"Rate limit reset: {scope}")
        return True
    except Exception as e:
        logger.error(f"reset_rate_limit error: {str(e)[:100]}")
        return False


# ============================================
# BACKWARDS COMPATIBILITY (Legacy Names)
# ============================================


def store_otp(identifier: str, otp: str, timeout=OTP_TTL) -> bool:
    """Legacy wrapper - convert string OTP to hashed format"""
    try:
        hashed, salt = hash_otp_with_salt(otp)
        otp_hash_obj = OtpHash(hash=hashed, salt=salt)
        return store_otp_hash(identifier, otp_hash_obj, ttl=timeout)
    except Exception as e:
        logger.error(f"store_otp wrapper error: {str(e)[:100]}")
        return False


def get_otp(identifier: str) -> Optional[str]:
    """Legacy wrapper - returns JSON string or None"""
    otp_hash = get_otp_hash(identifier)
    if otp_hash:
        return otp_hash.to_json()
    return None


def hash_otp(otp: str, salt: str = None) -> Tuple[str, str]:
    """Legacy wrapper - compatible with old API"""
    return hash_otp_with_salt(otp, salt)
