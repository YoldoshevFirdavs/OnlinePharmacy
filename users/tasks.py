import logging
from celery import shared_task
from django.core.mail import EmailMessage, get_connection, send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from config import email_config
from users.models import Deliverer, SalaryRecord, PayrollStats

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


@shared_task(bind=True, max_retries=3, default_retry_delay=60 * 60)
def send_deliverer_onboarding_email(
    self, email, onboarding_link, token_lifetime_minutes=24 * 60
):
    """Sends an onboarding email to a new deliverer with a set-password link."""
    if not _acquire_send_lock(email, onboarding_link, "deliverer_onboarding"):
        logger.info(
            "Duplicate send prevented for deliverer onboarding email to %s", email
        )
        return

    try:
        subject = "OnlinePharmacy Yetkazuvchi Hisobini Faollashtirish"
        text_body = render_to_string(
            "emails/deliverer_onboarding.txt",
            {
                "link": onboarding_link,
                "token_lifetime_minutes": token_lifetime_minutes,
                "user": {"email": email},
            },
        )
        html_body = render_to_string(
            "emails/deliverer_onboarding.html",
            {
                "link": onboarding_link,
                "token_lifetime_minutes": token_lifetime_minutes,
                "user": {"email": email},
            },
        )

        if email_config.DEBUG_PRINT_CONFIG:
            print(f"\n[Celery Task] send_deliverer_onboarding_email: Task boshlandi")
            print(f"[Celery Task] send_deliverer_onboarding_email: Kimga: {email}")
            print(
                f"[Celery Task] send_deliverer_onboarding_email: Link: {onboarding_link}"
            )
            print(
                f"[Celery Task] send_deliverer_onboarding_email: From: {email_config.DEFAULT_FROM_EMAIL}"
            )

        _send_via_configured_connection(subject, text_body, html_body, email)
        logger.info("Sent deliverer onboarding email to %s", email)
        if email_config.DEBUG_PRINT_CONFIG:
            print(
                f"[Celery Task] send_deliverer_onboarding_email: Email muvaffaqiyatli yuborildi to {email}"
            )

    except Exception as exc:
        logger.exception(
            "Failed to send deliverer onboarding email to %s: %s", email, exc
        )
        cache.delete(f"email_sent:deliverer_onboarding:{email}:{onboarding_link}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60 * 60)
def calculate_monthly_payroll(self):
    """Calculates monthly payroll for all active deliverers and triggers payouts."""
    logger.info("Starting monthly payroll calculation task.")
    today = timezone.now().date()
    last_month_end = today.replace(day=1) - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    month = last_month_end.month
    year = last_month_end.year

    if PayrollStats.objects.filter(month=month, year=year).exists():
        logger.info("Payroll for %s/%s already processed. Skipping.", month, year)
        return

    total_gross_month = 0
    total_net_month = 0
    total_fees_month = 0
    total_payouts_month = 0

    deliverers = Deliverer.objects.filter(status="active")
    if not deliverers.exists():
        logger.info("No active deliverers found for payroll calculation.")
        return

    for deliverer in deliverers:
        try:
            with transaction.atomic():
                # Placeholder for hours worked calculation
                hours_worked = 160

                rate_per_hour = (
                    deliverer.rate_per_hour
                    if deliverer.rate_per_hour > 0
                    else settings.PAYROLL_RATE_PER_HOUR
                )

                gross_amount = hours_worked * rate_per_hour
                taxes_amount = gross_amount * settings.PAYROLL_TAX_RATE
                net_amount = gross_amount - taxes_amount

                salary_record, created = SalaryRecord.objects.get_or_create(
                    deliverer=deliverer,
                    period_start=last_month_start,
                    period_end=last_month_end,
                    defaults={
                        "hours_worked": hours_worked,
                        "rate_per_hour": rate_per_hour,
                        "gross_amount": gross_amount,
                        "taxes_amount": taxes_amount,
                        "net_amount": net_amount,
                        "status": "pending",
                    },
                )

                if not created and salary_record.status != "pending":
                    logger.info(
                        "Salary record for deliverer %s for %s/%s already exists and is not pending. Skipping payout.",
                        deliverer.user.email,
                        month,
                        year,
                    )
                    continue

                logger.info(
                    "Calculated payroll for %s: Gross=%s, Net=%s",
                    deliverer.user.email,
                    gross_amount,
                    net_amount,
                )

                # Simulate Stripe Payout/Transfer
                stripe_payment_id = None
                payout_successful = False
                if deliverer.stripe_account_id:
                    try:
                        # In a real application, integrate with Stripe API here.
                        # Example: stripe.Payout.create(...)
                        stripe_payment_id = f"mock_stripe_id_{salary_record.id}"
                        payout_successful = True
                        logger.info(
                            "Simulated Stripe payout for deliverer %s, amount %s",
                            deliverer.user.email,
                            net_amount,
                        )
                    except Exception as stripe_exc:
                        logger.error(
                            "Stripe payout failed for deliverer %s (ID: %s): %s",
                            deliverer.user.email,
                            deliverer.id,
                            stripe_exc,
                        )
                        salary_record.status = "failed"
                        salary_record.save()
                        continue

                if payout_successful:
                    salary_record.status = "paid"
                    salary_record.stripe_payment_id = stripe_payment_id
                    salary_record.paid_at = timezone.now()
                    salary_record.save()
                    logger.info(
                        "Payout successful for deliverer %s", deliverer.user.email
                    )

                    total_gross_month += gross_amount
                    total_net_month += net_amount
                    total_fees_month += taxes_amount
                    total_payouts_month += net_amount

        except Exception as e:
            logger.exception(
                "Error processing payroll for deliverer %s: %s", deliverer.user.email, e
            )

    if deliverers.exists():
        try:
            with transaction.atomic():
                payroll_stats, created = PayrollStats.objects.get_or_create(
                    month=month,
                    year=year,
                    defaults={
                        "total_gross": total_gross_month,
                        "total_net": total_net_month,
                        "total_fees": total_fees_month,
                        "total_payouts": total_payouts_month,
                    },
                )
                if not created:
                    payroll_stats.total_gross = total_gross_month
                    payroll_stats.total_net = total_net_month
                    payroll_stats.total_fees = total_fees_month
                    payroll_stats.total_payouts = total_payouts_month
                    payroll_stats.save()
                logger.info(
                    "Monthly payroll stats for %s/%s updated. Gross: %s, Net: %s",
                    month,
                    year,
                    total_gross_month,
                    total_net_month,
                )
        except Exception as e:
            logger.exception(
                "Error saving monthly payroll stats for %s/%s: %s", month, year, e
            )

    logger.info("Monthly payroll calculation task finished.")


send_subscription_verification = send_subscription_verification_email
