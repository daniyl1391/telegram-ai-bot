"""Shared helpers for handlers: language, safe message editing and the FSM.

The old bot had no state machine at all, which is why nothing in the admin panel
could ever accept input (no way to type an API key or a product price). Flows
are stored in context.user_data so they are per-user and survive between
messages without a global.
"""
import logging

from telegram.error import BadRequest
from telegram.constants import ParseMode

from bot.database import get_db
from bot.i18n import t
from bot.security import is_admin
from bot import keyboards as kb

logger = logging.getLogger(__name__)

FLOW_KEY = "flow"

# Link previews off everywhere: an AI answer full of URLs should not explode into
# preview cards. LinkPreviewOptions is the current API (Bot API 7.0 / PTB 20.8+);
# the fallback keeps this working on older PTB releases.
try:
    from telegram import LinkPreviewOptions

    _NO_PREVIEW = {"link_preview_options": LinkPreviewOptions(is_disabled=True)}
except ImportError:  # pragma: no cover - PTB < 20.8
    _NO_PREVIEW = {"disable_web_page_preview": True}


def send_kwargs(reply_markup=None):
    kwargs = dict(_NO_PREVIEW)
    kwargs["parse_mode"] = ParseMode.HTML
    if reply_markup is not None:
        kwargs["reply_markup"] = reply_markup
    return kwargs


# ------------------------------------------------------------------- language
def lang_of(update, context=None):
    user = update.effective_user
    if user is None:
        return "fa"
    if context is not None:
        cached = context.user_data.get("lang")
        if cached:
            return cached
    language = get_db().get_language(user.id)
    if context is not None:
        context.user_data["lang"] = language
    return language


# ----------------------------------------------------------------- FSM helpers
def set_flow(context, name, step=None, **data):
    context.user_data[FLOW_KEY] = {"name": name, "step": step, "data": data}


def get_flow(context):
    return context.user_data.get(FLOW_KEY)


def update_flow(context, step=None, **data):
    flow = context.user_data.get(FLOW_KEY)
    if not flow:
        return None
    if step is not None:
        flow["step"] = step
    flow["data"].update(data)
    return flow


def clear_flow(context):
    context.user_data.pop(FLOW_KEY, None)


# --------------------------------------------------------------- send / edit
async def safe_edit(query, text, reply_markup=None):
    """Edit a message, tolerating Telegram's "message is not modified" error."""
    try:
        await query.edit_message_text(text, **send_kwargs(reply_markup))
        return True
    except BadRequest as exc:
        message = str(exc).lower()
        if "not modified" in message:
            return True
        if "no text in the message" in message or "message can't be edited" in message:
            # The original message was a photo (a payment receipt), so reply instead.
            try:
                await query.message.reply_text(text, **send_kwargs(reply_markup))
                return True
            except Exception:
                logger.exception("safe_edit fallback failed")
                return False
        logger.warning("safe_edit failed: %s", exc)
        return False


async def reply(update, text, reply_markup=None):
    target = update.effective_message
    if target is None:
        return None
    return await target.reply_text(text, **send_kwargs(reply_markup))


async def show_main_menu(update, context, edit=False, prefix=None):
    """Render the main menu, from either a command or a callback."""
    from bot.services.subscription import subscription_manager

    db = get_db()
    user = update.effective_user
    lang = lang_of(update, context)
    clear_flow(context)

    state, sub = subscription_manager.status(user.id)
    plan_key = "plan_premium" if (sub and sub.get("plan") != "free") else "plan_free"
    text = t(
        "welcome", lang,
        name=(user.first_name or "").strip() or str(user.id),
        plan=t(plan_key, lang),
        remaining=subscription_manager.remaining(user.id),
    )
    if prefix:
        text = prefix + "\n\n" + text
    markup = kb.main_menu(
        lang,
        is_admin_user=is_admin(user.id),
        shop_on=db.get_bool_setting("shop_enabled", True),
        support_on=db.get_bool_setting("support_enabled", True),
    )
    if edit and update.callback_query:
        return await safe_edit(update.callback_query, text, markup)
    return await reply(update, text, markup)


def parse_callback(data):
    """'adm:medit:api_key:7' -> ('adm', ['medit', 'api_key', '7'])"""
    parts = (data or "").split(":")
    return (parts[0] if parts else ""), parts[1:]
