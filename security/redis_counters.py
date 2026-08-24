import logging
import os

import redis
from django.conf import settings

logger = logging.getLogger(__name__)

_redis_url = getattr(settings, "REDIS_URL", None) or os.getenv("REDIS_URL", "redis://redis:6379/0")
try:
    redis_client = redis.StrictRedis.from_url(_redis_url, decode_responses=True)
except Exception as e:
    logger.error("Failed to initialize Redis client: %s", e)
    redis_client = None


def incr_with_ttl(key: str, ttl: int = 60):
    if not redis_client:
        return 0
    val = redis_client.incr(key)
    if val == 1:
        redis_client.expire(key, ttl)
    return int(val)


def get_int(key: str, default: int = 0) -> int:
    if not redis_client:
        return default
    v = redis_client.get(key)
    return int(v) if v else default


def set_with_ttl(key: str, value: int, ttl: int):
    if not redis_client:
        return
    redis_client.set(key, value, ex=ttl)


def delete_key(key: str):
    if not redis_client:
        return
    redis_client.delete(key)
