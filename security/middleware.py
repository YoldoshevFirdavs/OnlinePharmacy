import logging
from datetime import timedelta
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .models import BanRecord

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Get real client IP address from request, considering proxy headers"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


def get_device_fingerprint(request):
    """Extract device fingerprint from cookie or header"""
    fp = request.COOKIES.get('device_fp')
    if not fp:
        fp = request.META.get('HTTP_X_DEVICE_FINGERPRINT')
    return fp


class BanMiddleware:
    """
    Ban va rate-limit middleware - redirect loop yo'q
    
    Features:
    - IP/fingerprint/user based bans
    - Temporary/permanent ban types
    - No redirect loop (403 direct return)
    - Debounced logging (1 log per 60s per IP)
    - Auto-expire temporary bans
    """
    
    # Configuration
    RATE_THRESHOLD = 20  # requests in RATE_WINDOW
    RATE_WINDOW = 10  # seconds
    TEMP_BAN_THRESHOLD = 100  # requests
    TEMP_BAN_WINDOW = 60  # seconds
    
    # Paths to exclude from ban checking
    EXCLUDED_PATHS = [
        '/static/',
        '/media/',
        '/health/',
        '/favicon.ico',
        '/robots.txt',
        '/security/not-allowed/',  # Don't block not-allowed page itself
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip excluded paths
        if any(request.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return self.get_response(request)
        
        # Get identifiers
        ip = get_client_ip(request)
        fp = get_device_fingerprint(request)
        user = getattr(request, 'user', None)  # Safe access to user (may not exist yet)
        
        # Check if banned
        ban = BanRecord.get_active_ban(ip=ip, fingerprint=fp, user=user if user and user.is_authenticated else None)
        
        if ban:
            # Log ban (debounced)
            self._log_ban_attempt(ip, ban)
            
            # Return 403 with not-allowed HTML (no redirect loop)
            return self._render_not_allowed(request, ban)
        
        # Check rate limit and create temporary ban if needed
        if self._check_and_update_rate_limit(ip, fp):
            # Create temporary ban
            ban = BanRecord.objects.create(
                ip=ip,
                fingerprint=fp,
                user=user,
                reason=f'Rate limit exceeded: {self.TEMP_BAN_THRESHOLD}+ requests in {self.TEMP_BAN_WINDOW}s',
                ban_type='temporary',
                created_by='system',
                attempts=self.TEMP_BAN_THRESHOLD,
                source=request.path,
                expires_at=timezone.now() + timedelta(minutes=5),
                meta={'request_path': request.path, 'user_agent': request.META.get('HTTP_USER_AGENT')}
            )
            
            logger.warning(f"[BAN] Temporary ban created for IP {ip}: {ban.reason}")
            
            return self._render_not_allowed(request, ban)
        
        # Normal request
        response = self.get_response(request)
        return response
    
    def _check_and_update_rate_limit(self, ip, fp):
        """Check rate limit using cache counters"""
        if not ip and not fp:
            return False
        
        # Use IP as primary identifier
        identifier = ip if ip else fp
        cache_key = f"rate_limit:{identifier}"
        
        try:
            current_count = cache.get(cache_key, 0)
            current_count += 1
            
            # Set with RATE_WINDOW TTL (first increment)
            if current_count == 1:
                cache.set(cache_key, current_count, timeout=self.RATE_WINDOW)
            else:
                # Ensure TTL stays (use timeout to refresh)
                cache.set(cache_key, current_count, timeout=self.RATE_WINDOW)
            
            # Ban if threshold exceeded
            return current_count > self.TEMP_BAN_THRESHOLD
            
        except Exception as e:
            logger.error(f"[BAN] Rate limit check error for {identifier}: {str(e)}")
            return False
    
    def _log_ban_attempt(self, ip, ban):
        """Log ban attempt (debounced - once per 60s per IP)"""
        log_key = f"ban_log:{ip}"
        
        if cache.get(log_key):
            return  # Already logged recently
        
        # Set debounce flag
        cache.set(log_key, True, timeout=60)
        
        logger.warning(f"[BAN] IP {ip} blocked - Type: {ban.get_ban_type_display()}, Reason: {ban.reason}, Created: {ban.created_by}")
    
    def _render_not_allowed(self, request, ban):
        """Render not-allowed page directly (no redirect loop)"""
        context = {
            'ban': ban,
            'ip': get_client_ip(request),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@pharmacy.local'),
            'support_phone': getattr(settings, 'SUPPORT_PHONE', '+998 (71) 200-00-00'),
        }
        
        html = render_to_string('security/not_allowed.html', context, request=request)
        return HttpResponseForbidden(html, content_type='text/html; charset=utf-8')
