# Static Files & Media Management

## Table of Contents
1. [Overview](#overview)
2. [Static Files Organization](#static-files-organization)
3. [Media Files & User Uploads](#media-files--user-uploads)
4. [Production Serving](#production-serving)
5. [Development Setup](#development-setup)
6. [Optimization & Caching](#optimization--caching)
7. [CDN Integration](#cdn-integration)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The OnlinePharmacy project distinguishes between **static files** (CSS, JS, images) and **media files** (user uploads). Both are served through Nginx in production and Django's development server in development.

### Key Configuration

```python
# config/settings.py

# Static files (app code, vendor libraries)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # Production collected files
STATICFILES_DIRS = [BASE_DIR / "static"]  # Source files

# Media files (user uploads)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"  # Uploaded files directory

# WhiteNoise for efficient static serving
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
```

### Directory Structure

```
OnlinePharmacy/
├── static/                      # Source static files
│   ├── css/
│   │   ├── dashboard.css
│   │   ├── shop.css
│   │   └── responsive.css
│   ├── js/
│   │   ├── cart.js
│   │   ├── search.js
│   │   └── vendor/
│   ├── images/
│   │   ├── icons/
│   │   ├── logos/
│   │   └── default/              # Default fallback images
│   │       ├── default_avatar.png
│   │       ├── default_product.png
│   │       └── default_icon.png
│   ├── dashboard/
│   ├── shop/
│   ├── vendor/                   # Third-party libraries
│   ├── webfonts/                 # Custom fonts
│   └── favicon.ico
├── staticfiles/                 # Production collected (auto-generated)
│   ├── admin/
│   ├── css/
│   ├── js/
│   └── manifest.json           # WhiteNoise cache manifest
├── media/                       # User uploads (development)
│   ├── users_profile_avatars/
│   ├── medicines/
│   │   ├── main/
│   │   └── gallery/
│   ├── drivers/
│   ├── uploads/
│   └── temp/
└── manage.py
```

---

## Static Files Organization

### Django Admin & Third-Party

Django automatically collects static files from installed apps:

```bash
python manage.py collectstatic
```

This gathers files from:
- `django.contrib.admin/` — Django admin interface
- `rest_framework/` — DRF UI
- `drf_yasg/` — Swagger documentation
- `app_name/static/` — App-specific static files

### Custom Static Files

**CSS Hierarchy:**

```
static/css/
├── base.css               # Global styles
├── dashboard.css          # Dashboard/admin UI
├── shop.css              # Storefront styles
├── responsive.css        # Mobile/tablet styles
└── variables.css         # SCSS/CSS custom properties
```

**JavaScript Organization:**

```
static/js/
├── main.js               # Entry point
├── cart.js              # Shopping cart logic
├── search.js            # Product search
├── api.js               # API client (fetch/axios)
├── auth.js              # Authentication helpers
├── dashboard/
│   ├── orders.js
│   ├── analytics.js
│   └── admin.js
└── vendor/
    ├── jquery.js
    ├── bootstrap.js
    └── other-libs/
```

**Images Directory:**

```
static/images/
├── icons/
│   ├── telegram.png
│   ├── instagram.png
│   └── facebook.png
├── logos/
│   ├── logo-light.png
│   ├── logo-dark.png
│   └── favicon.ico
├── default/
│   ├── default_avatar.png     # Fallback for missing user avatars
│   ├── default_product.png    # Fallback for missing product images
│   └── default_icon.png       # Generic fallback icon
└── backgrounds/
    ├── hero.jpg
    └── pattern.png
```

### Default Image Fallbacks

When users don't upload profile pictures or product images, Django returns these static defaults:

```python
# users/models.py
@property
def get_avatar_url(self):
    if self.avatar:
        return self.avatar.url
    return "/static/images/default/default_avatar.png"

# pharmacy/views/detail.py
DEFAULT_IMAGE = "/static/images/default/default_avatar.png"

# Template usage
<img src="{{ medicine.main_image.url|default:'/static/images/default/default_product.png' }}" alt="Product">
```

---

## Media Files & User Uploads

### Upload Paths (Model Configuration)

Media files are organized by content type:

```python
# users/models.py
class CustomUser(models.Model):
    avatar = ImageField(upload_to="users_profile_avatars/", blank=True, null=True)

class Seller(models.Model):
    avatar = ImageField(upload_to="users_profile_avatars/", blank=True, null=True)

class DeliveryDriver(models.Model):
    avatar = ImageField(upload_to="drivers/", blank=True, null=True)

# pharmacy/models/medicine.py
class Medicine(models.Model):
    main_image = ImageField(upload_to="medicines/main/", null=True, blank=True)

class MedicineImage(models.Model):
    image = ImageField(upload_to="medicines/gallery/")
```

### Resulting Directory Structure

```
media/
├── users_profile_avatars/
│   ├── user_1_avatar.jpg
│   ├── user_2_avatar.jpg
│   └── seller_1_avatar.png
├── medicines/
│   ├── main/
│   │   ├── aspirin_main.jpg
│   │   ├── paracetamol_main.jpg
│   │   └── ...
│   └── gallery/
│       ├── medicine_1_gallery_1.jpg
│       ├── medicine_1_gallery_2.jpg
│       └── ...
├── drivers/
│   ├── driver_1_avatar.jpg
│   ├── driver_2_avatar.jpg
│   └── ...
└── temp/
    └── processing/     # Temporary uploads during processing
```

### File Upload Handling

**Image validation in serializers:**

```python
# pharmacy/serializers/medicine.py
class MedicineSerializer(serializers.ModelSerializer):
    main_image = serializers.ImageField(required=False, allow_null=True)

    def validate_main_image(self, value):
        if value:
            # Check file size (max 5MB)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Image size must be less than 5MB")
            
            # Check file format
            if value.content_type not in ['image/jpeg', 'image/png', 'image/webp']:
                raise serializers.ValidationError("Only JPEG, PNG, and WebP allowed")
        
        return value

    class Meta:
        model = Medicine
        fields = ['name', 'price', 'main_image', ...]
```

### Serving Media in Development

Django automatically serves media files in development:

```python
# config/urls.py
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ... your patterns
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

**Development server command:**

```bash
python manage.py runserver 0.0.0.0:8000
```

---

## Production Serving

### Static Files Collection

Before deploying, collect all static files:

```bash
# From project root
python manage.py collectstatic --no-input --clear

# Options explained:
# --no-input: Don't ask for confirmation
# --clear: Remove old staticfiles before collecting
```

This creates `/staticfiles/` directory with:
- All admin files
- All app static files
- Manifest (for WhiteNoise cache busting)

### WhiteNoise Configuration

WhiteNoise efficiently serves static files without Nginx:

```python
# config/settings.py
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Add after SecurityMiddleware
    # ... other middleware
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
```

**Features:**
- Compresses CSS/JS (gzip, brotli)
- Cache busting with manifest.json
- Fingerprinted file names (e.g., `main.a1b2c3d4.css`)
- HTTP caching headers

### Nginx Configuration

For production with separate Nginx server:

```nginx
# nginx/nginx.prod.conf
upstream django {
    server web:8000;
}

server {
    listen 80;
    server_name onlinepharmacy.uz www.onlinepharmacy.uz;

    # Static files (served directly by Nginx)
    location /static/ {
        alias /vol/web/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files (user uploads)
    location /media/ {
        alias /vol/web/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # Django application
    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Docker Volume Mapping:**

```yaml
# docker-compose.prod.yml
services:
  web:
    volumes:
      - static_volume:/vol/web/static
      - media_volume:/vol/web/media
  
  nginx:
    volumes:
      - static_volume:/vol/web/static:ro
      - media_volume:/vol/web/media:ro
    depends_on:
      - web

volumes:
  static_volume:
  media_volume:
```

---

## Development Setup

### Running Locally

**Step 1: Install dependencies**

```bash
pip install -r requirements-dev.txt
```

**Step 2: Collect static files (optional for development)**

```bash
python manage.py collectstatic
```

**Step 3: Start development server**

```bash
python manage.py runserver 0.0.0.0:8000
```

Django will serve:
- Static files from `/static/` (automatic)
- Media files from `/media/` (automatic, via `static()` in urls.py)
- Admin interface at `/admin/`

### Docker Development

```bash
docker-compose up -d

# Access application
# Frontend: http://localhost:8000
# API: http://localhost:8000/api/
# Admin: http://localhost:8000/admin/
```

**Static files are automatically collected in Docker:**

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Collect static files on container start
RUN python manage.py collectstatic --no-input --clear

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]
```

---

## Optimization & Caching

### HTTP Caching Headers

Configure browser caching in Nginx:

```nginx
# Static files: 30 days (immutable)
location /static/ {
    expires 30d;
    add_header Cache-Control "public, immutable";
}

# Media files: 7 days (can change)
location /media/ {
    expires 7d;
    add_header Cache-Control "public, max-age=604800";
}
```

### CSS/JS Minification

WhiteNoise automatically compresses files:

```bash
# Inspect collected files
ls -lh staticfiles/css/
# Output: main.a1b2c3d4.css (minified & fingerprinted)
```

**Manual compression with Django Compressor (optional):**

```bash
pip install django-compressor

python manage.py compress --force
```

### Image Optimization

Optimize images before upload:

```python
# Use Pillow for image processing
from PIL import Image
import io

def optimize_image(image_field):
    img = Image.open(image_field)
    
    # Convert to RGB if RGBA
    if img.mode == 'RGBA':
        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
        rgb_img.paste(img, mask=img.split()[3] if len(img.split()) == 4 else None)
        img = rgb_img
    
    # Resize if too large
    max_size = (2000, 2000)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # Save with compression
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=85)
    output.seek(0)
    return output
```

### Lazy Loading Images

In templates:

```html
<!-- Use native lazy loading -->
<img src="{{ product.main_image.url|default:'/static/images/default/default_product.png' }}"
     alt="{{ product.name }}"
     loading="lazy">

<!-- Or with JavaScript library (LQIP) -->
<img class="lazy"
     data-src="{{ product.main_image.url }}"
     src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 300'%3E%3C/svg%3E"
     alt="{{ product.name }}">

<script src="/static/js/vendor/lqip.min.js"></script>
```

---

## CDN Integration

### AWS CloudFront

Store static and media files in S3, serve via CloudFront:

**Configuration:**

```python
# config/settings.py (production)
if not DEBUG:
    AWS_STORAGE_BUCKET_NAME = "onlinepharmacy-static"
    AWS_S3_REGION_NAME = "us-east-1"
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
    STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/static/"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
    STATICFILES_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
```

**Install django-storages:**

```bash
pip install django-storages boto3
```

**Environment variables:**

```env
AWS_ACCESS_KEY_ID=your-key-id
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=onlinepharmacy-static
AWS_S3_REGION_NAME=us-east-1
AWS_CLOUDFRONT_DOMAIN=d123456.cloudfront.net
```

### Google Cloud Storage

Alternative to S3:

```python
# config/settings.py
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        "OPTIONS": {
            "bucket_name": "onlinepharmacy-static",
            "project_id": "my-gcp-project",
        }
    }
}

STATIC_URL = "https://storage.googleapis.com/onlinepharmacy-static/static/"
```

---

## Troubleshooting

### Static Files Not Loading

**Development:**

```bash
# Ensure static files are being served
python manage.py runserver

# Check if files exist
ls -la static/css/
ls -la static/js/

# Collect static files
python manage.py collectstatic --no-input
```

**Production:**

```bash
# SSH into server
docker exec pharmacy_web python manage.py collectstatic --no-input

# Check Nginx logs
docker logs pharmacy_nginx

# Verify paths in Nginx
curl -I http://localhost/static/css/main.css
curl -I http://localhost/media/users_profile_avatars/avatar.jpg
```

### Media Files Permission Issues

```bash
# Set correct permissions
chmod -R 755 media/
chown -R www-data:www-data media/

# In Docker
docker exec pharmacy_web chown -R www-data:www-data /vol/web/media
```

### Cache Busting Not Working

WhiteNoise uses manifest.json for cache busting:

```bash
# Verify manifest exists
cat staticfiles/manifest.json

# Example output:
# {
#   "css/main.css": "css/main.a1b2c3d4.css",
#   "js/app.js": "js/app.e5f6g7h8.js"
# }

# Force regeneration
python manage.py collectstatic --no-input --clear
```

### Large File Uploads Failing

Increase Nginx and Django limits:

```nginx
# nginx.conf
client_max_body_size 50M;
```

```python
# config/settings.py
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB
```

### CORS Issues with Media Files

Add CORS headers for cross-origin requests:

```nginx
location /media/ {
    add_header Access-Control-Allow-Origin "*";
    add_header Access-Control-Allow-Methods "GET, HEAD, OPTIONS";
    add_header Access-Control-Allow-Headers "Content-Type";
}
```

### Missing Default Images

Ensure default images exist:

```bash
# Check
ls -la static/images/default/

# Should contain:
# default_avatar.png
# default_product.png
# default_icon.png

# If missing, add .gitkeep
touch static/images/default/.gitkeep
```

---

## Summary

The OnlinePharmacy static and media management:

- **Static files** (CSS, JS, images, vendors) served via WhiteNoise (dev) or Nginx (prod)
- **Media files** (user uploads) organized by content type in `/media/`
- **Default images** as fallback for missing user/product images
- **Production optimization** with compression, caching, and CDN support
- **Development simplicity** with automatic Django serving

Key files:
- `static/` — Development static files source
- `staticfiles/` — Production collected files (auto-generated)
- `media/` — User-uploaded files
- `nginx/nginx.prod.conf` — Production serving configuration
- `Dockerfile` — Container static file collection
