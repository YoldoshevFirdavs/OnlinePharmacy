from django.conf import settings
from django.db import models

from users.models import DeliveryDriver


class Payout(models.Model):
    """
    Model to track payouts made to delivery drivers.
    """

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Processing", "Processing"),
        ("Completed", "Completed"),
        ("Failed", "Failed"),
        ("Canceled", "Canceled"),
    ]

    driver = models.ForeignKey(
        DeliveryDriver,
        on_delete=models.CASCADE,
        related_name="payouts",
        help_text="The driver receiving the payout.",
    )
    amount_gross = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Total amount before any deductions."
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Amount deducted for taxes.",
    )
    commission_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Platform commission deducted from gross amount.",
    )
    net_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Net amount paid to the driver (gross - tax - commission).",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending",
        help_text="Current status of the payout.",
    )
    stripe_transfer_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="ID of the corresponding Stripe transfer, if applicable.",
    )
    period_start = models.DateField(
        null=True,
        blank=True,
        help_text="Start date of the earning period for this payout.",
    )
    period_end = models.DateField(
        null=True,
        blank=True,
        help_text="End date of the earning period for this payout.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp when the payout was processed."
    )

    class Meta:
        verbose_name = "Payout"
        verbose_name_plural = "Payouts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payout #{self.id} for {self.driver.user.full_name} - {self.net_amount} ({self.status})"
