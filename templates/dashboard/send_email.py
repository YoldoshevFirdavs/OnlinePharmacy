import os
import django
import smtplib
from django.conf import settings
from django.core.mail import send_mail

# Fill in your details
EMAIL_HOST_USER = "yoldoshev.firdavs67@gmail.com"
EMAIL_HOST_PASSWORD = "aggv omfw ldnv icuc"
TO_EMAIL = "firdavsyoldoshevpython@gmail.com"

# Enable SMTP debug output
smtplib.SMTP.debuglevel = 1

settings.configure(
    DEBUG=True,
    EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
    EMAIL_HOST='smtp.gmail.com',
    EMAIL_PORT=587,
    EMAIL_USE_TLS=True,
    EMAIL_HOST_USER=EMAIL_HOST_USER,
    EMAIL_HOST_PASSWORD=EMAIL_HOST_PASSWORD,
    DEFAULT_FROM_EMAIL=EMAIL_HOST_USER,
)

django.setup()

try:
    sent_count = send_mail(
        subject="Django Gmail Debug Test",
        message="Salom men Firdavs ertangi 2:00 am dabulib utadigan meting ni siz ga aytib quymoqchi eid.Bu favquloqda emial buni hech kimga kursatmang  your code is: 754 219",
        from_email=EMAIL_HOST_USER,
        recipient_list=[TO_EMAIL],
        fail_silently=False,
    )
    print(f"✅ Django send_mail() returned: {sent_count}")
except Exception as e:
    print("❌ Error sending email:", e)
