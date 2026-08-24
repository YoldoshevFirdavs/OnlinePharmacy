from django.db import models

from users.models import DeliveryDriver


class Salary(models.Model):
    """
    Model to track salaries for delivery drivers.
    """

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Paid", "Paid"),
    ]

    driver = models.ForeignKey(
        DeliveryDriver,
        on_delete=models.CASCADE,
        related_name="salaries",
        help_text="The driver receiving the salary.",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Salary amount.")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending",
        help_text="Current status of the salary.",
    )
    period_start = models.DateField(
        null=True,
        blank=True,
        help_text="Start date of the earning period for this salary.",
    )
    period_end = models.DateField(
        null=True,
        blank=True,
        help_text="End date of the earning period for this salary.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the salary was paid.")

    class Meta:
        verbose_name = "Salary"
        verbose_name_plural = "Salaries"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Salary for {self.driver.user.full_name} - {self.amount} ({self.status})"
