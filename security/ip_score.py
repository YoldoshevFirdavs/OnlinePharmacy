import logging

from django.conf import settings

from .redis_counters import delete_key, get_int, redis_client

logger = logging.getLogger(__name__)


def incr_ip_score(ip: str, delta: int = 10, ttl: int = 86400):
    if not redis_client:
        return 0
    key = f"ip:score:{ip}"
    new_score = redis_client.incrby(key, delta)
    redis_client.expire(key, ttl)
    HIGH_RISK_IP_SCORE = getattr(settings, "AUTH_HIGH_RISK_IP_SCORE", 50)
    BLOCK_IP_SCORE = getattr(settings, "AUTH_BLOCK_IP_SCORE", 80)
    if new_score >= BLOCK_IP_SCORE:
        logger.critical(
            "IP %s score reached BLOCKING threshold (%s/%s).",
            ip,
            new_score,
            BLOCK_IP_SCORE,
        )
    elif new_score >= HIGH_RISK_IP_SCORE:
        logger.warning(
            "IP %s score reached HIGH RISK threshold (%s/%s).",
            ip,
            new_score,
            HIGH_RISK_IP_SCORE,
        )
    return int(new_score)


def decr_ip_score(ip: str, delta: int = 5, min_score: int = 0):
    if not redis_client:
        return 0
    key = f"ip:score:{ip}"
    current_score = get_ip_score(ip)
    if current_score > min_score:
        new_score = max(min_score, current_score - delta)
        redis_client.set(key, new_score)
        return new_score
    return current_score


def get_ip_score(ip: str) -> int:
    return get_int(f"ip:score:{ip}")


def reset_ip_score(ip: str):
    delete_key(f"ip:score:{ip}")
