import os
from django.core.mail import send_mail
import pytest
from django.test import override_settings
from config.email_config import ( # email_config.py dan import qilindi
    EMAIL_BACKEND as EMAIL_BACKEND_CFG,
    EMAIL_HOST as EMAIL_HOST_CFG,
    EMAIL_PORT as EMAIL_PORT_CFG,
    EMAIL_USE_TLS as EMAIL_USE_TLS_CFG,
    EMAIL_HOST_USER as EMAIL_HOST_USER_CFG,
    EMAIL_HOST_PASSWORD as EMAIL_HOST_PASSWORD_CFG,
    DEFAULT_FROM_EMAIL as DEFAULT_FROM_EMAIL_CFG,
)

@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND=EMAIL_BACKEND_CFG,
    EMAIL_HOST=EMAIL_HOST_CFG,
    EMAIL_PORT=EMAIL_PORT_CFG,
    EMAIL_USE_TLS=EMAIL_USE_TLS_CFG,
    EMAIL_HOST_USER=EMAIL_HOST_USER_CFG,
    EMAIL_HOST_PASSWORD=EMAIL_HOST_PASSWORD_CFG,
    DEFAULT_FROM_EMAIL=DEFAULT_FROM_EMAIL_CFG,
    # Agar EMAIL_USE_SSL ham bo'lsa, uni ham override qiling
    # EMAIL_USE_SSL=EMAIL_USE_SSL_CFG,
)
def test_send_real_email_with_config():
    """
    Haqiqiy email yuborishni sinovdan o'tkazadi va email konfiguratsiyasini chop etadi.
    Bu test config/email_config.py dagi sozlamalardan foydalanadi.
    """
    print("\n--- Email Konfiguratsiyasi (config/email_config.py dan) ---")
    print(f"EMAIL_BACKEND: {EMAIL_BACKEND_CFG}")
    print(f"EMAIL_HOST: {EMAIL_HOST_CFG}")
    print(f"EMAIL_PORT: {EMAIL_PORT_CFG}")
    print(f"EMAIL_HOST_USER: {EMAIL_HOST_USER_CFG}")
    print(f"EMAIL_HOST_PASSWORD: {'********' if EMAIL_HOST_PASSWORD_CFG else 'N/A'}")
    print(f"EMAIL_USE_TLS: {EMAIL_USE_TLS_CFG}")
    # print(f"EMAIL_USE_SSL: {EMAIL_USE_SSL_CFG}") # Agar email_config.py da bo'lsa
    print(f"DEFAULT_FROM_EMAIL: {DEFAULT_FROM_EMAIL_CFG}")
    print("------------------------------\n")

    subject = "Test Email from OnlinePharmacy"
    message = "Salom, bu test xabari OnlinePharmacy loyihasidan yuborildi."
    from_email = DEFAULT_FROM_EMAIL_CFG
    recipient_list = ["firdavsyoldoshevpython@gmail.com"]

    print(f"Email yuborilmoqda...")
    print(f"Kimga: {recipient_list[0]}")
    print(f"Mavzu: {subject}")
    print(f"Kimdan: {from_email}")
    print(f"Xabar: {message}")

    try:
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        print("Email muvaffaqiyatli yuborildi!")
        assert True # Muvaffaqiyatni ko'rsatish
    except Exception as e:
        print(f"Email yuborishda xatolik yuz berdi: {e}")
        pytest.fail(f"Email yuborishda xatolik yuz berdi: {e}")

    print("\n--- Email Yuborish Testi Yakunlandi ---\n")
