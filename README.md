# Online Pharmacy - E-Commerce Platform

Pharmaceutical e-commerce platform built with Django, PostgreSQL, and Docker.

## Features
- ✓ User authentication (JWT + OTP)
- ✓ Product catalog with search & filters
- ✓ Shopping cart & orders
- ✓ Admin analytics dashboard
- ✓ Celery background tasks (email)
- ✓ Redis caching
- ✓ Docker containerization
- ✓ AWS EC2 deployment ready

## Tech Stack
- **Backend**: Django 5.1, Django REST Framework
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Task Queue**: Celery with Redis broker
- **API Docs**: Swagger/OpenAPI
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Deployment**: Docker, Nginx, Gunicorn
- **Cloud**: AWS EC2 (Ubuntu 22.04)

## Project Structure
```
online-pharmacy/
├── config/              # Django settings
│   ├── settings.py      # Development
│   ├── settings_prod.py # Production
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── users/               # Authentication
│   ├── models.py        # CustomUser
│   ├── views.py         # Registration, Login
│   ├── otp_service.py   # OTP logic
│   └── tests.py
├── pharmacy/            # Products
│   ├── models.py        # Product, Category
│   ├── views.py         # Product API
│   └── serializers.py
├── orders/              # Shopping
│   ├── models.py        # Order, OrderItem
│   └── views.py         # Order API
├── frontend/            # UI
│   ├── html/            # HTML templates
│   ├── css/             # Stylesheets
│   └── js/              # JavaScript
├── docker-compose.yml   # Development
├── docker-compose.prod.yml # Production
├── Dockerfile
├── nginx.conf
├── requirements.txt
└── manage.py
```

## Quick Start

### Development
```bash
# Clone repo
git clone https://github.com/yourusername/online-pharmacy.git
cd online-pharmacy

# Create .env
cp .env.example .env

# Start containers
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Access app
http://localhost:8000
http://localhost:8000/api/v1/  (Swagger)
```

### Production (AWS EC2)
See [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md)

## API Endpoints

### Authentication
```
POST   /api/v1/users/register/       - Register user
POST   /api/v1/users/login/          - Login with credentials
POST   /api/v1/users/verify-otp/     - Verify OTP code
POST   /api/v1/token/refresh/        - Refresh JWT token
GET    /api/v1/users/me/             - Get current user
PATCH  /api/v1/users/me/             - Update profile
```

### Products
```
GET    /api/v1/pharmacy/products/    - List products
GET    /api/v1/pharmacy/products/{id}/ - Get product detail
GET    /api/v1/pharmacy/categories/  - List categories
```

### Orders
```
POST   /api/v1/orders/create/        - Create order
GET    /api/v1/orders/               - List user's orders
GET    /api/v1/orders/{id}/          - Get order detail
PATCH  /api/v1/orders/{id}/          - Update order status
```

## Environment Variables (.env)
```
# Django
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,localhost

# Database
DB_NAME=pharmacy
DB_USER=postgres
DB_PASSWORD=strong-password
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your@gmail.com
EMAIL_HOST_PASSWORD=app-password

# JWT
JWT_SECRET=your-jwt-secret

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
```

## Database Models

### Users
```python
- id (UUID)
- email (unique)
- phone (optional)
- password (hashed)
- full_name
- is_staff
- is_active
- created_at
```

### Products
```python
- id
- name
- description
- price
- stock
- category (FK)
- image
- created_at
```

### Orders
```python
- id
- user (FK)
- items (M2M)
- total_price
- status (pending/confirmed/delivered)
- created_at
```

## Testing
```bash
# Run all tests
docker-compose exec web python manage.py test

# Run specific app
docker-compose exec web python manage.py test users

# With coverage
docker-compose exec web coverage run --source='.' manage.py test
docker-compose exec web coverage report
```

## Deployment Checklist
- [ ] SECRET_KEY changed
- [ ] DEBUG=False
- [ ] ALLOWED_HOSTS configured
- [ ] Database created & migrated
- [ ] Superuser created
- [ ] Static files collected
- [ ] Email configured
- [ ] Celery workers running
- [ ] Redis cache working
- [ ] SSL certificate installed
- [ ] Nginx proxy configured

## Monitoring
```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f web

# Check container status
docker-compose -f docker-compose.prod.yml ps

# Database backups
docker-compose exec db pg_dump -U postgres pharmacy > backup.sql
```

## Common Issues

### Database connection error
```bash
# Check if db container is healthy
docker-compose logs db
# Ensure DB_HOST=db in .env
```

### Static files not loading
```bash
docker-compose exec web python manage.py collectstatic --noinput
```

### Celery not sending emails
```bash
# Check Redis connection
docker-compose logs celery
# Verify EMAIL settings in .env
```

### CORS errors
```bash
# Update CORS_ALLOWED_ORIGINS in .env
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
```

## Performance Tips
- Database indexing on frequently queried fields
- Redis caching for product lists
- Celery for email sending (async)
- Nginx gzip compression
- CSS/JS minification
- Database connection pooling

## Security
- JWT token expiry: 1 hour
- Refresh token expiry: 7 days
- OTP expiry: 10 minutes
- Password hashing: PBKDF2
- SQL injection protection: ORM parameterized queries
- CSRF protection: Django middleware
- XSS protection: Django template escaping
- Rate limiting: 100 req/hour (anon), 1000 req/hour (user)

## Contributing
1. Fork the repo
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

## License
MIT License - See LICENSE.md

## Contact
- Author: Yoldashev Firdavs
- Email: firdavs@example.com
- GitHub: @firdavs_yoldashev

## Acknowledgments
- Mentor: Komiljon Hamidjonov
- Django & DRF community
- Swagger for API documentation

---
**Last Updated**: June 2026
**Version**: 1.0.0 (Production)