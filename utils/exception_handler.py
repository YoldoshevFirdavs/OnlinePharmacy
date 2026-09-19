"""
Exception handling utilities for API views
Provides decorators and middleware to handle custom exceptions
"""

import logging
from functools import wraps

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response

from .exceptions import OnlinePharmacyException

logger = logging.getLogger(__name__)


def handle_api_exceptions(view_func):
    """
    Decorator for API views to handle OnlinePharmacyException and convert to HTTP responses
    Usage:
        @handle_api_exceptions
        def my_view(request):
            ...
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except OnlinePharmacyException as e:
            logger.warning("API exception: %s - %s", e.error_code, e.message)
            return Response(
                {
                    "ok": False,
                    "error": e.error_code,
                    "message": e.message,
                    "details": e.details,
                },
                status=e.http_status,
            )
        except Exception as e:
            logger.exception("Unexpected error in API view: %s", str(e))
            return Response(
                {
                    "ok": False,
                    "error": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    return wrapper


def custom_exception_handler(exc, context):
    """
    DRF custom exception handler that catches OnlinePharmacyException
    """
    if isinstance(exc, OnlinePharmacyException):
        logger.warning("OnlinePharmacy exception in view: %s - %s", exc.error_code, exc.message)
        return Response(
            {
                "error": exc.message,
            },
            status=exc.http_status,
        )

    # Let DRF handle the rest
    from rest_framework.views import exception_handler as drf_exception_handler

    return drf_exception_handler(exc, context)


def handle_view_exceptions(view_func):
    """
    Decorator for template views to handle exceptions with proper logging
    Usage:
        @handle_view_exceptions
        def my_view(request):
            ...
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except OnlinePharmacyException as e:
            logger.warning("View exception: %s - %s", e.error_code, e.message)
            raise
        except Exception as e:
            logger.exception("Unexpected error in view: %s", str(e))
            raise

    return wrapper


class APIExceptionMiddleware:
    """
    Middleware for handling OnlinePharmacyException globally in API endpoints
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except OnlinePharmacyException as e:
            if request.path.startswith("/api/"):
                logger.warning("API exception caught by middleware: %s - %s", e.error_code, e.message)
                return Response(
                    {
                        "ok": False,
                        "error": e.error_code,
                        "message": e.message,
                        "details": e.details,
                    },
                    status=e.http_status,
                )
            raise
        except Exception:
            raise
