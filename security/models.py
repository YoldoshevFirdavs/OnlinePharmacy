from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    target_type = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    target_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    meta = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    @property
    def created_at(self):
        return self.timestamp

    def __str__(self):
        return f"{self.user} - {self.action} at {self.timestamp}"

    def delete(self, *args, **kwargs):
        raise ValueError("AuditLog records are immutable and cannot be deleted")

    class Meta:
        ordering = ["-timestamp"]


class UndoLog(models.Model):
    """O'chirilgan obyektlarni qaytarish uchun log"""

    ITEM_TYPE_CHOICES = (
        ("user", "Foydalanuvchi"),
        ("medicine", "Dori"),
        ("category", "Kategoriya"),
        ("delivery", "Haydovchi"),
        ("order", "Buyurtma"),
        ("ban", "Ban"),
        ("history", "Tarix"),
    )

    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES)
    item_id = models.PositiveIntegerField()
    item_name = models.CharField(max_length=255)

    # O'chirilgan ma'lumotlar (JSON formatda)
    deleted_data = models.JSONField(default=dict)

    # Admin
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="deleted_items"
    )
    deleted_at = models.DateTimeField(auto_now_add=True)

    # Qaytarilganmi?
    is_restored = models.BooleanField(default=False)
    restored_at = models.DateTimeField(null=True, blank=True)

    # Qaytarish muddati (24 soat)
    restore_until = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["-deleted_at"]
        indexes = [
            models.Index(fields=["restore_until", "is_restored"]),
        ]

    def __str__(self):
        return f"{self.item_name} ({self.get_item_type_display()}) - {self.deleted_at}"

    def is_expired(self):
        """Check if undo period expired"""
        return timezone.now() > self.restore_until

    def restore(self):
        """Restore a deleted item atomically with a lock on the log record."""
        allowed_types = {"user", "medicine", "category", "delivery", "order", "ban", "history"}

        if self.item_type not in allowed_types:
            return False, "Unsupported item type for restore"

        if self.is_restored:
            return False, "Already restored"

        if self.is_expired():
            return False, "Undo period expired (24 hours)"

        try:
            with transaction.atomic():
                log = UndoLog.objects.select_for_update().get(pk=self.pk)

                if log.is_restored:
                    return False, "Already restored"
                if log.is_expired():
                    return False, "Undo period expired (24 hours)"

                item_type = log.item_type
                deleted_data = dict(log.deleted_data or {})

                # Helper: sanitize deleted_data to model concrete fields and remap common aliases
                def _sanitize_for_model(ModelClass, data):
                    # Build set of allowed keyword names for ModelClass create()
                    allowed_names = set()
                    for f in ModelClass._meta.get_fields():
                        # Skip many-to-many and reverse relations
                        if (
                            getattr(f, "many_to_many", False)
                            or getattr(f, "auto_created", False)
                            and not getattr(f, "concrete", True)
                        ):
                            continue
                        # field name (e.g., 'short_description')
                        name = getattr(f, "name", None)
                        if name:
                            allowed_names.add(name)
                        # attname (e.g., 'category_id' for FK)
                        att = getattr(f, "attname", None)
                        if att:
                            allowed_names.add(att)

                    # Keep only keys that the model accepts
                    sanitized = {k: v for k, v in data.items() if k in allowed_names}

                    # If original data had 'description' but model doesn't accept it, map to common alt fields
                    if "description" in data and "description" not in allowed_names:
                        for alt in ("short_description", "instruction", "summary", "description"):
                            if alt in allowed_names:
                                sanitized[alt] = data["description"]
                                break

                    # Ensure we don't pass unexpected 'description' key
                    if "description" in sanitized and "description" not in allowed_names:
                        sanitized.pop("description", None)

                    return sanitized

                if item_type == "user":
                    from users.models import CustomUser

                    create_data = _sanitize_for_model(CustomUser, deleted_data)
                    CustomUser.objects.create(**create_data)
                elif item_type == "medicine":
                    from pharmacy.models import Medicine

                    create_data = _sanitize_for_model(Medicine, deleted_data)
                    Medicine.objects.create(**create_data)
                elif item_type == "category":
                    from pharmacy.models import Category

                    create_data = _sanitize_for_model(Category, deleted_data)
                    Category.objects.create(**create_data)
                elif item_type == "delivery":
                    from users.models import DeliveryDriver

                    driver_data = deleted_data.copy()
                    if "user" in driver_data and "user_id" not in driver_data:
                        driver_data["user_id"] = driver_data.pop("user")
                    if "user_id" in driver_data and driver_data["user_id"] is None:
                        driver_data.pop("user_id")
                    create_data = _sanitize_for_model(DeliveryDriver, driver_data)
                    DeliveryDriver.objects.create(**create_data)
                elif item_type == "order":
                    from orders.models import Order, OrderItem

                    order_data = deleted_data.copy()
                    order_items = order_data.pop("order_items", [])
                    create_data = _sanitize_for_model(Order, order_data)
                    order = Order.objects.create(**create_data)
                    for item in order_items:
                        OrderItem.objects.create(order=order, **item)
                elif item_type == "ban":
                    create_data = _sanitize_for_model(BanRecord, deleted_data)
                    BanRecord.objects.create(**create_data)
                elif item_type == "history":
                    from pharmacy.models.history import CustomerUserHistory

                    create_data = _sanitize_for_model(CustomerUserHistory, deleted_data)
                    CustomerUserHistory.objects.create(**create_data)

                AuditLog.objects.create(
                    user=log.deleted_by,
                    action="undo_restore",
                    description=f"Restored {item_type} #{log.item_id}",
                    target_type=item_type,
                    target_id=log.item_id,
                    meta={"restore_window_hours": 24, "restored_at": timezone.now().isoformat()},
                )

                log.is_restored = True
                log.restored_at = timezone.now()
                log.save(update_fields=["is_restored", "restored_at"])

            return True, "Item restored successfully"
        except Exception as e:
            return False, f"Error restoring item: {str(e)}"

    @classmethod
    def create_for_delete(cls, item, item_type, deleted_by=None):
        """Create undo log entry for deleted item"""
        import json
        from datetime import timedelta

        # Get item data
        deleted_data = {}

        if item_type == "user":
            from users.models import CustomUser

            if isinstance(item, CustomUser):
                deleted_data = {
                    "full_name": item.full_name,
                    "email": item.email,
                    "phone_number": item.phone_number,
                    "role": item.role,
                    "is_active": item.is_active,
                }

        elif item_type == "medicine":
            from pharmacy.models import Medicine

            if isinstance(item, Medicine):
                # Be defensive: some deployments use different field names (short_description/instruction)
                try:
                    price_val = float(getattr(item, "price", 0) or 0)
                except Exception:
                    price_val = 0.0
                deleted_data = {
                    "name": getattr(item, "name", "") or str(item),
                    "category_id": getattr(item, "category_id", None),
                    "price": price_val,
                    "stock": getattr(item, "stock", 0),
                    # Prefer description, fall back to short_description
                    "description": getattr(item, "description", getattr(item, "short_description", "")),
                }

        elif item_type == "category":
            from pharmacy.models import Category

            if isinstance(item, Category):
                deleted_data = {
                    "name": getattr(item, "name", "") or str(item),
                    "description": getattr(item, "description", ""),
                }

        elif item_type == "delivery":
            from users.models import DeliveryDriver

            if isinstance(item, DeliveryDriver):
                deleted_data = {
                    "user_id": item.user_id,
                    "phone_number": item.phone_number,
                    "vehicle_info": item.vehicle_info,
                    "status": item.status,
                }

        elif item_type == "order":
            from orders.models import Order, OrderItem

            if isinstance(item, Order):
                deleted_data = {
                    "user_id": item.user_id,
                    "address": item.address,
                    "notes": item.notes,
                    "total_price": float(item.total_price),
                    "status": item.status,
                    "order_items": [
                        {
                            "product_id": oi.product_id,
                            "quantity": oi.quantity,
                            "price_at_order": float(oi.price_at_order),
                        }
                        for oi in item.order_items.all()
                    ],
                }

        elif item_type == "ban":
            from security.models import BanRecord

            if isinstance(item, BanRecord):
                deleted_data = {
                    "ip": item.ip,
                    "fingerprint": item.fingerprint,
                    "user_id": item.user_id,
                    "reason": item.reason,
                    "ban_type": item.ban_type,
                    "is_active": item.is_active,
                    "created_by": item.created_by,
                }

        elif item_type == "history":
            from pharmacy.models.history import CustomerUserHistory

            if isinstance(item, CustomerUserHistory):
                deleted_data = {
                    "user_id": item.user_id,
                    "product_id": item.product_id,
                    "seller_id": item.seller_id,
                    "action": item.action,
                    "meta": item.meta,
                    "ip_address": item.ip_address,
                    "user_agent": item.user_agent,
                }

        # Create undo log
        undo_log = cls.objects.create(
            item_type=item_type,
            item_id=item.id,
            item_name=deleted_data.get("name", str(item)) if deleted_data else str(item),
            deleted_data=deleted_data,
            deleted_by=deleted_by,
            restore_until=timezone.now() + timedelta(hours=24),
        )

        return undo_log


class BanRecord(models.Model):
    """Blok va ban yozuvlari - IP, fingerprint yoki user asosida"""

    BAN_TYPE_CHOICES = (
        ("temporary", "Vaqtli"),
        ("permanent", "Doimiy"),
    )

    SOURCE_CHOICES = (
        ("system", "Tizim"),
        ("admin", "Admin"),
        ("telegram", "Telegram"),
    )

    # Identifiers
    ip = models.CharField(max_length=45, blank=True, null=True, db_index=True, help_text="IP manzil")
    fingerprint = models.CharField(max_length=255, blank=True, null=True, db_index=True, help_text="Device fingerprint")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Foydalanuvchi (agar mavjud)",
    )

    # Ban details
    reason = models.TextField(help_text="Blok sababi")
    ban_type = models.CharField(max_length=20, choices=BAN_TYPE_CHOICES, default="temporary")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(
        blank=True, null=True, db_index=True, help_text="Blok tugash vaqti (permanent uchun bo'sh)"
    )

    # Metadata
    created_by = models.CharField(max_length=50, choices=SOURCE_CHOICES, default="system", help_text="Blok yaratuvchi")
    attempts = models.PositiveIntegerField(default=0, help_text="Xato so'rov soni")
    source = models.CharField(max_length=100, blank=True, help_text="Manba (URL path, API endpoint)")
    meta = models.JSONField(default=dict, blank=True, help_text="Qo'shimcha ma'lumotlar")

    # Admin
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["ip", "is_active"]),
            models.Index(fields=["fingerprint", "is_active"]),
            models.Index(fields=["expires_at", "is_active"]),
        ]

    def __str__(self):
        identifiers = []
        if self.user_id:
            identifiers.append(f"User {self.user_id}")
        if self.ip:
            identifiers.append(f"IP {self.ip}")
        if self.fingerprint:
            identifiers.append(f"FP {self.fingerprint[:12]}...")
        identifier = ", ".join(identifiers) or "unknown"
        return f"{identifier} - {self.ban_type} ({self.created_by})"

    def get_related_identifiers(self):
        """Get all related IPs, fingerprints, and users from ban history"""
        related = {
            "ips": set(),
            "fingerprints": set(),
            "users": set(),
        }

        if self.ip:
            related["ips"].add(self.ip)
            # Find all fingerprints used with this IP
            related_fps = BanRecord.objects.filter(ip=self.ip).values_list("fingerprint", flat=True)
            related["fingerprints"].update(fp for fp in related_fps if fp)
            # Find all users who used this IP
            related_users = BanRecord.objects.filter(ip=self.ip).values_list("user_id", flat=True)
            related["users"].update(uid for uid in related_users if uid)

        if self.fingerprint:
            related["fingerprints"].add(self.fingerprint)
            # Find all IPs used with this fingerprint
            related_ips = BanRecord.objects.filter(fingerprint=self.fingerprint).values_list("ip", flat=True)
            related["ips"].update(ip for ip in related_ips if ip)
            # Find all users who used this fingerprint
            related_users = BanRecord.objects.filter(fingerprint=self.fingerprint).values_list("user_id", flat=True)
            related["users"].update(uid for uid in related_users if uid)

        if self.user_id:
            related["users"].add(self.user_id)
            # Find all IPs used by this user
            related_ips = BanRecord.objects.filter(user_id=self.user_id).values_list("ip", flat=True)
            related["ips"].update(ip for ip in related_ips if ip)
            # Find all fingerprints used by this user
            related_fps = BanRecord.objects.filter(user_id=self.user_id).values_list("fingerprint", flat=True)
            related["fingerprints"].update(fp for fp in related_fps if fp)

        return related

    def is_expired(self):
        """Check if temporary ban expired"""
        if self.ban_type == "permanent":
            return False
        if self.expires_at is None:
            return False
        return timezone.now() > self.expires_at

    @classmethod
    def get_active_ban(cls, ip=None, fingerprint=None, user=None):
        """
        Get active ban for IP, fingerprint, yoki user.

        Smart matching:
        1. Direct match (same IP, fingerprint, or user)
        2. Related device matching (if one identifier is banned, check related devices/IPs/fingerprints)
        3. Related user matching (if user is banned, ban all their IPs/fingerprints)

        Hisob-kitob: Agar bitta malumot (IP, fingerprint, yoki user) ban qilingan bo'lsa,
        shu malumotdan foydalanib boshqa qaysidir qurilmadan yoki IP'dan kirish urinishi
        aniqlanadi va ban qilinadi.
        """
        active_query = models.Q(is_active=True)

        # 1. Direct identifiers
        direct_filters = models.Q()
        if ip:
            direct_filters |= models.Q(ip=ip)
        if fingerprint:
            direct_filters |= models.Q(fingerprint=fingerprint)
        if user:
            direct_filters |= models.Q(user=user)

        if not direct_filters:
            return None

        # Try direct ban first
        ban = cls.objects.filter(active_query & direct_filters).order_by("-created_at").first()
        if ban:
            if not ban.is_expired():
                return ban
            else:
                ban.is_active = False
                ban.save()

        # 2. Related device matching - if IP/fingerprint is banned,
        #    find other IPs/fingerprints used by the same user or similar patterns
        related_filters = models.Q()

        # Find if this IP was used by a banned user
        if ip:
            banned_users_for_ip = (
                cls.objects.filter(active_query & models.Q(ip=ip) & models.Q(user__isnull=False))
                .values_list("user_id", flat=True)
                .distinct()
            )

            if banned_users_for_ip:
                related_filters |= models.Q(user_id__in=banned_users_for_ip)

        # Find if this fingerprint was used by a banned user
        if fingerprint:
            banned_users_for_fp = (
                cls.objects.filter(active_query & models.Q(fingerprint=fingerprint) & models.Q(user__isnull=False))
                .values_list("user_id", flat=True)
                .distinct()
            )

            if banned_users_for_fp:
                related_filters |= models.Q(user_id__in=banned_users_for_fp)

        # 3. User-based matching - if user is authenticated and banned,
        #    also check their historical IPs and fingerprints
        if user and user.is_authenticated:
            related_filters |= models.Q(user=user)

            # Get all IPs and fingerprints used by this user
            user_ip_fp = cls.objects.filter(user=user).values_list("ip", "fingerprint")

            for rec_ip, rec_fp in user_ip_fp:
                if rec_ip:
                    related_filters |= models.Q(ip=rec_ip)
                if rec_fp:
                    related_filters |= models.Q(fingerprint=rec_fp)

        # Try related bans
        if related_filters:
            ban = cls.objects.filter(active_query & related_filters).order_by("-created_at").first()
            if ban:
                if not ban.is_expired():
                    return ban
                else:
                    ban.is_active = False
                    ban.save()

        return None
