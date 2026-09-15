import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from dotenv import load_dotenv

from bot.config import TELEGRAM_BOT_TOKEN
from bot.handlers.start import start, account
from bot.handlers.admin import admin_menu, admin_stats

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_menu))
    
    app.add_handler(CallbackQueryHandler(account, pattern="^account$"))
    app.add_handler(CallbackQueryHandler(admin_stats, pattern="^admin_stats$"))
    
    logger.info("Bot started polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
