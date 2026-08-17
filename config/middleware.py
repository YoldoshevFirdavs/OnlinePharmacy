import logging
import time
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.core.cache import cache
from users.services import BanService

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Get real client IP address from request, considering proxy headers"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


# Dual approval request cache keys
def get_unban_request_key(fp=None, user_id=None):
    """Generate cache key for unban request"""
    if fp:
        return f"unban_request_fp:{fp}"
    elif user_id:
        return f"unban_request_user:{user_id}"
    return None


def get_pending_unban_request_key(request_id):
    """Generate cache key for pending unban request"""
    return f"pending_unban:{request_id}"


class DeviceFingerprintMiddleware:
    """
    Device fingerprint-based ban and rate limiting middleware.
    Implements per-fingerprint rate limiting and ban checking using Redis/Django cache.
    
    Features:
    - Fingerprint extraction from cookie or header
    - Per-fingerprint rate limiting (RATE_THRESHOLD req/s)
    - IP blocking after rate limit violations
    - Main page refresh limit monitoring
    - Dual approval workflow support
    """
    
    # Configuration constants
    RATE_THRESHOLD = getattr(settings, 'FINGERPRINT_RATE_THRESHOLD', 10)  # requests per second
    TEMP_BAN_DURATION = getattr(settings, 'FINGERPRINT_TEMP_BAN_DURATION', 60)  # minutes
    IP_BLOCK_DURATION = getattr(settings, 'FINGERPRINT_IP_BLOCK_DURATION', 3600)  # seconds
    MAIN_PAGE_REFRESH_LIMIT = getattr(settings, 'FINGERPRINT_MAIN_PAGE_REFRESH_LIMIT', 20)  # per hour
    ADMIN_UNBAN_LIMIT = getattr(settings, 'ADMIN_UNBAN_LIMIT', 10)  # per hour
    
    EXCLUDED_PATHS = [
        '/static/',
        '/media/',
        '/health/',
        '/favicon.ico',
        '/robots.txt',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Extract device fingerprint
        fp = self._get_fingerprint(request)
        ip = get_client_ip(request)
        
        # Skip processing for excluded paths
        if any(request.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return self.get_response(request)
        
        # Store fingerprint in request for other middleware/views to use
        request.device_fingerprint = fp
        request.client_ip = ip
        
        # Process fingerprint-based checks
        if fp:
            try:
                # Check if IP is temporarily blocked
                if self._is_ip_blocked(ip):
                    logger.warning(f"[FINGERPRINT] IP {ip} is temporarily blocked")
                    return self._redirect_not_allowed(request, "IP temporarily blocked")
                
                # Rate limiting check
                if self._check_rate_limit(fp, ip, request.path):
                    logger.warning(f"[FINGERPRINT] Rate limit exceeded for {fp[:8]}... from IP {ip}")
                    return self._redirect_not_allowed(request, "Rate limit exceeded")
                
                # Ban check
                ban_info = self._check_ban_status(fp)
                if ban_info and ban_info['is_banned']:
                    # Check if ban has expired
                    if ban_info.get('ban_expires_at'):
                        if timezone.now() > ban_info['ban_expires_at']:
                            # Ban expired, remove it
                            BanService.unban_by_fp(fp, actor=None)
                        else:
                            logger.warning(f"[FINGERPRINT] Banned fingerprint {fp[:8]}... attempted access to {request.path}")
                            return self._redirect_not_allowed(request, f"Banned: {ban_info.get('reason', 'Unknown')}")
                    else:
                        # Permanent ban
                        logger.warning(f"[FINGERPRINT] Permanently banned fingerprint {fp[:8]}... attempted access to {request.path}")
                        return self._redirect_not_allowed(request, f"Permanently banned: {ban_info.get('reason', 'Unknown')}")
                
                # Main page refresh limit
                if request.path == '/' and self._check_main_page_limit(fp):
                    logger.warning(f"[FINGERPRINT] Main page refresh limit exceeded for {fp[:8]}...")
                    BanService.ban_by_fp(
                        fp, 
                        duration_minutes=self.TEMP_BAN_DURATION,
                        reason='Main page refresh limit exceeded',
                        banned_for='main_page_flood',
                        actor='system'
                    )
                    return self._redirect_not_allowed(request, "Main page refresh limit exceeded")
                    
                # Admin unban request limit check
                if request.user.is_staff and self._check_admin_unban_limit(request.user.id, ip):
                    logger.warning(f"[FINGERPRINT] Admin {request.user.id} exceeded unban request limit")
                    return self._redirect_not_allowed(request, "Admin unban request limit exceeded")
                    
            except Exception as e:
                logger.error(f"[FINGERPRINT] Error in fingerprint processing: {str(e)}")
                # Continue processing on error to avoid breaking the site
        else:
            # No fingerprint - skip fingerprint-based checks
            pass
        
        response = self.get_response(request)
        return response

    def _get_fingerprint(self, request):
        """Extract device fingerprint from cookie or header"""
        fp = request.COOKIES.get('device_fp')
        if not fp:
            fp = request.META.get('HTTP_AUTHORIZATION_FINGERPRINT')
        return fp

    def _is_ip_blocked(self, ip):
        """Check if IP is temporarily blocked"""
        if not ip:
            return False
        return cache.get(f"ip_block:{ip}", False)

    def _check_rate_limit(self, fp, ip, path):
        """
        Check per-fingerprint rate limiting using fixed window (Redis INCR + EXPIRE 1s).
        Returns True if rate limit exceeded, False otherwise.
        """
        if not fp:
            return False
            
        cache_key = f"rate_fp:{fp}"
        try:
            # Get current count safely
            current_count = cache.get(cache_key, 0)
            current_count += 1
            
            # Set with 1 second TTL
            cache.set(cache_key, current_count, timeout=1)
            
            if current_count > self.RATE_THRESHOLD:
                # Rate limit exceeded - ban fingerprint and block IP
                BanService.ban_by_fp(
                    fp,
                    duration_minutes=self.TEMP_BAN_DURATION,
                    reason=f'Rate limit exceeded: {current_count} requests/sec',
                    banned_for='rate_limit',
                    actor='system'
                )
                
                # Also temporarily block the IP
                if ip:
                    cache.set(f"ip_block:{ip}", True, timeout=self.IP_BLOCK_DURATION)
                    logger.warning(f"[FINGERPRINT] IP {ip} blocked for {self.IP_BLOCK_DURATION}s due to rate limiting")
                
                # Record the event
                BanService.record_blocked_event(
                    actor='system',
                    fp=fp,
                    path=path,
                    reason=f'Rate limit exceeded: {current_count} requests/sec',
                    banned_for='rate_limit'
                )
                
                return True
                
        except Exception as e:
            logger.error(f"[FINGERPRINT] Rate limiting error for key '{cache_key}': {str(e)}")
            
        return False

    def _check_ban_status(self, fp):
        """Check if fingerprint is banned"""
        if not fp:
            return None
            
        try:
            ban_info = cache.get(f"ban_fp:{fp}")
            return ban_info
        except Exception as e:
            logger.error(f"[FINGERPRINT] Ban check error: {str(e)}")
            return None

    def _check_main_page_limit(self, fp):
        """Check main page refresh limit (MAIN_PAGE_REFRESH_LIMIT per hour)"""
        if not fp:
            return False
            
        cache_key = f"main_page_fp:{fp}"
        
        try:
            current_count = cache.incr(cache_key)
            if current_count == 1:
                cache.expire(cache_key, 3600)  # 1 hour TTL
            
            return current_count > self.MAIN_PAGE_REFRESH_LIMIT
        except Exception as e:
            logger.error(f"[FINGERPRINT] Main page limit check error: {str(e)}")
            return False

    def _check_admin_unban_limit(self, admin_id, ip):
        """Check if admin exceeded unban request limit"""
        if not admin_id:
            return False
            
        cache_key = f"admin_unban:{admin_id}"
        
        try:
            # Get current count safely
            current_count = cache.get(cache_key, 0)
            current_count += 1
            
            # Set with 1 hour TTL
            cache.set(cache_key, current_count, timeout=3600)
            
            return current_count > self.ADMIN_UNBAN_LIMIT
        except Exception as e:
            logger.error(f"[FINGERPRINT] Admin unban limit check error for key '{cache_key}': {str(e)}")
            return False

    def _redirect_not_allowed(self, request, reason):
        """Redirect to not allowed page with context"""
        next_url = request.get_full_path()
        return redirect(f"/dashboard/not-allowed/?next={next_url}&reason={reason}")


class CustomErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        # Agar DEBUG rejimi yoqilgan bo'lsa va bu sozlama maxsus
        # o'chirib qo'yilmagan bo'lsa, Django'ning standart xatolik
        # sahifasini ko'rsatamiz.
        if settings.DEBUG and not getattr(settings, "SHOW_CUSTOM_ERROR_PAGES", False):
            return None

        # API so'rovlari uchun JSON formatida javob qaytaramiz
        if request.path.startswith("/api/"):
            return JsonResponse(
                {"error": "Xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring."},
                status=500,
            )

        # Oddiy sahifalar uchun 500.html shablonini ko'rsatamiz
        return render(request, "500.html", status=500)


class BanCheckMiddleware:
    """
    Har requestda foydalanuvchining ban holatini tekshirish
    + Main page refresh limit monitoring (anti-flood)
    """
    
    EXCLUDED_PATHS = [
        '/account/',
        '/api/auth/',
        '/auth/',
        '/admin/check',
        '/static/',
        '/media/',
        '/health/',
    ]
    
    ADMIN_PATHS = [
        '/dashboard/',
    ]
    
    # Main page refresh limit
    MAIN_PAGE_REFRESH_LIMIT = 20  # per hour
    MAIN_PAGE_REFRESH_WINDOW = 3600  # 1 soat (seconds)

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Ban tekshirish - faqat authenticated users uchun
        if request.user.is_authenticated:
            self._check_ban_status(request)
            self._check_main_page_flood(request)
        
        response = self.get_response(request)
        return response

    def _check_main_page_flood(self, request):
        """Main page refresh limit monitoring (fingerprint-based)"""
        # Faqat main page (/) uchun
        if request.path != '/':
            return
        
        user = request.user
        if not user.is_authenticated:
            return
        
        try:
            # Refresh count saqlash - sessionda yoki user profile-da
            now = timezone.now().timestamp()
            
            # Sessiondan oldingi refresh time-larni olish
            if not hasattr(request.session, '_refresh_times'):
                request.session['_refresh_times'] = []
            
            refresh_times = request.session['_refresh_times']
            
            # Eski time-larni o'chirish (window tashqarisidagi)
            cutoff_time = now - self.MAIN_PAGE_REFRESH_WINDOW
            refresh_times = [t for t in refresh_times if t > cutoff_time]
            
            # Yangi refresh time qo'shish
            refresh_times.append(now)
            request.session['_refresh_times'] = refresh_times
            
            # Limit tekshirish
            if len(refresh_times) > self.MAIN_PAGE_REFRESH_LIMIT:
                # Limit oshib ketti - vaqtli ban qo'yish
                BanService.ban_user(
                    user,
                    duration_minutes=60,
                    reason=f'Main page refresh limit exceeded ({len(refresh_times)} requests in 1 hour)',
                    banned_for='main_page_flood',
                    banned_by=None
                )
                
                # Audit log
                BanService.record_blocked_event(
                    user,
                    '/',
                    f'Main page refresh limit exceeded: {len(refresh_times)} requests',
                    'main_page_flood'
                )
                
                # Sessionni reset qilish
                request.session['_refresh_times'] = []
                
        except Exception as e:
            logger.error(f"Error in main page flood check: {str(e)}")

    def _check_ban_status(self, request):
        """Ban holatini tekshirish"""
        user = request.user
        current_path = request.path
        
        # Excluded paths-da ban tekshirmiz
        if any(current_path.startswith(path) for path in self.EXCLUDED_PATHS):
            return
        
        # Admin paths-da special tekshirish
        if any(current_path.startswith(path) for path in self.ADMIN_PATHS):
            # Agar admin bo'lmasa, redirect qiling (ban bermang, faqat block qiling)
            if not user.is_staff and not user.is_superuser:
                BanService.record_blocked_event(
                    user,
                    current_path,
                    'Admin panelga kirish urinishi - admin roli yo\'q'
                )
                raise AdminAccessDeniedException(f"Admin roli yo'q: {current_path}")
        
        # Ban tekshirish
        ban_info = BanService.get_ban_info(user)
        if ban_info and ban_info['is_banned']:
            # Ban qo'yilgan
            BanService.record_blocked_event(
                user,
                current_path,
                ban_info['ban_reason'],
                ban_info['banned_for']
            )
            raise BannedException(
                f"User {user.id} is banned for {ban_info['banned_for']}",
                ban_info
            )

    def process_exception(self, request, exception):
        """Exception-larni handle qilish"""
        if isinstance(exception, BannedException):
            # not_allowed sahifasiga redirect
            return redirect(f"/dashboard/not-allowed/?next={request.path}")
        
        if isinstance(exception, AdminAccessDeniedException):
            # not_allowed sahifasiga redirect
            return redirect(f"/dashboard/not-allowed/?next={request.path}")
        
        return None


class BannedException(Exception):
    """Foydalanuvchi bannalangan exception"""
    def __init__(self, message, ban_info=None):
        self.message = message
        self.ban_info = ban_info
        super().__init__(self.message)


class AdminAccessDeniedException(Exception):
    """Admin roli yo'q exception"""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
