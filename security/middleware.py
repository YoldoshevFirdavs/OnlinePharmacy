import re

from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework.exceptions import APIException


class SafeErrorMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # This part handles responses that are already generated (e.g., by DRF views)
        # and have a status code >= 400.
        if response.status_code >= 400 and not settings.DEBUG:
            # We only want to generalize the message if it's not already a generic one
            # or if it's a 404/500 that might expose internal details.
            # For simplicity, we'll apply the generic message to all 4xx/5xx in production
            # unless a more specific exception handler has already provided a safe message.
            # This might override some DRF default messages, but aligns with the strict requirement.
            return JsonResponse(
                {"error": "Login failed, please try again."},
                status=response.status_code,
            )
        return response

    def process_exception(self, request, exception):
        # This part handles exceptions raised during request processing.
        if isinstance(exception, APIException):
            # DRF exceptions are already well-structured.
            # In production, we can generalize their messages if needed,
            # but DRF's default exception handler usually does a good job.
            # For now, we'll let DRF handle its own exceptions in debug mode,
            # and apply the generic message in production.
            if not settings.DEBUG:
                return JsonResponse(
                    {"error": "Login failed, please try again."},
                    status=exception.status_code,
                )
            return None  # Let DRF's default exception handler process APIException in DEBUG mode

        if not settings.DEBUG:
            # Catch all other unexpected exceptions (e.g., 500 errors)
            # and replace them with a generic safe message in production.
            return JsonResponse(
                {"error": "Login failed, please try again."}, status=500
            )
        # In debug mode, re-raise the exception to see the traceback
        return None


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add common security headers to every response.
    Includes HSTS, X-Content-Type-Options, X-Frame-Options, X-XSS-Protection.
    CSP is handled by Django's 'csp' app.
    """

    def process_response(self, request, response):
        # Strict-Transport-Security (only on HTTPS)
        if request.is_secure():
            response["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        # X-Content-Type-Options
        response["X-Content-Type-Options"] = "nosniff"
        # X-Frame-Options
        response["X-Frame-Options"] = "DENY"
        # X-XSS-Protection
        response["X-XSS-Protection"] = "1; mode=block"
        return response
