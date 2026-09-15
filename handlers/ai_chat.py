"""AI chat: the feature the old bot advertised but never wired up.

There was no MessageHandler at all, so typing to the bot did nothing and
ai_manager.chat() was never called from anywhere.
"""
import logging

from telegram.constants import ChatAction

from bot.database import get_db
from bot.i18n import t
from bot.security import esc, check_flood, check_duplicate, MAX_MESSAGE_CHARS
from bot.services.ai_manager import ai_manager, AIError
from bot.services.subscription import subscription_manager, OK, EXPIRED
from bot.handlers.common import (
    lang_of, safe_edit, reply, parse_callback, clear_flow, set_flow, send_kwargs,
)
from bot import keyboards as kb

logger = logging.getLogger(__name__)


def _active_model_name(user_id, context):
    chosen = context.user_data.get("model_pk")
    model = ai_manager.resolve_model(model_pk=chosen)
    return (model or {}).get("name")


async def open_ai(update, context):
    query = update.callback_query
    if query:
        await query.answer()
    lang = lang_of(update, context)
    clear_flow(context)
    models = ai_manager.list_models()
    if not models:
        text = t("ai_no_models", lang)
        markup = kb.back_to_main(lang)
    else:
        set_flow(context, "ai_chat")
        text = t(
            "ai_start", lang,
            model=esc(_active_model_name(update.effective_user.id, context) or "-"),
            remaining=subscription_manager.remaining(update.effective_user.id),
        )
        markup = kb.ai_menu(lang, has_multiple_models=len(models) > 1)
    if query:
        return await safe_edit(query, text, markup)
    return await reply(update, text, markup)


async def model_picker(update, context):
    query = update.callback_query
    await query.answer()
    lang = lang_of(update, context)
    models = ai_manager.list_models()
    if not models:
        return await safe_edit(query, t("ai_no_models", lang), kb.back_to_main(lang))
    active = _active_model_name(update.effective_user.id, context)
    return await safe_edit(query, t("ai_choose_model", lang),
                           kb.ai_model_picker(lang, models, active))


async def model_use(update, context):
    query = update.callback_query
    lang = lang_of(update, context)
    _, args = parse_callback(query.data)
    try:
        model_pk = int(args[-1])
    except (ValueError, IndexError):
        await query.answer(t("unknown_action", lang), show_alert=True)
        return None
    model = get_db().get_ai_model(model_pk)
    if not model or not model["status"]:
        await query.answer(t("unknown_action", lang), show_alert=True)
        return None
    context.user_data["model_pk"] = model_pk
    ai_manager.clear_history(update.effective_user.id)
    await query.answer(t("ai_model_selected", lang, model=model["name"]))
    return await open_ai(update, context)


async def clear_history(update, context):
    query = update.callback_query
    lang = lang_of(update, context)
    ai_manager.clear_history(update.effective_user.id)
    await query.answer(t("ai_history_cleared", lang))
    return await open_ai(update, context)


async def handle_prompt(update, context):
    """Called by the text router for any plain message that is not part of a flow."""
    lang = lang_of(update, context)
    user_id = update.effective_user.id
    message = update.effective_message
    prompt = (message.text or "").strip()

    if not prompt:
        return None
    if len(prompt) > MAX_MESSAGE_CHARS:
        return await reply(update, t("msg_too_long", lang, max=MAX_MESSAGE_CHARS))

    allowed, retry_after = check_flood(user_id)
    if not allowed:
        return await reply(update, t("rate_limited", lang, seconds=retry_after))
    if not check_duplicate(user_id, prompt):
        return await reply(update, t("spam_duplicate", lang))

    state, _sub = subscription_manager.status(user_id)
    if state == EXPIRED:
        return await reply(update, t("sub_expired", lang),
                           kb.account_menu(lang, get_db().get_bool_setting("shop_enabled", True)))
    if state != OK:
        return await reply(update, t("quota_exhausted", lang),
                           kb.account_menu(lang, get_db().get_bool_setting("shop_enabled", True)))

    if not ai_manager.list_models():
        return await reply(update, t("ai_no_models", lang), kb.back_to_main(lang))

    placeholder = await reply(update, t("ai_thinking", lang))
    try:
        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
    except Exception:
        pass  # chat action is cosmetic, never fail the request over it

    try:
        answer, model_name = await ai_manager.chat(
            user_id, prompt, model_pk=context.user_data.get("model_pk")
        )
    except AIError as exc:
        logger.warning("AI failed for user %s: %s", user_id, exc)
        text = t("ai_failed", lang, detail=esc(str(exc)))
        if placeholder:
            try:
                await placeholder.edit_text(text, **send_kwargs())
                return placeholder
            except Exception:
                pass
        return await reply(update, text)

    # Only charge the user once the provider actually answered.
    subscription_manager.consume(user_id)
    remaining = subscription_manager.remaining(user_id)
    body = "%s\n\n<i>🤖 %s · %s: %s</i>" % (
        esc(answer), esc(model_name), t("btn_account", lang), remaining
    )
    if len(body) > 4096:
        body = esc(answer)[:3900] + "\n\n<i>…</i>"

    if placeholder:
        try:
            await placeholder.edit_text(body, **send_kwargs())
            return placeholder
        except Exception:
            pass
    return await reply(update, body)
