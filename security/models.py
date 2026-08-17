from django.conf import settings
from django.db import models
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
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.action} at {self.timestamp}"

    class Meta:
        ordering = ["-timestamp"]


class BanRecord(models.Model):
    """Blok va ban yozuvlari - IP, fingerprint yoki user asosida"""
    
    BAN_TYPE_CHOICES = (
        ('temporary', 'Vaqtli'),
        ('permanent', 'Doimiy'),
    )
    
    SOURCE_CHOICES = (
        ('system', 'Tizim'),
        ('admin', 'Admin'),
        ('telegram', 'Telegram'),
    )
    
    # Identifiers
    ip = models.CharField(max_length=45, blank=True, null=True, db_index=True, help_text="IP manzil")
    fingerprint = models.CharField(max_length=255, blank=True, null=True, db_index=True, help_text="Device fingerprint")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, help_text="Foydalanuvchi (agar mavjud)")
    
    # Ban details
    reason = models.TextField(help_text="Blok sababi")
    ban_type = models.CharField(max_length=20, choices=BAN_TYPE_CHOICES, default='temporary')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(blank=True, null=True, db_index=True, help_text="Blok tugash vaqti (permanent uchun bo'sh)")
    
    # Metadata
    created_by = models.CharField(max_length=50, choices=SOURCE_CHOICES, default='system', help_text="Blok yaratuvchi")
    attempts = models.PositiveIntegerField(default=0, help_text="Xato so'rov soni")
    source = models.CharField(max_length=100, blank=True, help_text="Manba (URL path, API endpoint)")
    meta = models.JSONField(default=dict, blank=True, help_text="Qo'shimcha ma'lumotlar")
    
    # Admin
    is_active = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ip', 'is_active']),
            models.Index(fields=['fingerprint', 'is_active']),
            models.Index(fields=['expires_at', 'is_active']),
        ]
    
    def __str__(self):
        identifier = self.ip or self.fingerprint or f"User {self.user_id}" or "unknown"
        return f"{identifier} - {self.ban_type} ({self.created_by})"
    
    def is_expired(self):
        """Check if temporary ban expired"""
        if self.ban_type == 'permanent':
            return False
        if self.expires_at is None:
            return False
        return timezone.now() > self.expires_at
    
    @classmethod
    def get_active_ban(cls, ip=None, fingerprint=None, user=None):
        """Get active ban for IP, fingerprint, yoki user"""
        query = models.Q(is_active=True)
        
        filters = []
        if ip:
            filters.append(models.Q(ip=ip))
        if fingerprint:
            filters.append(models.Q(fingerprint=fingerprint))
        if user:
            filters.append(models.Q(user=user))
        
        if not filters:
            return None
        
        combined = models.Q()
        for f in filters:
            combined |= f
        
        ban = cls.objects.filter(query & combined).order_by('-created_at').first()
        
        if ban and ban.is_expired():
            ban.is_active = False
            ban.save()
            return None
        
        return ban
