"""Entry point.

Every callback_data string produced anywhere in bot/keyboards.py is registered
here. tests.py cross-checks the two lists, so a dead button (the old build had
ten of them) fails the test suite instead of shipping.
"""
import logging

from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters,
)

from bot.config import (
    TELEGRAM_BOT_TOKEN, ADMIN_USER_IDS, LOG_LEVEL, DB_PATH, die_if_misconfigured,
)
from bot.database import get_db
from bot.handlers import admin as admin_handlers
from bot.handlers import ai_chat, shop, start as start_handlers, support
from bot.handlers.errors import error_handler
from bot.handlers.router import route_message, unknown_command

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=getattr(logging, LOG_LEVEL, logging.INFO),
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext.Application").setLevel(logging.INFO)

logger = logging.getLogger("bot")


def build_application(token=None):
    """Assemble the Application. Kept separate from main() so tests can inspect
    the registered handlers without starting a network connection."""
    app = Application.builder().token(token or TELEGRAM_BOT_TOKEN).build()
    register_handlers(app)
    return app


def register_handlers(app):
    # ------------------------------------------------------------- commands
    app.add_handler(CommandHandler("start", start_handlers.start))
    app.add_handler(CommandHandler("help", start_handlers.help_command))
    app.add_handler(CommandHandler("menu", start_handlers.start))
    app.add_handler(CommandHandler("account", start_handlers.account))
    app.add_handler(CommandHandler("language", start_handlers.language_command))
    app.add_handler(CommandHandler("shop", shop.shop_list))
    app.add_handler(CommandHandler("support", support.support_open))
    app.add_handler(CommandHandler("admin", admin_handlers.admin_command))

    # ------------------------------------------------------------ callbacks
    app.add_handler(CallbackQueryHandler(start_handlers.nav, pattern=r"^nav:"))
    app.add_handler(CallbackQueryHandler(start_handlers.language_menu, pattern=r"^lang:menu$"))
    app.add_handler(CallbackQueryHandler(start_handlers.language_set, pattern=r"^lang:(fa|en)$"))
    app.add_handler(CallbackQueryHandler(start_handlers.account, pattern=r"^acct:view$"))

    app.add_handler(CallbackQueryHandler(ai_chat.open_ai, pattern=r"^ai:open$"))
    app.add_handler(CallbackQueryHandler(ai_chat.model_picker, pattern=r"^ai:models$"))
    app.add_handler(CallbackQueryHandler(ai_chat.clear_history, pattern=r"^ai:clear$"))
    app.add_handler(CallbackQueryHandler(ai_chat.model_use, pattern=r"^ai:use:\d+$"))

    app.add_handler(CallbackQueryHandler(shop.shop_list, pattern=r"^shop:list$"))
    app.add_handler(CallbackQueryHandler(shop.shop_item, pattern=r"^shop:item:\d+$"))
    app.add_handler(CallbackQueryHandler(shop.shop_buy, pattern=r"^shop:buy:\d+$"))
    app.add_handler(CallbackQueryHandler(shop.pay_card, pattern=r"^pay:card:\d+$"))
    app.add_handler(CallbackQueryHandler(shop.pay_gateway, pattern=r"^pay:gw:\d+$"))

    app.add_handler(CallbackQueryHandler(support.support_open, pattern=r"^sup:open$"))
    app.add_handler(CallbackQueryHandler(support.support_new, pattern=r"^sup:new$"))
    app.add_handler(CallbackQueryHandler(support.support_mine, pattern=r"^sup:mine$"))
    app.add_handler(CallbackQueryHandler(support.support_view, pattern=r"^sup:view:\d+$"))
    app.add_handler(CallbackQueryHandler(support.support_reply, pattern=r"^sup:reply:\d+$"))

    # One guarded router for the entire admin panel.
    app.add_handler(CallbackQueryHandler(admin_handlers.admin_callback, pattern=r"^adm:"))

    # -------------------------------------------------------------- messages
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND,
        route_message,
    ))

    # ---------------------------------------------------------------- errors
    app.add_error_handler(error_handler)
    return app


def main():
    die_if_misconfigured()

    db = get_db()
    logger.info("Database ready at %s", DB_PATH)
    logger.info("Admins: %s", ", ".join(str(i) for i in ADMIN_USER_IDS))
    if not db.get_ai_models():
        logger.warning(
            "No AI model configured yet. Open the bot, send /admin, then "
            "AI Models -> Add model to set one up."
        )

    app = build_application()
    logger.info("Starting polling...")
    # drop_pending_updates avoids replaying a backlog after a Railway redeploy.
    app.run_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
