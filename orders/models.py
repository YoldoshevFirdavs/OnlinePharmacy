from django.conf import settings
from django.db import models

from pharmacy.models.medicine import Medicine


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
        ("Assigned", "Assigned to Driver"),
        ("Accepted", "Accepted by Driver"),
        ("Picked Up", "Picked Up by Driver"),
        ("On The Way", "On The Way for Delivery"),
        ("Arrived", "Arrived at Customer Location"),
        ("Delivered", "Delivered"),
        ("Canceled", "Canceled"),
        ("Returned", "Returned"),
    ]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders"
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Changed to settings.AUTH_USER_MODEL
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_orders",
        help_text="The delivery driver assigned to this order.",
    )
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    assigned_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    on_the_way_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    driver_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id} - {self.customer.full_name or self.customer.phone_number}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="order_items"
    )
    product = models.ForeignKey(Medicine, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    price_at_order = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.product.name if self.product else 'Deleted'} x {self.quantity}"
