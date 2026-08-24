import logging

from django.conf import settings

from .redis_counters import get_int, incr_with_ttl, set_with_ttl

logger = logging.getLogger(__name__)

# Configurable lockout duration
LOCKOUT_TTL = getattr(settings, "AUTH_LOCKOUT_TTL", 60 * 15)  # 15 minutes default


def record_failed_attempt(account_key: str):
    """
    Records a failed authentication attempt for a given account key.
    If thresholds are exceeded, the account is locked out.
    """
    ACCOUNT_ATTEMPTS_10MIN = getattr(settings, "AUTH_ATTEMPTS_10MIN", 5)
    ACCOUNT_ATTEMPTS_DAY = getattr(settings, "AUTH_ATTEMPTS_DAY", 20)

    k1 = f"acct:fail:10min:{account_key}"
    k2 = f"acct:fail:day:{account_key}"

    v1 = incr_with_ttl(k1, ttl=600)  # 10 minutes
    v2 = incr_with_ttl(k2, ttl=86400)  # 1 day

    if v1 >= ACCOUNT_ATTEMPTS_10MIN:
        lock_key = f"acct:lock:{account_key}"
        set_with_ttl(lock_key, 1, LOCKOUT_TTL)
        logger.warning(f"Account {account_key} locked out for {LOCKOUT_TTL} seconds due to too many failed attempts.")

    logger.debug(f"Failed attempt recorded for {account_key}: 10min={v1}, 1day={v2}")
    return v1, v2


def is_locked(account_key: str) -> bool:
    """Checks if an account is currently locked out."""
    return get_int(f"acct:lock:{account_key}") > 0


def reset_lockout(account_key: str):
    """Resets the lockout status for an account."""
    from .redis_counters import delete_key

    delete_key(f"acct:lock:{account_key}")
    delete_key(f"acct:fail:10min:{account_key}")
    delete_key(f"acct:fail:day:{account_key}")
    logger.info(f"Lockout and failed attempts reset for {account_key}")
