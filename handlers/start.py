"""/start, language selection, account view and generic navigation."""
import logging

from bot.database import get_db, parse_iso
from bot.i18n import t, LANGUAGES
from bot.security import is_admin
from bot.services.subscription import subscription_manager
from bot.handlers.common import (
    lang_of, safe_edit, reply, show_main_menu, clear_flow, parse_callback,
)
from bot import keyboards as kb

logger = logging.getLogger(__name__)


async def start(update, context):
    db = get_db()
    user = update.effective_user
    is_new = db.add_user(user.id, user.username or "", user.first_name or "")
    subscription_manager.ensure_subscription(user.id)
    clear_flow(context)
    context.user_data.pop("lang", None)

    if db.is_banned(user.id):
        return await reply(update, t("banned", db.get_language(user.id)))

    if is_new:
        # First contact: ask for a language before anything else.
        return await reply(update, t("lang_choose", "fa") + "\n" + t("lang_choose", "en"),
                           kb.language_menu())
    return await show_main_menu(update, context)


async def language_menu(update, context):
    query = update.callback_query
    await query.answer()
    lang = lang_of(update, context)
    return await safe_edit(query, t("lang_choose", lang), kb.language_menu())


async def language_set(update, context):
    query = update.callback_query
    _, args = parse_callback(query.data)
    code = args[0] if args else "fa"
    if code not in LANGUAGES:
        code = "fa"
    get_db().set_language(update.effective_user.id, code)
    context.user_data["lang"] = code
    await query.answer(t("lang_saved", code))
    return await show_main_menu(update, context, edit=True, prefix=t("lang_saved", code))


async def account(update, context):
    query = update.callback_query
    if query:
        await query.answer()
    lang = lang_of(update, context)
    db = get_db()
    user_id = update.effective_user.id
    state, sub = subscription_manager.status(user_id)
    expire = parse_iso(sub.get("expire_date")) if sub else None
    plan_key = "plan_premium" if (sub and sub.get("plan") != "free") else "plan_free"
    text = t(
        "account_title", lang,
        user_id=user_id,
        plan=t(plan_key, lang),
        used=int(sub.get("message_used") or 0) if sub else 0,
        limit=int(sub.get("message_limit") or 0) if sub else 0,
        remaining=subscription_manager.remaining(user_id),
        expire=expire.strftime("%Y-%m-%d %H:%M UTC") if expire else t("never", lang),
    )
    if state == "expired":
        text += "\n\n" + t("sub_expired", lang)
    elif state == "exhausted":
        text += "\n\n" + t("quota_exhausted", lang)
    markup = kb.account_menu(lang, shop_on=db.get_bool_setting("shop_enabled", True))
    if query:
        return await safe_edit(query, text, markup)
    return await reply(update, text, markup)


async def nav(update, context):
    """nav:main and nav:cancel."""
    query = update.callback_query
    _, args = parse_callback(query.data)
    action = args[0] if args else "main"
    lang = lang_of(update, context)
    if action == "cancel":
        clear_flow(context)
        await query.answer(t("cancelled", lang))
        return await show_main_menu(update, context, edit=True)
    await query.answer()
    return await show_main_menu(update, context, edit=True)


async def help_command(update, context):
    lang = lang_of(update, context)
    lines = [
        t("main_menu_title", lang),
        "",
        "/start — " + t("btn_main_menu", lang),
        "/account — " + t("btn_account", lang),
        "/shop — " + t("btn_shop", lang),
        "/support — " + t("btn_support", lang),
        "/language — " + t("btn_language", lang),
    ]
    if is_admin(update.effective_user.id):
        lines.append("/admin — " + t("btn_admin_panel", lang))
    return await reply(update, "\n".join(lines), kb.back_to_main(lang))


async def language_command(update, context):
    lang = lang_of(update, context)
    return await reply(update, t("lang_choose", lang), kb.language_menu())
