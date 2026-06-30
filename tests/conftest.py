import sys
import pytest
from django.conf import settings

REQUIRED_PYTHON = (3, 10)

def pytest_configure(config):
    if sys.version_info[:2] != REQUIRED_PYTHON:
        pytest.exit(
            f"Tests must run under Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}. "
            f"Current: {sys.version_info.major}.{sys.version_info.minor}"
        )

# 🚀 DB override olib tashlandi, chunki u settings_test.py da sozlangan

@pytest.fixture(autouse=True)
def _fast_password_hashers(settings):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

@pytest.fixture(autouse=True)
def _email_backend_locmem(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "noreply@example.com"
    settings.EMAIL_HOST_USER = "noreply@example.com"

@pytest.fixture(autouse=True)
def enable_celery_eager(settings):
    """
    Fixture to enable Celery eager mode for all tests.
    This makes Celery tasks run synchronously, allowing them to be tested directly.
    """
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    settings.USE_CELERY = False # Ensure sync fallback is used if implemented in views

@pytest.fixture(autouse=True)
def set_test_redis_url(settings):
    """
    Fixture to set a specific Redis URL for tests.
    This ensures tests use a dedicated Redis instance or fakeredis.
    """
    # Use a different DB for tests to avoid conflicts with dev Redis
    settings.REDIS_URL = 'redis://localhost:6379/1'
    # If using fakeredis, you would configure it here
    # settings.CACHES['default']['BACKEND'] = 'fakeredis.django.FakeRedisCache'


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()