import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMessage, get_connection, send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from config import email_config
from users.models import DeliveryDriver

logger = logging.getLogger(__name__)


def _send_via_configured_connection(subject, text_body, html_body, to_email):
    """Helper to send email using configured connection."""
    if email_config.DEBUG_PRINT_CONFIG:
        logger.warning(
            "Email config: backend=%s host=%s user=%s port=%s use_tls=%s",
            email_config.EMAIL_BACKEND,
            email_config.EMAIL_HOST,
            email_config.EMAIL_HOST_USER,
            email_config.EMAIL_PORT,
            email_config.EMAIL_USE_TLS,
        )

    if email_config.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
        send_mail(
            subject,
            text_body,
            email_config.DEFAULT_FROM_EMAIL,
            [to_email],
            fail_silently=False,
        )
        return

    conn = get_connection(
        backend=email_config.EMAIL_BACKEND,
        host=email_config.EMAIL_HOST,
        port=email_config.EMAIL_PORT,
        username=email_config.EMAIL_HOST_USER,
        password=email_config.EMAIL_HOST_PASSWORD,
        use_tls=email_config.EMAIL_USE_TLS,
        fail_silently=False,
    )
    msg = EmailMessage(
        subject, text_body, email_config.DEFAULT_FROM_EMAIL, [to_email], connection=conn
    )
    if html_body:
        msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)


def _acquire_send_lock(email, token, purpose, timeout=300):
    """Acquires a cache lock to prevent duplicate email sends."""
    key = f"email_sent:{purpose}:{email}:{token}"
    if cache.get(key):
        return False
    cache.set(key, True, timeout=timeout)
    return True


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_admin_login_email(self, email, token, token_lifetime_minutes=15):
    """Sends an admin login email with a verification link."""
    if not _acquire_send_lock(email, token, "admin_login"):
        logger.info(
            "Duplicate send prevented for %s token=%s (purpose: admin_login)",
            email,
            token,
        )
        return

    try:
        link = f"{email_config.SITE_URL}/api/v1/users/admin/verify-login/?token={token}"
        subject = "Admin Dashboard Kirish Havolasi"
        text_body = render_to_string(
            "emails/admin_login.txt",
            {
                "link": link,
                "token_lifetime_minutes": token_lifetime_minutes,
                "user": {"email": email},
            },
        )
        html_body = render_to_string(
            "emails/admin_login.html",
            {
                "link": link,
                "token_lifetime_minutes": token_lifetime_minutes,
                "user": {"email": email},
            },
        )

        if email_config.DEBUG_PRINT_CONFIG:
            print("\n[Celery Task] send_admin_login_email: Task boshlandi")
            print(f"[Celery Task] send_admin_login_email: Kimga: {email}")
            print(f"[Celery Task] send_admin_login_email: Token: {token}")
            print(f"[Celery Task] send_admin_login_email: Link: {link}")
            print(
                f"[Celery Task] send_admin_login_email: From: {email_config.DEFAULT_FROM_EMAIL}"
            )

        _send_via_configured_connection(subject, text_body, html_body, email)
        logger.info("Sent admin login email to %s (token=%s)", email, token)
        if email_config.DEBUG_PRINT_CONFIG:
            print(
                f"[Celery Task] send_admin_login_email: Email muvaffaqiyatli yuborildi to {email}"
            )

    except Exception as exc:
        logger.exception("Failed to send admin login email to %s: %s", email, exc)
        cache.delete(f"email_sent:admin_login:{email}:{token}")
        raise self.retry(exc=exc)


def send_admin_login_email_sync(email, token, token_lifetime_minutes=15):
    """Synchronously sends an admin login email."""
    link = f"{email_config.SITE_URL}/api/v1/users/admin/verify-login/?token={token}"
    subject = "Admin Dashboard Kirish Havolasi"
    text_body = render_to_string(
        "emails/admin_login.txt",
        {
            "link": link,
            "token_lifetime_minutes": token_lifetime_minutes,
            "user": {"email": email},
        },
    )
    html_body = render_to_string(
        "emails/admin_login.html",
        {
            "link": link,
            "token_lifetime_minutes": token_lifetime_minutes,
            "user": {"email": email},
        },
    )

    if email_config.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
        send_mail(
            subject,
            text_body,
            email_config.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return

    conn = get_connection(
        backend=email_config.EMAIL_BACKEND,
        host=email_config.EMAIL_HOST,
        port=email_config.EMAIL_PORT,
        username=email_config.EMAIL_HOST_USER,
        password=email_config.EMAIL_HOST_PASSWORD,
        use_tls=email_config.EMAIL_USE_TLS,
        fail_silently=False,
    )
    msg = EmailMessage(
        subject, text_body, email_config.DEFAULT_FROM_EMAIL, [email], connection=conn
    )
    if html_body:
        msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)
    logger.info("Sent admin login email synchronously to %s (token=%s)", email, token)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_subscription_verification_email(
    self, to_email: str, verification_link: str
) -> None:
    """Sends a subscription verification email."""
    subject = "Confirm your subscription to OnlinePharmacy"
    text_body = (
        "Hello,\n\n"
        "Thanks for subscribing to OnlinePharmacy.\n\n"
        "Please confirm your subscription by visiting the link below:\n\n"
        f"{verification_link}\n\n"
        "If you did not request this, you can ignore this email."
    )
    html_body = None

    if email_config.DEBUG_PRINT_CONFIG:
        print(f"\n[Celery Task] send_subscription_verification_email: Task boshlandi")
        print(f"[Celery Task] send_subscription_verification_email: Kimga: {to_email}")
        print(
            f"[Celery Task] send_subscription_verification_email: Link: {verification_link}"
        )
        print(
            f"[Celery Task] send_subscription_verification_email: From: {email_config.DEFAULT_FROM_EMAIL}"
        )

    try:
        _send_via_configured_connection(subject, text_body, html_body, to_email)
        logger.info("Subscription verification email sent to %s", to_email)
        if email_config.DEBUG_PRINT_CONFIG:
            print(
                f"[Celery Task] send_subscription_verification_email: Email muvaffaqiyatli yuborildi to {to_email}"
            )
    except Exception as exc:
        logger.exception(
            "Failed to send subscription verification email to %s: %s", to_email, exc
        )
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_simple_notification_email(
    self, to_email: str, subject: str, body: str
) -> None:
    """Sends a simple notification email."""
    text_body = body
    html_body = None

    if email_config.DEBUG_PRINT_CONFIG:
        print(f"\n[Celery Task] send_simple_notification_email: Task boshlandi")
        print(f"[Celery Task] send_simple_notification_email: Kimga: {to_email}")
        print(f"[Celery Task] send_simple_notification_email: Mavzu: {subject}")
        print(f"[Celery Task] send_simple_notification_email: Xabar: {body}")
        print(
            f"[Celery Task] send_simple_notification_email: From: {email_config.DEFAULT_FROM_EMAIL}"
        )

    try:
        _send_via_configured_connection(subject, text_body, html_body, to_email)
        logger.info("Notification email sent to %s with subject %s", to_email, subject)
        if email_config.DEBUG_PRINT_CONFIG:
            print(
                f"[Celery Task] send_simple_notification_email: Email muvaffaqiyatli yuborildi to {to_email}"
            )
    except Exception as exc:
        logger.exception("Failed to send notification email to %s: %s", to_email, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_otp_email(self, to_email: str, otp_code: str, user_name: str = None):
    """Sends an OTP email to the user."""
    subject = "OnlinePharmacy - Tasdiqlash kodi"
    text_body = f"Salom {user_name or 'foydalanuvchi'},\n\nSizning kodingiz: {otp_code}\n\nBu kodni hech kimga bermang."
    html_body = None

    if email_config.DEBUG_PRINT_CONFIG:
        print(f"\n[Celery Task] send_otp_email: Task boshlandi")
        print(f"[Celery Task] send_otp_email: Kimga: {to_email}")
        print(f"[Celery Task] send_otp_email: OTP: {otp_code}")
        print(f"[Celery Task] send_otp_email: From: {email_config.DEFAULT_FROM_EMAIL}")

    try:
        _send_via_configured_connection(subject, text_body, html_body, to_email)
        logger.info("OTP email successfully sent to %s", to_email)
        if email_config.DEBUG_PRINT_CONFIG:
            print(
                f"[Celery Task] send_otp_email: Email muvaffaqiyatli yuborildi to {to_email}"
            )
    except Exception as exc:
        logger.exception("Failed to send OTP email to %s: %s", to_email, exc)
        raise self.retry(exc=exc)


send_subscription_verification = send_subscription_verification_email
