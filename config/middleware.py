import re
from django.utils.deprecation import MiddlewareMixin

class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add common security headers to every response.
    Includes HSTS, X-Content-Type-Options, X-Frame-Options, X-XSS-Protection.
    CSP is handled by Django's 'csp' app.
    """

    def process_response(self, request, response):
        # Strict-Transport-Security (only on HTTPS)
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        # X-Content-Type-Options
        response['X-Content-Type-Options'] = 'nosniff'
        # X-Frame-Options
        response['X-Frame-Options'] = 'DENY'
        # X-XSS-Protection
        response['X-XSS-Protection'] = '1; mode=block'
        return response