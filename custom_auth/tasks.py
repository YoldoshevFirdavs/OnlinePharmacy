import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from celery.exceptions import MaxRetriesExceededError

logger = logging.getLogger(__name__)


@shared_task(bind=True, default_retry_delay=300, max_retries=3) # Retry after 5 minutes, up to 3 times
def send_otp_email(self, email: str, otp: str):
    """Send OTP to a user's email address with retry logic."""
    logger.info("Attempting to send OTP email to %s (attempt %s/%s)", email, self.request.retries + 1, self.max_retries)
    try:
        send_mail(
            "OnlinePharmacy - Tasdiqlash kodi",
            f"Sizning kodingiz: {otp}",
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        logger.info("OTP email successfully sent to %s", email)
    except Exception as exc:
        logger.error("Failed to send OTP email to %s: %s", email, exc)
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.critical("Max retries exceeded for OTP email to %s. Giving up.", email)


@shared_task
def send_otp_sms(phone: str, otp: str):
    """Stub SMS sender — replace with real SMS provider integration."""
    message = f"[SMS] Send OTP to {phone}: {otp}"
    try:
        logger.info(message)
    except Exception:
        logger.exception("Failed to enqueue SMS for %s", phone)


@shared_task
def send_telegram_otp(phone: str, otp: str):
    """Stub Telegram sender — log for now. Integration with bot can be added later."""
    message = f"[Telegram] Send OTP to {phone}: {otp}"
    try:
        logger.info(message)
    except Exception:
        logger.exception("Failed to enqueue Telegram OTP for %s", phone)


@shared_task
def clear_expired_sessions():
    """Delete expired sessions from the Django session store."""
    try:
        from django.utils import timezone
        from django.contrib.sessions.models import Session

        now = timezone.now()
        expired_qs = Session.objects.filter(expire_date__lt=now)
        count = expired_qs.count()
        expired_qs.delete()
        logger.info("Cleared %d expired sessions", count)
        return count
    except Exception:
        logger.exception("Failed to clear expired sessions")
        return 0


@shared_task(bind=True, default_retry_delay=300, max_retries=3) # Retry after 5 minutes, up to 3 times
def send_subscription_verification_email(self, email: str, verify_url: str):
    """Send subscription verification email with link and retry logic."""
    logger.info("Attempting to send subscription verification email to %s (attempt %s/%s)", email, self.request.retries + 1, self.max_retries)
    try:
        send_mail(
            "Email tasdiqlash",
            f"Obuna bo'lishni tasdiqlash uchun linkni bosing: {verify_url}",
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        logger.info("Subscription verification email successfully sent to %s", email)
    except Exception as exc:
        logger.error("Failed to send subscription verification email to %s: %s", email, exc)
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.critical("Max retries exceeded for subscription verification email to %s. Giving up.", email)