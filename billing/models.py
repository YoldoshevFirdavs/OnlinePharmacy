from orders.models import Order
from django.db import models

# Payment model
class Payment(models.Model):
    order = models.ForeignKey(Order, related_name='payments', on_delete=models.CASCADE)
    stripe_charge_id = models.CharField(max_length=70)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending')

    def __str__(self):
        return f"Payment for Order {self.order.id} - {self.status}"