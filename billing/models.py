from django.db import models

from orders.models import Order


# Payment model
class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("cash", "Naqd pul"),
        ("card", "Karta"),
    ]

    order = models.ForeignKey(Order, related_name="payments", on_delete=models.CASCADE)
    stripe_charge_id = models.CharField(max_length=70, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default="cash")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="pending")

    def __str__(self):
        return f"Payment for Order {self.order.id} - {self.status}"
