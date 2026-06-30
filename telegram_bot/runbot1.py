import os
import sys
import django
import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from dotenv import load_dotenv

# Django setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.otp_service import get_session_meta, create_otp_session, bind_session_to_user
from users.models import CustomUser

load_dotenv()
BOT_TOKEN = os.getenv("AUTH_BOT_TOKEN")
WEB_APP_URL = os.getenv("WEB_APP_URL", "http://localhost:8000")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_handler(update: Update, context: CallbackContext):
    args = context.args
    if not args:
        update.message.reply_text("Iltimos, veb-saytdan kiring.")
        return

    session_id = args[0]
    meta = get_session_meta(session_id)
    
    if not meta:
        update.message.reply_text("Sessiya topilmadi yoki muddati tugagan.")
        return

    context.user_data["session_id"] = session_id
    context.user_data["identifier"] = meta["identifier"]
    context.user_data["purpose"] = meta["purpose"] # Store purpose to differentiate flows

    btn = [[KeyboardButton("📲 Telefon raqamni yuborish", request_contact=True)]]
    update.message.reply_text("Tasdiqlash uchun telefon raqamingizni yuboring:", reply_markup=ReplyKeyboardMarkup(btn, one_time_keyboard=True, resize_keyboard=True))

def contact_handler(update: Update, context: CallbackContext):
    if not update.message.contact: return

    session_id = context.user_data.get("session_id")
    identifier = context.user_data.get("identifier")
    purpose = context.user_data.get("purpose")

    if not session_id or not identifier or not purpose:
        update.message.reply_text("Xatolik! Veb-saytdan qayta boshlang.")
        return

    phone_number = update.message.contact.phone_number
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number

    if purpose == "admin_telegram_login":
        try:
            admin_user = CustomUser.objects.get(phone_number=phone_number, is_staff=True)
            # Create a new session for the check_admin.html redirect
            new_session = create_otp_session(purpose="admin_check_redirect")
            bind_session_to_user(new_session.session_id, admin_user.id, admin_user.email or admin_user.phone_number)
            
            deeplink = f"{WEB_APP_URL}/admin/check/?session_id={new_session.session_id}"
            update.message.reply_text(
                f"Admin tasdiqlash uchun ushbu linkni bosing: {deeplink}\n\n"
                f"Ushbu linkni brauzeringizda oching va ma'lumotlaringizni kiriting."
            )
            logger.info(f"Admin deeplink sent for {phone_number} with session_id: {new_session.session_id}")
        except CustomUser.DoesNotExist:
            update.message.reply_text("Bu telefon raqam bilan admin topilmadi.")
            logger.warning(f"Admin user not found for Telegram login with phone number: {phone_number}")
        except Exception as e:
            update.message.reply_text("Admin login jarayonida xatolik yuz berdi.")
            logger.error(f"Error during admin Telegram login for {phone_number}: {e}")
    else:

        update.message.reply_text("Bu funksiya hozirda faqat adminlar uchun ishlaydi.")
        logger.info(f"Non-admin Telegram login attempt for {phone_number} with purpose {purpose}")


def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start_handler))
    dp.add_handler(MessageHandler(Filters.contact, contact_handler))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()