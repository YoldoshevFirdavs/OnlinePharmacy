# Testing Guide

This project uses pytest for test automation. The test suite is intentionally structured to allow isolated unit tests without requiring a running Docker service.

## Run the suite

```bash
pytest
```

## Focused runs

```bash
pytest tests/dashboard
pytest tests/security
pytest tests/orders
```

## Mocking guidance

Use `unittest.mock` or `pytest.MonkeyPatch` for external services and Django model interactions. Keep tests fast and deterministic.

```python
from unittest.mock import Mock, patch

with patch('security.models.UndoLog.restore', return_value=(True, 'ok')):
    assert True
```

## CI note

The repository workflow installs dependencies and runs lint/test checks in GitHub Actions. No Playwright browser installation is required for these unit tests.
