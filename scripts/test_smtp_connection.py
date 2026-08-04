import smtplib
import ssl
import os
import sys

# Loyiha ildiziga PATH qo'shish, shunda config.email_config ni import qila olamiz
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from config.email_config import (
        EMAIL_HOST,
        EMAIL_PORT,
        EMAIL_USE_TLS,
        EMAIL_HOST_USER,
        EMAIL_HOST_PASSWORD,
        DEFAULT_FROM_EMAIL,
    )
except ImportError:
    print("Xato: config/email_config.py fayli topilmadi yoki unda xatolik bor.")
    print(
        "Iltimos, config/email_config.py faylini to'g'ri yaratganingizga ishonch hosil qiling."
    )
    sys.exit(1)


def test_smtp_connection():
    print("\n--- SMTP Ulanish Testi Boshlandi ---")
    print(f"SMTP Host: {EMAIL_HOST}")
    print(f"SMTP Port: {EMAIL_PORT}")
    print(f"TLS ishlatilmoqda: {EMAIL_USE_TLS}")
    print(f"Foydalanuvchi: {EMAIL_HOST_USER}")
    print(f"Kimdan: {DEFAULT_FROM_EMAIL}")
    print(f"Parol: {'********' if EMAIL_HOST_PASSWORD else 'YOQ'}")

    if (
        not EMAIL_HOST_USER
        or not EMAIL_HOST_PASSWORD
        or EMAIL_HOST_USER == "your_gmail_address@gmail.com"
    ):
        print("\n!!! DIQQAT !!!")
        print(
            "EMAIL_HOST_USER yoki EMAIL_HOST_PASSWORD config/email_config.py faylida to'g'ri konfiguratsiya qilinmagan."
        )
        print(
            "Iltimos, 'your_gmail_address@gmail.com' va 'your_app_password' joyiga haqiqiy ma'lumotlarni kiriting."
        )
        print("Test bekor qilindi.")
        sys.exit(1)

    try:
        if EMAIL_USE_TLS:
            context = ssl.create_default_context()
            print("TLS konteksti yaratildi.")
            with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
                server.starttls(context=context)
                print("TLS ulanishi boshlandi.")
                server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
                print("SMTP autentifikatsiyasi muvaffaqiyatli.")
                server.sendmail(
                    DEFAULT_FROM_EMAIL,
                    EMAIL_HOST_USER,
                    "Subject: SMTP Test\n\nThis is a test email from smtplib.",
                )
                print(f"Test emaili {EMAIL_HOST_USER} manziliga yuborildi.")
                server.quit()
                print("SMTP serveridan chiqildi.")
        else:
            # Agar TLS ishlatilmasa (masalan, SSL port 465 uchun)
            with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT) as server:
                server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
                print("SMTP autentifikatsiyasi muvaffaqiyatli (SSL).")
                server.sendmail(
                    DEFAULT_FROM_EMAIL,
                    EMAIL_HOST_USER,
                    "Subject: SMTP Test\n\nThis is a test email from smtplib.",
                )
                print(f"Test emaili {EMAIL_HOST_USER} manziliga yuborildi.")
                server.quit()
                print("SMTP serveridan chiqildi.")

        print("\n--- SMTP Ulanish Testi Muvaffaqiyatli Yakunlandi ---")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"\n!!! XATO: SMTP Autentifikatsiya Xatosi (535) !!!")
        print(f"Xato tafsiloti: {e}")
        print("Sabablar:")
        print("1. EMAIL_HOST_USER (Gmail manzili) noto'g'ri kiritilgan.")
        print("2. EMAIL_HOST_PASSWORD (App Password) noto'g'ri yoki muddati o'tgan.")
        print(
            "3. Gmail hisobingizda 2-bosqichli tekshirish (2-Step Verification) yoqilmagan."
        )
        print("4. App Password o'rniga asosiy Gmail paroli ishlatilgan.")
        print(
            "Iltimos, Gmail App Password'ingizni qayta yaratib, config/email_config.py faylini yangilang."
        )
    except smtplib.SMTPConnectError as e:
        print(f"\n!!! XATO: SMTP Ulanish Xatosi !!!")
        print(f"Xato tafsiloti: {e}")
        print("Sabablar:")
        print("1. EMAIL_HOST yoki EMAIL_PORT noto'g'ri kiritilgan.")
        print("2. Tarmoq ulanishi yo'q yoki firewall SMTP portini bloklagan.")
        print("3. SMTP serveri ishlamayapti.")
    except Exception as e:
        print(f"\n!!! XATO: Kutilmagan Xato !!!")
        print(f"Xato tafsiloti: {e}")

    print("\n--- SMTP Ulanish Testi Muvaffaqiyatsiz Yakunlandi ---")
    return False


if __name__ == "__main__":
    test_smtp_connection()
