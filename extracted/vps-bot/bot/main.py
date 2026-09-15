"""
Entry-point for the Telegram VPS Bot.
Supports both Webhook (Railway with public URL) and Polling modes.
Railway works best with polling (no need for public URL).
"""

import logging
import asyncio
import signal
import sys
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
)

from bot.config import TELEGRAM_BOT_TOKEN, WEBHOOK_URL, PORT
from bot.handlers.start import start_command, help_command
from bot.handlers.provision import (
    create_command,
    confirm_create_callback,
    cancel_command,
)
from bot.handlers.status import status_command, reboot_command, delete_command
from bot.db.database import init_db

# ── Logging ──────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class _SensitiveFilter(logging.Filter):
    """Mask passwords & tokens that accidentally reach log output."""

    KEYWORDS = ("password", "token", "secret", "api_key", "encryption_key")

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage().lower()
        for kw in self.KEYWORDS:
            if kw in msg:
                record.msg = "[REDACTED — sensitive content masked]"
                record.args = None
        return True


for handler in logging.root.handlers:
    handler.addFilter(_SensitiveFilter())


async def main() -> None:
    """Main entry point."""
    # Initialise database tables
    init_db()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # ── Command handlers ──────────────────────────────────
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("create", create_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("reboot", reboot_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(CommandHandler("cancel", cancel_command))

    # Inline-keyboard callbacks
    app.add_handler(
        CallbackQueryHandler(confirm_create_callback, pattern=r"^confirm_create$")
    )
    app.add_handler(
        CallbackQueryHandler(cancel_command, pattern=r"^cancel_create$")
    )

    # ── Graceful shutdown ─────────────────────────────────
    def signal_handler(sig, frame):
        logger.info("Received signal %s, shutting down gracefully", sig)
        app.stop()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # ── Start ─────────────────────────────────────────────
    try:
        if WEBHOOK_URL:
            logger.info("Starting bot in WEBHOOK mode on port %s", PORT)
            await app.bot.set_webhook(
                url=f"{WEBHOOK_URL}/webhook",
                allowed_updates=[
                    "message",
                    "callback_query",
                    "poll",
                    "poll_answer",
                ],
            )
            await app.run_webhook(
                listen="0.0.0.0",
                port=PORT,
                url_path="webhook",
                webhook_url=f"{WEBHOOK_URL}/webhook",
            )
        else:
            logger.info("Starting bot in POLLING mode (Railway-friendly)")
            await app.run_polling(
                drop_pending_updates=True,
                allowed_updates=[
                    "message",
                    "callback_query",
                    "poll",
                    "poll_answer",
                ],
            )
    except Exception as e:
        logger.error("Fatal error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
