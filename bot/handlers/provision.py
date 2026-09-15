"""
/create and /cancel handlers — the core VPS provisioning flow.
"""

import asyncio
import logging
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.config import (
    ADMIN_USER_IDS,
    VPS_PLAN_ID,
    VPS_REGION,
    VPS_IMAGE_ID,
    MAX_SERVERS_PER_USER,
)
from bot.services.factory import get_provider
from bot.services.rate_limiter import check_rate_limit, record_create
from bot.services.encryption import encrypt
from bot.db.repository import (
    create_server_record,
    update_server_status,
    count_active_servers,
    log_audit,
)

logger = logging.getLogger(__name__)

_pending_creates: dict[int, bool] = {}  # user_id → waiting for confirmation


def _is_authorised(user_id: int) -> bool:
    """Only admin users may provision servers."""
    return user_id in ADMIN_USER_IDS


def _is_private(update: Update) -> bool:
    return update.effective_chat and update.effective_chat.type == "private"


async def create_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    # ── Guards ────────────────────────────────────────────
    if not _is_private(update):
        await update.message.reply_text(
            "⛔ Server creation is only allowed in <b>private chat</b>.",
            parse_mode="HTML",
        )
        return

    if not _is_authorised(user_id):
        await update.message.reply_text("⛔ You are not authorised to create servers.")
        return

    allowed, remaining = check_rate_limit(user_id)
    if not allowed:
        await update.message.reply_text(
            f"⏳ Rate limit: please wait <b>{remaining}s</b> before creating another server.",
            parse_mode="HTML",
        )
        return

    active = count_active_servers(user_id)
    if active >= MAX_SERVERS_PER_USER:
        await update.message.reply_text(
            f"⛔ You already have <b>{active}</b> active server(s). "
            f"Maximum allowed: {MAX_SERVERS_PER_USER}.",
            parse_mode="HTML",
        )
        return

    # ── Show spec & ask for confirmation ──────────────────
    spec_text = (
        "📋 <b>Server Specification</b>\n\n"
        f"🖥 OS: Windows Server\n"
        f"📍 Region: <code>{VPS_REGION or 'default'}</code>\n"
        f"📦 Plan: <code>{VPS_PLAN_ID or 'default'}</code>\n"
        f"💿 Image: <code>{VPS_IMAGE_ID or 'default'}</code>\n\n"
        "Do you want to proceed?"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Confirm", callback_data="confirm_create"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_create"),
            ]
        ]
    )

    _pending_creates[user_id] = True
    await update.message.reply_text(spec_text, parse_mode="HTML", reply_markup=keyboard)


async def confirm_create_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if user_id not in _pending_creates:
        await query.edit_message_text("⚠️ No pending create request found.")
        return

    del _pending_creates[user_id]

    # Double-check authorisation
    if not _is_authorised(user_id):
        await query.edit_message_text("⛔ Unauthorised.")
        return

    allowed, remaining = check_rate_limit(user_id)
    if not allowed:
        await query.edit_message_text(
            f"⏳ Rate limit: wait {remaining}s."
        )
        return

    await query.edit_message_text(
        "⏳ <b>Provisioning your Windows VPS…</b>", parse_mode="HTML"
    )

    provider = get_provider()
    server_name = f"vps-{user_id}-{int(asyncio.get_event_loop().time())}"

    try:
        info = await asyncio.wait_for(
            provider.create_server(
                name=server_name,
                region=VPS_REGION,
                plan_id=VPS_PLAN_ID,
                image_id=VPS_IMAGE_ID,
            ),
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        logger.error("Provider create_server timed out")
        await query.edit_message_text(
            "⏱ Server creation timed out. Try again later."
        )
        log_audit(user_id, "create", detail="TIMEOUT")
        return
    except Exception as exc:
        logger.error("Provider create_server failed: %s", type(exc).__name__)
        await query.edit_message_text(
            f"❌ Server creation failed: {type(exc).__name__}. Please try again later or contact an admin."
        )
        log_audit(user_id, "create", detail=f"FAILED: {type(exc).__name__}: {str(exc)[:100]}")
        return

    # Record the server
    record_create(user_id)
    create_server_record(
        user_id=user_id,
        provider_server_id=info.server_id,
        server_name=info.name,
        region=info.region,
        plan=info.plan,
    )
    log_audit(user_id, "create", target_server_id=info.server_id)

    # ── Poll until active (max ~120s) ────────────────────
    for attempt in range(24):
        if info.status == "active" and info.ip_address:
            break
        await asyncio.sleep(5)
        try:
            info = await asyncio.wait_for(
                provider.get_server_status(info.server_id), timeout=15.0
            )
        except Exception as e:
            logger.debug("Status check %d failed: %s", attempt, e)
            continue

    # ── Retrieve IP & password ────────────────────────────
    ip = info.ip_address or ""
    password = info.password or ""

    if not ip:
        try:
            ip = await asyncio.wait_for(provider.get_server_ip(info.server_id), timeout=15.0)
        except Exception as e:
            logger.warning("Failed to get IP: %s", e)

    if not password:
        try:
            password = await asyncio.wait_for(
                provider.get_initial_password(info.server_id), timeout=15.0
            )
        except Exception as e:
            logger.warning("Failed to get password: %s", e)

    # Store encrypted password (or skip if no key)
    enc_pw = encrypt(password)
    update_server_status(
        provider_server_id=info.server_id,
        status="active" if ip else "creating",
        ip_address=ip,
        encrypted_password=enc_pw,
    )

    if not ip or not password:
        await query.edit_message_text(
            f"⚠️ Server <code>{info.server_id}</code> is still provisioning.\n"
            f"Status: <code>{info.status}</code>\n"
            "Use /status to check later.",
            parse_mode="HTML",
        )
        return

    # ── Send RDP credentials (private chat only) ─────────
    rdp_text = (
        "✅ <b>Your Windows VPS is ready!</b>\n\n"
        f"🏷 Server Name: <code>{info.name}</code>\n"
        f"🆔 Server ID: <code>{info.server_id}</code>\n"
        f"🌐 IP: <code>{ip}</code>\n"
        f"🔌 Protocol: RDP\n"
        f"🚪 Port: <code>3389</code>\n"
        f"👤 Username: <code>{info.username}</code>\n"
        f"🔑 Password: <tg-spoiler>{password}</tg-spoiler>\n\n"
        "⚠️ <b>Change your password immediately after first login!</b>"
    )

    await query.edit_message_text(rdp_text, parse_mode="HTML")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel any pending operation."""
    try:
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            user_id = update.effective_user.id
            _pending_creates.pop(user_id, None)
            await query.edit_message_text("❌ Operation cancelled.")
        else:
            user_id = update.effective_user.id
            removed = _pending_creates.pop(user_id, None)
            if removed:
                await update.message.reply_text("❌ Pending server creation cancelled.")
            else:
                await update.message.reply_text("ℹ️ Nothing to cancel.")
    except Exception as e:
        logger.error("Cancel error: %s", e)
