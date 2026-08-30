#!/bin/bash
# Production entrypoint script for OnlinePharmacy Django application
# This script runs database migrations and starts Gunicorn
# NOTE: Static files collection is handled OUTSIDE Docker on the host
# (collectstatic runs on EC2 host, not inside Docker container)

echo "🚀 Starting OnlinePharmacy Production Entrypoint..."

# 1. Run database migrations (non-blocking)
echo "📦 Running database migrations..."
python manage.py migrate --noinput 2>&1 || {
    echo "⚠️ Migration warning - DB might not be fully ready";
}

# 2. SKIP collectstatic - it runs on host, not in Docker
echo "⏭️  Skipping collectstatic (runs on host via DOCKER_HOST_SETUP.sh)"
echo "   Static files location: /app/staticfiles → /home/ec2-user/OnlinePharmacy/staticfiles"

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
