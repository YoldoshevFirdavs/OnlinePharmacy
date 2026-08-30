# Host-Based Static Files Collection (NOT in Docker)

## Overview

Static files (CSS, JavaScript, images) are now collected **ON THE EC2 HOST**, not inside Docker. This ensures all assets are on the host filesystem where Nginx can serve them directly.

## Architecture

```
Old Way (❌ Not recommended):
  Docker entrypoint → runs collectstatic inside container
  → Files in Docker volume → Must export/map to host
  → Slower, more complex

New Way (✅ Recommended):
  Host machine → runs collectstatic directly
  → Files directly on /home/ec2-user/OnlinePharmacy/staticfiles/
  → Docker just uses the mounted directory
  → Faster, simpler, files always visible on host
```

## How It Works

### 1. DOCKER_HOST_SETUP.sh Script

When you run this script on EC2 host:

```bash
bash DOCKER_HOST_SETUP.sh
```

It does:
1. Creates `/home/ec2-user/OnlinePharmacy/staticfiles/`
2. Creates `/home/ec2-user/OnlinePharmacy/media/`
3. Creates `/home/ec2-user/OnlinePharmacy/postgres_data/`
4. **Runs `python manage.py collectstatic --noinput` on HOST**
5. Sets proper permissions

Result: All static files are on host BEFORE Docker starts.

### 2. Docker Starts

When you run:

```bash
docker compose -f docker-compose.prod.yml up -d
```

Docker:
1. Mounts host directories to container paths
2. Django reads from `/app/staticfiles/` (which is `/home/ec2-user/OnlinePharmacy/staticfiles/` on host)
3. **No collectstatic runs inside Docker** (skipped in entrypoint.sh)
4. Nginx serves from host staticfiles directory
5. Gunicorn handles API only

### 3. File Flow

```
Host: /home/ec2-user/OnlinePharmacy/staticfiles/static/
                           ↑
                           │ (volume mount)
                           ↓
Container: /app/staticfiles/static/
                           ↑
                           │ (Nginx reads from here)
                           ↓
User: Browser downloads CSS/JS/images
```

## Prerequisites

You need Django installed on EC2 host:

```bash
# Check if Python is on host
python --version

# Check if Django is installed
python -c "import django; print(django.VERSION)"

# If not, install:
pip install django djangorestframework python-dotenv psycopg2-binary
```

## Step-by-Step Setup

### 1. Ensure Python & Django on Host

```bash
# SSH to EC2
ssh -i your-key.pem ec2-user@your-ec2-ip

# Check Python
python --version          # Should show Python 3.10+
python -m pip --version   # Should work

# Check Django
python -c "import django; print(django.__version__)"
```

### 2. Run Setup Script

```bash
cd /home/ec2-user/OnlinePharmacy

# Run setup (collects static files on host)
bash DOCKER_HOST_SETUP.sh
```

Expected output:
```
✅ staticfiles created
✅ media created
✅ media/uploads/avatars created
✅ postgres_data created
✅ Collecting static files...
🎨 Running: python manage.py collectstatic --noinput --clear
123 static files copied to...
✅ collectstatic completed successfully
```

### 3. Verify Static Files

```bash
# Check staticfiles directory
ls -la /home/ec2-user/OnlinePharmacy/staticfiles/static/

# Should see: admin/, css/, js/, images/, ...
```

### 4. Start Docker

```bash
# Build image
docker compose -f docker-compose.prod.yml build

# Start services
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps
```

### 5. Initialize Database

```bash
# Run migrations
docker compose -f docker-compose.prod.yml exec web python manage.py migrate

# Create superuser
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

## What Changed

### entrypoint.sh (Inside Docker)

**BEFORE:**
```bash
python manage.py collectstatic --noinput --clear
exec gunicorn ...
```

**AFTER:**
```bash
# SKIP collectstatic - runs on host
echo "Skipping collectstatic (runs on host)"
exec gunicorn ...
```

### DOCKER_HOST_SETUP.sh (On Host)

**BEFORE:**
```bash
# Just creates directories
mkdir -p /home/ec2-user/OnlinePharmacy/staticfiles
```

**AFTER:**
```bash
# Creates directories AND runs collectstatic
mkdir -p /home/ec2-user/OnlinePharmacy/staticfiles
python manage.py collectstatic --noinput --clear
```

## Volume Mounts

In `docker-compose.prod.yml`:

```yaml
volumes:
  # staticfiles from host
  - /home/ec2-user/OnlinePharmacy/staticfiles:/app/staticfiles
  # media from host
  - /home/ec2-user/OnlinePharmacy/media:/app/media
```

This means:
- Docker container `/app/staticfiles/` points to host `/home/ec2-user/OnlinePharmacy/staticfiles/`
- Any file written to `/app/staticfiles/` is visible on host
- Nginx can read directly from host

## Troubleshooting

### Problem: Python not found on host

```bash
Error: Python not found on host
Solution: You can run collectstatic from inside Docker:
  docker compose exec web python manage.py collectstatic --noinput
```

### Problem: Static files not found (404)

```bash
# Verify files exist on host
ls -la /home/ec2-user/OnlinePharmacy/staticfiles/static/

# If empty, run collectstatic:
cd /home/ec2-user/OnlinePharmacy
python manage.py collectstatic --noinput
```

### Problem: Permission denied

```bash
# Fix permissions
chmod -R 755 /home/ec2-user/OnlinePharmacy/staticfiles
chmod -R 755 /home/ec2-user/OnlinePharmacy/media
```

### Problem: .env.prod not found

```bash
# Collectstatic needs .env.prod to be readable
# Make sure it's in: /home/ec2-user/OnlinePharmacy/.env.prod
ls -la /home/ec2-user/OnlinePharmacy/.env.prod

# If it's in Docker container, copy it from there:
# docker compose cp web:/app/.env.prod /home/ec2-user/OnlinePharmacy/
```

## Benefits

✅ **Static files always on host** - visible when SSH'ing to EC2  
✅ **Faster collection** - runs once on host, not every container start  
✅ **Simpler Docker** - no collectstatic in entrypoint  
✅ **Better for Nginx** - serves directly from host filesystem  
✅ **Easier debugging** - see all files without docker commands  
✅ **Easier backups** - copy `/home/ec2-user/OnlinePharmacy/` includes staticfiles  

## File Locations

After setup, you'll have:

```
/home/ec2-user/OnlinePharmacy/
├── staticfiles/                    ← All static files here
│   └── static/
│       ├── admin/
│       ├── css/
│       │   └── main.css
│       ├── js/
│       │   ├── main.js
│       │   └── messages.js
│       └── images/
│           ├── favicon.ico
│           ├── logo.png
│           └── ...
│
├── media/                          ← User uploads
│   └── uploads/
│       └── avatars/
│           ├── user1.jpg
│           ├── user2.png
│           └── ...
│
└── .env.prod                       ← Environment (needed for collectstatic)
```

## Commands Reference

### Collect Static Files (On Host)

```bash
# One-time setup (includes static collection)
bash DOCKER_HOST_SETUP.sh

# OR manually if script fails
cd /home/ec2-user/OnlinePharmacy
python manage.py collectstatic --noinput --clear

# Verify
ls -la staticfiles/static/
```

### Collect Static Files (From Inside Docker)

```bash
# If Python not on host, use Docker
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

### After Adding New Static Files

1. Add files to `static/` directory on host
2. Run collectstatic again:

```bash
python manage.py collectstatic --noinput
```

3. Files automatically available at `/static/` in browser

## Best Practices

1. **Run collectstatic before Docker starts**
   ```bash
   bash DOCKER_HOST_SETUP.sh  # Do this first
   docker compose up -d       # Then start Docker
   ```

2. **Never edit staticfiles directly**
   - They're regenerated by collectstatic
   - Edit source files in `static/` or app directories instead

3. **Backup staticfiles directory**
   ```bash
   tar -czf staticfiles_backup.tar.gz /home/ec2-user/OnlinePharmacy/staticfiles/
   ```

4. **Monitor disk space for media uploads**
   ```bash
   du -sh /home/ec2-user/OnlinePharmacy/media/
   ```

5. **Set proper permissions**
   ```bash
   chmod -R 755 /home/ec2-user/OnlinePharmacy/staticfiles
   chmod -R 755 /home/ec2-user/OnlinePharmacy/media
   ```

## Summary

| Aspect | Old Way | New Way |
|--------|---------|---------|
| Where collected | Inside Docker | On host |
| When collected | Each container start | Before Docker starts |
| File location | Docker volume | Host filesystem |
| Nginx access | Through volume mount | Direct from host |
| Debugging | Requires docker commands | Direct SSH access |
| Backup | Export Docker volume | Copy directory |
| Speed | Slower | Faster |

✅ **Use the new way for production!**

