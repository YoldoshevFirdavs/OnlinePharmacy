from django.db import models

from pharmacy.models.medicine import Medicine
from users.models import CustomUser


class CustomerUserHistory(models.Model):
    """
    Immutable audit log for all customer actions.
    Records: product views, seller views, add_to_cart, comments, orders
    """

    ACTION_CHOICES = [
        ("view_product", "Mahsulot ko'rildi"),
        ("view_seller", "Sotuvchi ko'rildi"),
        ("add_to_cart", "Savatchaga qo'shildi"),
        ("comment_create", "Fikr qoldirildi"),
        ("comment_edit", "Fikr tahrirlandi"),
        ("comment_delete", "Fikr o'chirildi"),
        ("order_create", "Buyurtma qilindi"),
        ("order_cancel", "Buyurtma bekor qilindi"),
        ("admin_delete", "Admin tomonidan o'chirildi"),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="customer_history")
    product = models.ForeignKey(Medicine, on_delete=models.SET_NULL, null=True, blank=True, related_name="view_history")
    seller = models.ForeignKey(
        "users.Seller", on_delete=models.SET_NULL, null=True, blank=True, related_name="seller_history"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)
    meta = models.JSONField(default=dict, blank=True, help_text="Additional action data (e.g., comment_id, order_id)")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["action", "-timestamp"]),
            models.Index(fields=["product", "-timestamp"]),
        ]
        verbose_name = "Customer History"
        verbose_name_plural = "Customer Histories"
        # Immutable model - no update/delete allowed

    def __str__(self):
        return f"{self.user.full_name or self.user.phone_number} - {self.get_action_display()} - {self.timestamp}"

    def save(self, *args, **kwargs):
        """Override save to prevent updates - only allow create"""
        if self.pk:
            raise ValueError("CustomerUserHistory records are immutable and cannot be updated")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Override delete to prevent deletion"""
        raise ValueError("CustomerUserHistory records are immutable and cannot be deleted")
