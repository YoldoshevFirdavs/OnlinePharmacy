# Architecture Overview

## Table of Contents
1. [Project Structure](#project-structure)
2. [Django Apps Architecture](#django-apps-architecture)
3. [Data Models & Relationships](#data-models--relationships)
4. [API Design](#api-design)
5. [Authentication & Authorization](#authentication--authorization)
6. [Undo & Audit System](#undo--audit-system)
7. [Error Handling](#error-handling)
8. [Scalability Considerations](#scalability-considerations)

---

## Project Structure

```
OnlinePharmacy/
├── config/                          # Django configuration
│   ├── settings.py                 # Settings (dev/prod)
│   ├── urls.py                     # URL routing
│   ├── wsgi.py                     # WSGI application
│   ├── asgi.py                     # ASGI for async
│   ├── celery.py                   # Celery configuration
│   ├── email_config.py             # Email backend config
│   └── middleware.py               # Custom middleware
│
├── users/                           # User management & authentication
│   ├── models.py                   # CustomUser, Seller, DeliveryDriver
│   ├── serializers.py              # DRF serializers
│   ├── views.py                    # API views
│   ├── permissions.py              # Custom permissions
│   └── tasks.py                    # Celery tasks (email, OTP)
│
├── pharmacy/                        # Medicine catalog
│   ├── models/
│   │   ├── medicine.py            # Medicine, Category, MedicineImage
│   │   ├── comments.py            # ProductComment, CommentLike, CommentAnalysis
│   │   ├── misc.py                # Seller ratings, SiteConfiguration
│   │   └── history.py             # CustomerUserHistory (audit log)
│   ├── views/
│   │   ├── detail.py              # Product detail view
│   │   ├── list.py                # Product listing/search
│   │   └── filters.py             # Advanced filtering
│   ├── serializers/               # Model serializers
│   ├── templatetags/              # Django template tags
│   └── context_processors.py      # Template context
│
├── orders/                          # Order management
│   ├── models.py                   # Order, OrderItem, Cart, DeliveryOrder
│   ├── serializers.py              # Order serializers
│   ├── views.py                    # Order endpoints
│   └── permissions.py              # Order access controls
│
├── billing/                         # Payment processing
│   ├── models.py                   # Payment model
│   ├── views.py                    # Stripe checkout, webhooks
│   ├── serializers.py              # Payment serializers
│   └── urls.py                     # Payment URLs
│
├── payments/                        # Driver payroll
│   ├── models.py                   # Salary model
│   ├── views.py                    # Salary management
│   └── serializers.py              # Salary serializers
│
├── security/                        # Audit, logging, bans
│   ├── models.py                   # AuditLog, UndoLog, BanRecord
│   ├── views.py                    # Admin restore endpoints
│   ├── middleware.py               # Ban checking middleware
│   └── permissions.py              # Ban-aware permissions
│
├── dashboard/                       # Admin dashboard
│   ├── views.py                    # Dashboard HTML views
│   ├── api_admin.py                # Admin API endpoints
│   ├── api_admin_orders.py         # Order management
│   ├── api_admin_undo.py           # Undo/restore operations
│   ├── api_stats.py                # Analytics/stats
│   ├── permissions.py              # Admin-only checks
│   └── forms.py                    # HTML form definitions
│
├── telegram_bot/                    # Telegram bot integration
│   ├── models.py                   # TelegrambotUser, OrderNotification
│   ├── handlers.py                 # Bot message handlers
│   ├── views.py                    # Telegram webhook endpoint
│   └── tasks.py                    # Celery bot tasks
│
├── static/                          # Static assets
│   ├── css/                        # Stylesheets
│   ├── js/                         # JavaScript
│   ├── images/                     # Image assets
│   │   └── default/               # Default fallback images
│   └── vendor/                     # Third-party libraries
│
├── templates/                       # Django HTML templates
│   ├── admin/                      # Admin templates
│   ├── auth/                       # Login/signup templates
│   ├── base.html                   # Base template
│   └── ...
│
├── nginx/                           # Nginx configuration
│   ├── nginx.conf                  # Development config
│   └── nginx.prod.conf             # Production config
│
├── grafana/                         # Monitoring dashboards
│   ├── dashboards/                 # Dashboard JSON files
│   └── provisioning/               # Auto-provisioning configs
│
├── docker-compose.yml              # Local dev container setup
├── docker-compose.prod.yml         # Production container setup
├── Dockerfile                       # Container image definition
├── prometheus.yml                  # Prometheus metrics config
├── requirements.txt                # Production dependencies
├── requirements-dev.txt            # Development dependencies
├── .github/workflows/ci.yml        # GitHub Actions CI/CD
├── pytest.ini                      # Pytest configuration
├── pyproject.toml                  # Project metadata (black, isort)
└── manage.py                       # Django management CLI
```

---

## Django Apps Architecture

### 1. Users App — Authentication & Profiles

**Purpose:** Manage user identity, authentication, and role-based access.

**Key Models:**
- `CustomUser` — Phone-first auth with multi-role support (user, seller, admin)
- `Seller` — Shop owner profile with ratings and commission tracking
- `DeliveryDriver` — Logistics partner profile with vehicle info
- `TelegrambotUser` — Telegram bot user mapping
- `AdminLoginToken` — Secure admin login tokens
- `AdminLoginAttempt` — Failed login attempt tracking

**Auth Flow:**
```
Phone/Email + OTP → CustomUser created → JWT token issued → Refresh token in cache
     ↓
  Phone validation (E164)
     ↓
  Email verification optional
     ↓
  Telegram ID linking optional
```

**Key Endpoints:**
- `POST /api/v1/auth/register/` — Phone registration
- `POST /api/v1/auth/login/` — Authenticate and get JWT
- `POST /api/v1/auth/refresh/` — Refresh token
- `GET /api/v1/profile/` — User profile
- `PATCH /api/v1/profile/` — Update profile

---

### 2. Pharmacy App — Product Catalog

**Purpose:** Manage medicine inventory, search, and user interactions.

**Key Models:**
- `Medicine` — Product with inventory, pricing, seller
- `Category` — Hierarchical taxonomy (parent/child)
- `ProductComment` — Threaded comments with AI moderation
- `CommentLike` — Emoji reactions on comments
- `MedicineImage` — Product gallery
- `CustomerUserHistory` — Immutable audit log of user actions

**Search & Filtering:**
```python
# Full-text search (icontains, can be upgraded to PostgreSQL FTS)
medicines = Medicine.objects.search("aspirin").available()

# Filtering
medicines = Medicine.objects.filter(
    category__slug="pain-relief",
    price__gte=10,
    price__lte=100,
    is_active=True
)

# Aggregation
avg_rating = Medicine.objects.values('category').annotate(
    avg=Avg('average_rating')
)
```

**Key Endpoints:**
- `GET /api/v1/medicines/` — Product listing
- `GET /api/v1/medicines/{id}/` — Product detail
- `POST /api/v1/medicines/{id}/comments/` — Post comment
- `POST /api/v1/medicines/{id}/comments/{cid}/reactions/` — React to comment
- `GET /api/v1/categories/` — Category tree

---

### 3. Orders App — Purchase Workflow

**Purpose:** Manage shopping cart and order lifecycle.

**Key Models:**
- `Cart` — User's shopping cart (OneToOne)
- `CartItem` — Items in cart
- `Order` — Purchase order with delivery info
- `OrderItem` — Line items with captured prices
- `DeliveryOrder` — Assignment to delivery driver

**Order Lifecycle:**
```
Cart Items → Checkout → Order created (Pending)
              ↓
         Payment method?
         ├─ Cash → Wait for driver
         └─ Card → Stripe checkout → Payment webhook
              ↓
         Order status: Delivered
              ↓
         Payment status: Paid
```

**Key Endpoints:**
- `POST /api/v1/cart/items/` — Add to cart
- `DELETE /api/v1/cart/items/{id}/` — Remove from cart
- `POST /api/v1/orders/` — Create order
- `GET /api/v1/orders/{id}/` — Order details
- `PATCH /api/v1/orders/{id}/cancel/` — Cancel order

---

### 4. Security App — Audit & Access Control

**Purpose:** Track all administrative actions and enforce bans.

**Key Models:**
- `AuditLog` — Immutable append-only log of admin actions
- `UndoLog` — 24-hour restore window for deleted items
- `BanRecord` — IP/fingerprint/user bans with smart matching

**Undo Mechanism:**

```python
# When deleting an item
@transaction.atomic()
def delete_order(order_id):
    order = Order.objects.get(id=order_id)
    UndoLog.create_for_delete(order, 'order', deleted_by=request.user)
    order.delete()
    AuditLog.objects.create(
        user=request.user,
        action='order_deleted',
        target_type='order',
        target_id=order_id
    )

# Restoring deleted item
@transaction.atomic()
def restore_order(undo_log_id):
    log = UndoLog.objects.select_for_update().get(id=undo_log_id)
    if log.is_expired() or log.is_restored:
        raise ValueError("Cannot restore")
    
    # Recreate from JSON
    Order.objects.create(**log.deleted_data)
    log.is_restored = True
    log.save()
```

**Ban System:**

```python
# Smart ban matching
ban = BanRecord.get_active_ban(ip="192.168.1.1")
# Checks:
# 1. Direct IP ban
# 2. Devices historically used from this IP
# 3. Users associated with this IP

# Banning a user
BanRecord.objects.create(
    user=user,
    reason="Abusive behavior",
    ban_type="temporary",
    expires_at=timezone.now() + timedelta(hours=24),
    source="admin"
)
```

---

## Data Models & Relationships

### Entity-Relationship Diagram

```
CustomUser (auth center)
    ├─ OneToOne → Seller
    ├─ OneToOne → DeliveryDriver
    ├─ ForeignKey → Order (one user, many orders)
    ├─ ForeignKey → ProductComment (one user, many comments)
    ├─ ForeignKey → AuditLog (who performed action)
    └─ ForeignKey → BanRecord (who can be banned)

Seller
    ├─ OneToOne ← CustomUser
    ├─ ForeignKey ← Medicine (one seller, many medicines)
    └─ ForeignKey ← DeliveryOrder (seller's inventory)

Medicine (product)
    ├─ ForeignKey → Category (many medicines in one category)
    ├─ ForeignKey → Seller
    ├─ OneToMany → MedicineImage (gallery)
    ├─ OneToMany → ProductComment (threaded comments)
    ├─ OneToMany → OrderItem (in orders)
    └─ OneToMany → CartItem (in carts)

Order
    ├─ ForeignKey → CustomUser
    ├─ OneToMany → OrderItem (line items)
    ├─ OneToMany → Payment (payment records)
    └─ OneToMany → DeliveryOrder (assigned driver)
```

### Indexes Strategy

**High-Priority Indexes:**
- `User.phone_number` (unique, authentication hot-path)
- `CustomUser.is_banned` (ban checks on every request)
- `Order.status` (filtering by order state)
- `ProductComment.product, -created_at` (nested comment queries)
- `UndoLog.restore_until, is_restored` (24-hour window lookups)
- `BanRecord.ip, is_active` (ban lookups by IP)

**Composite Indexes:**
- `(user, -created_at)` on Order (user's order history)
- `(product, -created_at)` on ProductComment (product's comments)
- `(is_active, expires_at)` on BanRecord (active temporary bans)

---

## API Design

### RESTful Conventions

```
GET    /api/v1/medicines/              → List (with pagination)
POST   /api/v1/medicines/              → Create (admin only)
GET    /api/v1/medicines/{id}/         → Retrieve
PATCH  /api/v1/medicines/{id}/         → Partial update
DELETE /api/v1/medicines/{id}/         → Delete (soft delete)

GET    /api/v1/orders/                 → List user's orders
POST   /api/v1/orders/                 → Create order
GET    /api/v1/orders/{id}/            → Order detail
PATCH  /api/v1/orders/{id}/            → Modify (status, etc.)
```

### Pagination

```python
# Default: 20 items per page, configurable via query param
GET /api/v1/medicines/?page=1&page_size=50

# Response format
{
    "count": 1250,
    "next": "http://.../medicines/?page=2",
    "previous": null,
    "results": [...]
}
```

### Filtering & Search

```
GET /api/v1/medicines/?search=aspirin&category=pain-relief&price_min=10&price_max=100
GET /api/v1/orders/?status=delivered&date_after=2026-08-01
```

### Response Format

**Success (200):**
```json
{
    "id": 123,
    "name": "Aspirin",
    "price": 15.99,
    "created_at": "2026-08-24T10:30:00Z"
}
```

**Error (400, 401, 404, 500):**
```json
{
    "error": "InvalidRequest",
    "message": "Missing required field: email",
    "code": "MISSING_FIELD",
    "details": {
        "field": "email",
        "expected_type": "string"
    }
}
```

---

## Authentication & Authorization

### JWT Token Flow

```
1. POST /api/v1/auth/login/
   ├─ Phone + OTP
   ├─ Verify OTP (time-based, 5-minute window)
   └─ Return access + refresh tokens

2. Client stores tokens (access in memory, refresh in httpOnly cookie)

3. Include token in requests:
   Authorization: Bearer <access_token>

4. Token expires → use refresh token
   POST /api/v1/auth/refresh/
   └─ Return new access token

5. Refresh token expires or revoked → re-login required
```

### Permission Classes

```python
# DRF permission system
class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user or request.method in ['GET', 'HEAD']

# Usage in views
class OrderDetail(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
```

### Role-Based Access Control

```python
# Admin-only endpoints
class AdminOrderList(APIView):
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        orders = Order.objects.all()
        return Response(OrderSerializer(orders, many=True).data)

# Seller-specific endpoints
class SellerMedicineList(APIView):
    permission_classes = [IsAuthenticated, IsSellerUser]
    
    def get(self, request):
        medicines = Medicine.objects.filter(seller__user=request.user)
        return Response(MedicineSerializer(medicines, many=True).data)
```

---

## Undo & Audit System

### Design Principles

1. **Immutability**: AuditLog and CustomerUserHistory cannot be updated/deleted
2. **Atomicity**: All-or-nothing operations with `transaction.atomic()`
3. **Locking**: Use `select_for_update()` to prevent race conditions
4. **Time Window**: 24-hour restore window for safety

### Implementation

```python
# Undo mechanism in action
@transaction.atomic()
def delete_and_log(model_instance, model_name, user):
    # 1. Create undo log BEFORE deletion
    undo_log = UndoLog.create_for_delete(
        model_instance, 
        model_name, 
        deleted_by=user
    )
    
    # 2. Delete the item
    model_instance.delete()
    
    # 3. Create audit record
    AuditLog.objects.create(
        user=user,
        action=f"{model_name}_deleted",
        target_type=model_name,
        target_id=model_instance.id
    )
    
    return undo_log

# Restoring within 24 hours
@transaction.atomic()
def restore_item(undo_log_id, user):
    log = UndoLog.objects.select_for_update().get(id=undo_log_id)
    
    # Check conditions
    if log.is_expired():
        raise ValueError("Restore window expired")
    if log.is_restored:
        raise ValueError("Already restored")
    
    # Recreate object
    if log.item_type == "medicine":
        Medicine.objects.create(**log.deleted_data)
    
    # Mark as restored
    log.is_restored = True
    log.restored_at = timezone.now()
    log.save()
    
    # Audit the restore
    AuditLog.objects.create(
        user=user,
        action="item_restored",
        target_type=log.item_type,
        target_id=log.item_id
    )
```

---

## Error Handling

### Global Exception Handler

```python
# config/middleware.py
class CustomErrorMiddleware:
    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except ValidationError as e:
            return JsonResponse({
                "error": "ValidationError",
                "message": str(e),
                "details": e.detail if hasattr(e, 'detail') else None
            }, status=400)
        except PermissionDenied:
            return JsonResponse({
                "error": "PermissionDenied",
                "message": "You don't have permission"
            }, status=403)
        except Exception as e:
            logger.error(f"Unhandled error: {e}", exc_info=True)
            return JsonResponse({
                "error": "InternalServerError",
                "message": "An unexpected error occurred"
            }, status=500)
```

---

## Scalability Considerations

### Current Bottlenecks & Solutions

| Bottleneck | Current | Solution |
|-----------|---------|----------|
| Search | icontains (slow with millions) | PostgreSQL Full-Text Search or Elasticsearch |
| Image processing | Synchronous | Celery async tasks with PIL |
| Reports generation | In-memory | Async Celery tasks with streaming |
| Real-time notifications | Polling | WebSockets + Redis channel layer |
| Database connections | Default pool | pgBouncer (connection pooling) |

### Horizontal Scaling

```
Load Balancer (Nginx)
    ├─ Django App 1 (gunicorn)
    ├─ Django App 2 (gunicorn)
    └─ Django App 3 (gunicorn)
         ↓
    Shared PostgreSQL (read replicas)
    Shared Redis (cluster)
    Shared Celery queue
```

### Caching Strategy

```python
# Cache frequently accessed data
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "pharmacy",
        "TIMEOUT": 900,  # 15 minutes
    }
}

# Cache product catalog
@cache_page(600)  # 10 minutes
def medicine_list(request):
    ...

# Cache computed metrics
from django.views.decorators.cache import cache_page

@cache_page(3600)  # 1 hour
def dashboard_stats(request):
    ...
```

---

## Summary

OnlinePharmacy architecture:

- **Django Monolith** with feature-based apps
- **Phone-first authentication** with JWT tokens
- **Marketplace model** (users, sellers, drivers)
- **Immutable audit logs** for compliance
- **24-hour undo window** for safe restoration
- **Multi-level ban system** for abuse prevention
- **Async task processing** with Celery
- **Comprehensive monitoring** with Prometheus/Grafana
- **Production-ready** with Docker, Nginx, PostgreSQL
