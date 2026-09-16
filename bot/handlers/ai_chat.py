"""AI chat handler: multimodal inputs, fast streaming edits and fair metering."""
import logging
import time

from telegram.constants import ChatAction

from bot.database import get_db
from bot.i18n import t
from bot.security import esc, check_flood, check_duplicate, MAX_MESSAGE_CHARS
from bot.services.ai_manager import ai_manager, AIError
from bot.services.subscription import subscription_manager, OK, EXPIRED
from bot.handlers.common import (
    lang_of, safe_edit, reply, parse_callback, clear_flow, set_flow, send_kwargs,
)
from bot.media import prepare_attachment, MediaError
from bot import keyboards as kb

logger = logging.getLogger(__name__)


def _active_model_name(user_id, context):
    chosen = context.user_data.get("model_pk")
    model = ai_manager.resolve_model(model_pk=chosen, user_id=user_id)
    return (model or {}).get("name")


def _answer_body(answer, model_name, lang, remaining, usage=None):
    answer = str(answer or "")
    usage = usage or {}
    tokens = int(usage.get("total_tokens") or 0)
    estimate_mark = " ~" if usage.get("estimated") else ""
    meta = "<i>🤖 %s · %s: %s · %s%s</i>" % (
        esc(model_name), t("btn_account", lang), remaining,
        t("ai_tokens", lang), estimate_mark + str(tokens),
    )
    body = "%s\n\n%s" % (esc(answer), meta)
    if len(body) > 4096:
        body = esc(answer)[:3900] + "\n\n<i>…</i>"
    return body


async def open_ai(update, context):
    query = update.callback_query
    if query:
        await query.answer()
    lang = lang_of(update, context)
    clear_flow(context)
    models = ai_manager.list_models(user_id=update.effective_user.id)
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
    models = ai_manager.list_models(user_id=update.effective_user.id)
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
    if not model or not model["status"] or not ai_manager.is_model_allowed(update.effective_user.id, model):
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


async def _edit_answer(placeholder, answer, model_name, lang, remaining, usage):
    if not placeholder:
        return
    try:
        await placeholder.edit_text(
            _answer_body(answer, model_name, lang, remaining, usage), **send_kwargs())
    except Exception:
        # Telegram can reject an intermediate edit while a message is changing;
        # the final edit/send in handle_prompt still delivers the answer.
        logger.debug("stream edit failed", exc_info=True)


async def handle_prompt(update, context):
    """Handle text, photos and supported documents outside another flow."""
    lang = lang_of(update, context)
    user_id = update.effective_user.id
    message = update.effective_message
    db = get_db()

    is_attachment = bool(getattr(message, "photo", None) or getattr(message, "document", None))
    prompt = (getattr(message, "text", None) or getattr(message, "caption", None) or "").strip()
    if is_attachment:
        try:
            max_bytes = max(1, db.get_int_setting("max_file_mb", 10)) * 1024 * 1024
            prompt, _label = await prepare_attachment(
                message, context.bot, max_bytes,
                default_prompt=t("attachment_default_prompt", lang),
            )
        except MediaError as exc:
            return await reply(update, t("attachment_error", lang, detail=esc(str(exc))))
        except Exception as exc:
            logger.warning("attachment download failed for user %s: %s", user_id, exc)
            return await reply(update, t("attachment_error", lang, detail=t("generic_error", lang)))
    elif not prompt:
        return None

    # Text length applies to the visible request, while extracted files have a
    # larger internal cap in media.py.
    visible_prompt = "".join(
        item.get("text", "") for item in prompt if isinstance(item, dict)
    ) if isinstance(prompt, list) else prompt
    if len(visible_prompt) > MAX_MESSAGE_CHARS and not is_attachment:
        return await reply(update, t("msg_too_long", lang, max=MAX_MESSAGE_CHARS))

    allowed, retry_after = check_flood(user_id)
    if not allowed:
        return await reply(update, t("rate_limited", lang, seconds=retry_after))
    if not check_duplicate(user_id, visible_prompt):
        return await reply(update, t("spam_duplicate", lang))

    state, _sub = subscription_manager.status(user_id)
    if state == EXPIRED:
        return await reply(update, t("sub_expired", lang),
                           kb.account_menu(lang, db.get_bool_setting("shop_enabled", True)))
    if state != OK:
        return await reply(update, t("quota_exhausted", lang),
                           kb.account_menu(lang, db.get_bool_setting("shop_enabled", True)))

    if not ai_manager.list_models(user_id=user_id):
        return await reply(update, t("ai_no_models", lang), kb.back_to_main(lang))

    placeholder = await reply(update, t("ai_thinking", lang))
    try:
        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
    except Exception:
        pass

    stream_state = {"answer": "", "last_edit": 0.0}
    interval = max(100, db.get_int_setting("stream_edit_interval_ms", 700)) / 1000.0
    stream_enabled = db.get_bool_setting("ai_streaming", True)

    async def on_delta(delta):
        stream_state["answer"] += str(delta or "")
        now = time.monotonic()
        if now - stream_state["last_edit"] >= interval:
            stream_state["last_edit"] = now
            await _edit_answer(
                placeholder, stream_state["answer"],
                _active_model_name(user_id, context) or "AI", lang,
                subscription_manager.remaining(user_id), ai_manager.last_usage(user_id),
            )

    try:
        answer, model_name = await ai_manager.chat(
            user_id, prompt, model_pk=context.user_data.get("model_pk"),
            stream_callback=on_delta if stream_enabled else None,
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

    usage = ai_manager.last_usage(user_id)
    subscription_manager.consume(user_id, tokens=usage.get("total_tokens", 0))
    remaining = subscription_manager.remaining(user_id)
    body = _answer_body(answer, model_name, lang, remaining, usage)

    if placeholder:
        try:
            await placeholder.edit_text(body, **send_kwargs())
            return placeholder
        except Exception:
            pass
    return await reply(update, body)
