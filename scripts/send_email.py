import os
import django
from django.core.mail import send_mail
from config import email_config
import logging

# Configure logging for this script
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

TO_EMAIL = "firdavsyoldoshevpython@gmail.com"  # Replace with a test email
subject = "Django Gmail Debug Test"
message = "Test message body from send_email.py"

if email_config.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
    logger.info("[send_email.py] Using console backend for dev")
else:
    logger.info("[send_email.py] Using SMTP backend")

try:
    sent_count = send_mail(
        subject,
        message,
        email_config.DEFAULT_FROM_EMAIL,
        [TO_EMAIL],
        fail_silently=False,
    )
    logger.info(f"✅ Django send_mail() returned: {sent_count}")
except Exception as e:
    logger.error("❌ Error sending email: %s", e, exc_info=True)
