import os
import sys
import logging
import secrets
import random
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)
from dotenv import load_dotenv
from pathlib import Path
import time
import requests
from telegram.error import (
    TelegramError,
)

load_dotenv()

THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", os.getenv("DJANGO_SETTINGS_MODULE", "config.settings")
)
import django

django.setup()

from users.models import CustomUser
from django.core.cache import cache
from django.urls import reverse

load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
BOT_TOKEN = os.getenv("AUTH_BOT_TOKEN", "")
if not BOT_TOKEN:
    logger.critical(
        "BOT_TOKEN not found in environment variables. Please set AUTH_BOT_TOKEN. Exiting."
    )
    sys.exit(1)


def start_handler(update: Update, context: CallbackContext):
    telegram_id = update.message.from_user.id

    try:
        user = CustomUser.objects.get(telegram_id=str(telegram_id))
        otp = str(random.randint(100000, 999999))

        if user.is_staff:
            session_id = secrets.token_urlsafe(16)
            cache.set(f"admin_session:{session_id}", {'otp': otp, 'user_id': user.id}, timeout=300)
            deeplink = f"{API_BASE_URL}{reverse('admin_check')}?session={session_id}&otp={otp}"
            update.message.reply_text(
                f"Salom, {user.full_name or 'Admin'}!\n\n"
                f"Dashboardga kirish uchun quyidagi havolani bosing:\n\n"
                f"{deeplink}\n\n"
                f"⚠️ Bu havola 5 daqiqa davomida amal qiladi."
            )
        else:
            cache.set(f"otp_code:{user.email or user.phone_number}", otp, timeout=300)
            update.message.reply_text(f"Sizning kodingiz: {otp}")

    except CustomUser.DoesNotExist:
        update.message.reply_text("Siz tizimda ro'yxatdan o'tmagansiz. Iltimos, avval ro'yxatdan o'ting.")
    except Exception as e:
        logger.error(f"Error in start_handler for user {telegram_id}: {e}")
        update.message.reply_text(f"Xatolik yuz berdi: {e}")


def main():
    max_retries = 5
    retry_delay = 5
    for attempt in range(max_retries):
        try:
            updater = Updater(BOT_TOKEN, use_context=True)
            dp = updater.dispatcher
            dp.add_handler(CommandHandler("start", start_handler))
            logger.info(
                f"Starting bot polling (attempt {attempt + 1}/{max_retries})..."
            )
            updater.start_polling()
            updater.idle()
            break
        except (
            requests.exceptions.RequestException,
            TelegramError,
        ) as e:
            logger.error(
                f"Network or Telegram API error during polling (attempt {attempt + 1}/{max_retries}): {e}"
            )
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.critical(
                    "Max retries reached. Bot could not start polling. Exiting."
                )
                sys.exit(1)


if __name__ == "__main__":
    main()