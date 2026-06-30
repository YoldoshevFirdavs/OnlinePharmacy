import django
import pytest
from django.core.mail import send_mail
from config import email_config
from config.email_config import  EMAIL_HOST_USER, EMAIL_HOST_PASSWORD
from django.conf import settings
TO_EMAIL="firdavsyoldoshevpython@gmail.com"
@pytest.mark.django_db
def test_send_real_email():
    subject = "Test Email from OnlinePharmacy"
    message = "Salom, bu test xabari OnlinePharmacy loyihasidan yuborildi. Iltimos buni sizga biz xavfsizlik choralarini kurib quyish uchun yuboryabmzi bu emailni hech kimga kursatmang va odni ham your code: 947543"
    from_email = email_config.DEFAULT_FROM_EMAIL
    recipient_list = ["firdavsyoldoshevpython@gmail.com"]

    print("\n--- Email Konfiguratsiyasi (email_config.py dan) ---")
    print(f"EMAIL_BACKEND: {email_config.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {email_config.EMAIL_HOST}")
    print(f"EMAIL_PORT: {email_config.EMAIL_PORT}")
    print(f"EMAIL_HOST_USER: {email_config.EMAIL_HOST_USER}")
    print(f"EMAIL_HOST_PASSWORD: {'********' if email_config.EMAIL_HOST_PASSWORD else 'N/A'}")
    print(f"EMAIL_USE_TLS: {email_config.EMAIL_USE_TLS}")
    print(f"DEFAULT_FROM_EMAIL: {email_config.DEFAULT_FROM_EMAIL}")
    print("------------------------------\n")
    django.setup()
    try:
        sent_count = send_mail(
            subject="Django Gmail Debug Test",
            message="Salom men Firdavs man siz ni ertaga 8:00 da meting bulishi eslatib quymoqchi edim agar yana savollar bulsa telegram kanal yoki lichkamga yozib quying",
            from_email=EMAIL_HOST_USER,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        print(f"✅ Django send_mail() returned: {sent_count}")
    except Exception as e:
        print("❌ Error sending email:", e)
