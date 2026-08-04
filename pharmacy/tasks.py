import os
import json
import logging
from celery import shared_task
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def moderate_reviews_task(self):
    """
    Automated AI moderation for pharmacy reviews.
    Checks batches of 10 reviews using Gemini 2.5 Flash.
    """
    api_key = os.getenv("AI_STUDIO_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error(
            "AI_STUDIO_KEY or GOOGLE_API_KEY is missing in environment variables."
        )
        return

    try:
        # Import models inside the task to avoid AppRegistryNotReady
        from .models.misc import Review
        from users.models import CustomUser
        from google import genai

        # Fetching unmoderated reviews efficiently
        reviews = Review.objects.filter(is_ai_checked=False).select_related("user")[:10]
        if not reviews.exists():
            return

        client = genai.Client(api_key=api_key)

        # Preparing data for batch processing
        data_to_send = [{"id": r.id, "text": r.content} for r in reviews]

        prompt = (
            "Analyze these pharmacy reviews. A review is unsafe (False) if it gives medical advice, "
            "dosage recommendations, or makes false claims. Otherwise, it is safe (True). "
            'Return ONLY valid JSON: {"id": boolean}. '
            f"Data: {json.dumps(data_to_send)}"
        )

        # Using the specified Gemini 2.5 Flash model
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )

        # Clean response and parse JSON safely
        text = response.text.strip().replace("```json", "").replace("```", "")
        try:
            results = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"AI moderation returned invalid JSON: {text}")
            return

        # Atomically update the database
        with transaction.atomic():
            for rid, is_safe in results.items():
                try:
                    review = Review.objects.get(id=int(rid))
                    review.is_ai_checked = True

                    if not is_safe:
                        user = review.user
                        user.bad_comments_count = (user.bad_comments_count or 0) + 1
                        if user.bad_comments_count >= 10:
                            user.is_banned = True
                        user.save()

                        review.delete()
                        logger.info(f"Review ID #{rid} deleted by AI moderator.")
                    else:
                        review.is_approved = True
                        review.save()

                except Review.DoesNotExist:
                    continue

    except Exception as e:
        logger.error(f"AI Moderation task error: {str(e)}")
        # Exponential backoff retry logic
        raise self.retry(exc=e, countdown=60)
