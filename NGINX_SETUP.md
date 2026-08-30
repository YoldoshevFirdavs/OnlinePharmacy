# Nginx Setup for Docker Production

## Overview

This guide explains how to configure Nginx to serve static files and media from the host filesystem when using docker-compose with volume mounts.

## Current Setup

```
Docker Compose          Host Filesystem
├─ /app/staticfiles  → /home/ec2-user/OnlinePharmacy/staticfiles
├─ /app/media        → /home/ec2-user/OnlinePharmacy/media
└─ web:8000          → Gunicorn running inside container
```

## Nginx Configuration

### 1. Directory Structure on Host

```
/home/ec2-user/OnlinePharmacy/
├── staticfiles/          ← collectstatic output (served by Nginx)
│   └── static/
│       ├── admin/
│       ├── js/
│       ├── css/
│       ├── images/
│       └── ...
├── media/                ← User uploads (served by Nginx)
│   ├── uploads/
│   │   └── avatars/
│   └── ...
├── docker-compose.prod.yml
├── nginx/
│   └── nginx.conf        ← Nginx configuration
└── ...
```

### 2. Nginx Configuration File

Create `nginx/nginx.conf`:

```nginx
upstream gunicorn {
    server web:8000;
}

server {
    listen 80;
    server_name _;
    client_max_body_size 10M;

    # Static files (CSS, JS, etc.)
    location /static/ {
        # Serve from mounted host volume
        alias /app/staticfiles/static/;
        
        # Cache settings for static files
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files (user uploads, avatars)
    location /media/ {
        # Serve from mounted host volume
        alias /app/media/;
        
        # Cache settings for media
        expires 7d;
        add_header Cache-Control "public";
    }

    # Django application
    location / {
        proxy_pass http://gunicorn;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint
    location /health/ {
        proxy_pass http://gunicorn;
        access_log off;
    }
}
```

### 3. Docker Compose with Nginx

To use Nginx, uncomment in `docker-compose.prod.yml`:

```yaml
  nginx:
    image: nginx:latest
    container_name: nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - /home/ec2-user/OnlinePharmacy/staticfiles:/app/staticfiles:ro
      - /home/ec2-user/OnlinePharmacy/media:/app/media:ro
    depends_on:
      - web
    restart: unless-stopped
```

### 4. File Permissions

Make sure Nginx can read the files:

```bash
# Make sure staticfiles and media are readable
chmod -R 755 /home/ec2-user/OnlinePharmacy/staticfiles
chmod -R 755 /home/ec2-user/OnlinePharmacy/media

# Make sure files inside are readable
chmod -R 644 /home/ec2-user/OnlinePharmacy/staticfiles/*
chmod -R 644 /home/ec2-user/OnlinePharmacy/media/*
```

## How It Works

### Without Nginx (Current - Direct to Gunicorn)

```
User Request
    ↓
Port 8000 (Gunicorn)
    ↓
Django serves /static/ and /media/ directly
```

**Advantage:** Simple setup, everything in Docker  
**Disadvantage:** Gunicorn wastes time serving static files

### With Nginx (Recommended for Production)

```
User Request
    ↓
Port 80/443 (Nginx)
    ↓
├─ /static/* → Served from /app/staticfiles/ directly (no Django)
├─ /media/*  → Served from /app/media/ directly (no Django)
└─ /* other → Proxied to Gunicorn:8000
```

**Advantage:** Nginx is optimized for static files, faster  
**Disadvantage:** Slightly more complex setup

## Step-by-Step Setup

### 1. Create Nginx Config Directory

```bash
mkdir -p /home/ec2-user/OnlinePharmacy/nginx
```

### 2. Create nginx/nginx.conf

```bash
cat > /home/ec2-user/OnlinePharmacy/nginx/nginx.conf << 'EOF'
# (copy the nginx.conf content from above)
EOF
```

### 3. Run Host Setup Script

```bash
cd /home/ec2-user/OnlinePharmacy
bash DOCKER_HOST_SETUP.sh
```

### 4. Start Docker Compose

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 5. Run Collectstatic

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

### 6. Verify

Check that files are in the right places:

```bash
# Check staticfiles
ls -la /home/ec2-user/OnlinePharmacy/staticfiles/static/

# Check media
ls -la /home/ec2-user/OnlinePharmacy/media/

# Check Nginx is running
docker ps | grep nginx

# Test access
curl -I http://localhost/static/css/
curl -I http://localhost/api/v1/health/
```

## SSL/TLS (HTTPS)

To add HTTPS:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/nginx/certs/cert.pem;
    ssl_certificate_key /etc/nginx/certs/key.pem;
    
    # ... rest of configuration
}
```

Add certs volume to docker-compose:

```yaml
nginx:
  volumes:
    - ./certs:/etc/nginx/certs:ro
```

## Troubleshooting

### Issue: 403 Forbidden for Static Files

**Cause:** File permissions  
**Fix:**
```bash
chmod -R 755 /home/ec2-user/OnlinePharmacy/staticfiles
chmod -R 755 /home/ec2-user/OnlinePharmacy/media
```

### Issue: Static Files Not Found

**Cause:** collectstatic not run or not in the right place  
**Fix:**
```bash
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
ls -la /home/ec2-user/OnlinePharmacy/staticfiles/
```

### Issue: Nginx Can't Connect to Django

**Cause:** Docker network issue  
**Fix:**
```bash
# Verify networks
docker network ls
docker network inspect pharmacy_network
```

### Issue: Media Uploads Not Saved

**Cause:** Media directory permissions  
**Fix:**
```bash
chmod -R 755 /home/ec2-user/OnlinePharmacy/media
chown -R 1000:1000 /home/ec2-user/OnlinePharmacy/media  # Docker user
```

## Performance Tips

1. **Enable Gzip Compression**

```nginx
gzip on;
gzip_types text/plain text/css text/javascript application/json;
gzip_min_length 1024;
```

2. **Add Expires Headers**

```nginx
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

3. **Use CDN for Static Files** (for production scale)

```
StaticFiles → CloudFront/CloudFlare
Media → Direct from Nginx or CDN
```

4. **Monitor Disk Space**

```bash
# Check disk usage
du -sh /home/ec2-user/OnlinePharmacy/staticfiles
du -sh /home/ec2-user/OnlinePharmacy/media

# Clean old uploads (optional)
find /home/ec2-user/OnlinePharmacy/media -type f -mtime +90 -delete
```

## Summary

| Aspect | Without Nginx | With Nginx |
|--------|---|---|
| Setup Complexity | Simple | Medium |
| Static File Performance | Slower | Faster |
| SSL/TLS | In Gunicorn | In Nginx |
| Media Serving | From Django | Direct |
| Scalability | Limited | Better |
| Recommended | Development | Production |

Choose based on your needs:
- **Development/Testing:** No Nginx (current setup)
- **Production:** With Nginx (uncomment in docker-compose)

