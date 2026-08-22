import logging
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


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


def get_client_ip(request):
    """Extract client IP from request, honoring X-Forwarded-For when present."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        # return first IP in X-Forwarded-For
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class DeviceFingerprintMiddleware:
    """Compatibility middleware used by tests and older imports.

    This provides a lightweight implementation that extracts a device
    fingerprint from cookies or headers and performs simple ban / rate
    limit checks via users.services.BanService so the test-suite can run.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Bypass static/media and favicon paths
        path = request.path or ''
        if path.startswith('/static/') or path.startswith('/media/') or path == '/favicon.ico':
            return self.get_response(request)

        # Extract fingerprint: cookie takes priority
        fp = None
        try:
            fp = request.COOKIES.get('device_fp')
        except Exception:
            fp = None

        if not fp:
            fp = request.META.get('HTTP_AUTHORIZATION_FINGERPRINT') or request.META.get('HTTP_DEVICE_FP')

        if fp:
            # attach to request for downstream usage
            setattr(request, 'device_fingerprint', fp)

            # quick ban check
            from users.services import BanService
            try:
                if BanService.is_fp_banned(fp):
                    # Redirect to not-allowed page
                    from django.shortcuts import redirect
                    return redirect(f"/security/not-allowed/?next={path}")

                # rate-limit probe: if counter in cache exceeds threshold, call ban
                from django.core.cache import cache
                from django.conf import settings
                cnt = cache.get(f"rate_fp:{fp}", 0) or 0
                threshold = getattr(settings, 'FINGERPRINT_RATE_THRESHOLD', 5)
                if cnt and int(cnt) > int(threshold):
                    # call BanService.ban_by_fp (tests often patch this call)
                    BanService.ban_by_fp(fp, duration_minutes=getattr(settings, 'FINGERPRINT_TEMP_BAN_DURATION', 1), reason='Rate limit exceeded', banned_for='rate_limit', actor='system')
            except Exception:
                # Fail-safe: do not crash the request
                pass

        # proceed with request
        return self.get_response(request)
