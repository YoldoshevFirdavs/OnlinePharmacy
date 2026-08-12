import os
import sys
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

from .settings import *

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-key-123")
# SECRET_KEY for tests can be a fixed value, as it's not used for production security
# For actual production, ensure it's loaded from environment.
if not SECRET_KEY:
    SECRET_KEY = "test-secret-key-for-django-tests"

DEBUG = False
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "djoser",
    "drf_yasg",
    "corsheaders",
    "custom_auth",
    "users",
    "pharmacy",
    "orders",
    "billing",
    "payments",
    "security",
    "django_extensions",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.middleware.SecurityHeadersMiddleware",
]
ROOT_URLCONF = "config.urls"
APPEND_SLASH = False

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates", BASE_DIR / "html"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "pharmacy.context_processors.social_links",
                "pharmacy.context_processors.footer_links",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

IS_DOCKER = os.path.exists("/.dockerenv")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": ":memory:",
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "root"),
        "HOST": os.getenv("DB_HOST", "db" if IS_DOCKER else "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

REDIS_HOST = "redis" if IS_DOCKER else "localhost"
REDIS_PORT = 6379
REDIS_URL = (
    os.getenv("REDIS_URL") or f"redis://{REDIS_HOST}:{REDIS_PORT}/1"
)  # Use DB 1 for tests

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 10,
            "SOCKET_TIMEOUT": 10,
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "IGNORE_EXCEPTIONS": False,
            "CONNECTION_POOL_KWARGS": {"max_connections": 50, "retry_on_timeout": True},
        },
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 86400
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

AUTH_USER_MODEL = "users.CustomUser"
LANGUAGE_CODE = "uz-uz"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "100/hour", "user": "1000/hour"},
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_COOKIE": "refresh_token",
    "AUTH_COOKIE_SECURE": False,  # False for tests
    "AUTH_COOKIE_HTTP_ONLY": True,
    "AUTH_COOKIE_PATH": "/api/v1/",
    "AUTH_COOKIE_SAMESITE": "Lax",
}

SESSION_COOKIE_SECURE = False  # False for tests
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = False  # False for tests
CSRF_COOKIE_HTTPONLY = True

SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Tashkent"
CELERY_BEAT_SCHEDULE = {}  # Disable beat schedule for tests

CORS_ALLOW_ALL_ORIGINS = True  # Allow all origins for tests
CORS_ALLOWED_ORIGINS = ["http://localhost:8000"]  # Example for local testing
CSRF_TRUSTED_ORIGINS = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8001",
]
CORS_ALLOW_CREDENTIALS = True

SOCIAL_TELEGRAM = "https://t.me/testbot"
SOCIAL_INSTAGRAM = "https://instagram.com/test"
SOCIAL_FACEBOOK = "https://facebook.com/test"

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = os.path.join(BASE_DIR, "test_static")

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media_test"  # Use separate media root for tests

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
EMAIL_HOST = ""
EMAIL_PORT = 587
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = "no-reply@onlinepharmacy.local"

STRIPE_SECRET_KEY = "test_stripe_secret_key"
STRIPE_WEBHOOK_SECRET = "test_stripe_webhook_secret"

# Content Security Policy (CSP) - Disabled for tests
CONTENT_SECURITY_POLICY = {}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {},
    "loggers": {},
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}
print("✅ TEST SETTINGS LOADED")
