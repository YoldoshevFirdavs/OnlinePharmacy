# OnlinePharmacy - Docker Setup Qo'llanma

## 1. Talab Qilinadigan Programalar

Birinchi, kompyuteringizda quyidagilar o'rnatilgan bo'lishi kerak:

- **Docker** (version 20.10+)
- **Docker Compose** (version 2.0+)
- **Git**
- **Text Editor** (VSCode, PyCharm, vs)

### Windows'da Docker o'rnatish:
```bash
# Docker Desktop'ni yuklab oling: https://www.docker.com/products/docker-desktop
# O'rnatish va restart qiling
# PowerShell'da tekshiring:
docker --version
docker-compose --version
```

### Mac/Linux'da Docker o'rnatish:
```bash
# Ubuntu/Debian:
sudo apt-get update
sudo apt-get install docker.io docker-compose
sudo usermod -aG docker $USER

# Mac (Homebrew):
brew install docker docker-compose
```

---

## 2. Loyiya Fayllarini Klonlash

Repository'ni klonlang:

```bash
git clone https://github.com/your-username/OnlinePharmacy.git
cd OnlinePharmacy
```

---

## 3. Environment Faylini Tayyorlash

`.env` faylini yaratish uchun `.env.example`dan nusxa oling:

```bash
# Windows (PowerShell):
Copy-Item .env.example .env

# Mac/Linux:
cp .env.example .env
```

Keyin `.env` faylini tahrirlang va muhim qiymatlarni to'ldiring:

```env
# Django
DEBUG=False
SECRET_KEY=your-very-long-secret-key-minimum-50-chars-here
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=pharmacy_db
DB_USER=pharmacy_user
DB_PASSWORD=your-secure-password-here
DB_HOST=db
DB_PORT=5432

# Email
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Stripe (Test Keys uchun development)
STRIPE_SECRET_KEY=sk_test_your_test_key
STRIPE_PUBLIC_KEY=pk_test_your_test_key

# Telegram Bot
MAIN_BOT_TOKEN=your_telegram_bot_token
AUTH_BOT_TOKEN=your_auth_bot_token
ADMIN_ID=your_admin_user_id

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

---

## 4. Docker Images Qurilishi

Birinchi marta, Docker images'larni qurilishi kerak:

```bash
# Barcha services uchun images qurilishi
docker-compose build

# Yoki individual service:
docker-compose build web
docker-compose build celery
docker-compose build auth_bot
```

**Bu nima qiladi?**
- `Dockerfile`ni o'qiydi
- Python 3.10 image'sini yuklab oladi
- `requirements.txt` va `requirements-dev.txt`dagi barcha kutubxonalarni o'rnatadi
- Static files'larni tayyorlaydi
- Yangi Docker image yaratadi

---

## 5. Docker Containers'ni Ishga Tushirish

### A. Boshqasi uchun (Development)

```bash
# Barcha services'ni ishga tushirish
docker-compose up -d

# Yoki fonda ishga tushirmasdan logs'ni ko'rish uchun:
docker-compose up
```

**Bu nima qiladi?**
- PostgreSQL database container (5432 port)
- Redis cache container (6379 port)
- Django web server (8000 port)
- Celery worker (background tasks)
- Telegram bot service
- Prometheus monitoring (9090 port)
- Grafana dashboards (3000 port)

**Ports:**
- `http://localhost:8000` - Django app
- `http://localhost:3000` - Grafana (admin/admin)
- `http://localhost:9090` - Prometheus
- `http://localhost:5432` - PostgreSQL
- `http://localhost:6379` - Redis

### B. Production qo'llash

```bash
# .env.prod faylidan foydalanish
docker-compose --env-file .env.prod up -d
```

---

## 6. Database Migrations Bajarish

```bash
# Birinchi marta, database schema'sini yaratish kerak
docker-compose exec web python manage.py migrate

# Yoki superuser yaratish:
docker-compose exec web python manage.py createsuperuser
```

**Bu nima qiladi?**
- Database'da barcha table'larni yaratadi
- Migration'larni qo'llaydi
- Admin user'ni yaratadi

---

## 7. Static Files'larni Tayyorlash

```bash
# Static files'larni /staticfiles katalogiga ko'chirish
docker-compose exec web python manage.py collectstatic --noinput
```

---

## 8. Logs'ni Ko'rish va Debugging

```bash
# Barcha services'ning logs'ni real-time ko'rish
docker-compose logs -f

# Faqat Django app logs:
docker-compose logs -f web

# Faqat Celery worker logs:
docker-compose logs -f celery

# Faqat Telegram bot logs:
docker-compose logs -f auth_bot

# Oxirgi 100 satr logs:
docker-compose logs -f --tail=100
```

---

## 9. Containers'ga Kirib Debugging

```bash
# Django container'ga kirib terminal ochish
docker-compose exec web bash

# Ichida Python REPL:
python manage.py shell

# SQL bilan database'ga ulanish:
docker-compose exec db psql -U pharmacy_user -d pharmacy_db
```

---

## 10. Services'ni To'xtatish

```bash
# Barcha containers'ni to'xtatish (data saqlanib qoladi)
docker-compose down

# Barcha containers va volumes'ni o'chirish (DATA OCHIRILADI!)
docker-compose down -v

# Faqat web service'ni restart qilish:
docker-compose restart web
```

---

## 11. Containers'ning Holati

```bash
# Barcha containers'ning holatini ko'rish
docker-compose ps

# Container'ning resource ishlatishini ko'rish
docker stats

# Container'ning detailed info:
docker-compose ps web
```

---

## 12. Rebuild va Clean Setup

Agar xato bo'lsa yoki yangi start qilmoqchi bo'lsangiz:

```bash
# Barcha o'chirib yangi qayta build qilish
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d

# Migrations:
docker-compose exec web python manage.py migrate

# Superuser:
docker-compose exec web python manage.py createsuperuser
```

---

## 13. Häl qilish Uchun Common Masalalar

### 13.1 "Port 8000 already in use"
```bash
# Port'ni ozgartirish docker-compose.yml'da:
ports:
  - "8001:8000"  # 8000'ni 8001'ga o'zgartirish
```

### 13.2 "Database connection refused"
```bash
# Database'ning ishlayotganini tekshiring:
docker-compose logs db

# Database health check:
docker-compose exec db pg_isready -U pharmacy_user
```

### 13.3 "Static files not found"
```bash
# Static files'larni qayta collect qilish:
docker-compose exec web python manage.py collectstatic --noinput --clear
```

### 13.4 "Redis connection error"
```bash
# Redis'ning ishlayotganini tekshirish:
docker-compose exec redis redis-cli ping
```

### 13.5 "Celery tasks not running"
```bash
# Celery worker'ning logs'ni tekshiring:
docker-compose logs -f celery

# Redis'ga ulanishni tekshirish:
docker-compose exec redis redis-cli INFO
```

---

## 14. Monitoring va Debugging Tools

### Grafana Dashboard
```
URL: http://localhost:3000
Username: admin
Password: admin

Bu yerda:
- Django app performance
- CPU va Memory usage
- Request patterns
- Error rates
```

### Prometheus
```
URL: http://localhost:9090
Metrics: Django, Celery, PostgreSQL, Redis
```

### Django Admin Panel
```
URL: http://localhost:8000/admin
Username: (superuser nomingiz)
Password: (superuser parolingiz)
```

---

## 15. Production'da Deploy (AWS EC2)

```bash
# 1. SSH orqali EC2'ga ulanish
ssh -i your-key.pem ubuntu@your-ec2-ip

# 2. Repository'ni klonlash
git clone https://github.com/your-username/OnlinePharmacy.git
cd OnlinePharmacy

# 3. .env.prod fayl yaratish
nano .env.prod
# (.env.prod ma'lumotlarini to'ldirish)

# 4. Docker o'rnatish (agar o'rnatilmagan bo'lsa)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 5. Docker Compose o'rnatish
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 6. Production'da build va run
sudo docker-compose --env-file .env.prod build
sudo docker-compose --env-file .env.prod up -d

# 7. SSL sertifikat o'rnatish (Let's Encrypt)
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --standalone -d yourdomain.com

# 8. Nginx konfiguratsiyasi SSL bilan (nginx.conf'da)
# SSL sertifikat o'rnatish va reverse proxy konfiguratsiyasi
```

---

## 16. Fayllar Tuzilishi

```
OnlinePharmacy/
├── docker-compose.yml          ← Main orchestration file
├── Dockerfile                  ← Django app container tarifnomasi
├── .env.example               ← Environment variables template
├── .env                       ← Your actual .env (git'da yo'q)
├── .env.prod                  ← Production environment
├── requirements.txt           ← Python dependencies
├── requirements-dev.txt       ← Development dependencies
├── manage.py                  ← Django command line
├── config/                    ← Django settings
│   ├── settings.py           ← Main settings
│   ├── wsgi.py               ← WSGI server entry
│   ├── asgi.py               ← ASGI server entry
│   └── celery.py             ← Celery configuration
├── dashboard/                 ← Admin panel
├── pharmacy/                  ← Medicine catalog
├── users/                     ← User management
├── orders/                    ← Order management
├── billing/                   ← Payment handling
├── security/                  ← Security & audit
├── static/                    ← CSS, JS, images
├── media/                     ← User uploads
├── logs/                      ← Log files
├── telegram_bot/             ← Telegram bot service
│   └── runbot1.py           ← Bot entry point
├── prometheus.yml            ← Prometheus config
├── nginx/                    ← Nginx configuration
│   ├── nginx.dev.conf       ← Development config
│   └── nginx.conf           ← Production config
└── certs/                    ← SSL certificates (production)
```

---

## 17. Quick Reference Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Access database
docker-compose exec db psql -U pharmacy_user -d pharmacy_db

# Access Django shell
docker-compose exec web python manage.py shell

# Run tests
docker-compose exec web pytest

# Check service status
docker-compose ps

# Rebuild specific service
docker-compose build --no-cache web

# View Docker images
docker images

# Remove unused images
docker image prune -a

# View containers
docker ps -a

# Access container shell
docker-compose exec web bash

# View real-time resource usage
docker stats
```

---

## 18. Health Checks

```bash
# Django app health
curl http://localhost:8000/

# Database health
docker-compose exec db pg_isready -U pharmacy_user

# Redis health
docker-compose exec redis redis-cli ping

# Celery workers status
docker-compose exec celery celery -A config inspect active

# View all active tasks
docker-compose exec celery celery -A config inspect active
```

---

## Done! ✅

Endi Docker setup'ingiz tayyor! Savollar bo'lsa, logs'ni ko'rib hal qiling yoki `docker-compose logs -f` buyrug'idan foydalaning.

**Qo'shimcha yordam:**
- Django docs: https://docs.djangoproject.com/
- Docker docs: https://docs.docker.com/
- Docker Compose: https://docs.docker.com/compose/
