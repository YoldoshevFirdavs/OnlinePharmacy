"""
Universal Rate Limiting Manager

This module provides a centralized rate limiting system that:
1. Bypasses rate limiting during testing (TESTING=True)
2. Uses configurable limits per scope
3. Provides consistent API across the application
"""

from typing import Optional, Tuple

from django.conf import settings
from django.core.cache import cache


def _is_testing() -> bool:
    """Check if we're in testing mode"""
    return getattr(settings, "TESTING", False)


def _get_scope_key(scope: str) -> str:
    """Generate cache key for scope"""
    return f"rl:{scope}"


def check_rate_limit(scope: str, max_attempts: Optional[int] = None, window: int = 60) -> Tuple[bool, int]:
    """
    Check if action exceeds rate limit.

    Args:
        scope: Rate limit scope (e.g., "admin_login:user123", "otp:verify:+998901234567")
        max_attempts: Maximum attempts allowed (default: from settings or 100 for tests)
        window: Time window in seconds (default: 60)

    Returns:
        Tuple of (allowed: bool, remaining_seconds: int)
    """
    # Bypass rate limiting during testing
    if _is_testing():
        return True, 0

    # Use testing default for tests if max_attempts not specified
    if max_attempts is None:
        max_attempts = getattr(settings, "RATE_LIMIT_MAX_ATTEMPTS", 100 if _is_testing() else 5)

    try:
        key = _get_scope_key(scope)
        count = cache.get(key, 0)

        if count >= max_attempts:
            remaining = window  # Estimate
            return False, remaining

        cache.set(key, count + 1, timeout=window)
        return True, 0
    except Exception as e:
        # Fail-safe: allow request on error
        return True, 0


def reset_rate_limit(scope: str) -> bool:
    """
    Reset rate limit for a scope.

    Args:
        scope: Rate limit scope to reset

    Returns:
        True if successful, False otherwise
    """
    try:
        key = _get_scope_key(scope)
        cache.delete(key)
        return True
    except Exception:
        return False


def increment_rate_limit(scope: str, max_attempts: Optional[int] = None, window: int = 60) -> Tuple[bool, int]:
    """
    Manually increment rate limit counter (without checking first).

    Args:
        scope: Rate limit scope
        max_attempts: Maximum attempts allowed
        window: Time window in seconds

    Returns:
        Tuple of (allowed: bool, remaining_seconds: int)
    """
    return check_rate_limit(scope, max_attempts, window)
