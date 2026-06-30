from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
import hashlib
import phonenumbers
from phonenumbers import PhoneNumberFormat

class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email=None, phone_number=None, password=None, **extra_fields):
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
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email=email, phone_number=phone_number, password=password, **extra_fields)

    def create_superuser(self, email=None, phone_number=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if not email:
            raise ValueError("Superuser must have an email")
        return self._create_user(email=email, phone_number=phone_number, password=password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    USER_ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('deliverer', 'Deliverer'),
        ('admin', 'Admin'),
        ('seller', 'Seller'),
    ]

    phone_number = models.CharField(max_length=32, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    telegram_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    auth_code = models.CharField(max_length=64, null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    full_name = models.CharField(max_length=255,blank=True)
    address = models.CharField(max_length=255, blank=True)
    avatar = models.ImageField(upload_to='users_profile_avatars/', blank=True, null=True)
    date_joined = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    role = models.CharField(max_length=10, choices=USER_ROLE_CHOICES, default='customer')

    bad_comments_count = models.PositiveIntegerField(default=0)
    is_banned = models.BooleanField(default=False)

    objects = CustomUserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone_number']

    def __str__(self):
        return f"{self.full_name or self.email or self.phone_number}"

    @property
    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return f"/static/images/default_avatar.png"

    def clean_phone_number(self):
        if self.phone_number:
            try:
                parsed_number = phonenumbers.parse(self.phone_number, settings.PHONENUMBER_DEFAULT_REGION)
                if phonenumbers.is_valid_number(parsed_number):
                    self.phone_number = phonenumbers.format_number(parsed_number, PhoneNumberFormat.E164)
                else:
                    self.phone_number = None # Invalidate if not a valid number
            except phonenumbers.phonenumberutil.NumberParseException:
                self.phone_number = None # Invalidate if parsing fails

    def save(self, *args, **kwargs):
        self.clean_phone_number()
        super().save(*args, **kwargs)


class Seller(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='users_profile_avatars/', blank=True, null=True)
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

class TelegrambotUser(models.Model):
    shop_user = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL)
    username = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    phone_number =models.CharField(max_length=255, null=True,blank=True)
    language = models.IntegerField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    bot_status = models.CharField(max_length=50,null=True, blank=True)
    last_status = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_banned = models.BooleanField(default=False)
    pays_count = models.BigIntegerField(null=True, blank=True)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions", null=True, blank=True)
    telegram_user = models.ForeignKey(TelegrambotUser, on_delete=models.SET_NULL, related_name="subscriptions", null=True, blank=True)
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.email} ({'Verified' if self.is_verified else 'Not verified'})"

class Deliverer(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Onboarding'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='deliverer_profile')
    phone_number = models.CharField(max_length=32, unique=True)
    vehicle_info = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    stripe_account_id = models.CharField(max_length=255, blank=True, null=True)
    payout_method = models.CharField(max_length=50, blank=True, null=True)
    rate_per_hour = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Deliverer: {self.user.full_name or self.user.email}"

    def clean_phone_number(self):
        if self.phone_number:
            try:
                parsed_number = phonenumbers.parse(self.phone_number, settings.PHONENUMBER_DEFAULT_REGION)
                if phonenumbers.is_valid_number(parsed_number):
                    self.phone_number = phonenumbers.format_number(parsed_number, PhoneNumberFormat.E164)
                else:
                    self.phone_number = None # Invalidate if not a valid number
            except phonenumbers.phonenumberutil.NumberParseException:
                self.phone_number = None # Invalidate if parsing fails

    def save(self, *args, **kwargs):
        self.clean_phone_number()
        super().save(*args, **kwargs)

DeliveryDriver = Deliverer

class OnboardToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def check_token(self, token):
        return (not self.used) and self.expires_at > timezone.now() and hashlib.sha256(token.encode()).hexdigest() == self.token_hash

class SalaryRecord(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]
    deliverer = models.ForeignKey(Deliverer, on_delete=models.CASCADE, related_name='salary_records')
    period_start = models.DateField()
    period_end = models.DateField()
    hours_worked = models.DecimalField(max_digits=6, decimal_places=2)
    rate_per_hour = models.DecimalField(max_digits=6, decimal_places=2)
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    taxes_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    stripe_payment_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ('deliverer', 'period_start', 'period_end')
        ordering = ['-period_end', 'deliverer__user__full_name']

    def __str__(self):
        return f"Salary for {self.deliverer.user.full_name} ({self.period_start} to {self.period_end})"

class PayrollStats(models.Model):
    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()
    total_gross = models.DecimalField(max_digits=12, decimal_places=2)
    total_net = models.DecimalField(max_digits=12, decimal_places=2)
    total_fees = models.DecimalField(max_digits=12, decimal_places=2)
    total_payouts = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('month', 'year')
        verbose_name_plural = "Payroll Stats"

    def __str__(self):
        return f"Payroll Stats for {self.month}/{self.year}"

class AdminLoginToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_login_tokens')
    token_hash = models.CharField(max_length=128, default='', blank=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def mark_used(self):
        self.used = True
        self.save(update_fields=['used'])

    def is_valid(self, token: str) -> bool:
        if self.used or self.expires_at < timezone.now():
            return False
        return hashlib.sha256(token.encode()).hexdigest() == self.token_hash

class AdminLoginAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='admin_login_attempts')
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    success = models.BooleanField(default=False)
    reason = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)