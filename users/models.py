import hashlib

import phonenumbers
from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from phonenumbers import PhoneNumberFormat


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(
        self, email=None, phone_number=None, password=None, **extra_fields
    ):
        """
        Create and save a user with the given email or phone_number and password.
        """
        if not email and not phone_number:
            raise ValueError("The given email or phone number must be set")
        email = self.normalize_email(email) if email else None
        user = self.model(email=email, phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email=None, phone_number=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", "user")
        return self._create_user(
            email=email, phone_number=phone_number, password=password, **extra_fields
        )

    def create_superuser(
        self, email=None, phone_number=None, password=None, **extra_fields
    ):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "admin")
        if not email:
            raise ValueError("Superuser must have an email")
        return self._create_user(
            email=email, phone_number=phone_number, password=password, **extra_fields
        )


class CustomUser(AbstractBaseUser, PermissionsMixin):
    USER_ROLE_CHOICES = [
        ("user", "User"),
        ("admin", "Admin"),
        ("seller", "Seller"),
    ]

    phone_number = models.CharField(max_length=32, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    telegram_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    auth_code = models.CharField(max_length=64, null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    full_name = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=255, blank=True)
    avatar = models.ImageField(
        upload_to="users_profile_avatars/", blank=True, null=True
    )
    date_joined = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    role = models.CharField(max_length=10, choices=USER_ROLE_CHOICES, default="user")

    bad_comments_count = models.PositiveIntegerField(default=0)
    is_banned = models.BooleanField(default=False)  # Telegram login page uchun permanent ban
    
    # banned_for - Boshqa barcha page'lar uchun vaqtli/permanent ban
    banned_for = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        help_text="Qaysi page uchun ban qo'yilgan (masalan: 'admin_login', 'dashboard', etc.)"
    )
    ban_reason = models.CharField(
        max_length=500, 
        blank=True, 
        null=True,
        help_text="Ban berilgan sababi"
    )
    ban_until = models.DateTimeField(
        blank=True, 
        null=True,
        help_text="Vaqtli ban bo'lsa, bu vaqtgacha ban davom etadi. Null bo'lsa, permanent ban."
    )
    is_permanent_ban = models.BooleanField(
        default=False,
        help_text="Permanent ban bo'lsa True. Faqat boshqa adminlar ochishi mumkin."
    )
    banned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users_banned_by_me"
    )

    objects = CustomUserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # Removed "phone_number" from REQUIRED_FIELDS

    def __str__(self):
        return f"{self.full_name or self.email or self.phone_number}"

    def get_display_name(self):
        return self.full_name if self.full_name else self.email

    @property
    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return f"/static/images/default_avatar.png"

    def clean_phone_number(self):
        if self.phone_number:
            try:
                parsed_number = phonenumbers.parse(
                    self.phone_number, settings.PHONENUMBER_DEFAULT_REGION
                )
                if phonenumbers.is_valid_number(parsed_number):
                    self.phone_number = phonenumbers.format_number(
                        parsed_number, PhoneNumberFormat.E164
                    )
                else:
                    self.phone_number = None  # Invalidate if not a valid number
            except phonenumbers.phonenumberutil.NumberParseException:
                self.phone_number = None  # Invalidate if parsing fails

    def save(self, *args, **kwargs):
        self.clean_phone_number()
        super().save(*args, **kwargs)
    
    def is_active_ban(self, page: str = None) -> bool:
        """
        Foydalanuvchi hozir bannalangan yoki yo'qligini tekshirish.
        
        Args:
            page (str): Qaysi page uchun ban tekshirish (masalan 'admin_login')
                        Null bo'lsa, umumiy ban holatini qaytaradi
        
        Returns:
            bool: Agarda ban qo'yilgan bo'lsa True
        """
        if page and self.banned_for != page:
            return False
        
        # Agar permanent ban bo'lsa
        if self.is_permanent_ban and self.banned_for:
            return True
        
        # Vaqtli ban bo'lsa, vaqtni tekshirish
        if self.ban_until:
            if timezone.now() < self.ban_until:
                return True
            else:
                # Ban vaqti tugagan, avtomatik ochish
                self.banned_for = None
                self.ban_until = None
                self.is_permanent_ban = False
                self.save(update_fields=['banned_for', 'ban_until', 'is_permanent_ban'])
                return False
        
        return False
    
    def ban_user(self, page: str, duration_seconds: int = None, reason: str = None, banned_by = None, is_permanent: bool = False):
        """
        Foydalanuvchini ban qilish.
        
        Args:
            page (str): Qaysi page uchun ban (masalan 'admin_login')
            duration_seconds (int): Vaqtli ban bo'lsa, necha sekundga ban (default None = permanent)
            reason (str): Ban sababi
            banned_by: Ban qo'ygan admin user
            is_permanent (bool): Permanent ban bo'lsa True
        """
        self.banned_for = page
        self.ban_reason = reason
        self.banned_by = banned_by
        self.is_permanent_ban = is_permanent
        
        if is_permanent:
            self.ban_until = None
        elif duration_seconds:
            self.ban_until = timezone.now() + timezone.timedelta(seconds=duration_seconds)
        
        self.save()
    
    def unban_user(self):
        """Ban olib tashlash."""
        self.banned_for = None
        self.ban_until = None
        self.ban_reason = None
        self.is_permanent_ban = False
        self.banned_by = None
        self.save()


class Seller(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    avatar = models.ImageField(
        upload_to="users_profile_avatars/", blank=True, null=True
    )
    shop_name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, null=True, blank=True)
    short_description = models.CharField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    licence_number = models.CharField(max_length=255, blank=True, null=True)
    tax_id = models.CharField(max_length=20, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    sells_count = models.PositiveIntegerField(default=0)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    credit_card = models.CharField(max_length=16, blank=True, null=True)
    credit_card_expiry = models.CharField(max_length=5, blank=True, null=True)
    credit_card_holder = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.shop_name} ({self.user.email or self.user.phone_number})"

    @property
    def get_avatar_url(self):
        if self.avatar and hasattr(self.avatar, "url"):
            return self.avatar.url
        return "/static/images/default_avatar.png"


class TelegrambotUser(models.Model):
    shop_user = models.ForeignKey(
        CustomUser, null=True, blank=True, on_delete=models.SET_NULL
    )
    username = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    phone_number = models.CharField(max_length=255, null=True, blank=True)
    language = models.IntegerField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    bot_status = models.CharField(max_length=50, null=True, blank=True)
    last_status = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_banned = models.BooleanField(default=False)
    pays_count = models.BigIntegerField(null=True, blank=True)
    total_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    def __str__(self):
        return f"{self.username or 'No Name'} ({self.telegram_id})"


class Operator(models.Model):
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, unique=True)
    is_busy = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.phone_number})"


class SubscribedUser(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        null=True,
        blank=True,
    )
    telegram_user = models.ForeignKey(
        TelegrambotUser,
        on_delete=models.SET_NULL,
        related_name="subscriptions",
        null=True,
        blank=True,
    )
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email} ({'Verified' if self.is_verified else 'Not verified'})"


class DeliveryDriver(models.Model):
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="delivery_profile"
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    vehicle_info = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(
        max_length=50,
        choices=[("active", "Active"), ("inactive", "Inactive")],
        default="active",
    )
    avatar = models.ImageField(upload_to="drivers/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.full_name or self.user.email


class AdminLoginToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="admin_login_tokens",  # CHANGED from "onboard_tokens"
    )
    token_hash = models.CharField(max_length=128, default="", blank=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def mark_used(self):
        self.used = True
        self.save(update_fields=["used"])

    def is_valid(self, token: str) -> bool:
        if self.used or self.expires_at < timezone.now():
            return False
        return hashlib.sha256(token.encode()).hexdigest() == self.token_hash


class AdminLoginAttempt(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_login_attempts",
    )
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    success = models.BooleanField(default=False)
    reason = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
