import redis
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Ensure REDIS_URL is configured in settings.py
try:
    redis_client = redis.StrictRedis.from_url(settings.REDIS_URL, decode_responses=True)
    # Test connection
    redis_client.ping()
    logger.info("Successfully connected to Redis at %s", settings.REDIS_URL)
except Exception as e:
    logger.error("Failed to connect to Redis: %s. Please ensure Redis is running and REDIS_URL is correct.", e)
    # Fallback or raise error depending on application requirements
    # For now, we'll let it fail if Redis is critical.

def incr_with_ttl(key: str, ttl: int = 60):
    """Increments a counter in Redis and sets/resets its TTL."""
    val = redis_client.incr(key)
    if val == 1: # Only set TTL if it's the first increment in this cycle
        redis_client.expire(key, ttl)
    return int(val)

def get_int(key: str):
    """Retrieves an integer value from Redis."""
    v = redis_client.get(key)
    return int(v) if v else 0

def set_with_ttl(key: str, value: int, ttl: int):
    """Sets an integer value in Redis with a TTL."""
    redis_client.set(key, value, ex=ttl)

def delete_key(key: str):
    """Deletes a key from Redis."""
    redis_client.delete(key)
