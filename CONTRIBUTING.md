# Contributing

## Before You Start

1. Ensure you have Python 3.10+ and all dependencies installed:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

## Workflow

1. Create a short-lived branch from the default branch.
2. Keep changes focused and aligned to a single feature or fix.
3. Update relevant docs when behavior changes.
4. Run local checks before opening a pull request.
5. Submit a PR with a clear explanation and validation notes.

## Code Quality Requirements

**All code must pass these checks before submission:**

### 1. Code Formatting (black)

```bash
black .
```

- Line length: 120 characters
- Enforces consistent Python style

### 2. Import Sorting (isort)

```bash
isort .
```

- Organizes imports alphabetically
- Compatible with black formatter
- Profile: "black"

### 3. Linting (flake8)

```bash
flake8 . --max-line-length=120 --max-complexity=10
```

- Checks for style violations
- Enforces PEP 8 standards
- Fails on syntax errors (E9, F63, F7, F82)

### 4. Testing (pytest)

```bash
pytest
```

- All tests must pass
- Minimum coverage: 80% (recommended)
- Use `pytest --cov` to check coverage

### Quick Check Script

Run all checks before committing:

```bash
#!/bin/bash
set -e
echo "Formatting code..."
black .
echo "Sorting imports..."
isort .
echo "Linting..."
flake8 . --max-line-length=120 --max-complexity=10
echo "Running tests..."
pytest
echo "✓ All checks passed!"
```

## Coding Standards

- Keep business logic in existing app modules instead of creating new global services.
- Do not modify core models such as `CustomUser`, `Order`, `OrderItem`, `Cart`, `CartItem`, `Medicine`, or `DeliveryDriver` unless the task specifically requires it and it is directly connected to the bug.
- Keep server-side changes inside `transaction.atomic()` when writing state.
- Prefer existing templates and static assets over introducing new global CSS.
- Follow PEP 8 standards and black formatting guidelines.
- Keep functions small and focused (aim for < 30 lines).
- Write docstrings for all public methods and functions.
- Use type hints where applicable (Python 3.10+).

## PR Checklist

- [ ] Code passes `black --check .`
- [ ] Code passes `isort --check-only .`
- [ ] Code passes `flake8 . --max-line-length=120`
- [ ] All tests pass: `pytest`
- [ ] Does the change match the requested behavior?
- [ ] Are permissions and CSRF handled correctly?
- [ ] Does the code keep undo and audit operations safe and atomic?
- [ ] Are docs updated when necessary?
- [ ] Commit messages are clear and descriptive

## CI/CD Pipeline

Your PR will be automatically checked by GitHub Actions:

1. **Code Quality**: black, isort, flake8 validation
2. **Tests**: pytest runs all unit and integration tests
3. **Coverage**: Coverage reports are generated and uploaded

If any check fails, fix the issues and push again. The workflow will re-run automatically.

See [.github/workflows/cm.yml](.github/workflows/cm.yml) for full workflow details.

## Git Commit Messages

- Use clear, descriptive messages in present tense
- Example: "Fix user avatar sizing in dashboard" (not "Fixed avatar")
- Reference issues/PRs when applicable: "Fixes #123"

## Questions?

- Check [README.md](README.md) for project overview
- Review existing code and patterns in the codebase
- Ask in pull request comments if unclear

