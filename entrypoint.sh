#!/bin/bash
# Production entrypoint script for OnlinePharmacy Django application
# This script runs database migrations, collects static files, and starts Gunicorn

echo "🚀 Starting OnlinePharmacy Production Entrypoint..."

# 1. Run database migrations (continue even if fails - DB might not be ready)
echo "📦 Running database migrations..."
python manage.py migrate --noinput || {
    echo "⚠️ Migration failed or DB not ready yet. Continuing...";
    sleep 5;
}

# 2. Collect static files (ignore errors - may fail if DB not ready)
echo "🎨 Collecting static files..."
python manage.py collectstatic --noinput --clear || {
    echo "⚠️ Collectstatic encountered issues. Continuing...";
}

# 3. Start Gunicorn
echo "✅ Starting Gunicorn server..."
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
