"""Support tickets. The tables existed in the old build; the feature did not."""
import logging

from bot.config import ADMIN_USER_IDS
from bot.database import get_db, parse_iso
from bot.i18n import t
from bot.security import esc, check_flood, check_duplicate, MAX_MESSAGE_CHARS
from bot.capabilities import FEATURE_MAP, enabled as capability_enabled
from bot.handlers.common import (
    lang_of, safe_edit, reply, parse_callback, set_flow, clear_flow, get_flow,
)
from bot import keyboards as kb

logger = logging.getLogger(__name__)


async def support_open(update, context):
    query = update.callback_query
    if query:
        await query.answer()
    lang = lang_of(update, context)
    clear_flow(context)
    if not capability_enabled(update.effective_user.id, "support_tickets"):
        text, markup = t("feature_disabled", lang, feature=FEATURE_MAP["support_tickets"].label(lang)), kb.back_to_main(lang)
    elif not get_db().get_bool_setting("support_enabled", True):
        text, markup = t("support_disabled", lang), kb.back_to_main(lang)
    else:
        text, markup = t("support_title", lang), kb.support_menu(lang)
    if query:
        return await safe_edit(query, text, markup)
    return await reply(update, text, markup)


async def support_new(update, context):
    query = update.callback_query
    lang = lang_of(update, context)
    if not capability_enabled(update.effective_user.id, "support_tickets"):
        await query.answer(t("feature_disabled", lang, feature=FEATURE_MAP["support_tickets"].label(lang)), show_alert=True)
        return None
    if not get_db().get_bool_setting("support_enabled", True):
        await query.answer(t("support_disabled", lang), show_alert=True)
        return None
    await query.answer()
    set_flow(context, "support_new")
    return await safe_edit(query, t("support_ask_message", lang), kb.cancel_only(lang))


async def support_mine(update, context):
    query = update.callback_query
    await query.answer()
    lang = lang_of(update, context)
    tickets = get_db().list_tickets(user_id=update.effective_user.id, limit=10)
    if not tickets:
        return await safe_edit(query, t("support_no_tickets", lang), kb.support_menu(lang))
    return await safe_edit(query, t("support_title", lang),
                           kb.ticket_list_menu(lang, tickets))


def render_ticket(lang, ticket, messages, admin_view=False):
    lines = []
    for msg in messages:
        who = "👑" if msg["is_admin"] else "👤"
        when = parse_iso(msg["created_at"])
        stamp = when.strftime("%m-%d %H:%M") if when else ""
        lines.append("%s <i>%s</i>\n%s" % (who, stamp, esc(msg["message"])))
    body = "\n\n".join(lines) or "-"
    if len(body) > 3500:
        body = body[-3500:]
    return t("support_ticket_view", lang,
             ticket_id=ticket["id"],
             status=t("status_" + (ticket["status"] or "open"), lang),
             messages=body)


async def support_view(update, context):
    query = update.callback_query
    lang = lang_of(update, context)
    _, args = parse_callback(query.data)
    db = get_db()
    ticket = db.get_ticket(_int(args[-1]))
    if not ticket or ticket["user_id"] != update.effective_user.id:
        await query.answer(t("not_authorized", lang), show_alert=True)
        return None
    await query.answer()
    text = render_ticket(lang, ticket, db.get_ticket_messages(ticket["id"]))
    return await safe_edit(query, text, kb.ticket_view_menu(lang, ticket["id"]))


async def support_reply(update, context):
    query = update.callback_query
    lang = lang_of(update, context)
    _, args = parse_callback(query.data)
    ticket = get_db().get_ticket(_int(args[-1]))
    if not ticket or ticket["user_id"] != update.effective_user.id:
        await query.answer(t("not_authorized", lang), show_alert=True)
        return None
    if ticket["status"] == "closed":
        await query.answer(t("status_closed", lang), show_alert=True)
        return None
    await query.answer()
    set_flow(context, "support_reply", ticket_id=ticket["id"])
    return await safe_edit(query, t("support_ask_message", lang), kb.cancel_only(lang))


async def handle_message(update, context):
    """Router entry for support_new / support_reply flows."""
    lang = lang_of(update, context)
    flow = get_flow(context) or {}
    name = flow.get("name")
    data = flow.get("data") or {}
    text = (update.effective_message.text or "").strip()
    user = update.effective_user
    db = get_db()

    if not text:
        return await reply(update, t("invalid_input", lang, reason=t("v_too_short", lang, min=1)))
    if len(text) > MAX_MESSAGE_CHARS:
        return await reply(update, t("msg_too_long", lang, max=MAX_MESSAGE_CHARS))
    allowed, retry_after = check_flood(user.id)
    if not allowed:
        return await reply(update, t("rate_limited", lang, seconds=retry_after))
    if not check_duplicate(user.id, text):
        return await reply(update, t("spam_duplicate", lang))

    if name == "support_reply":
        ticket_id = data.get("ticket_id")
        ticket = db.get_ticket(ticket_id)
        if not ticket or ticket["user_id"] != user.id:
            clear_flow(context)
            return await reply(update, t("unknown_action", lang), kb.back_to_main(lang))
        db.add_ticket_message(ticket_id, user.id, text, is_admin=False)
    else:
        subject = text[:60]
        ticket_id = db.create_ticket(user.id, subject, text)

    clear_flow(context)
    await _notify_admins(context, ticket_id, user, text)
    return await reply(update, t("support_ticket_created", lang, ticket_id=ticket_id),
                       kb.back_to_main(lang))


async def _notify_admins(context, ticket_id, user, text):
    for admin_id in ADMIN_USER_IDS:
        admin_lang = get_db().get_language(admin_id)
        body = "🎫 <b>#%s</b> — 👤 %s (<code>%s</code>)\n\n%s" % (
            ticket_id, esc(user.first_name or user.id), user.id, esc(text[:500]))
        try:
            await context.bot.send_message(
                admin_id, body, parse_mode="HTML",
                reply_markup=kb.ticket_view_menu(admin_lang, ticket_id, is_admin_view=True))
        except Exception as exc:
            logger.warning("Could not notify admin %s about ticket: %s", admin_id, exc)


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
