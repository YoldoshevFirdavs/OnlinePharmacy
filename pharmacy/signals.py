from django.db.models.signals import post_save
from django.dispatch import receiver

from pharmacy.models.comments import CommentAnalysis, ProductComment


@receiver(post_save, sender=ProductComment)
def check_comment_batch_for_ai(sender, instance, created, **kwargs):
    """
    Signal handler to trigger AI analysis when batch of 10+ unapproved comments accumulates.
    Only processes top-level comments (not replies).

    AI Integration:
    - Faqat signal yaratish - background task (/tasks.py) chaqiradi
    - API kaliti settings.GOOGLE_AI_KEY orqali olinadi
    - Har 10-ta comment yoki admin batches da yuboriladi
    """

    if not created or instance.is_ai_checked or instance.parent is not None:
        # Skip: not a new comment, already checked, or is a reply
        return

    # Check if we have 10+ unapproved comments for this product
    unapproved_count = ProductComment.objects.filter(
        product=instance.product,
        is_ai_checked=False,
        is_approved=True,  # Only auto-approved comments (not manually rejected)
        parent__isnull=True,  # Only top-level comments
    ).count()

    if unapproved_count >= 10:
        # Trigger background task to process AI batch
        from pharmacy.tasks import process_comments_for_ai

        # Get the batch of comments to process
        batch = ProductComment.objects.filter(
            product=instance.product, is_ai_checked=False, is_approved=True, parent__isnull=True
        ).order_by("created_at")[:10]

        # Queue background task
        batch_ids = list(batch.values_list("id", flat=True))
        if batch_ids:
            # Use Celery or any other task queue
            process_comments_for_ai.delay(batch_ids)


def ready():
    """Register signals when app is ready"""
    import pharmacy.signals  # noqa
