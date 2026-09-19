# Dependency Management

This project uses a strict dependency management strategy to ensure reproducible builds and clear separation of runtime vs development dependencies.

## Files

### `requirements.txt` (Production)
Contains only runtime dependencies needed to run the application in production.

**Install with:**
```bash
pip install -r requirements.txt
```

### `requirements-dev.txt` (Development)
Contains development and testing tools. Includes `requirements.txt` as a base.

**Install with:**
```bash
pip install -r requirements-dev.txt
```

### `requirements.lock` (Lock File)
Contains exact pinned versions of all installed packages (generated via `pip freeze`).

**Use for reproducible builds:**
```bash
pip install -r requirements.lock
```

## Core Dependencies

### Framework
- **Django 5.1.1** - Web framework
- **djangorestframework 3.15.2** - REST API framework
- **djangorestframework-simplejwt 5.5.1** - JWT authentication

### Database
- **psycopg2-binary 2.9.7** - PostgreSQL adapter
- **redis ≥4.5.2** - Redis cache client
- **django-redis 6.0.0** - Redis cache backend

### Task Queue
- **celery 5.3.1** - Asynchronous task queue
- **kombu, billiard, vine, amqp** - Celery dependencies

### Authentication
- **djoser** - REST auth implementation
- **social-auth-app-django** - Social login
- **PyJWT** - JWT handling

### Security
- **cryptography 41.0.7** - Encryption primitives
- **django-csp 3.8** - Content Security Policy
- **django-ratelimit 4.1.0** - Rate limiting

### Monitoring
- **prometheus-client 0.20.0** - Prometheus metrics

### Other
- **stripe 8.0.0** - Stripe payment integration
- **phonenumbers 8.13.25** - Phone validation
- **google-genai 0.3.0** - Google AI integration
- **pillow 10.1.0** - Image processing

## Development-Only Dependencies

### Testing
- **pytest 8.0.0** - Test framework
- **pytest-django 4.7.0** - Django integration
- **pytest-cov 4.1.0** - Code coverage
- **faker 20.0.0** - Fake data generation
- **factory-boy 3.3.0** - Test fixtures

### Code Quality
- **black 23.12.0** - Code formatter
- **flake8 7.0.0** - Linter
- **isort 5.13.2** - Import sorting
- **pylint 3.0.3** - Code analyzer
- **mypy 1.7.1** - Type checker

### Debugging
- **django-debug-toolbar 4.2.0** - Debug toolbar
- **ipython 8.19.0** - Enhanced shell
- **notebook 7.0.6** - Jupyter notebooks

### Development Tools
- **django-extensions 3.2.3** - Admin commands
- **pre-commit 3.6.0** - Git hooks framework
- **invoke 2.2.0** - Task runner
- **watchdog 3.0.0** - File monitoring

## Workflow

### First Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Generate lock file
pip freeze > requirements.lock
```

### Installation
```bash
# Production
pip install -r requirements.txt

# Development
pip install -r requirements-dev.txt

# Exact versions
pip install -r requirements.lock
```

### Adding Dependencies

1. **Runtime dependency:**
   ```bash
   pip install new-package
   pip install new-package==1.2.3  # Pinned version
   echo "new-package==1.2.3" >> requirements.txt
   ```

2. **Development dependency:**
   ```bash
   pip install new-package
   echo "new-package==1.2.3" >> requirements-dev.txt
   ```

3. **Update lock file:**
   ```bash
   pip freeze > requirements.lock
   git add requirements.txt requirements-dev.txt requirements.lock
   ```

### Removing Dependencies
1. Remove from `requirements.txt` or `requirements-dev.txt`
2. Uninstall: `pip uninstall package-name`
3. Update lock file: `pip freeze > requirements.lock`
4. Commit changes

## Version Management

### Strategy
- Use **exact versions** in `requirements.txt` (e.g., `Django==5.1.1`)
- Avoid version ranges (e.g., ❌ `Django>=5.0,<6.0`)
- Pin to known working versions
- Test before upgrading major versions

### Regular Updates
- Check for security updates: `pip list --outdated`
- Update strategically: test updates before committing
- Keep lock file synchronized with requirements files

## Verification

Check for unused dependencies (requires `vulture` or similar):
```bash
pip install vulture
vulture --min-confidence 80
```

Check for security vulnerabilities (requires `safety` or similar):
```bash
pip install safety
safety check
```

## Docker

In Docker, install from `requirements.txt` for production:
```dockerfile
RUN pip install --no-cache-dir -r requirements.txt
```

For development Docker image:
```dockerfile
RUN pip install --no-cache-dir -r requirements-dev.txt
```
