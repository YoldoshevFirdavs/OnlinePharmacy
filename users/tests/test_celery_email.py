import os
from django.conf import settings
from users.tasks import send_simple_notification_email
import pytest
import time
from celery.result import AsyncResult

@pytest.mark.django_db
def test_celery_send_email():
    """
    Celery orqali email yuborish taskini sinovdan o'tkazadi.
    """
    print("\n--- Celery va Email Konfiguratsiyasi ---")
    print(f"CELERY_BROKER_URL: {getattr(settings, 'CELERY_BROKER_URL', 'N/A')}")
    print(f"CELERY_RESULT_BACKEND: {getattr(settings, 'CELERY_RESULT_BACKEND', 'N/A')}")
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'N/A')}")
    print(f"EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'N/A')}")
    print(f"EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'N/A')}")
    print(f"EMAIL_HOST_PASSWORD: {'********' if getattr(settings, 'EMAIL_HOST_PASSWORD', '') else 'N/A'}")
    print(f"EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'N/A')}")
    print(f"EMAIL_USE_SSL: {getattr(settings, 'EMAIL_USE_SSL', 'N/A')}")
    print(f"DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'N/A')}")
    print("-----------------------------------------\n")

    to_email = "firdavsyoldoshevpython@gmail.com"
    subject = "Salom"
    message = "Bu Celery test xabari OnlinePharmacy loyihasidan yuborildi."
    
    print(f"Celery task chaqirilmoqda: send_simple_notification_email.delay('{to_email}', '{subject}', '{message}')")
    
    # Celery taskni chaqirish
    task = send_simple_notification_email.delay(to_email, subject, message)
    
    print(f"Task ID: {task.id}")
    print(f"Task holati (dastlabki): {task.status}")

    # Task tugashini kutish
    # Haqiqiy testlarda bu yerda mock ishlatish yoki taskni sinxron ishlashga majburlash yaxshiroq.
    # Lekin bu yerda real worker bilan ishlash simulyatsiya qilinadi.
    timeout = 10 # sekund
    start_time = time.time()
    while task.status not in ['SUCCESS', 'FAILURE', 'REVOKED'] and (time.time() - start_time) < timeout:
        time.sleep(0.5) # Yarim sekund kutish
        task = AsyncResult(task.id) # Holatni yangilash
        print(f"Task holati (yangilangan): {task.status}")

    print(f"Task yakuniy holati: {task.status}")
    print(f"Task natijasi: {task.result}")

    assert task.status == "SUCCESS", f"Celery task muvaffaqiyatsiz tugadi. Holat: {task.status}, Natija: {task.result}"
    
    print("\n--- Celery Email Testi Yakunlandi ---\n")
