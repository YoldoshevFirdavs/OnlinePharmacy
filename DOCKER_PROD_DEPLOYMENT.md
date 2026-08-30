# Docker Production Deployment Guide

**Goal:** Run Django app in Docker using host filesystem for static files, media, and database.

## Architecture Overview

```
EC2 Host: /home/ec2-user/OnlinePharmacy/
├── staticfiles/         ← collectstatic output (shared with Docker)
├── media/              ← User uploads (shared with Docker)
├── postgres_data/      ← Database (shared with Docker)
├── docker-compose.prod.yml
├── .env.prod
└── nginx/ (optional)

Docker Containers (inside EC2):
├── web:8000           ← Django/Gunicorn (reads/writes to host paths)
├── db                 ← PostgreSQL (writes to host postgres_data/)
├── redis              ← Redis (in-memory)
├── celery             ← Background tasks
├── auth_bot           ← Telegram bot
└── nginx:80/443       ← Reverse proxy (optional)
```

## Setup Process

### Step 1: Prepare Host Directories

Run this on the EC2 host (NOT inside Docker):

```bash
# SSH into EC2
ssh -i your-key.pem ec2-user@your-ec2-ip

# Go to project directory
cd /home/ec2-user/OnlinePharmacy

# Run setup script
bash DOCKER_HOST_SETUP.sh
```

This creates:
- `/home/ec2-user/OnlinePharmacy/staticfiles/` - for collectstatic output
- `/home/ec2-user/OnlinePharmacy/media/` - for user uploads
- `/home/ec2-user/OnlinePharmacy/postgres_data/` - for database

### Step 2: Update Environment Variables

Edit `.env.prod`:

```bash
# Database (must match docker-compose.prod.yml environment)
DB_NAME=onlinepharmacy_prod
DB_USER=pharmacy_user
DB_PASSWORD=your-secure-password-here
POSTGRES_DB=onlinepharmacy_prod
POSTGRES_USER=pharmacy_user
POSTGRES_PASSWORD=your-secure-password-here

# Django
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,ec2-ip-address
SECRET_KEY=your-secret-key-here-make-it-long
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Redis
REDIS_URL=redis://redis:6379/0

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Telegram Bot
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_ADMIN_CHAT_ID=your-chat-id

# Media Files (for Django to find them)
MEDIA_ROOT=/app/media
MEDIA_URL=/media/
STATIC_ROOT=/app/staticfiles
STATIC_URL=/static/
```

### Step 3: Build Docker Images

```bash
cd /home/ec2-user/OnlinePharmacy

# Build images (this may take 5-10 minutes)
docker compose -f docker-compose.prod.yml build

# Check if build was successful
docker images | grep pharmacy
```

### Step 4: Start Services

```bash
# Start all services in background
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f web
```

### Step 5: Run Initial Setup

```bash
# Create superuser
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

# Collect static files
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Check if files were collected
ls -la /home/ec2-user/OnlinePharmacy/staticfiles/static/
```

### Step 6: Verify Setup

```bash
# Check services are running
docker compose -f docker-compose.prod.yml ps

# Test web endpoint
curl -I http://localhost:8000/api/v1/health/

# Test static files
curl -I http://localhost:8000/static/css/main.css

# Check logs for errors
docker compose -f docker-compose.prod.yml logs web
```

## Common Commands

### View Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f db
docker compose -f docker-compose.prod.yml logs -f celery

# Last 100 lines
docker compose -f docker-compose.prod.yml logs --tail=100 web
```

### Execute Commands Inside Container

```bash
# Django shell
docker compose -f docker-compose.prod.yml exec web python manage.py shell

# Run migrations
docker compose -f docker-compose.prod.yml exec web python manage.py migrate

# Create superuser
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

# Collect static files
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Database backup
docker compose -f docker-compose.prod.yml exec db pg_dump -U $DB_USER $DB_NAME > backup.sql
```

### Stop/Restart Services

```bash
# Stop all services
docker compose -f docker-compose.prod.yml down

# Restart services
docker compose -f docker-compose.prod.yml restart

# Restart specific service
docker compose -f docker-compose.prod.yml restart web

# Stop without removing data
docker compose -f docker-compose.prod.yml stop

# Remove everything (DATA LOSS!)
docker compose -f docker-compose.prod.yml down -v  # WARNING: Removes volumes!
```

### Database Operations

```bash
# Access PostgreSQL directly
docker compose -f docker-compose.prod.yml exec db psql -U $DB_USER -d $DB_NAME

# Backup database
docker compose -f docker-compose.prod.yml exec db pg_dump -U $DB_USER -d $DB_NAME > backup_$(date +%Y%m%d).sql

# Restore database
docker compose -f docker-compose.prod.yml exec -T db psql -U $DB_USER -d $DB_NAME < backup.sql
```

## Nginx Setup (Optional)

To serve static files and media with Nginx instead of Gunicorn:

### 1. Create Nginx Configuration

```bash
mkdir -p /home/ec2-user/OnlinePharmacy/nginx
# Create nginx/nginx.conf (see NGINX_SETUP.md for content)
```

### 2. Uncomment Nginx in docker-compose.prod.yml

Edit `docker-compose.prod.yml` and uncomment the `nginx` service.

### 3. Restart Services

```bash
docker compose -f docker-compose.prod.yml up -d nginx
```

### 4. Test

```bash
curl -I http://localhost/static/css/main.css
curl -I http://localhost/api/v1/health/
```

See `NGINX_SETUP.md` for detailed Nginx configuration.

## Volume Mounts Explained

The key part is how Docker volumes are mapped:

```yaml
volumes:
  # HOST PATH              → DOCKER PATH
  - /home/ec2-user/OnlinePharmacy/staticfiles:/app/staticfiles
  - /home/ec2-user/OnlinePharmacy/media:/app/media
  - /home/ec2-user/OnlinePharmacy/postgres_data:/var/lib/postgresql/data/
```

This means:
- Django writes to `/app/staticfiles` inside container
- That `/app/staticfiles` is actually `/home/ec2-user/OnlinePharmacy/staticfiles` on the host
- Nginx can read directly from the host path
- No Docker-managed volumes - everything is on the host

## Troubleshooting

### Docker Container Won't Start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs web

# Common issues:
# 1. Port already in use
lsof -i :8000

# 2. Database not ready
# Wait a few seconds and try again

# 3. .env.prod not found
ls -la /home/ec2-user/OnlinePharmacy/.env.prod
```

### Static Files Not Found (404)

```bash
# Check if collectstatic ran
ls -la /home/ec2-user/OnlinePharmacy/staticfiles/static/

# Manually run collectstatic
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Check file permissions
chmod -R 755 /home/ec2-user/OnlinePharmacy/staticfiles
```

### Media Uploads Not Working

```bash
# Check media directory exists
ls -la /home/ec2-user/OnlinePharmacy/media/

# Check permissions
chmod -R 755 /home/ec2-user/OnlinePharmacy/media

# Check Docker has access
docker compose -f docker-compose.prod.yml exec web ls -la /app/media/
```

### Database Connection Error

```bash
# Check database is running
docker compose -f docker-compose.prod.yml ps db

# Check logs
docker compose -f docker-compose.prod.yml logs db

# Verify environment variables
grep DB_NAME /home/ec2-user/OnlinePharmacy/.env.prod
grep POSTGRES_ /home/ec2-user/OnlinePharmacy/.env.prod
```

### Out of Disk Space

```bash
# Check disk usage
df -h /home/ec2-user/

# Check what's using space
du -sh /home/ec2-user/OnlinePharmacy/*

# Clean up old logs
docker system prune -a --volumes

# Remove old media files
find /home/ec2-user/OnlinePharmacy/media -type f -mtime +90 -delete
```

## Monitoring & Maintenance

### Check Service Status

```bash
# All services
docker compose -f docker-compose.prod.yml ps

# Detailed service info
docker compose -f docker-compose.prod.yml logs --tail=50 web
```

### Performance Monitoring

```bash
# Monitor container CPU/memory
docker stats

# Check disk usage
du -sh /home/ec2-user/OnlinePharmacy/

# Check database size
docker compose -f docker-compose.prod.yml exec db psql -U $DB_USER -d $DB_NAME -c "SELECT pg_size_pretty(pg_database.datsize) FROM pg_database WHERE datname = '$DB_NAME';"
```

### Regular Backups

```bash
# Create backup script
cat > /home/ec2-user/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/ec2-user/OnlinePharmacy/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U $DB_USER -d $DB_NAME > $BACKUP_DIR/db_backup_$DATE.sql

# Backup media files
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz /home/ec2-user/OnlinePharmacy/media/

echo "Backup complete: $BACKUP_DIR"
EOF

# Make executable
chmod +x /home/ec2-user/backup.sh

# Add to crontab (daily at 2 AM)
# 0 2 * * * /home/ec2-user/backup.sh
```

## Security Checklist

- [ ] `.env.prod` is NOT committed to git
- [ ] Database password is strong (min 16 chars, mixed case, symbols)
- [ ] `SECRET_KEY` is long and random
- [ ] `DEBUG=False` in production
- [ ] `ALLOWED_HOSTS` includes your domain
- [ ] SSL/TLS certificates installed
- [ ] Regular backups configured
- [ ] Firewall rules configured (only allow 80/443/ssh)
- [ ] Log files monitored for errors
- [ ] Database and media files have backups

## Post-Deployment Checklist

- [ ] Django admin accessible at `/admin/`
- [ ] Static files loading (`/static/css/main.css`)
- [ ] Media files uploading (avatar upload works)
- [ ] API endpoints responding (`/api/v1/health/`)
- [ ] Contact form working (`/api/v1/products/contact/`)
- [ ] Email sending working
- [ ] Telegram bot connected and responding
- [ ] Celery background tasks running
- [ ] Logs look normal (no errors)
- [ ] Database backup tested and working

## Next Steps

1. **Add SSL/TLS**: Use Let's Encrypt (Certbot)
2. **Add Nginx**: For better static file serving
3. **Add Monitoring**: New Relic, DataDog, etc.
4. **Add CI/CD**: GitHub Actions to auto-deploy
5. **Scale Up**: Add more Gunicorn workers, multiple replicas

See `NGINX_SETUP.md` for Nginx configuration details.

