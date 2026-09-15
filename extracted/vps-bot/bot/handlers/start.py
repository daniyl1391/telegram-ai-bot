"""
/start and /help command handlers.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

WELCOME_TEXT = (
    "🖥 <b>Windows VPS Bot</b>\n\n"
    "This bot provisions Windows VPS instances on demand.\n\n"
    "<b>Available commands:</b>\n"
    "/create — Create a new Windows VPS\n"
    "/status — List your active servers\n"
    "/reboot <code>SERVER_ID</code> — Reboot your server\n"
    "/delete <code>SERVER_ID</code> — Delete your server\n"
    "/cancel — Cancel the current operation\n"
    "/help — Show this help message\n\n"
    "⚠️ <b>Rules:</b>\n"
    "• Server creation is only available in <b>private chat</b>.\n"
    "• Do not share your RDP credentials with anyone.\n"
    "• Change the default password immediately after first login.\n"
    "• Abuse will result in permanent ban."
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_TEXT, parse_mode="HTML")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_TEXT, parse_mode="HTML")
