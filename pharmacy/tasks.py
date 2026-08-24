"""
Background tasks for pharmacy app (Celery/RQ compatible)
AI integration for comment analysis
"""

import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_comments_for_ai(self, comment_ids):
    """
    Background task to send batch of comments to AI for analysis.

    Called by: signals.py when 10+ comments accumulated
    AI Provider: Google AI Studio API (settings.GOOGLE_AI_KEY)

    Args:
        comment_ids: List of ProductComment IDs to process

    Returns:
        dict: Analysis result with summary, toxicity_score, flagged_count
    """

    try:
        from pharmacy.models.comments import CommentAnalysis, ProductComment

        # Get comments to analyze
        comments = ProductComment.objects.filter(id__in=comment_ids)
        if not comments.exists():
            logger.warning(f"No comments found for IDs: {comment_ids}")
            return {"error": "No comments found"}

        # Prepare data for AI (NO PII)
        comments_text = []
        for comment in comments:
            # Only send comment content, not user PII
            comments_text.append(
                {
                    "id": comment.id,
                    "content": comment.content,
                    "rating": comment.rating,
                }
            )

        # Get AI API key from settings
        ai_api_key = getattr(settings, "GOOGLE_AI_KEY", None) or getattr(settings, "GOOGLE_AI_API_KEY", None)
        if not ai_api_key:
            logger.warning("GOOGLE_AI_KEY/GOOGLE_AI_API_KEY not configured in settings. Skipping AI check.")

        # Call AI API (example structure - adapt to actual API)
        analysis_result = call_ai_api(comments_text, ai_api_key)

        if not analysis_result:
            logger.error("AI API returned empty result")
            return {"error": "AI analysis failed"}

        # Store analysis results
        analysis = CommentAnalysis.objects.create(
            summary=analysis_result.get("summary", ""),
            toxicity_score=analysis_result.get("toxicity_score", 0.0),
            flagged_count=analysis_result.get("flagged_count", 0),
        )

        # Link comments to analysis and update them
        analysis.comments.set(comments)

        # Update individual comments with AI results
        for comment in comments:
            comment.is_ai_checked = True
            comment.ai_summary = analysis_result.get("comment_summaries", {}).get(str(comment.id), "")
            comment.ai_toxicity_score = analysis_result.get("comment_toxicity", {}).get(str(comment.id), 0.0)

            # Flag if toxicity is high
            if comment.ai_toxicity_score and comment.ai_toxicity_score > 0.7:
                comment.is_approved = False

            comment.save()

        logger.info(f"Successfully processed {len(comments)} comments. Analysis ID: {analysis.id}")
        return {
            "success": True,
            "analysis_id": analysis.id,
            "comments_processed": len(comments),
            "summary": analysis.summary,
        }

    except Exception as exc:
        logger.error(f"Error processing comments for AI: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60)


def call_ai_api(comments_data, api_key):
    """
    Call Google AI Studio API to analyze comments.

    Args:
        comments_data: List of dicts with 'id', 'content', 'rating'
        api_key: GOOGLE_AI_KEY from settings

    Returns:
        dict: Analysis result with keys:
            - summary: Overall batch summary
            - toxicity_score: 0-1 average toxicity
            - flagged_count: Number of toxic comments
            - comment_summaries: Dict mapping comment ID to summary
            - comment_toxicity: Dict mapping comment ID to toxicity score
    """

    try:
        # Example implementation - adapt to actual API
        # This is a placeholder showing the structure

        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-pro")

        # Prepare prompt for AI
        comments_text = "\n\n".join([f"Comment {c['id']}: {c['content']}" for c in comments_data])

        prompt = f"""
Analyze the following product comments for:
1. Overall sentiment and summary
2. Toxicity level (0-1 scale)
3. Which comments are problematic

Comments:
{comments_text}

Return JSON with:
{{
    "summary": "Overall summary of comments",
    "toxicity_score": 0.3,
    "flagged_count": 1,
    "comment_summaries": {{"id": "summary", ...}},
    "comment_toxicity": {{"id": 0.2, ...}}
}}
"""

        response = model.generate_content(prompt)

        # Parse response
        import json

        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            logger.warning("Could not parse AI response as JSON")
            result = {
                "summary": response.text[:500],
                "toxicity_score": 0.5,
                "flagged_count": 0,
                "comment_summaries": {},
                "comment_toxicity": {},
            }

        return result

    except ImportError:
        logger.warning("google.generativeai not installed. Using mock response.")
        # Mock response if library not installed
        return {
            "summary": "Comments batch processed (mock)",
            "toxicity_score": 0.3,
            "flagged_count": 0,
            "comment_summaries": {c["id"]: "Comment processed" for c in comments_data},
            "comment_toxicity": {c["id"]: 0.2 for c in comments_data},
        }

    except Exception as e:
        logger.error(f"Error calling AI API: {str(e)}")
        return None
