"""
/status, /reboot, /delete command handlers.
"""

import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import ADMIN_USER_IDS
from bot.services.factory import get_provider
from bot.db.repository import (
    get_user_servers,
    get_server_by_provider_id,
    mark_server_deleted,
    log_audit,
)

logger = logging.getLogger(__name__)


def _is_authorised(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS


def _sanitize_server_id(raw: str) -> str | None:
    """Allow only alphanumeric, hyphens, and underscores."""
    cleaned = raw.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", cleaned):
        return cleaned
    return None


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if not _is_authorised(user_id):
        await update.message.reply_text("⛔ Unauthorised.")
        return

    servers = get_user_servers(user_id)
    if not servers:
        await update.message.reply_text("ℹ️ You have no active servers.")
        return

    lines = ["📋 <b>Your Servers</b>\n"]
    for s in servers:
        lines.append(
            f"• <code>{s.provider_server_id}</code>  "
            f"Status: <b>{s.status}</b>  "
            f"IP: <code>{s.ip_address or 'pending'}</code>"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def reboot_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if not _is_authorised(user_id):
        await update.message.reply_text("⛔ Unauthorised.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /reboot <code>SERVER_ID</code>", parse_mode="HTML")
        return

    server_id = _sanitize_server_id(context.args[0])
    if not server_id:
        await update.message.reply_text("⛔ Invalid server ID format.")
        return

    # Ownership check
    rec = get_server_by_provider_id(server_id, user_id)
    if not rec:
        await update.message.reply_text("⛔ Server not found or does not belong to you.")
        return

    provider = get_provider()
    try:
        ok = await provider.reboot_server(server_id)
    except Exception as exc:
        logger.error("Reboot failed: %s", exc)
        ok = False

    log_audit(user_id, "reboot", target_server_id=server_id)

    if ok:
        await update.message.reply_text(f"🔄 Server <code>{server_id}</code> is rebooting.", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Reboot failed. Try again later.")


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if not _is_authorised(user_id):
        await update.message.reply_text("⛔ Unauthorised.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /delete <code>SERVER_ID</code>", parse_mode="HTML")
        return

    server_id = _sanitize_server_id(context.args[0])
    if not server_id:
        await update.message.reply_text("⛔ Invalid server ID format.")
        return

    # Ownership check
    rec = get_server_by_provider_id(server_id, user_id)
    if not rec:
        await update.message.reply_text("⛔ Server not found or does not belong to you.")
        return

    provider = get_provider()
    try:
        ok = await provider.delete_server(server_id)
    except Exception as exc:
        logger.error("Delete failed: %s", exc)
        ok = False

    if ok:
        mark_server_deleted(server_id)
        log_audit(user_id, "delete", target_server_id=server_id)
        await update.message.reply_text(f"🗑 Server <code>{server_id}</code> deleted.", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Deletion failed. Try again later.")
