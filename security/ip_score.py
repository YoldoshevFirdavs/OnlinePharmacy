from .redis_counters import redis_client, get_int, delete_key
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def incr_ip_score(ip: str, delta: int = 10, ttl: int = 86400):
    """
    Increments the risk score for a given IP address.
    Sets a TTL for the score.
    """
    key = f"ip:score:{ip}"
    new_score = redis_client.incrby(key, delta)
    redis_client.expire(key, ttl) # Reset TTL on every update
    logger.debug(f"IP {ip} score increased by {delta} to {new_score}")

    # Log if IP score crosses a high-risk threshold
    HIGH_RISK_IP_SCORE = getattr(settings, 'AUTH_HIGH_RISK_IP_SCORE', 50)
    BLOCK_IP_SCORE = getattr(settings, 'AUTH_BLOCK_IP_SCORE', 80)

    if new_score >= BLOCK_IP_SCORE:
        logger.critical(f"IP {ip} score reached BLOCKING threshold ({new_score}/{BLOCK_IP_SCORE}). Consider blocking this IP.")
        # Here you might trigger an alert (e.g., Sentry, email)
    elif new_score >= HIGH_RISK_IP_SCORE:
        logger.warning(f"IP {ip} score reached HIGH RISK threshold ({new_score}/{HIGH_RISK_IP_SCORE}). Monitoring for suspicious activity.")
        # Here you might trigger an alert (e.g., Sentry, email)

    return int(new_score)

def decr_ip_score(ip: str, delta: int = 5, min_score: int = 0):
    """
    Decrements the risk score for a given IP address, ensuring it doesn't go below min_score.
    """
    key = f"ip:score:{ip}"
    current_score = get_ip_score(ip)
    if current_score > min_score:
        new_score = max(min_score, current_score - delta)
        redis_client.set(key, new_score)
        logger.debug(f"IP {ip} score decreased by {delta} to {new_score}")
        return new_score
    return current_score

def get_ip_score(ip: str) -> int:
    """Retrieves the current risk score for an IP address."""
    return get_int(f"ip:score:{ip}")

def reset_ip_score(ip: str):
    """Resets the IP score to 0."""
    delete_key(f"ip:score:{ip}")
    logger.info(f"IP {ip} score reset.")