#!/bin/bash
# Production entrypoint script for OnlinePharmacy Django application
# This script runs database migrations, collects static files, and starts Gunicorn

set -e

echo "🚀 Starting OnlinePharmacy Production Entrypoint..."

# 1. Run database migrations
echo "📦 Running database migrations..."
python manage.py migrate --noinput

# 2. Collect static files
echo "🎨 Collecting static files..."
python manage.py collectstatic --noinput

# 3. Start Gunicorn
echo "✅ Starting Gunicorn server..."
gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --worker-class sync \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    config.wsgi:application
