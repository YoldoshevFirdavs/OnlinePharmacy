#!/bin/bash
# Production entrypoint script for OnlinePharmacy Django application
# This script runs database migrations, collects static files, and starts Gunicorn

echo "🚀 Starting OnlinePharmacy Production Entrypoint..."

# 1. Run database migrations (non-blocking)
echo "📦 Running database migrations..."
python manage.py migrate --noinput 2>&1 || {
    echo "⚠️ Migration warning - DB might not be fully ready";
}

# 2. Collect static files - SKIP if collectstatic causes issues
echo "🎨 Collecting static files..."
# Try to collect static files with timeout to prevent hanging
timeout 30 python manage.py collectstatic --noinput --clear 2>&1 || {
    echo "⚠️ Collectstatic skipped or timed out - Gunicorn will serve from staticfiles directory";
}

# 3. Start Gunicorn with exec to replace shell process
echo "✅ Starting Gunicorn server on 0.0.0.0:8000..."
exec gunicorn \
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
