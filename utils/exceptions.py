"""
Custom exception classes for OnlinePharmacy
Provide specific error handling and clear error codes
"""

from rest_framework import status
from rest_framework.exceptions import APIException


class OnlinePharmacyException(Exception):
    """Base exception for OnlinePharmacy"""

    error_code = "INTERNAL_ERROR"
    http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
    message = "An error occurred"

    def __init__(self, message=None, error_code=None, **kwargs):
        self.message = message or self.message
        self.error_code = error_code or self.error_code
        self.details = kwargs
        super().__init__(self.message)


# Authentication Exceptions
class AuthenticationException(OnlinePharmacyException):
    """Base authentication exception"""

    error_code = "AUTH_ERROR"
    http_status = status.HTTP_401_UNAUTHORIZED


class InvalidTokenException(AuthenticationException):
    error_code = "INVALID_TOKEN"
    message = "Token is invalid or expired"


class TokenBlacklistedException(AuthenticationException):
    error_code = "TOKEN_BLACKLISTED"
    message = "Token has been revoked"


class InvalidCredentialsException(AuthenticationException):
    error_code = "INVALID_CREDENTIALS"
    message = "Invalid email or password"


class OTPExpiredException(AuthenticationException):
    error_code = "OTP_EXPIRED"
    message = "OTP code has expired"


class OTPInvalidException(AuthenticationException):
    error_code = "OTP_INVALID"
    message = "OTP code is invalid"


class RateLimitExceededException(AuthenticationException):
    error_code = "RATE_LIMIT_EXCEEDED"
    http_status = status.HTTP_429_TOO_MANY_REQUESTS
    message = "Too many requests. Please try again later"


# Authorization Exceptions
class PermissionDeniedException(OnlinePharmacyException):
    """Base permission exception"""

    error_code = "PERMISSION_DENIED"
    http_status = status.HTTP_403_FORBIDDEN
    message = "You do not have permission to perform this action"


class AccessDeniedException(PermissionDeniedException):
    error_code = "ACCESS_DENIED"
    message = "Access denied"


class UserBannedException(PermissionDeniedException):
    error_code = "USER_BANNED"
    message = "Your account has been suspended"


# Resource Exceptions
class ResourceNotFoundException(OnlinePharmacyException):
    """Base not found exception"""

    error_code = "NOT_FOUND"
    http_status = status.HTTP_404_NOT_FOUND
    message = "Resource not found"


class OrderNotFoundException(OnlinePharmacyException):
    error_code = "ORDER_NOT_FOUND"
    http_status = status.HTTP_400_BAD_REQUEST  # 400 for "not found or not owned"
    message = "Order not found"


class UserNotFoundException(ResourceNotFoundException):
    error_code = "USER_NOT_FOUND"
    message = "User not found"


class ProductNotFoundException(ResourceNotFoundException):
    error_code = "PRODUCT_NOT_FOUND"
    message = "Product not found"


# Validation Exceptions
class ValidationException(OnlinePharmacyException):
    """Base validation exception"""

    error_code = "VALIDATION_ERROR"
    http_status = status.HTTP_400_BAD_REQUEST
    message = "Validation failed"


class InvalidPhoneNumberException(ValidationException):
    error_code = "INVALID_PHONE_NUMBER"
    message = "Invalid phone number format"


class InvalidEmailException(ValidationException):
    error_code = "INVALID_EMAIL"
    message = "Invalid email format"


class InvalidCardDataException(ValidationException):
    error_code = "INVALID_CARD_DATA"
    message = "Invalid card data"


class InsufficientBalanceException(ValidationException):
    error_code = "INSUFFICIENT_BALANCE"
    message = "Insufficient balance for this operation"


# Payment Exceptions
class PaymentException(OnlinePharmacyException):
    """Base payment exception"""

    error_code = "PAYMENT_ERROR"
    http_status = status.HTTP_402_PAYMENT_REQUIRED
    message = "Payment failed"


class PaymentGatewayException(PaymentException):
    error_code = "PAYMENT_GATEWAY_ERROR"
    http_status = status.HTTP_502_BAD_GATEWAY
    message = "Payment gateway error"


class DuplicatePaymentException(PaymentException):
    error_code = "DUPLICATE_PAYMENT"
    message = "Duplicate payment detected"


class WebhookSignatureException(PaymentException):
    error_code = "INVALID_WEBHOOK_SIGNATURE"
    message = "Invalid webhook signature"


# Delivery Exceptions
class DeliveryException(OnlinePharmacyException):
    """Base delivery exception"""

    error_code = "DELIVERY_ERROR"
    http_status = status.HTTP_400_BAD_REQUEST
    message = "Delivery error"


class DriverAlreadyAssignedException(DeliveryException):
    error_code = "DRIVER_ALREADY_ASSIGNED"
    message = "Order already assigned to another driver"


class DriverNotAvailableException(DeliveryException):
    error_code = "DRIVER_NOT_AVAILABLE"
    message = "Driver is not available"


# System Exceptions
class CacheException(OnlinePharmacyException):
    """Cache operation failed"""

    error_code = "CACHE_ERROR"
    http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
    message = "Cache operation failed"


class DatabaseException(OnlinePharmacyException):
    """Database operation failed"""

    error_code = "DATABASE_ERROR"
    http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
    message = "Database operation failed"


class ExternalServiceException(OnlinePharmacyException):
    """External service error (Stripe, Telegram, etc.)"""

    error_code = "EXTERNAL_SERVICE_ERROR"
    http_status = status.HTTP_502_BAD_GATEWAY
    message = "External service error"


class TelegramException(ExternalServiceException):
    error_code = "TELEGRAM_ERROR"
    message = "Telegram service error"


class StripeException(ExternalServiceException):
    error_code = "STRIPE_ERROR"
    message = "Stripe service error"


# Utility functions
def get_error_response(exception):
    """Convert exception to API response format"""
    if isinstance(exception, OnlinePharmacyException):
        return {"ok": False, "error": exception.error_code, "message": exception.message, "details": exception.details}
    else:
        # Unknown exception
        return {"ok": False, "error": "INTERNAL_ERROR", "message": "An unexpected error occurred", "details": {}}
