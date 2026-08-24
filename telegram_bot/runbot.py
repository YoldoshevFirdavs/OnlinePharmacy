import importlib
import logging
import os
import sys

import django
from dotenv import load_dotenv
from telegram.ext import CallbackQueryHandler, CommandHandler, Filters, MessageHandler, Updater

# 1. Loglarni terminalda chiroyli ko'rish uchun sozlama
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. .env faylini yuklash
load_dotenv()
BOT_TOKEN = os.getenv("MAIN_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

# 3. Django muhitini sozlama
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Django-ni ishga tushirish
from django.apps import apps

if not apps.ready:
    django.setup()

import telegram_bot.bot_routes
import telegram_bot.handlers
import telegram_bot.messages

_HANDLERS_LOADED = False


def reload_bot_handlers(dispatcher, force_reload=False):
    global _HANDLERS_LOADED
    if _HANDLERS_LOADED and not force_reload:
        return

    try:
        # Fayllarni yangidan yuklash
        importlib.reload(telegram_bot.messages)
        importlib.reload(telegram_bot.bot_routes)
        importlib.reload(telegram_bot.handlers)

        if 0 in dispatcher.handlers:
            dispatcher.handlers[0].clear()

        routes = telegram_bot.bot_routes.ROUTES
        handlers_mod = telegram_bot.handlers

        for route in routes:
            h_func = getattr(handlers_mod, route["handler"], None)
            if not h_func:
                continue

            if route["type"] == "command":
                dispatcher.add_handler(CommandHandler(route["trigger"], h_func), group=0)
            elif route["type"] == "callback":
                dispatcher.add_handler(CallbackQueryHandler(h_func, pattern=route["trigger"]), group=0)
            elif route["type"] == "message":
                if route["trigger"] == "contact":
                    dispatcher.add_handler(MessageHandler(Filters.contact, h_func), group=0)

        _HANDLERS_LOADED = True
        logger.info("🤖 Tizim (Handlerlar va Matnlar) muvaffaqiyatli yangilandi!")
    except Exception as e:
        logger.error(f"❌ Reload xatosi: {e}", exc_info=True)


def admin_refresh_bot(update, context):
    if str(update.effective_user.id) != str(ADMIN_ID):
        return
    reload_bot_handlers(context.dispatcher, force_reload=True)
    update.message.reply_text("✅ Bot kodi va matnlari yangilandi!")


def main():
    if not BOT_TOKEN:
        logger.error("🚫 BOT_TOKEN topilmadi!")
        return

    updater = Updater(token=BOT_TOKEN)
    dispatcher = updater.dispatcher

    from telegram_bot.handlers import ban_command, unban_command

    dispatcher.add_handler(MessageHandler(Filters.regex("^/refresh$"), admin_refresh_bot), group=1)
    dispatcher.add_handler(MessageHandler(Filters.regex("^/ban"), ban_command), group=1)
    dispatcher.add_handler(MessageHandler(Filters.regex("^/unban"), unban_command), group=1)

    reload_bot_handlers(dispatcher)

    from telegram import BotCommand

    commands = [
        BotCommand("start", "Botni ishga tushirish"),
        BotCommand("help", "Yordam markazi"),
        BotCommand("about", "Biz haqimizda"),
        BotCommand("terms", "Foydalanish shartlari"),
        BotCommand("lang", "Tilni o'zgartirish"),
    ]
    updater.bot.set_my_commands(commands)

    logger.info("🚀 Bot polling rejimida start oldi...")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
