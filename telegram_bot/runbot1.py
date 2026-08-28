import logging
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.error import TelegramError
from telegram.ext import CallbackContext, CommandHandler, Filters, MessageHandler, Updater

load_dotenv()

THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.getenv("DJANGO_SETTINGS_MODULE", "config.settings"))
import django

django.setup()

from django.core.cache import cache
from django.urls import reverse

from users.models import CustomUser

load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
BOT_TOKEN = os.getenv("AUTH_BOT_TOKEN", "")
if not BOT_TOKEN:
    logger.critical("BOT_TOKEN not found in environment variables. Please set AUTH_BOT_TOKEN. Exiting.")
    sys.exit(1)


def _normalize_phone(value):
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _is_session_expired(session_data, ttl_seconds=300):
    if not isinstance(session_data, dict):
        return True
    created_at = session_data.get("created_at")
    if created_at is None:
        return False
    try:
        return (time.time() - float(created_at)) > ttl_seconds
    except (TypeError, ValueError):
        return False


def start_handler(update: Update, context: CallbackContext):
    telegram_id = update.message.from_user.id
    payload = ""
    if context.args:
        payload = context.args[0]

    admin_session = cache.get(f"admin_session:{payload}") if payload else None
    expected_phone = (admin_session or {}).get("phone_number")
    expected_user_id = (admin_session or {}).get("user_id")

    if (
        not admin_session
        or admin_session.get("used")
        or _is_session_expired(admin_session, ttl_seconds=300)
        or not expected_phone
        or not expected_user_id
    ):
        cache.delete(f"telegram_pending:{telegram_id}")
        update.message.reply_text("Login sessiyasi yaroqsiz yoki muddati tugagan.")
        return

    target_user = CustomUser.objects.filter(id=expected_user_id).first()
    if not target_user:
        cache.delete(f"telegram_pending:{telegram_id}")
        update.message.reply_text(
            "Foydalanuvchi topilmadi. Login bekor qilindi.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # Check if user is ADMIN (is_superuser, is_staff, role="admin")
    is_admin = target_user.is_superuser and target_user.is_staff and str(target_user.role).lower() == "admin"

    # If ADMIN: telegram_id must match
    if is_admin:
        if not target_user.telegram_id or str(target_user.telegram_id) != str(telegram_id):
            cache.delete(f"telegram_pending:{telegram_id}")
            update.message.reply_text(
                "Telegram ID xato yoki admin akkauntiga bog'lanmagan. Login bekor qilindi.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return
    # If NOT ADMIN: Save telegram_id for first-time login (optional for users/sellers/drivers)
    else:
        # For non-admin users, save telegram_id if not already set
        if not target_user.telegram_id:
            target_user.telegram_id = str(telegram_id)
            target_user.save(update_fields=["telegram_id"])

    normalized_expected_phone = _normalize_phone(expected_phone)
    if not normalized_expected_phone or _normalize_phone(target_user.phone_number) != normalized_expected_phone:
        cache.delete(f"telegram_pending:{telegram_id}")
        update.message.reply_text(
            "Telefon raqami akkauntga mos kelmayapti. Login bekor qilindi.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    pending_payload = {
        "payload": payload,
        "user_id": expected_user_id,
        "phone_number": expected_phone,
        "created_at": time.time(),
    }
    cache.set(f"telegram_pending:{telegram_id}", pending_payload, timeout=300)
    keyboard = [[KeyboardButton("Telefon raqamni yuborish", request_contact=True)]]
    update.message.reply_text(
        "Davom etish uchun Telegram'dagi telefon raqamingizni quyidagi tugma orqali yuboring.",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
    )


def contact_handler(update: Update, context: CallbackContext):
    telegram_id = update.message.from_user.id
    contact = update.message.contact
    pending = cache.get(f"telegram_pending:{telegram_id}")

    if not pending or not contact or contact.user_id != telegram_id:
        update.message.reply_text(
            "Telefon tasdiqlash sessiyasi topilmadi. Login tugmasidan qayta boshlang.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if _is_session_expired(pending, ttl_seconds=300):
        cache.delete(f"telegram_pending:{telegram_id}")
        update.message.reply_text("Login sessiyasi muddati tugadi. Qayta boshlang.", reply_markup=ReplyKeyboardRemove())
        return

    submitted_phone = _normalize_phone(contact.phone_number)
    expected_phone = _normalize_phone(pending.get("phone_number"))
    if submitted_phone != expected_phone:
        cache.delete(f"telegram_pending:{telegram_id}")
        update.message.reply_text(
            "Yuborilgan telefon raqami login sahifasidagi raqamga mos emas.", reply_markup=ReplyKeyboardRemove()
        )
        return

    user = CustomUser.objects.filter(id=pending["user_id"]).first()
    if not user or user.id != pending["user_id"]:
        cache.delete(f"telegram_pending:{telegram_id}")
        update.message.reply_text(
            "Bu telefon raqami bo'yicha foydalanuvchi topilmadi.", reply_markup=ReplyKeyboardRemove()
        )
        return

    # Check if user is ADMIN (is_superuser, is_staff, role="admin")
    is_admin = user.is_superuser and user.is_staff and str(user.role).lower() == "admin"

    # If ADMIN: telegram_id must match
    if is_admin:
        if not user.telegram_id or str(user.telegram_id) != str(telegram_id):
            cache.delete(f"telegram_pending:{telegram_id}")
            update.message.reply_text(
                "Telegram ID yoki admin ma'lumoti xato. Admin linki yuborilmadi.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return
    # If NOT ADMIN: Save telegram_id for first-time login (optional for users/sellers/drivers)
    else:
        # For non-admin users, save telegram_id if not already set
        if not user.telegram_id:
            user.telegram_id = str(telegram_id)
            user.save(update_fields=["telegram_id"])

    actual_user_phone = _normalize_phone(user.phone_number)
    if actual_user_phone != expected_phone:
        cache.delete(f"telegram_pending:{telegram_id}")
        update.message.reply_text("Telefon raqami sessiyadagi raqamga mos emas.", reply_markup=ReplyKeyboardRemove())
        return

    payload = pending["payload"]
    admin_session = cache.get(f"admin_session:{payload}")
    if _is_session_expired(admin_session, ttl_seconds=300):
        cache.delete(f"telegram_pending:{telegram_id}")
        update.message.reply_text("Login sessiyasi muddati tugadi.", reply_markup=ReplyKeyboardRemove())
        return

    if (
        admin_session
        and admin_session.get("user_id") == user.id
        and not admin_session.get("used")
        and _normalize_phone(admin_session.get("phone_number")) == expected_phone
    ):
        admin_session["verified"] = True
        cache.set(f"admin_session:{payload}", admin_session, timeout=1800)
        web_link = f"{API_BASE_URL}{reverse('admin_check')}?session={payload}"
        message = f"Admin Telegram tasdiqlandi. Sahifani oching:\n{web_link}"
    else:
        message = "Login sessiyasi yaroqsiz yoki allaqachon ishlatilgan."

    cache.delete(f"telegram_pending:{telegram_id}")
    update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())


def text_handler(update: Update, context: CallbackContext):
    if update.message and update.message.text:
        update.message.reply_text("Telefon raqamni faqat 'Telefon raqamni yuborish' tugmasi orqali yuboring.")


def main():
    max_retries = 5
    retry_delay = 5
    for attempt in range(max_retries):
        try:
            updater = Updater(BOT_TOKEN, use_context=True)
            dp = updater.dispatcher
            dp.add_handler(CommandHandler("start", start_handler))
            dp.add_handler(MessageHandler(Filters.contact, contact_handler))
            dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))
            logger.info(f"Starting bot polling (attempt {attempt + 1}/{max_retries})...")
            updater.start_polling()
            updater.idle()
            break
        except (
            requests.exceptions.RequestException,
            TelegramError,
        ) as e:
            logger.error(f"Network or Telegram API error during polling (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.critical("Max retries reached. Bot could not start polling. Exiting.")
                sys.exit(1)


if __name__ == "__main__":
    main()
