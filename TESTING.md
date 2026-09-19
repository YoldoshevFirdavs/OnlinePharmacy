# Testing Guide - OnlinePharmacy

## Quick Start

### Prerequisites
```bash
# Python 3.10+
python --version

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Run Tests Locally (NO Docker Required)

```bash
# Run all tests
pytest -v

# Run specific test file
pytest tests/delivery/test_concurrent_delivery.py -v

# Run with coverage
pytest --cov=. --cov-report=html

# Run only fast tests (no integration tests)
pytest -m "not integration" -v
```

### Run Tests with Docker

```bash
# Start services
docker-compose -f docker-compose.local.yml up -d

# Run tests inside container
docker exec onlinepharmacy-web-1 python manage.py test
docker exec onlinepharmacy-web-1 pytest -v
```

---

## Cache Configuration in Tests

### What Changed?
- **BEFORE**: Tests required Redis to be running
- **AFTER**: Tests use LocMemCache (in-memory) by default - Redis optional

### Cache Backend Details

#### LocMemCache (Default for Local Testing)
```python
# config/settings_test.py
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}
```
- ✅ No external service required
- ✅ Fast (in-memory)
- ✅ Isolated per test run
- ❌ Not distributed (single-process only)

#### Redis (Optional - for real testing)
If you need Redis behavior:
```bash
# Install fakeredis for Redis simulation
pip install fakeredis

# Uncomment in config/settings_test.py to use Redis
```

---

## Test Categories

### 1. Unit Tests
```bash
pytest tests/users/ -v
pytest tests/orders/test_models.py -v
```
✅ Fast, isolated, no external services

### 2. Integration Tests
```bash
pytest tests/billing/test_security.py -v
pytest tests/delivery/test_concurrent_delivery.py -v
```
⚠️ May need database transactions

### 3. API Tests
```bash
pytest tests/ -k "API" -v
```
Uses test client, simulates HTTP requests

### 4. Security Tests
```bash
pytest billing/tests/test_security.py -v
pytest users/tests/test_fingerprint_system.py -v
```
Tests authentication, permissions, webhooks

---

## Fixing Common Test Issues

### Issue: "Redis Connection Failed"
**Solution**: Update `config/settings_test.py` to use LocMemCache
```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}
```

### Issue: "TransactionTestCase requires TestCase"
**Solution**: Use `TransactionTestCase` for tests that need database isolation
```python
from django.test import TransactionTestCase

class ParallelDriverAcceptTests(TransactionTestCase):
    # Tests that verify concurrent behavior
    pass
```

### Issue: "Thread test hangs"
**Solution**: Use `threading.join(timeout=5)` to prevent infinite waits
```python
thread.join(timeout=5)
if thread.is_alive():
    print("Thread timeout")
```

---

## Environment Variables for Testing

### Auto-detected by manage.py
```bash
# manage.py automatically uses settings_test.py for tests
python manage.py test
```

### Explicit (if needed)
```bash
DJANGO_SETTINGS_MODULE=config.settings_test pytest -v
DJANGO_SETTINGS_MODULE=config.settings_test python manage.py test
```

---

## CI/CD Pipeline (GitHub Actions)

### What's Tested
- Python linting (flake8, black, isort)
- Django system checks
- All 160+ tests
- Coverage reporting

### Environment
```yaml
# GitHub Actions CI
TESTING=true
DJANGO_SETTINGS_MODULE=config.settings_test
DATABASE: PostgreSQL (from docker service)
CACHE: LocMemCache (no Redis needed)
```

### Run Locally Like CI
```bash
# Exact command from CI
pytest -v --tb=short
```

---

## Best Practices

### ✅ DO:
1. Use LocMemCache for unit tests
2. Use `TransactionTestCase` for concurrency tests
3. Use `@override_settings` for temporary config changes
4. Mock external services (Stripe, Telegram)
5. Test edge cases (empty, null, invalid data)

### ❌ DON'T:
1. Depend on Redis in unit tests
2. Leave mock objects hardcoded
3. Skip security tests
4. Mix unit and integration tests
5. Use `time.sleep()` without timeout

---

## Example Test Structure

```python
from django.test import TestCase, TransactionTestCase, override_settings
from unittest.mock import patch
from rest_framework.test import APIClient

class OrderPaymentTests(TestCase):
    """Unit tests - use LocMemCache"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(...)
        self.order = Order.objects.create(...)
    
    def test_order_total_calculation(self):
        self.assertEqual(self.order.total_price, 100.00)

class ConcurrentDeliveryTests(TransactionTestCase):
    """Integration tests - database transactions needed"""
    
    def test_parallel_driver_accept(self):
        # Use threading for concurrency
        pass

class StripeWebhookTests(TestCase):
    """Security tests - mock external services"""
    
    @patch('stripe.Webhook.construct_event')
    def test_webhook_signature_validation(self, mock_stripe):
        mock_stripe.return_value = {"type": "checkout.session.completed"}
        # Test webhook handling
        pass
```

---

## Performance Tips

### Speed Up Tests
```bash
# Run only fast tests
pytest -m "not slow" -v

# Run in parallel (if pytest-xdist installed)
pytest -n auto -v

# Run specific test class
pytest tests/users/test_models.py::UserTestCase -v
```

### Profile Test Speed
```bash
# Show slowest 10 tests
pytest --durations=10
```

---

## Troubleshooting

### Tests fail locally but pass in CI
- Check Django settings (TESTING flag)
- Check Python version (must be 3.10+)
- Check database: `python manage.py migrate`

### Tests pass locally but fail in CI
- Redis not available in CI (use LocMemCache)
- Environment variables not set
- Docker image out of sync

### Cache not working
```bash
# Clear cache
python manage.py shell
from django.core.cache import cache
cache.clear()
```

---

## Resources

- [Django Testing Docs](https://docs.djangoproject.com/en/4.2/topics/testing/)
- [pytest Docs](https://docs.pytest.org/)
- [Django REST Framework Testing](https://www.django-rest-framework.org/api-guide/testing/)
- [LocMemCache vs Redis](https://docs.djangoproject.com/en/4.2/topics/cache/#local-memory-caching)

---

*Last updated: September 15, 2026*
*Test Suite: 160+ tests, LocMemCache default, 0 external service dependencies*
