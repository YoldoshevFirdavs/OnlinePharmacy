from django.conf import settings
from django.db import models

from pharmacy.models.medicine import Medicine
from users.models import DeliveryDriver


class Cart(models.Model):
    user = models.OneToOneField(
        "users.CustomUser", on_delete=models.CASCADE, related_name="user_cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.full_name or self.user.phone_number} savatchasi"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product.name} ({self.quantity} ta)"


class Order(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Processing", "Processing"),
        ("Delivered", "Delivered"),
        ("Canceled", "Canceled"),
        ("Returned", "Returned"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders"
    )
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.full_name or self.user.phone_number}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="order_items"
    )
    product = models.ForeignKey(Medicine, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    price_at_order = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.product.name if self.product else 'Deleted'} x {self.quantity}"


class DeliveryOrder(models.Model):
    driver = models.ForeignKey(
        DeliveryDriver, on_delete=models.SET_NULL, null=True, blank=True
    )
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=50,
        choices=[("assigned", "Assigned"), ("completed", "Completed")],
        default="assigned",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Delivery for Order #{self.order.id} by {self.driver.user.full_name if self.driver else 'N/A'}"
