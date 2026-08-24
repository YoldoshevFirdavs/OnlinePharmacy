# Database Architecture & Design

## Table of Contents
1. [PostgreSQL Configuration](#postgresql-configuration)
2. [Core Models & Relationships](#core-models--relationships)
3. [Query Optimization](#query-optimization)
4. [Indexes & Performance](#indexes--performance)
5. [Migration Strategy](#migration-strategy)
6. [Data Integrity](#data-integrity)
7. [Backup & Recovery](#backup--recovery)

---

## PostgreSQL Configuration

The OnlinePharmacy project uses **PostgreSQL 13+** as the primary database with connection pooling and containerization via Docker.

### Connection Settings

Configure via environment variables (`.env`):

```env
# Database credentials
DB_NAME=pharmacy_db
DB_USER=pharmacy_admin
DB_PASSWORD=secure_password_here
DB_HOST=db                    # Docker service name
DB_PORT=5432
```

### Django Settings

```python
# config/settings.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "pharmacy_db"),
        "USER": os.getenv("DB_USER", "pharmacy_admin"),
        "PASSWORD": os.getenv("DB_PASSWORD", "root"),
        "HOST": os.getenv("DB_HOST", "db"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "TEST": {
            "NAME": "test_" + os.getenv("DB_NAME", "pharmacy_db"),
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"  # 64-bit IDs for scalability
```

### Docker Setup

The `docker-compose.yml` includes a PostgreSQL service:

```yaml
services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
```

**Production deployment** uses `.env.prod` with:
- Strong passwords (12+ characters with special chars)
- SSL/TLS connection encryption (SSLMODE=require)
- Read replicas for scaling
- Automated backups to S3/GCS

---

## Core Models & Relationships

### 1. Users App (`users/models.py`)

#### CustomUser (Authentication Core)

**Purpose:** Custom user model with phone-first authentication, multi-role support, and sophisticated ban management.

**Key Fields:**

```python
class CustomUser(AbstractBaseUser, PermissionsMixin):
    # Authentication identifiers
    phone_number = CharField(max_length=32, unique=True, null=True, blank=True)
    email = EmailField(unique=True, null=True, blank=True)
    telegram_id = CharField(max_length=255, unique=True, null=True, blank=True)
    auth_code = CharField(max_length=64, null=True, blank=True)  # OTP
    is_verified = BooleanField(default=False)

    # Profile information
    full_name = CharField(max_length=255, blank=True)
    address = CharField(max_length=255, blank=True)
    avatar = ImageField(upload_to="users_profile_avatars/", blank=True, null=True)

    # Status fields
    is_active = BooleanField(default=True)
    is_staff = BooleanField(default=False)
    is_superuser = BooleanField(default=False)
    role = CharField(max_length=10, choices=USER_ROLE_CHOICES, default="user")
    
    # Ban system (multi-page & multi-duration)
    is_banned = BooleanField(default=False)  # Telegram login permanent ban
    banned_for = CharField(max_length=255, blank=True, null=True)  # Page-specific
    ban_reason = CharField(max_length=500, blank=True, null=True)
    ban_until = DateTimeField(blank=True, null=True)  # Temporary ban expiry
    is_permanent_ban = BooleanField(default=False)
    banned_by = ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    # Statistics
    bad_comments_count = PositiveIntegerField(default=0)
    date_joined = DateTimeField(default=timezone.now)

    objects = CustomUserManager()
    USERNAME_FIELD = "email"  # or "phone_number"
```

**Methods:**

```python
@property
def get_avatar_url(self):
    """Returns avatar URL or default static image"""
    if self.avatar:
        return self.avatar.url
    return "/static/images/default/default_avatar.png"

def clean_phone_number(self):
    """Validate and normalize phone to E164 format"""
    if self.phone_number:
        parsed = phonenumbers.parse(self.phone_number, 'UZ')
        if phonenumbers.is_valid_number(parsed):
            self.phone_number = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)

def is_active_ban(self, page: str = None) -> bool:
    """Check if user is currently banned for a specific page"""
    if page and self.banned_for != page:
        return False
    if self.is_permanent_ban and self.banned_for:
        return True
    if self.ban_until and timezone.now() < self.ban_until:
        return True
    return False

def ban_user(self, page: str, duration_seconds: int = None, reason: str = None, 
             banned_by=None, is_permanent: bool = False):
    """Ban user for specific page with optional duration"""
    self.banned_for = page
    self.ban_reason = reason
    self.banned_by = banned_by
    self.is_permanent_ban = is_permanent
    if is_permanent:
        self.ban_until = None
    elif duration_seconds:
        self.ban_until = timezone.now() + timedelta(seconds=duration_seconds)
    self.save()

def unban_user(self):
    """Remove ban"""
    self.banned_for = None
    self.ban_until = None
    self.ban_reason = None
    self.banned_by = None
    self.save()
```

**Indexes:**
- `phone_number` (unique, db_index)
- `email` (unique, db_index)
- `is_active` (db_index) — for filtering active users
- `role` (db_index) — for role-based queries

---

#### Seller (Marketplace)

**Purpose:** Shop owner profile linked to CustomUser.

```python
class Seller(models.Model):
    user = OneToOneField(CustomUser, on_delete=CASCADE)
    avatar = ImageField(upload_to="users_profile_avatars/", blank=True, null=True)
    shop_name = CharField(max_length=255)
    slug = SlugField(unique=True, null=True, blank=True)
    short_description = CharField(max_length=500, blank=True, null=True)
    description = TextField(blank=True, null=True)
    address = CharField(max_length=255, blank=True, null=True)
    
    # Legal info
    licence_number = CharField(max_length=255, blank=True, null=True)
    tax_id = CharField(max_length=20, blank=True, null=True)
    is_verified = BooleanField(default=False)
    
    # Statistics & payment
    rating = DecimalField(max_digits=3, decimal_places=2, default=0.00)
    balance = DecimalField(max_digits=12, decimal_places=2, default=0.00)
    sells_count = PositiveIntegerField(default=0)
    commission_rate = DecimalField(max_digits=5, decimal_places=2, default=10.00)
    
    # Payout info
    credit_card = CharField(max_length=16, blank=True, null=True)
    credit_card_expiry = CharField(max_length=5, blank=True, null=True)
    credit_card_holder = CharField(max_length=255, blank=True, null=True)
    
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    @property
    def get_avatar_url(self):
        if self.avatar and hasattr(self.avatar, "url"):
            return self.avatar.url
        return "/static/images/default/default_avatar.png"
```

**Indexes:**
- `slug` (unique, db_index)
- `is_verified` (db_index) — filter verified shops
- `created_at` (db_index) — ordering/pagination

---

#### DeliveryDriver (Logistics)

```python
class DeliveryDriver(models.Model):
    user = OneToOneField(CustomUser, on_delete=CASCADE, related_name="delivery_profile")
    phone_number = CharField(max_length=20, blank=True, null=True)
    vehicle_info = CharField(max_length=255, blank=True, null=True)
    status = CharField(max_length=50, choices=[("active", "Active"), ("inactive", "Inactive")], default="active")
    avatar = ImageField(upload_to="drivers/", blank=True, null=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

---

#### TelegrambotUser (Telegram Integration)

```python
class TelegrambotUser(models.Model):
    shop_user = ForeignKey(CustomUser, null=True, blank=True, on_delete=SET_NULL)
    telegram_id = BigIntegerField(unique=True, db_index=True)
    username = CharField(max_length=255, null=True, blank=True)
    first_name = CharField(max_length=255, null=True, blank=True)
    last_name = CharField(max_length=255, null=True, blank=True)
    phone_number = CharField(max_length=255, null=True, blank=True)
    
    # Bot state
    bot_status = CharField(max_length=50, null=True, blank=True)
    last_status = CharField(max_length=50, null=True, blank=True)
    is_active = BooleanField(default=True)
    is_banned = BooleanField(default=False)
    
    # Statistics
    pays_count = BigIntegerField(null=True, blank=True)
    total_cost = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    date_joined = DateTimeField(auto_now_add=True)
```

**Index:** `telegram_id` (unique, db_index) — fast Telegram user lookup

---

### 2. Pharmacy App (`pharmacy/models/`)

#### Medicine (Product Catalog)

**Purpose:** Medicine/product listing with inventory, ratings, and seller association.

```python
class Medicine(models.Model):
    name = CharField(max_length=255, db_index=True)
    slug = SlugField(unique=True, db_index=True)
    category = ForeignKey("Category", on_delete=PROTECT, related_name="medicines")
    
    # Pricing & Inventory
    price = DecimalField(max_digits=12, decimal_places=2)
    stock = PositiveIntegerField(default=0)
    is_active = BooleanField(default=True)
    seller = ForeignKey("users.Seller", on_delete=CASCADE, related_name="medicines", null=True, blank=True)
    
    # Content
    short_description = CharField(max_length=500)
    instruction = TextField()
    side_effects = TextField(blank=True)
    contraindications = TextField(blank=True)
    storage_conditions = CharField(max_length=255, blank=True)
    is_prescription_required = BooleanField(default=False)
    main_image = ImageField(upload_to="medicines/main/", null=True, blank=True)
    
    # Aggregated ratings
    average_rating = DecimalField(max_digits=3, decimal_places=2, default=0.00)
    reviews_count = PositiveIntegerField(default=0)
    
    updated_at = DateTimeField(auto_now=True)

    objects = MedicineManager()
    available = MedicineAvailableManager()  # is_active=True AND stock>0

    def reduce_stock(self, quantity):
        """Atomically reduce stock on order"""
        if quantity <= self.stock:
            self.stock -= quantity
            self.save(update_fields=["stock"])
            return True
        return False
```

**Managers:**

```python
class MedicineManager(models.Manager):
    def search(self, query):
        return self.filter(
            Q(name__icontains=query) | 
            Q(short_description__icontains=query)
        ).distinct()

class MedicineAvailableManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True, stock__gt=0)
    
    def search(self, query):
        return self.get_queryset().filter(
            Q(name__icontains=query) | 
            Q(short_description__icontains=query)
        ).distinct()
```

**Indexes:**
- `name` (db_index)
- `slug` (unique, db_index)
- `category` (db_index)
- `seller` (db_index)
- `is_active` (db_index)

---

#### Category (Taxonomy)

```python
class Category(models.Model):
    name = CharField(max_length=255)
    slug = SlugField(max_length=255, unique=True)
    parent = ForeignKey("self", on_delete=SET_NULL, null=True, blank=True, related_name="children")
    is_default = BooleanField(default=False)

    class Meta:
        ordering = ["name"]
```

**Index:** `slug` (unique, db_index)

**Hierarchy Example:**
```
Respiratory (parent=None)
├── Cough Syrups (parent=Respiratory)
└── Antihistamines (parent=Respiratory)
```

---

#### ProductComment (Threaded Comments)

**Purpose:** YouTube-style nested comments with AI toxicity detection and emoji reactions.

```python
class ProductComment(models.Model):
    product = ForeignKey(Medicine, on_delete=CASCADE, related_name="comments")
    user = ForeignKey(CustomUser, on_delete=CASCADE, related_name="product_comments")
    parent = ForeignKey("self", on_delete=CASCADE, null=True, blank=True, related_name="replies")
    
    content = TextField()
    rating = PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    
    # Moderation
    is_approved = BooleanField(default=True)
    is_ai_checked = BooleanField(default=False)
    ai_summary = TextField(blank=True)
    ai_toxicity_score = FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    
    likes_count = PositiveIntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True, db_index=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            Index(fields=["product", "-created_at"]),
            Index(fields=["user", "-created_at"]),
            Index(fields=["is_approved", "-created_at"]),
        ]

    def is_reply(self):
        return self.parent is not None
```

**Indexes:**
- `product, -created_at` — get comments for a medicine in chronological order
- `user, -created_at` — get user's comments
- `is_approved, -created_at` — moderation queue

---

#### CommentLike (Emoji Reactions)

```python
class CommentLike(models.Model):
    EMOJI_CHOICES = [("like", "👍"), ("heart", "❤️"), ("laugh", "😂"), ("wow", "😮"), ("sad", "😢"), ("angry", "😠")]
    
    comment = ForeignKey(ProductComment, on_delete=CASCADE, related_name="emoji_reactions")
    user = ForeignKey(CustomUser, on_delete=CASCADE, related_name="comment_reactions")
    emoji = CharField(max_length=10, choices=EMOJI_CHOICES)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("comment", "user", "emoji")  # One emoji per user per comment
```

---

#### CustomerUserHistory (Immutable Audit Log)

**Purpose:** Immutable audit trail of all user actions for analytics and compliance.

```python
class CustomerUserHistory(models.Model):
    ACTION_CHOICES = [
        ("view_product", "Mahsulot ko'rildi"),
        ("view_seller", "Sotuvchi ko'rildi"),
        ("add_to_cart", "Savatchaga qo'shildi"),
        ("comment_create", "Fikr qoldirildi"),
        ("order_create", "Buyurtma qilindi"),
    ]
    
    user = ForeignKey(CustomUser, on_delete=CASCADE, related_name="customer_history")
    product = ForeignKey(Medicine, on_delete=SET_NULL, null=True, blank=True, related_name="view_history")
    seller = ForeignKey("users.Seller", on_delete=SET_NULL, null=True, blank=True)
    action = CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)
    
    meta = JSONField(default=dict, blank=True)  # Additional data: comment_id, order_id
    timestamp = DateTimeField(auto_now_add=True, db_index=True)
    ip_address = GenericIPAddressField(null=True, blank=True)
    user_agent = TextField(blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            Index(fields=["user", "-timestamp"]),
            Index(fields=["action", "-timestamp"]),
            Index(fields=["product", "-timestamp"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("CustomerUserHistory records are immutable")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("CustomerUserHistory records cannot be deleted")
```

---

### 3. Orders App (`orders/models.py`)

#### Order & OrderItem

**Purpose:** Shopping cart checkout and order management.

```python
class Cart(models.Model):
    user = OneToOneField(CustomUser, on_delete=CASCADE, related_name="user_cart")
    created_at = DateTimeField(auto_now_add=True)

class CartItem(models.Model):
    cart = ForeignKey(Cart, on_delete=CASCADE, related_name="items")
    product = ForeignKey(Medicine, on_delete=CASCADE)
    quantity = PositiveIntegerField(default=1)

class Order(models.Model):
    STATUS_CHOICES = [("Pending", "Pending"), ("Processing", "Processing"), 
                      ("Delivered", "Delivered"), ("Canceled", "Canceled")]
    
    user = ForeignKey(CustomUser, on_delete=CASCADE, related_name="orders")
    total_price = DecimalField(max_digits=12, decimal_places=2)
    status = CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    address = TextField(blank=True, null=True)
    phone_number = CharField(max_length=20, blank=True, null=True)
    payment_method = CharField(max_length=20, choices=[("cash", "Naqd"), ("card", "Karta")], default="cash")
    created_at = DateTimeField(auto_now_add=True, db_index=True)
    delivered_at = DateTimeField(null=True, blank=True)

class OrderItem(models.Model):
    order = ForeignKey(Order, on_delete=CASCADE, related_name="order_items")
    product = ForeignKey(Medicine, on_delete=SET_NULL, null=True)
    quantity = PositiveIntegerField()
    price_at_order = DecimalField(max_digits=12, decimal_places=2)  # Capture price at order time
```

**Indexes:**
- `Order.user, -created_at` — user order history
- `Order.status` — filter by status
- `OrderItem.order` — retrieve order items

---

### 4. Security App (`security/models.py`)

#### AuditLog (Append-Only)

**Purpose:** Immutable audit trail of all admin actions.

```python
class AuditLog(models.Model):
    user = ForeignKey(CustomUser, on_delete=SET_NULL, null=True, blank=True, related_name="audit_logs")
    action = CharField(max_length=255)
    description = TextField(blank=True, null=True)
    ip_address = GenericIPAddressField(null=True, blank=True)
    target_type = CharField(max_length=64, blank=True, null=True, db_index=True)
    target_id = PositiveIntegerField(null=True, blank=True, db_index=True)
    meta = JSONField(default=dict, blank=True)
    timestamp = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def delete(self, *args, **kwargs):
        raise ValueError("AuditLog records are immutable")
```

**Index:** `(target_type, target_id)` — fast lookup of actions on specific objects

---

#### UndoLog (24-Hour Restore Window)

**Purpose:** Safely restore deleted items within 24 hours with transactional integrity.

```python
class UndoLog(models.Model):
    ITEM_TYPE_CHOICES = [("user", "User"), ("medicine", "Medicine"), ("order", "Order"), ...]
    
    item_type = CharField(max_length=20, choices=ITEM_TYPE_CHOICES)
    item_id = PositiveIntegerField()
    item_name = CharField(max_length=255)
    deleted_data = JSONField(default=dict)
    deleted_by = ForeignKey(CustomUser, on_delete=SET_NULL, null=True, related_name="deleted_items")
    deleted_at = DateTimeField(auto_now_add=True)
    
    is_restored = BooleanField(default=False)
    restored_at = DateTimeField(null=True, blank=True)
    restore_until = DateTimeField(db_index=True)  # 24 hours

    class Meta:
        ordering = ["-deleted_at"]
        indexes = [
            Index(fields=["restore_until", "is_restored"]),  # Find active/unexpired logs
        ]

    def restore(self):
        """Atomically restore with transactional lock"""
        with transaction.atomic():
            log = UndoLog.objects.select_for_update().get(pk=self.pk)
            if log.is_restored or log.is_expired():
                return False, "Cannot restore"
            
            # Recreate object based on item_type
            if self.item_type == "medicine":
                Medicine.objects.create(**log.deleted_data)
            # ... other types
            
            AuditLog.objects.create(user=log.deleted_by, action="undo_restore", ...)
            log.is_restored = True
            log.save()
            return True, "Restored"

    @classmethod
    def create_for_delete(cls, item, item_type, deleted_by=None):
        """Create undo log before deletion"""
        undo_log = cls.objects.create(
            item_type=item_type,
            item_id=item.id,
            item_name=str(item),
            deleted_data={...},  # Capture item state
            deleted_by=deleted_by,
            restore_until=timezone.now() + timedelta(hours=24),
        )
        return undo_log
```

---

#### BanRecord (Smart Multi-Level Ban)

**Purpose:** IP/fingerprint/user bans with smart graph-based matching.

```python
class BanRecord(models.Model):
    BAN_TYPE_CHOICES = [("temporary", "Temporary"), ("permanent", "Permanent")]
    SOURCE_CHOICES = [("system", "System"), ("admin", "Admin"), ("telegram", "Telegram")]
    
    # Identifiers
    ip = CharField(max_length=45, blank=True, null=True, db_index=True)
    fingerprint = CharField(max_length=255, blank=True, null=True, db_index=True)
    user = ForeignKey(CustomUser, on_delete=SET_NULL, null=True, blank=True)
    
    # Ban details
    reason = TextField()
    ban_type = CharField(max_length=20, choices=BAN_TYPE_CHOICES, default="temporary")
    source = CharField(max_length=50, choices=SOURCE_CHOICES, default="system")
    
    # Timestamps
    created_at = DateTimeField(auto_now_add=True, db_index=True)
    expires_at = DateTimeField(blank=True, null=True, db_index=True)
    is_active = BooleanField(default=True, db_index=True)
    
    # Metadata
    attempts = PositiveIntegerField(default=0)
    meta = JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            Index(fields=["ip", "is_active"]),
            Index(fields=["fingerprint", "is_active"]),
            Index(fields=["expires_at", "is_active"]),
        ]

    @classmethod
    def get_active_ban(cls, ip=None, fingerprint=None, user=None):
        """Smart matching: direct -> related device -> related user"""
        # 1. Check direct bans
        direct_ban = cls.objects.filter(
            is_active=True,
            expires_at__gt=timezone.now() if expires_at else True
        ).filter(
            Q(ip=ip) | Q(fingerprint=fingerprint) | Q(user=user)
        ).first()
        
        if direct_ban:
            return direct_ban
        
        # 2. Check related device bans (if one identifier banned, check related)
        if ip:
            related_bans = cls.objects.filter(
                is_active=True,
                fingerprint__in=BanRecord.objects.filter(ip=ip).values('fingerprint')
            ).first()
            if related_bans:
                return related_bans
        
        # 3. Check related user bans
        if user:
            user_ban = cls.objects.filter(
                is_active=True,
                user=user
            ).first()
            if user_ban:
                return user_ban
        
        return None

    def get_related_identifiers(self):
        """Get all IPs, fingerprints, users linked to this ban"""
        related = {"ips": set(), "fingerprints": set(), "users": set()}
        
        if self.ip:
            related["ips"].add(self.ip)
            related["fingerprints"].update(
                BanRecord.objects.filter(ip=self.ip).values_list("fingerprint", flat=True)
            )
        
        if self.fingerprint:
            related["fingerprints"].add(self.fingerprint)
            related["ips"].update(
                BanRecord.objects.filter(fingerprint=self.fingerprint).values_list("ip", flat=True)
            )
        
        if self.user_id:
            related["users"].add(self.user_id)
            related["ips"].update(
                BanRecord.objects.filter(user_id=self.user_id).values_list("ip", flat=True)
            )
        
        return related
```

---

## Query Optimization

### N+1 Query Prevention

Use `select_related()` for ForeignKey and OneToOne:

```python
# BAD: N+1 queries
medicines = Medicine.objects.all()
for medicine in medicines:
    print(medicine.category.name)  # Query per item

# GOOD: Single query
medicines = Medicine.objects.select_related("category", "seller")
```

### Pagination for Large Datasets

```python
from rest_framework.pagination import PageNumberPagination

class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
```

### Full-Text Search

Current implementation uses `icontains`:

```python
def search(self, query):
    return self.filter(
        Q(name__icontains=query) | 
        Q(short_description__icontains=query)
    ).distinct()
```

**Future: PostgreSQL Full-Text Search**

```python
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

# Index on create:
SearchVector("name", weight="A") + SearchVector("short_description", weight="B")

# Query:
medicines = Medicine.objects.annotate(
    rank=SearchRank(search_vector, query)
).order_by("-rank")
```

---

## Indexes & Performance

### Index Strategy

**Indexes created automatically:**
- Primary keys (BigAutoField)
- Foreign keys
- `unique=True` fields

**Custom indexes:**

```python
class Meta:
    indexes = [
        Index(fields=["user", "-timestamp"]),  # Composite index (most useful)
        Index(fields=["is_active", "-created_at"]),
        Index(fields=["status"]),  # Single-field for WHERE clauses
    ]
```

### Query Performance Monitoring

View slow queries in PostgreSQL logs:

```sql
-- Enable slow query logging
SET log_min_duration_statement = 100;  -- Milliseconds

-- Check indexes
SELECT * FROM pg_stat_user_indexes ORDER BY idx_blks_read DESC;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan 
FROM pg_stat_user_indexes 
WHERE idx_scan = 0  -- Unused indexes
ORDER BY pg_relation_size(indexrelid) DESC;
```

---

## Migration Strategy

### Creating Migrations

```bash
# Generate migration after model change
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Apply specific app migrations
python manage.py migrate users
```

### Best Practices

1. **Backward-compatible changes:**
   - Add new field with `null=True, blank=True`
   - Never remove fields in one migration
   
2. **Data migrations for transformations:**
   ```bash
   python manage.py makemigrations --empty users --name transform_phone_numbers
   ```

3. **Testing migrations:**
   ```bash
   python manage.py migrate --plan
   python manage.py sqlmigrate users 0001
   ```

4. **Reverting migrations:**
   ```bash
   python manage.py migrate users 0001  # Go back to 0001
   ```

---

## Data Integrity

### Transactional Consistency

Use Django's transaction management:

```python
from django.db import transaction

with transaction.atomic():
    order = Order.objects.create(user=user, total_price=100)
    for item in cart_items:
        OrderItem.objects.create(order=order, **item)
    cart.items.all().delete()
    # All succeed or all rollback
```

### Foreign Key Constraints

- `on_delete=CASCADE` — Delete child records when parent deleted
- `on_delete=PROTECT` — Prevent deletion if children exist
- `on_delete=SET_NULL` — Set FK to NULL when parent deleted

```python
category = ForeignKey("Category", on_delete=PROTECT)  # Prevents accidental deletion
product = ForeignKey(Medicine, on_delete=CASCADE)  # Cascade deletes with order
```

### Unique Constraints

```python
class CommentLike(models.Model):
    class Meta:
        unique_together = ("comment", "user", "emoji")  # One emoji per user per comment
```

---

## Backup & Recovery

### Docker Backup

```bash
# Backup database
docker exec pharmacy_db pg_dump -U pharmacy_admin pharmacy_db > backup.sql

# Restore database
docker exec -i pharmacy_db psql -U pharmacy_admin pharmacy_db < backup.sql
```

### Production Backup Strategy

**Automated daily backups to AWS S3:**

```bash
# In crontab (runs daily at 2 AM)
0 2 * * * /scripts/backup_to_s3.sh
```

**Backup script:**

```bash
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="pharmacy_db_${TIMESTAMP}.sql.gz"

docker exec pharmacy_db pg_dump -U pharmacy_admin pharmacy_db | gzip > /tmp/${BACKUP_FILE}
aws s3 cp /tmp/${BACKUP_FILE} s3://my-backups/pharmacy/${BACKUP_FILE}
rm /tmp/${BACKUP_FILE}
```

### Disaster Recovery

```bash
# List recent backups
aws s3 ls s3://my-backups/pharmacy/

# Download and restore
aws s3 cp s3://my-backups/pharmacy/pharmacy_db_20260824_020000.sql.gz .
gunzip pharmacy_db_20260824_020000.sql.gz
docker exec -i pharmacy_db psql -U pharmacy_admin pharmacy_db < pharmacy_db_20260824_020000.sql
```

---

## Monitoring & Maintenance

### Database Size

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Vacuum & Analyze

```bash
# Manual maintenance (runs automatically in PostgreSQL)
python manage.py dbshell
VACUUM ANALYZE;
```

### Connection Pooling (Production)

Use PgBouncer for connection pooling in production:

```ini
[databases]
pharmacy_db = host=localhost port=5432 dbname=pharmacy_db

[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
```

---

## Environment-Specific Configuration

### Development (.env)

```env
DB_HOST=db
DB_NAME=pharmacy_db
DB_USER=pharmacy_admin
DB_PASSWORD=root
DEBUG=True
```

### Production (.env.prod)

```env
DB_HOST=pharmacy-db-prod.c.googlecloud.com
DB_NAME=pharmacy_db_prod
DB_USER=pharmacy_admin_prod
DB_PASSWORD=<strong_password>
DB_SSL_MODE=require
DEBUG=False
```

---

## Summary

The OnlinePharmacy database architecture uses:

- **PostgreSQL 15** with BigAutoField primary keys
- **Immutable audit logs** (AuditLog, CustomerUserHistory) for compliance
- **24-hour undo window** (UndoLog) for safe restoration
- **Smart ban system** (BanRecord) with IP/fingerprint/user matching
- **Threaded comments** with AI moderation and emoji reactions
- **Marketplace model** with Seller and multiple payment methods
- **Transactional consistency** for order/payment flows
- **Comprehensive indexes** for query performance

All sensitive operations are wrapped in `transaction.atomic()` and use `select_for_update()` for distributed locking.
