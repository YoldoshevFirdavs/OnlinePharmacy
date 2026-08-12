import hashlib
import json
import logging
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

User = get_user_model()
logger = logging.getLogger(__name__)

# ============================================
# CONSTANTS
# ============================================

OTP_TTL = 900  # 15 minutes
ADMIN_SESSION_TTL = 600  # 10 minutes
ADMIN_CODE_TTL = 300  # 5 minutes
TELEGRAM_OTP_LENGTH = 4
EMAIL_OTP_LENGTH = 6
SALT_LENGTH = 16  # 32 hex chars (16 bytes)
RATE_LIMIT_WINDOW = 60  # seconds
MAX_OTP_ATTEMPTS = 5
RATE_LIMIT_SECONDS = 60

# Admin specific limits
MAX_ATTEMPTS = getattr(settings, "ADMIN_LOGIN_MAX_ATTEMPTS", 5)
BAN_SECONDS = getattr(settings, "ADMIN_BAN_SECONDS", 3600)


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
        salt = secrets.token_hex(SALT_LENGTH // 2)
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


def create_otp_session(purpose: str, *args, **kwargs):
    """
    Create an OTP session. Accepts 'telegram', 'email'.
    'registration' is an alias for 'email'.
    """
    if purpose == "registration":
        purpose = "email"

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
            "identifier": str(identifier),
            "created_at": int(time.time()),
        }

        for attempt in range(3):
            try:
                cache.set(key, payload, timeout=ttl)
                logger.info(f"Session bound: {session_id[:8]}... (TTL: {ttl}s)")
                return True
            except Exception as e:
                logger.warning(f"Cache set attempt {attempt+1} failed: {str(e)[:100]}")
                time.sleep(0.1)

        logger.error(f"Failed to bind session after 3 attempts")
        return False
    except Exception as e:
        logger.error(f"bind_session_to_user error: {str(e)[:200]}")
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


def increment_attempts(session_id: str) -> int:
    """Increment attempt counter for session and return new count."""
    try:
        key = f"auth_session:{session_id}"
        session = cache.get(key)
        if not session or not isinstance(session, dict):
            return 0

        current_attempts = session.get("attempts", 0)
        new_attempts = current_attempts + 1
        session["attempts"] = new_attempts
        cache.set(key, session, timeout=session.get("ttl", OTP_TTL))
        logger.debug(
            f"Incremented attempts for session {session_id[:8]}... to {new_attempts}"
        )
        return new_attempts
    except Exception as e:
        logger.error(f"increment_attempts error: {str(e)[:100]}")
        return 0


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
        json_data = otp_hash_obj.to_json()
        result = cache.set(key, json_data, timeout=ttl)
        logger.info(
            f"OTP hash stored (TTL: {ttl}s) key={key} - cache.set result: {result}"
        )
        return result
    except Exception as e:
        logger.error(f"store_otp_hash error: {str(e)[:200]}")
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
# ADMIN SESSION & CODE HELPERS
# ============================================


def create_admin_session(identifier: str, user_id: int) -> Dict[str, Any]:
    """
    Creates an admin session and stores metadata in cache.
    Returns a dictionary containing session_id and the stored meta.
    """
    session_id = generate_session_id()
    key = f"admin_session:{session_id}"
    meta = {
        "identifier": identifier,
        "user_id": user_id,
        "created_at": int(time.time()),
    }
    try:
        cache.set(key, meta, timeout=ADMIN_SESSION_TTL)
        logger.info(
            f"Admin session created: {session_id[:8]}... for {mask_pii(identifier)}"
        )
        return {"session_id": session_id, **meta}
    except Exception as e:
        logger.error(f"create_admin_session error: {str(e)[:100]}")
        raise


def get_admin_session_meta(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves admin session metadata from cache."""
    if not session_id:
        return None
    try:
        key = f"admin_session:{session_id}"
        result = cache.get(key)
        if result is None:
            logger.warning(f"Admin session not found: {session_id[:8]}...")
            return None
        if not isinstance(result, dict):
            logger.error(
                f"Admin session meta corrupted (type: {type(result).__name__})"
            )
            return None
        return result
    except Exception as e:
        logger.error(f"get_admin_session_meta error: {str(e)[:100]}")
        return None


def verify_admin_session(
    session_id: str, email: str
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Verifies an admin session by session_id and email.
    Returns (True, meta) or (False, None).
    """
    meta = get_admin_session_meta(session_id)
    if meta and meta.get("email") == email:
        logger.info(
            f"Admin session verified: {session_id[:8]}... for {mask_pii(email)}"
        )
        return True, meta
    logger.warning(
        f"Admin session verification failed for {session_id[:8]}... (email mismatch or not found)"
    )
    return False, None


def delete_admin_session(session_id: str) -> None:
    """Deletes an admin session from cache."""
    try:
        key = f"admin_session:{session_id}"
        cache.delete(key)
        logger.debug(f"Admin session deleted: {session_id[:8]}...")
    except Exception as e:
        logger.error(f"delete_admin_session error: {str(e)[:100]}")


def store_admin_code_hash(
    session_id: str, code: str, ttl: int = ADMIN_CODE_TTL
) -> bool:
    """
    Stores a hashed admin verification code in cache, keyed by session_id.
    """
    if not session_id or not code:
        logger.error("Missing session_id or code for store_admin_code_hash")
        return False
    try:
        hashed, salt = hash_otp_with_salt(code)
        otp_hash_obj = OtpHash(hash=hashed, salt=salt)
        key = f"admin_code:{session_id}"
        cache.set(key, otp_hash_obj.to_json(), timeout=ttl)
        logger.info(
            f"Admin code hash stored for session: {session_id[:8]}... (TTL: {ttl}s)"
        )
        return True
    except Exception as e:
        logger.error(f"store_admin_code_hash error: {str(e)[:100]}")
        return False


def get_admin_code_hash(session_id: str) -> Optional[OtpHash]:
    """Retrieves a hashed admin verification code from cache."""
    if not session_id:
        return None
    try:
        key = f"admin_code:{session_id}"
        stored = cache.get(key)
        if stored is None:
            logger.debug(f"Admin code not found for session: {session_id[:8]}...")
            return None
        return OtpHash.from_json(stored)
    except ValueError as e:
        logger.warning(f"Invalid Admin code hash format: {str(e)[:50]}")
        return None
    except Exception as e:
        logger.error(f"get_admin_code_hash error: {str(e)[:100]}")
        return None


def delete_admin_code(session_id: str) -> None:
    """Deletes an admin verification code from cache."""
    try:
        key = f"admin_code:{session_id}"
        cache.delete(key)
        logger.debug(f"Admin code deleted for session: {session_id[:8]}...")
    except Exception as e:
        logger.error(f"delete_admin_code error: {str(e)[:100]}")


def verify_admin_code(
    session_id: str, provided_code: str
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Verifies an admin code and returns the associated session meta on success.
    Returns (True, meta) or (False, None).
    """
    if not session_id or not provided_code:
        logger.warning(
            "Missing session_id or provided_code for admin code verification"
        )
        return False, None

    otp_hash_obj = get_admin_code_hash(session_id)
    if not otp_hash_obj:
        logger.warning(
            f"Admin code not found or expired for session: {session_id[:8]}..."
        )
        return False, None

    is_valid = verify_otp_code(provided_code, otp_hash_obj)

    if is_valid:
        meta = get_admin_session_meta(session_id)
        if meta:
            logger.info(f"Admin code verified for session: {session_id[:8]}...")
            return True, meta
        else:
            logger.error(
                f"Admin session meta not found after code verification for session: {session_id[:8]}..."
            )
            return False, None
    else:
        logger.warning(f"Invalid admin code provided for session: {session_id[:8]}...")
        return False, None


# ============================================
# ADMIN LOGIN ATTEMPTS & BANNING
# ============================================


def get_admin_attempts_key(identifier: str) -> str:
    """Helper to get the cache key for login attempts."""
    return f"admin_login_attempts:{identifier}"


def get_admin_ban_key(identifier: str) -> str:
    """Helper to get the cache key for a ban."""
    return f"admin_login_banned:{identifier}"


def is_banned(identifier: str) -> bool:
    """Checks if an admin identifier (IP, email, etc.) is currently banned."""
    return cache.get(get_admin_ban_key(identifier)) is not None


def record_failed_attempt(identifier: str) -> bool:
    """
    Records a failed login attempt for an admin.
    Bans the identifier if attempts exceed MAX_ATTEMPTS.
    Returns True if banned, False otherwise.
    """
    if is_banned(identifier):
        return True

    key = get_admin_attempts_key(identifier)
    # Use a dedicated timeout for the attempt counter
    # Same as ban seconds, so it clears after the ban would have expired anyway
    attempts = cache.get(key, 0) + 1

    if attempts >= MAX_ATTEMPTS:
        ban_key = get_admin_ban_key(identifier)
        cache.set(ban_key, True, timeout=BAN_SECONDS)
        cache.delete(key)  # Clean up the attempts counter
        logger.warning(f"Admin identifier banned: {mask_pii(identifier)}")
        return True
    else:
        cache.set(key, attempts, timeout=BAN_SECONDS)
        logger.info(
            f"Admin failed attempt {attempts}/{MAX_ATTEMPTS} for: {mask_pii(identifier)}"
        )
        return False


def reset_failed_attempts(identifier: str):
    """Resets the failed attempt counter and ban for an admin."""
    cache.delete(get_admin_attempts_key(identifier))
    cache.delete(get_admin_ban_key(identifier))
    logger.info(f"Admin login attempts reset for: {mask_pii(identifier)}")


def is_admin_identifier(identifier: str) -> bool:
    """
    Checks if the given identifier (email or phone number) belongs to an admin user.
    """
    if not identifier:
        return False
    try:
        if "@" in identifier:
            return User.objects.filter(email=identifier, is_staff=True).exists()
        return User.objects.filter(phone_number=identifier, is_staff=True).exists()
    except Exception as e:
        logger.error(f"Error checking admin identifier {mask_pii(identifier)}: {e}")
        return False


# ============================================
# VERIFICATION FLOW
# ============================================


def verify_otp_once(
    session_id: str, provided_code: str, identifier: str = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Verify OTP code and invalidate on success.
    Returns (is_valid, message, session_meta) tuple.
    session_meta is returned on success so caller can access user_id.
    """
    if not all([session_id, provided_code]):
        msg = "Missing session_id or provided_code"
        logger.warning(msg)
        return False, msg, None

    session_meta = get_session_meta(session_id)
    if not session_meta:
        msg = "Session expired or not found"
        logger.warning(msg)
        return False, msg, None

    identifier = identifier or session_meta.get("identifier")
    if not identifier:
        msg = "Identifier not found in session"
        logger.error(msg)
        return False, msg, None

    otp_hash_obj = get_otp_hash(identifier)
    if not otp_hash_obj:
        otp_hash_obj = get_bot_otp(session_id)
    if not otp_hash_obj:
        msg = "OTP code not found or expired"
        logger.warning(msg)
        return False, msg, None

    if not verify_otp_code(provided_code, otp_hash_obj):
        msg = "Invalid OTP code"
        logger.warning(msg)
        return False, msg, None

    delete_otp(identifier)
    delete_session(session_id)

    logger.info(f"OTP verification SUCCESS for session {session_id[:8]}...")
    return True, "OTP verified successfully", session_meta


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
            remaining = window
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
        if isinstance(otp, str) and otp.startswith("{"):
            otp_hash = OtpHash.from_json(otp)
        else:
            hashed, salt = hash_otp_with_salt(otp)
            otp_hash = OtpHash(hash=hashed, salt=salt)
        return store_otp_hash(identifier, otp_hash, ttl=timeout)
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


# ============================================
# BACKWARDS COMPATIBILITY (Test Session Store)
# ============================================


def _store_otp_for_test_session(
    session: OtpSession, code: str, ttl_seconds: int = OTP_TTL
) -> None:
    """Legacy: Store OTP for test sessions"""
    try:
        store_bot_otp(session.session_id, code, ttl=ttl_seconds)
    except Exception as e:
        logger.error(f"_store_otp_for_test_session error: {str(e)[:100]}")


def rate_limit_or_raise(scope: str, window=60, window_seconds=None):
    """Legacy: Rate-limit a given scope; raises ValueError if limit exceeded."""
    if window_seconds is not None:
        window = window_seconds
    allowed, remaining = check_rate_limit(scope, window=window)
    if not allowed:
        raise ValueError(f"Rate limit exceeded for {scope}")
    return True


def mask_pii(value: str, show_chars: int = 3) -> str:
    """Mask PII for safe logging"""
    if not value:
        return "***"
    if len(value) <= show_chars:
        return value[0] + "*" * (len(value) - 1)
    return f"{value[:show_chars]}{'*' * (len(value) - show_chars)}"
