"""Django settings for OnlinePharmacy project.

This file is configured to load all sensitive and environment-specific settings from environment variables.
Safe default values are provided for development and testing environments.
In production, ensure all sensitive variables are set in the .env file."""

import logging  # Import logging module
import logging.handlers
import os
import re  # Import re module for regex
import sys
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

import config.email_config as email_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(BASE_DIR))

# Load .env file if it exists
from dotenv import load_dotenv

env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# SECRET_KEY loading logic
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    if DEBUG:
        logger.warning("SECRET_KEY not found in environment. Using a default, insecure key for development.")
        SECRET_KEY = "django-insecure-fallback-for-development-only"
    else:
        raise ImproperlyConfigured("The DJANGO_SECRET_KEY environment variable must be set in production.")

# Strip whitespace/CRLF from each entry — Windows .env files often have \r artifacts
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "users",
    "telegram_bot",
    "dashboard",
    "pharmacy",
    "orders",
    "billing",
    "payments",
    "security",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "phonenumbers",
    "django_filters",
    "djoser",
    "social_django",
    "drf_yasg",
    "templated_mail",
    "whitenoise.runserver_nostatic",
    "whitenoise",
    "django_extensions",
    # 'django_seed',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "security.middleware.BanMiddleware",  # Ban middleware AFTER auth to check user bans
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # "config.middleware.DeviceFingerprintMiddleware",  # DISABLED: Replaced by BanMiddleware
    # "config.middleware.BanCheckMiddleware",  # DISABLED: Replaced by BanMiddleware
    "config.middleware.CustomErrorMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "pharmacy.context_processors.site_configuration",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "pharmacy_db"),
        "USER": os.getenv("DB_USER", "pharmacy_admin"),
        "PASSWORD": os.getenv("DB_PASSWORD", "root"),
        "HOST": os.getenv("DB_HOST", "db"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "TEST": {
            "NAME": "test_" + os.getenv("DB_NAME", "pharmacy_db"),
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "uz-uz"
TIME_ZONE = "Asia/Tashkent"

USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "users.CustomUser"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": int(os.getenv("REST_FRAMEWORK_PAGE_SIZE", 10)),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/min",
        "user": "300/min",
        # Lenient rate for GET requests (caching-friendly)
        "comments_get": "1000/min",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", 30))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_TOKEN_LIFETIME_DAYS", 7))),
    "ROTATE_REFRESH_TOKENS": os.getenv("JWT_ROTATE_REFRESH_TOKENS", "true").lower() == "true",
    "BLACKLIST_AFTER_ROTATION": os.getenv("JWT_BLACKLIST_AFTER_ROTATION", "true").lower() == "true",
    "UPDATE_LAST_LOGIN": os.getenv("JWT_UPDATE_LAST_LOGIN", "true").lower() == "true",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "JWK_URL": None,
    "LEEWAY": 0,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_SLIDING_TOKEN_LIFETIME_MINUTES", 60))),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(
        days=int(os.getenv("JWT_SLIDING_TOKEN_REFRESH_TOKEN_LIFETIME_DAYS", 7))
    ),
    # ADDED: Custom serializer for token obtain to include role in JWT claims
    "TOKEN_OBTAIN_SERIALIZER": "users.serializers.CustomTokenObtainPairSerializer",
}

SESSION_COOKIE_AGE = 1800
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
ADMIN_SESSION_TIMEOUT = 1800
ADMIN_SESSION_DURATION = 1800

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000,http://localhost,http://127.0.0.1",
    ).split(",")
    if o.strip()
]
CORS_ALLOW_ALL_ORIGINS = DEBUG or os.getenv("CORS_ALLOW_ALL_ORIGINS", "False").lower() == "true"
CORS_ALLOW_CREDENTIALS = True

PHONENUMBER_DEFAULT_REGION = os.getenv("PHONENUMBER_DEFAULT_REGION", "UZ")
PHONENUMBER_DEFAULT_REGION_CODE = os.getenv("PHONENUMBER_DEFAULT_REGION_CODE", "998")  # Added this line

AUTH_BOT_TOKEN = os.getenv("AUTH_BOT_TOKEN", "")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

EMAIL_BACKEND = email_config.EMAIL_BACKEND
EMAIL_HOST = email_config.EMAIL_HOST
EMAIL_PORT = email_config.EMAIL_PORT
EMAIL_USE_TLS = email_config.EMAIL_USE_TLS
EMAIL_USE_SSL = email_config.EMAIL_USE_SSL
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@example.com")

# Fall back to a path inside the project if the env-specified path is not writable.
# This prevents a missing /var/log/... directory from crashing Gunicorn on startup.
_env_log_file = os.getenv("LOG_FILE", "")
if _env_log_file:
    LOG_FILE_PATH = Path(_env_log_file)
    try:
        LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOG_FILE_PATH.touch(exist_ok=True)  # verify it is actually writable
    except Exception:
        LOG_FILE_PATH = BASE_DIR / "logs" / "django.log"  # safe fallback
else:
    LOG_FILE_PATH = BASE_DIR / "logs" / "django.log"
try:
    LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
LOG_FILE = str(LOG_FILE_PATH)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DJANGO_LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO")
DJANGO_REQUEST_LOG_LEVEL = os.getenv("DJANGO_REQUEST_LOG_LEVEL", "INFO")


# Custom filter to redact sensitive information
class SensitiveDataFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record, "msg") and isinstance(record.msg, str):
            # Mask OTP codes (4–6 digit numbers)
            record.msg = re.sub(r"\b\d{4,6}\b", "******", record.msg)

            # Mask sensitive fields
            for field in ["password", "otp", "secret", "token"]:
                # Fix: Use re.escape and a simpler regex pattern without lookbehind
                pattern = re.escape(field) + r"[:=]\s*(\S+)"
                record.msg = re.sub(pattern, field + ": ********", record.msg, flags=re.IGNORECASE)

        return True


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "sensitive_data_filter": {
            "()": "config.settings.SensitiveDataFilter",
        },
    },
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_FILE,
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
            "level": "DEBUG",
            "filters": ["sensitive_data_filter"],  # Apply the filter
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "level": "DEBUG",
            "filters": ["sensitive_data_filter"],  # Apply the filter
        },
    },
    "root": {
        "handlers": ["file", "console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["file", "console"],
            "level": DJANGO_LOG_LEVEL,
            "propagate": False,
        },
        "django.request": {
            "handlers": ["file", "console"],
            "level": DJANGO_REQUEST_LOG_LEVEL,
            "propagate": False,
        },
        "avatar_upload": {
            "handlers": ["file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

PAYROLL_RATE_PER_HOUR = float(os.getenv("PAYROLL_RATE_PER_HOUR", 20.0))
PAYROLL_TAX_RATE = float(os.getenv("PAYROLL_TAX_RATE", 0.15))

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLIC_KEY", "")

GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY", "")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")  # This is for Django Cache
# Celery Redis connection configuration
CELERY_REDIS_HOST = os.getenv("CELERY_REDIS_HOST", "localhost")  # Default to localhost for local dev
CELERY_BROKER_URL = f"redis://{CELERY_REDIS_HOST}:6379/1"
CELERY_RESULT_BACKEND = f"redis://{CELERY_REDIS_HOST}:6379/1"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "IGNORE_EXCEPTIONS": False,
        },
        "KEY_PREFIX": "pharmacy",
        "TIMEOUT": 900,
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# ---------------------------------------------------------------------------
# HTTPS / Security settings — driven entirely by environment variables.
# Local dev (.env):  all values below resolve to False / disabled.
# Production (.env):  all values resolve to True / enabled.
# ---------------------------------------------------------------------------

# Django's built-in SSL redirect (SecurityMiddleware).
# Keep False — Nginx handles the redirect in production; Django must never
# double-redirect or break health-checks that arrive over plain HTTP internally.
SECURE_SSL_REDIRECT = False

# Cookies must only travel over HTTPS in production.
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "False").lower() == "true"
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() == "true"

# Tell Django to trust the X-Forwarded-Proto header set by Nginx.
# Required in production so request.is_secure() returns True behind the proxy.
# Must be disabled locally (no Nginx proxy in front of runserver).
_proxy_ssl_header = os.getenv("SECURE_PROXY_SSL_HEADER", "False").lower() == "true"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if _proxy_ssl_header else None

# HSTS — only meaningful when HTTPS is active.
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))  # 0 = disabled
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False").lower() == "true"
SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "False").lower() == "true"

# Use simple static files storage to prevent collectstatic loops
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"


# ============================================
# DEVICE FINGERPRINT SECURITY SETTINGS
# ============================================

# Device fingerprint rate limiting (requests per second per fingerprint)
FINGERPRINT_RATE_THRESHOLD = int(os.getenv("FINGERPRINT_RATE_THRESHOLD", "10"))

# Temporary ban duration for rate limiting violations (minutes)
FINGERPRINT_TEMP_BAN_DURATION = int(os.getenv("FINGERPRINT_TEMP_BAN_DURATION", "60"))

# IP block duration after rate limiting (seconds)
FINGERPRINT_IP_BLOCK_DURATION = int(os.getenv("FINGERPRINT_IP_BLOCK_DURATION", "3600"))

# Main page refresh limit per fingerprint per hour
FINGERPRINT_MAIN_PAGE_REFRESH_LIMIT = int(os.getenv("FINGERPRINT_MAIN_PAGE_REFRESH_LIMIT", "20"))

# Fingerprint ban cache TTL (seconds) - how long to keep ban info in cache
# For permanent bans, this is ignored
FINGERPRINT_BAN_CACHE_TTL = int(os.getenv("FINGERPRINT_BAN_CACHE_TTL", "86400"))  # 24 hours

# Fingerprint to user mapping TTL (seconds)
FINGERPRINT_USER_MAPPING_TTL = int(os.getenv("FINGERPRINT_USER_MAPPING_TTL", "86400"))  # 24 hours

# Auto cleanup settings
FINGERPRINT_AUTO_CLEANUP_ENABLED = os.getenv("FINGERPRINT_AUTO_CLEANUP_ENABLED", "True").lower() == "true"
FINGERPRINT_CLEANUP_BATCH_SIZE = int(os.getenv("FINGERPRINT_CLEANUP_BATCH_SIZE", "100"))

# Security settings
FINGERPRINT_REQUIRE_HTTPS_COOKIE = os.getenv("FINGERPRINT_REQUIRE_HTTPS_COOKIE", "True").lower() == "true"
FINGERPRINT_COOKIE_SAMESITE = os.getenv("FINGERPRINT_COOKIE_SAMESITE", "Lax")  # Strict, Lax, None
FINGERPRINT_HEADER_NAME = os.getenv("FINGERPRINT_HEADER_NAME", "Authorization-Fingerprint")

# Logging settings
FINGERPRINT_LOG_LEVEL = os.getenv("FINGERPRINT_LOG_LEVEL", "WARNING")
FINGERPRINT_LOG_BLOCKED_REQUESTS = os.getenv("FINGERPRINT_LOG_BLOCKED_REQUESTS", "True").lower() == "true"
FINGERPRINT_LOG_RATE_LIMITS = os.getenv("FINGERPRINT_LOG_RATE_LIMITS", "True").lower() == "true"


# ============================================
# ADMIN LOGIN SECURITY SETTINGS
# ============================================

# Admin login maximum failed attempts before ban
ADMIN_LOGIN_MAX_ATTEMPTS = int(os.getenv("ADMIN_LOGIN_MAX_ATTEMPTS", "10"))

# Admin ban duration in seconds (1 hour = 3600)
ADMIN_BAN_SECONDS = int(os.getenv("ADMIN_BAN_SECONDS", "3600"))

# Admin session timeout in seconds (30 minutes = 1800)
ADMIN_SESSION_TIMEOUT = int(os.getenv("ADMIN_SESSION_TIMEOUT", "1800"))
