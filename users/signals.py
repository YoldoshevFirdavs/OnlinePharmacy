from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CustomUser, Seller


@receiver(post_save, sender=CustomUser)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create or update related profiles based on the user's role.
    Deliverer profiles are managed exclusively by admin — not via signals.
    """
    if instance.role == "seller":
        # If the user is marked as a seller, ensure a Seller profile exists.
        Seller.objects.get_or_create(user=instance)
