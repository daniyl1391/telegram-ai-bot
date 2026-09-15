"""The single text/photo entry point.

The old bot registered no MessageHandler whatsoever, so every plain message was
dropped on the floor. This router decides what a non-command message means based
on the user's current flow, and falls through to AI chat by default.
"""
import logging

from bot.database import get_db
from bot.i18n import t
from bot.security import is_admin
from bot.handlers.common import lang_of, reply, get_flow, clear_flow
from bot import keyboards as kb

logger = logging.getLogger(__name__)

ADMIN_FLOWS = {
    "admin_usearch", "admin_quota", "admin_dm", "admin_add_model", "admin_medit",
    "admin_add_product", "admin_pedit", "admin_setcard", "admin_setholder",
    "admin_setting", "admin_tkreply", "admin_bcast",
}
SUPPORT_FLOWS = {"support_new", "support_reply"}


async def route_message(update, context):
    from bot.handlers import admin as admin_handlers
    from bot.handlers import support as support_handlers
    from bot.handlers import shop as shop_handlers
    from bot.handlers import ai_chat

    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return None

    db = get_db()
    # Keep the user row fresh; also makes the very first message self-healing
    # if /start was somehow skipped (e.g. added via a deep link).
    db.add_user(user.id, user.username or "", user.first_name or "")
    lang = lang_of(update, context)

    if db.is_banned(user.id):
        logger.info("Ignoring message from banned user %s", user.id)
        return await reply(update, t("banned", lang))

    flow = get_flow(context) or {}
    name = flow.get("name")

    if name in ADMIN_FLOWS:
        if not is_admin(user.id):
            clear_flow(context)
            return await reply(update, t("not_authorized", lang))
        return await admin_handlers.handle_admin_text(update, context, flow)

    if name in SUPPORT_FLOWS:
        return await support_handlers.handle_message(update, context)

    if name == "await_receipt":
        return await shop_handlers.handle_receipt(update, context)

    if message.photo or message.document:
        # A stray attachment with no open payment order.
        return await reply(update, t("pay_no_pending", lang), kb.back_to_main(lang))

    return await ai_chat.handle_prompt(update, context)


async def unknown_command(update, context):
    lang = lang_of(update, context)
    return await reply(update, t("unknown_action", lang), kb.back_to_main(lang))
