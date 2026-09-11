"""
Pytest configuration for Django test setup.
"""

import os

import django
from django.conf import settings
from django.test.utils import get_runner

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_test")


def pytest_configure():
    """Configure Django settings for pytest"""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_test")
    django.setup()


def pytest_runtest_setup():
    """Setup Django before each test"""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_test")
    django.setup()


# Default test runner configuration
def pytest_configure(config):
    """Configure Django and set up test database"""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_test")
    django.setup()


# Make Django available in all test files
pytest_plugins = []
