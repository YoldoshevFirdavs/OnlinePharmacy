# OnlinePharmacy

This is my first project — created by Firdavs Yo'ldashev.

OnlinePharmacy is a Django-based pharmacy and management platform for selling medicines, managing users, handling orders, and supporting admin operations. The project combines a storefront, seller/admin dashboard, notification flows, OTP authentication, and internal administrative tools in one monolithic Django application.

## Project purpose

The main idea is to provide a working pharmacy platform with:

- customer-facing product browsing and order creation
- multi-role access for admins, sellers, deliverers, and end users
- dashboard pages for analytics, user history, and order management
- secure authentication and OTP-based login workflows
- API endpoints for admin actions, listing, and restore operations
- deployment support via Docker, Gunicorn, and Nginx

## Architecture overview

The project is split into Django apps, each with a clear purpose:

- `config/` — project settings, URL routing, middleware, and deployment config
- `users/` — user model, profiles, authentication, OTP, delivery drivers, role logic
- `pharmacy/` — medicines, categories, product metadata, history records
- `orders/` — order flow, order items, cart/context-related business logic
- `dashboard/` — admin and user dashboard pages, administrative API routes, account pages
- `security/` — audit logs, undo operations, ban logic, request/device security checks
- `billing/` and `payments/` — payment and billing integrations
- `telegram_bot/` — Telegram bot integration and related bot flows
- `templates/` and `static/` — frontend templates and static assets

## Core features

- user registration and OTP-based verification flow
- admin dashboard with analytics and management tools
- order creation and order status handling
- product/category management
- delivery driver management
- audit and restore history with `UndoLog` support
- Docker-based local development environment
- API support using Django REST Framework

## Local development

Use Docker Compose for local setup:

```bash
docker compose up -d --build
```

Then run the app migrations and static collection:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput
```

Open the app in the browser at:

```text
http://localhost:8000
```

## Environment variables

Create a `.env` file based on your local or production needs. Typical variables include:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=pharmacy_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
REDIS_URL=redis://redis:6379/0
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-google-app-password
JWT_SECRET=another-super-secret-key-for-jwt
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

## Testing

The project includes pytest-based testing patterns and can run in a local environment without requiring a browser-based setup. Example commands:

```bash
pytest
pytest tests/dashboard
pytest tests/security
```

The repository also contains CI-oriented configuration for linting and tests, but browser-driven Playwright checks are optional and not required for the local unit-level flows.

## Deployment

For production or staging, the usual deployment pattern is:

- EC2 or another Linux VM
- Nginx as reverse proxy
- Gunicorn as the Django WSGI server
- PostgreSQL for production data
- Redis for cache and task support
- SSL certificates via Certbot

Typical deployment steps:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check
```

Then point Nginx to the Gunicorn service on localhost:8000 and serve static files from the collected `staticfiles` directory.

## Monitoring Stack

OnlinePharmacy includes a complete monitoring solution with Prometheus, Grafana, and Sentry:

### Quick Start

```bash
# Start monitoring stack with Docker Compose
docker compose up -d --build

# Access monitoring tools:
# - Prometheus: http://localhost:9090 (metrics collection)
# - Grafana: http://localhost:3000 (login: admin/admin - visualization)
# - Sentry: http://localhost:9000 (error tracking)
# - Django Metrics: http://localhost:8000/metrics/ (raw metrics endpoint)
```

### Setup Monitoring

1. **Grafana Dashboard**: Add Prometheus datasource at http://prometheus:9090
2. **Sentry Configuration**: Set `SENTRY_DSN` in `.env`:
   ```env
   SENTRY_DSN=http://sentry:9000/
   SENTRY_TRACES_SAMPLE_RATE=1.0
   ```
3. **View Metrics**: Access http://localhost:8000/metrics/ to see all collected metrics

### Components

- **Prometheus**: Scrapes Django `/metrics/` endpoint every 15 seconds
- **Grafana**: Visualizes metrics with dashboards and alerts
- **Sentry**: Captures errors, exceptions, and performance data
- **django-prometheus**: Middleware that exports Django metrics

For detailed monitoring setup, see [monitoring.md](monitoring.md).

## Security notes

- keep `.env` and secrets out of version control
- use `DEBUG=False` in production
- restrict admin routes to staff/admin users
- handle CSRF for all state-changing requests
- protect restore operations with proper checks and audit logging

## Code Quality & Linting

OnlinePharmacy uses industry-standard tools for code quality and formatting:

### Tools Used

- **black**: Code formatter (enforces consistent style)
- **isort**: Import sorter (organizes imports alphabetically)
- **flake8**: Linter (checks for style violations and errors)
- **pytest**: Test framework

### Local Development

Before committing, ensure your code passes all checks:

```bash
# Format code with black
black .

# Sort imports with isort
isort .

# Check linting with flake8
flake8 . --max-line-length=120

# Run tests
pytest

# Or run all checks at once (recommended)
black . && isort . && flake8 . --max-line-length=120 && pytest
```

### CI/CD Pipeline

All checks run automatically on `push` and `pull_request`:

1. **Linting** (flake8): Checks for syntax errors and style violations
2. **Import Sorting** (isort): Ensures imports are properly organized
3. **Code Formatting** (black): Validates code follows black style
4. **Tests** (pytest): Runs all unit and integration tests

See [.github/workflows/cm.yml](.github/workflows/cm.yml) for workflow details.

### Configuration

All tool configurations are in `pyproject.toml`:
- Black: line length = 120
- isort: profile = "black", compatible with black settings
- flake8: max complexity = 10, max line length = 120
- pytest: Django settings module configured

For detailed guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Author

Firdavs Yo'ldashev

## Project status

This repository is a working Django-based project used for local development and a strong base for further production hardening.
