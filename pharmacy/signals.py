from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg
from django.db import models

from models.misc import Review


@receiver(post_save, sender=Review)
def update_medicine_rating(sender, instance, **kwargs):
    medicine = instance.medicine
    approved_reviews = medicine.reviews.filter(is_approved=True)
    stats = approved_reviews.aggregate(
        count=models.Count('id'),
        avg=Avg('rating')
    )
    medicine.reviews_count = stats['count']
    medicine.average_rating = stats['avg'] or 0.00
    medicine.save(update_fields=['reviews_count', 'average_rating'])