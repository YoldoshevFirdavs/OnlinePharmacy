import time
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from .redis_counters import incr_with_ttl
import logging

logger = logging.getLogger(__name__)

class AuthRateLimitMiddleware(MiddlewareMixin):
    def process_request(self, request):
        ip = request.META.get('REMOTE_ADDR')
        path = request.path

        if path.startswith('/api/v1/users/login') or path.startswith('/api/v1/users/verify-otp'):
            IP_REQ_PER_MIN = getattr(settings, 'AUTH_IP_REQ_PER_MIN', 100)

            ip_min_key = f"ip:minute:{ip}:{int(time.time()//60)}"
            ip_min_count = incr_with_ttl(ip_min_key, ttl=60)
            if ip_min_count > IP_REQ_PER_MIN:
                logger.warning(f"IP rate limit exceeded for {ip} on path {path}. Count: {ip_min_count}")
                return JsonResponse({'detail':'Too many requests from IP. Please try again in a minute.'}, status=429)
            
        return None