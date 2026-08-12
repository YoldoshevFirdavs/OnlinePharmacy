from django.db import models
from django.db.models import Avg
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from pharmacy.models import Category, Medicine
from security.models import AuditLog

from .models.misc import Review


def get_request():
    """Walk the stack to find the request object."""
    import inspect

    for frame_info in inspect.stack():
        request = frame_info.frame.f_locals.get("request")
        if request:
            return request
    return None


def log_activity(instance, action, status="succeeded"):
    user = None
    ip_address = None
    request = get_request()
    if request:
        user = request.user if request.user.is_authenticated else None
        ip_address = request.META.get("REMOTE_ADDR")

    description = f"{instance.__class__.__name__} '{instance}' was {action}."
    AuditLog.objects.create(
        user=user,
        action=action,
        description=description,
        ip_address=ip_address,
    )


@receiver(post_save, sender=Category)
def log_category_save(sender, instance, created, **kwargs):
    if created:
        log_activity(instance, "created")
    else:
        log_activity(instance, "updated")


@receiver(post_delete, sender=Category)
def log_category_delete(sender, instance, **kwargs):
    log_activity(instance, "deleted")


@receiver(post_save, sender=Medicine)
def log_medicine_save(sender, instance, created, **kwargs):
    if created:
        log_activity(instance, "created")
    else:
        log_activity(instance, "updated")


@receiver(post_delete, sender=Medicine)
def log_medicine_delete(sender, instance, **kwargs):
    log_activity(instance, "deleted")


@receiver(post_save, sender=Review)
def update_medicine_rating(sender, instance, **kwargs):
    medicine = instance.medicine
    approved_reviews = medicine.reviews.filter(is_approved=True)
    stats = approved_reviews.aggregate(count=models.Count("id"), avg=Avg("rating"))
    medicine.reviews_count = stats["count"]
    medicine.average_rating = stats["avg"] or 0.00
    medicine.save(update_fields=["reviews_count", "average_rating"])
