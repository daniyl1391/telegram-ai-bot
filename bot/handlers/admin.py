"""The in-Telegram admin panel.

In the old build, six of the seven admin buttons had no handler at all, and
bot/admin/panel.py (add model / add product / set default) was never imported by
anything, so every "manage from the panel" claim was fiction. Everything below
is reachable and does real work.

Access is enforced by @admin_only on both entry points, and every callback is
re-checked, so a leaked callback_data string is useless to a non-admin.
"""
import logging

from bot.database import get_db, parse_iso, utcnow
from bot.i18n import t
from bot.security import (
    admin_only, is_admin, esc, mask_secret, format_card, ValidationError,
    validate_int, validate_url, validate_text, validate_card, validate_api_key,
    MAX_DESC_CHARS, MAX_NAME_CHARS,
)
from bot.services.ai_manager import ai_manager
from bot.services.payment import payment_manager, PaymentError
from bot.services.subscription import subscription_manager
from bot.handlers.common import (
    lang_of, safe_edit, reply, parse_callback, set_flow, clear_flow, update_flow,
)
from bot.handlers.support import render_ticket
from bot import keyboards as kb
from bot.admin import panel as admin_ops

logger = logging.getLogger(__name__)

USERS_PER_PAGE = 8

NUMERIC_SETTINGS = {
    "free_message_limit": (1, 1000000),
    "free_period_days": (1, 3650),
    "rate_limit_messages": (0, 1000),
    "rate_limit_seconds": (0, 3600),
    "ai_max_history": (0, 50),
    "free_token_limit": (0, 1000000000),
    "stream_edit_interval_ms": (100, 5000),
    "ai_max_output_tokens": (0, 100000),
    "max_file_mb": (1, 50),
    "ai_timeout_seconds": (5, 300),
    "ai_max_retries": (1, 10),
}


def _money(value):
    try:
        return "{:,}".format(int(value or 0))
    except (TypeError, ValueError):
        return str(value)


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_quota_mode(raw):
    value = str(raw or "").strip().lower()
    aliases = {"پیام": "messages", "توکن": "tokens", "هر دو": "both", "both": "both"}
    value = aliases.get(value, value)
    if value not in ("messages", "tokens", "both"):
        raise ValidationError("v_bad_quota_mode")
    return value


def _quota_label(mode, token_count, lang):
    mode = str(mode or "messages").lower()
    label = t("quota_mode_" + mode if mode in ("messages", "tokens", "both") else "quota_mode_messages", lang)
    if mode in ("tokens", "both") and int(token_count or 0):
        label += " (%s)" % _money(token_count)
    return label


# ------------------------------------------------------------------ entrypoints
@admin_only
async def admin_command(update, context):
    clear_flow(context)
    return await _render_home(update, context, edit=False)


async def _render_home(update, context, edit=True):
    lang = lang_of(update, context)
    db = get_db()
    text = t("admin_title", lang,
             users=db.count_users(),
             models=len(db.get_ai_models(only_active=False)),
             products=len(db.get_products(only_active=False)),
             pending=db.count_payments("pending"),
             tickets=db.count_tickets(open_only=True))
    markup = kb.admin_home(lang)
    if edit and update.callback_query:
        return await safe_edit(update.callback_query, text, markup)
    return await reply(update, text, markup)


@admin_only
async def admin_callback(update, context):
    """Single router for every adm:* callback."""
    query = update.callback_query
    lang = lang_of(update, context)
    _, args = parse_callback(query.data)
    action = args[0] if args else "home"
    rest = args[1:]

    handler = _ROUTES.get(action)
    if handler is None:
        await query.answer(t("unknown_action", lang), show_alert=True)
        return None
    return await handler(update, context, lang, rest)


# ----------------------------------------------------------------------- home
async def _home(update, context, lang, rest):
    await update.callback_query.answer()
    clear_flow(context)
    return await _render_home(update, context)


async def _stats(update, context, lang, rest):
    await update.callback_query.answer()
    db = get_db()
    midnight = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    text = t("admin_stats_body", lang,
             users=db.count_users(),
             users_today=db.count_users_since(midnight),
             active_subs=db.count_active_subscriptions(),
             messages=db.count_ai_messages(),
             tokens=db.total_ai_tokens(),
             revenue=_money(db.total_revenue()),
             pending=db.count_payments("pending"),
             tickets_open=db.count_tickets(open_only=True))
    return await safe_edit(update.callback_query, text, kb.admin_back(lang))


# ---------------------------------------------------------------------- users
async def _users(update, context, lang, rest):
    await update.callback_query.answer()
    db = get_db()
    page = max(0, _int(rest[0] if rest else 0))
    total = db.count_users()
    pages = max(1, (total + USERS_PER_PAGE - 1) // USERS_PER_PAGE)
    page = min(page, pages - 1)
    users = db.list_users(limit=USERS_PER_PAGE, offset=page * USERS_PER_PAGE)
    text = t("admin_users_title", lang, page=page + 1, pages=pages)
    markup = kb.admin_users_menu(lang, users, page, page > 0, (page + 1) * USERS_PER_PAGE < total)
    return await safe_edit(update.callback_query, text, markup)


def _user_detail_text(lang, user_id):
    db = get_db()
    user = db.get_user(user_id)
    if not user:
        return None
    sub = subscription_manager.ensure_subscription(user_id) or {}
    expire = parse_iso(sub.get("expire_date"))
    joined = parse_iso(user.get("created_at"))
    plan_key = "plan_premium" if sub.get("plan") not in (None, "free") else "plan_free"
    return t("admin_user_detail", lang,
             name=esc(user.get("first_name") or user_id),
             user_id=user_id,
             username=("@" + user["username"]) if user.get("username") else "-",
             ulang=user.get("language") or "fa",
             state=t("state_banned" if user.get("is_banned") else "state_active", lang),
             joined=joined.strftime("%Y-%m-%d") if joined else "-",
             plan=t(plan_key, lang),
             used=_int(sub.get("message_used")),
             limit=_int(sub.get("message_limit")),
             expire=expire.strftime("%Y-%m-%d") if expire else t("never", lang))


async def _user(update, context, lang, rest):
    query = update.callback_query
    user_id = _int(rest[0] if rest else 0)
    text = _user_detail_text(lang, user_id)
    if text is None:
        await query.answer(t("admin_user_not_found", lang), show_alert=True)
        return None
    await query.answer()
    banned = get_db().is_banned(user_id)
    return await safe_edit(query, text, kb.admin_user_menu(lang, user_id, banned))


async def _usearch(update, context, lang, rest):
    await update.callback_query.answer()
    set_flow(context, "admin_usearch")
    return await safe_edit(update.callback_query, t("admin_ask_search_user", lang),
                           kb.cancel_only(lang))


async def _quota(update, context, lang, rest):
    await update.callback_query.answer()
    user_id = _int(rest[0] if rest else 0)
    set_flow(context, "admin_quota", user_id=user_id)
    return await safe_edit(update.callback_query, t("admin_ask_quota", lang),
                           kb.cancel_only(lang))


async def _policy(update, context, lang, rest):
    user_id = _int(rest[0] if rest else 0)
    if not get_db().get_user(user_id):
        await update.callback_query.answer(t("admin_user_not_found", lang), show_alert=True)
        return None
    await update.callback_query.answer()
    set_flow(context, "admin_user_policy", step="mode", user_id=user_id)
    return await safe_edit(update.callback_query, t("admin_ask_quota_mode", lang),
                           kb.cancel_only(lang))


async def _ban(update, context, lang, rest):
    query = update.callback_query
    db = get_db()
    user_id = _int(rest[0] if rest else 0)
    if not db.get_user(user_id):
        await query.answer(t("admin_user_not_found", lang), show_alert=True)
        return None
    if is_admin(user_id):
        await query.answer(t("not_authorized", lang), show_alert=True)
        return None
    db.set_banned(user_id, not db.is_banned(user_id))
    await query.answer(t("admin_user_updated", lang))
    return await _user(update, context, lang, rest)


async def _grant(update, context, lang, rest):
    query = update.callback_query
    await query.answer()
    user_id = _int(rest[0] if rest else 0)
    products = get_db().get_products(only_active=False)
    if not products:
        return await safe_edit(query, t("admin_products_empty", lang),
                               kb.admin_back(lang, "adm:user:%s" % user_id))
    return await safe_edit(query, t("btn_grant", lang),
                           kb.admin_grant_menu(lang, user_id, products))


async def _grantp(update, context, lang, rest):
    query = update.callback_query
    user_id = _int(rest[0] if len(rest) > 0 else 0)
    product = get_db().get_product(_int(rest[1] if len(rest) > 1 else 0))
    if not product:
        await query.answer(t("unknown_action", lang), show_alert=True)
        return None
    messages = _int(product["messages_count"]) or 1000
    subscription_manager.grant_plan(
        user_id, "premium", messages, _int(product["duration_days"], 30),
        quota_mode=product.get("quota_mode", "messages"),
        token_limit=_int(product.get("token_count"), 0),
        model_scope=product.get("model_scope", "all"),
    )
    await query.answer(t("admin_user_updated", lang))
    try:
        user_lang = get_db().get_language(user_id)
        sub = get_db().get_subscription(user_id) or {}
        expire = parse_iso(sub.get("expire_date"))
        await context.bot.send_message(
            user_id,
            t("pay_approved_user", user_lang,
              plan=t("plan_premium", user_lang), messages=messages,
              expire=expire.strftime("%Y-%m-%d") if expire else t("never", user_lang)),
            parse_mode="HTML")
    except Exception as exc:
        logger.warning("grant notice failed for %s: %s", user_id, exc)
    return await _user(update, context, lang, [user_id])


async def _dm(update, context, lang, rest):
    await update.callback_query.answer()
    user_id = _int(rest[0] if rest else 0)
    set_flow(context, "admin_dm", user_id=user_id)
    return await safe_edit(update.callback_query, t("admin_ask_dm", lang), kb.cancel_only(lang))


# ------------------------------------------------------------------ ai models
async def _models(update, context, lang, rest):
    await update.callback_query.answer()
    models = get_db().get_ai_models(only_active=False)
    listing = "\n".join(
        "%s %s <code>%s</code>" % ("⭐️" if m["is_default"] else "▫️", esc(m["name"]),
                                   esc(m["model_id"]))
        for m in models) or t("admin_models_empty", lang)
    return await safe_edit(update.callback_query,
                           t("admin_models_title", lang, list=listing),
                           kb.admin_models_menu(lang, models))


async def _model(update, context, lang, rest):
    query = update.callback_query
    model = get_db().get_ai_model(_int(rest[0] if rest else 0))
    if not model:
        await query.answer(t("unknown_action", lang), show_alert=True)
        return await _models(update, context, lang, [])
    await query.answer()
    text = t("admin_model_detail", lang,
             name=esc(model["name"]),
             api_url=esc(model["api_url"]),
             api_key=esc(mask_secret(model["api_key"])),  # never the real key
             model_id=esc(model["model_id"]),
             status=t("on" if model["status"] else "off", lang),
             is_default=t("yes" if model["is_default"] else "no", lang))
    return await safe_edit(query, text, kb.admin_model_menu(lang, model["id"]))


async def _addmodel(update, context, lang, rest):
    await update.callback_query.answer()
    set_flow(context, "admin_add_model", step="name")
    return await safe_edit(update.callback_query, t("admin_model_ask_name", lang),
                           kb.cancel_only(lang))


_MODEL_FIELD_PROMPTS = {
    "name": "admin_model_ask_name",
    "api_url": "admin_model_ask_url",
    "api_key": "admin_model_ask_key",
    "model_id": "admin_model_ask_id",
}


async def _medit(update, context, lang, rest):
    query = update.callback_query
    field = rest[0] if rest else ""
    model_pk = _int(rest[1] if len(rest) > 1 else 0)
    if field not in _MODEL_FIELD_PROMPTS or not get_db().get_ai_model(model_pk):
        await query.answer(t("unknown_action", lang), show_alert=True)
        return None
    await query.answer()
    set_flow(context, "admin_medit", step=field, model_pk=model_pk)
    return await safe_edit(query, t(_MODEL_FIELD_PROMPTS[field], lang), kb.cancel_only(lang))


async def _mtest(update, context, lang, rest):
    query = update.callback_query
    model_pk = _int(rest[0] if rest else 0)
    await query.answer(t("admin_testing", lang))
    ok, detail, ms = await ai_manager.test_connection(model_pk)
    if ok:
        text = t("admin_model_test_ok", lang, ms=ms, sample=esc(detail))
    else:
        text = t("admin_model_test_fail", lang, detail=esc(detail))
    return await safe_edit(query, text, kb.admin_model_menu(lang, model_pk))


async def _mdefault(update, context, lang, rest):
    query = update.callback_query
    model_pk = _int(rest[0] if rest else 0)
    name = get_db().set_default_ai_model(model_pk)
    if not name:
        await query.answer(t("unknown_action", lang), show_alert=True)
        return None
    await query.answer(t("admin_model_default_set", lang, name=name))
    return await _model(update, context, lang, [model_pk])


async def _mtoggle(update, context, lang, rest):
    query = update.callback_query
    db = get_db()
    model_pk = _int(rest[0] if rest else 0)
    model = db.get_ai_model(model_pk)
    if not model:
        await query.answer(t("unknown_action", lang), show_alert=True)
        return None
    db.update_ai_model(model_pk, status=0 if model["status"] else 1)
    await query.answer(t("admin_setting_saved", lang))
    return await _model(update, context, lang, [model_pk])


async def _mdel(update, context, lang, rest):
    query = update.callback_query
    get_db().delete_ai_model(_int(rest[0] if rest else 0))
    await query.answer(t("admin_model_deleted", lang))
    return await _models(update, context, lang, [])


# -------------------------------------------------------------------- products
async def _products(update, context, lang, rest):
    await update.callback_query.answer()
    products = get_db().get_products(only_active=False)
    listing = "\n".join(
        "▫️ %s — <b>%s</b> / %sd / %s✉️" % (esc(p["name"]), _money(p["price"]),
                                            p["duration_days"], p["messages_count"])
        for p in products) or t("admin_products_empty", lang)
    return await safe_edit(update.callback_query,
                           t("admin_products_title", lang, list=listing),
                           kb.admin_products_menu(lang, products))


async def _product(update, context, lang, rest):
    query = update.callback_query
    product = get_db().get_product(_int(rest[0] if rest else 0))
    if not product:
        await query.answer(t("unknown_action", lang), show_alert=True)
        return await _products(update, context, lang, [])
    await query.answer()
    text = t("admin_product_detail", lang,
             name=esc(product["name"]),
             description=esc(product["description"] or "-"),
             price=_money(product["price"]),
             days=product["duration_days"],
             messages=product["messages_count"],
             quota=_quota_label(product.get("quota_mode"), product.get("token_count"), lang),
             models=esc(product.get("model_scope") or "all"),
             status=t("on" if product["status"] else "off", lang))
    return await safe_edit(query, text, kb.admin_product_menu(lang, product["id"]))


async def _addproduct(update, context, lang, rest):
    await update.callback_query.answer()
    set_flow(context, "admin_add_product", step="name")
    return await safe_edit(update.callback_query, t("admin_product_ask_name", lang),
                           kb.cancel_only(lang))


_PRODUCT_FIELD_PROMPTS = {
    "name": "admin_product_ask_name",
    "price": "admin_product_ask_price",
    "duration_days": "admin_product_ask_days",
    "messages_count": "admin_product_ask_messages",
    "quota_mode": "admin_ask_text",
    "token_count": "admin_ask_number",
    "model_scope": "admin_ask_text",
    "description": "admin_product_ask_desc",
}


async def _pedit(update, context, lang, rest):
    query = update.callback_query
    field = rest[0] if rest else ""
    product_id = _int(rest[1] if len(rest) > 1 else 0)
    if field not in _PRODUCT_FIELD_PROMPTS or not get_db().get_product(product_id):
        await query.answer(t("unknown_action", lang), show_alert=True)
        return None
    await query.answer()
    set_flow(context, "admin_pedit", step=field, product_id=product_id)
    return await safe_edit(query, t(_PRODUCT_FIELD_PROMPTS[field], lang), kb.cancel_only(lang))


async def _ptoggle(update, context, lang, rest):
    query = update.callback_query
    db = get_db()
    product_id = _int(rest[0] if rest else 0)
    product = db.get_product(product_id)
    if not product:
        await query.answer(t("unknown_action", lang), show_alert=True)
        return None
    db.update_product(product_id, status=0 if product["status"] else 1)
    await query.answer(t("admin_setting_saved", lang))
    return await _product(update, context, lang, [product_id])


async def _pdel(update, context, lang, rest):
    query = update.callback_query
    get_db().delete_product(_int(rest[0] if rest else 0))
    await query.answer(t("admin_product_deleted", lang))
    return await _products(update, context, lang, [])


# -------------------------------------------------------------------- payments
async def _payments(update, context, lang, rest):
    await update.callback_query.answer()
    db = get_db()
    pending = db.list_payments(status="pending", limit=10)
    if not pending:
        listing = t("admin_payments_empty", lang)
    else:
        listing = "\n".join(
            "🧾 #%s — %s — <code>%s</code>" % (p["id"], _money(p["amount"]), p["user_id"])
            for p in pending)
    return await safe_edit(update.callback_query,
                           t("admin_payments_title", lang, list=listing),
                           kb.admin_payments_menu(lang, pending))


async def _payment(update, context, lang, rest):
    query = update.callback_query
    db = get_db()
    payment = db.get_payment(_int(rest[0] if rest else 0))
    if not payment:
        await query.answer(t("unknown_action", lang), show_alert=True)
        return await _payments(update, context, lang, [])
    await query.answer()
    user = db.get_user(payment["user_id"]) or {}
    product = db.get_product(payment["product_id"]) or {}
    created = parse_iso(payment["created_at"])
    receipt = payment.get("receipt_value")
    if payment.get("receipt_type") in ("photo", "document"):
        receipt = "📎 " + (payment["receipt_type"])
    text = t("admin_payment_detail", lang,
             payment_id=payment["id"],
             name=esc(user.get("first_name") or "-"),
             user_id=payment["user_id"],
             product=esc(product.get("name") or "-"),
             amount=_money(payment["amount"]),
             method=esc(payment.get("payment_method") or "-"),
             status=t("status_" + (payment.get("status") or "pending"), lang),
             created=created.strftime("%Y-%m-%d %H:%M") if created else "-",
             receipt=esc(receipt or "-"))
    return await safe_edit(query, text,
                           kb.admin_payment_menu(lang, payment["id"],
                                                 payment["status"] == "pending"))


async def _papprove(update, context, lang, rest):
    query = update.callback_query
    payment_id = _int(rest[0] if rest else 0)
    try:
        payment, product, sub = payment_manager.approve(payment_id, update.effective_user.id)
    except PaymentError as exc:
        await query.answer(str(exc), show_alert=True)
        return await _payments(update, context, lang, [])
    await query.answer(t("admin_payment_approved", lang, payment_id=payment_id))
    try:
        user_lang = get_db().get_language(payment["user_id"])
        expire = parse_iso((sub or {}).get("expire_date"))
        await context.bot.send_message(
            payment["user_id"],
            t("pay_approved_user", user_lang,
              plan=t("plan_premium", user_lang),
              messages=(sub or {}).get("message_limit", "-"),
              expire=expire.strftime("%Y-%m-%d") if expire else t("never", user_lang)),
            parse_mode="HTML")
    except Exception as exc:
        logger.warning("approval notice failed: %s", exc)
    return await _payments(update, context, lang, [])


async def _preject(update, context, lang, rest):
    query = update.callback_query
    payment_id = _int(rest[0] if rest else 0)
    try:
        payment = payment_manager.reject(payment_id, update.effective_user.id)
    except PaymentError as exc:
        await query.answer(str(exc), show_alert=True)
        return await _payments(update, context, lang, [])
    await query.answer(t("admin_payment_rejected", lang, payment_id=payment_id))
    try:
        user_lang = get_db().get_language(payment["user_id"])
        await context.bot.send_message(
            payment["user_id"],
            t("pay_rejected_user", user_lang, payment_id=payment_id), parse_mode="HTML")
    except Exception as exc:
        logger.warning("rejection notice failed: %s", exc)
    return await _payments(update, context, lang, [])


async def _payset(update, context, lang, rest):
    await update.callback_query.answer()
    db = get_db()
    card = db.get_setting("card_number")
    text = t("admin_payment_settings", lang,
             card=format_card(card) if card else t("not_set", lang),
             holder=esc(db.get_setting("card_holder") or t("not_set", lang)),
             gateway=t("on" if db.get_bool_setting("gateway_enabled") else "off", lang))
    return await safe_edit(update.callback_query, text,
                           kb.admin_payment_settings_menu(
                               lang, db.get_bool_setting("gateway_enabled")))


async def _setcard(update, context, lang, rest):
    await update.callback_query.answer()
    set_flow(context, "admin_setcard")
    return await safe_edit(update.callback_query, t("admin_ask_card", lang), kb.cancel_only(lang))


async def _setholder(update, context, lang, rest):
    await update.callback_query.answer()
    set_flow(context, "admin_setholder")
    return await safe_edit(update.callback_query, t("admin_ask_holder", lang), kb.cancel_only(lang))


async def _gwtoggle(update, context, lang, rest):
    db = get_db()
    db.set_setting("gateway_enabled", "0" if db.get_bool_setting("gateway_enabled") else "1")
    await update.callback_query.answer(t("admin_setting_saved", lang))
    return await _payset(update, context, lang, rest)


# --------------------------------------------------------------------- tickets
async def _tickets(update, context, lang, rest):
    await update.callback_query.answer()
    tickets = get_db().list_tickets(open_only=True, limit=10)
    listing = "\n".join(
        "🎫 #%s — <code>%s</code> — %s" % (ti["id"], ti["user_id"],
                                           t("status_" + (ti["status"] or "open"), lang))
        for ti in tickets) or t("admin_tickets_empty", lang)
    return await safe_edit(update.callback_query,
                           t("admin_tickets_title", lang, list=listing),
                           kb.admin_tickets_menu(lang, tickets))


async def _ticket(update, context, lang, rest):
    query = update.callback_query
    db = get_db()
    ticket = db.get_ticket(_int(rest[0] if rest else 0))
    if not ticket:
        await query.answer(t("unknown_action", lang), show_alert=True)
        return await _tickets(update, context, lang, [])
    await query.answer()
    text = render_ticket(lang, ticket, db.get_ticket_messages(ticket["id"]), admin_view=True)
    return await safe_edit(query, text, kb.ticket_view_menu(lang, ticket["id"], True))


async def _tkreply(update, context, lang, rest):
    query = update.callback_query
    ticket_id = _int(rest[0] if rest else 0)
    if not get_db().get_ticket(ticket_id):
        await query.answer(t("unknown_action", lang), show_alert=True)
        return None
    await query.answer()
    set_flow(context, "admin_tkreply", ticket_id=ticket_id)
    return await safe_edit(query, t("admin_ask_reply", lang, ticket_id=ticket_id),
                           kb.cancel_only(lang))


async def _tkclose(update, context, lang, rest):
    query = update.callback_query
    get_db().close_ticket(_int(rest[0] if rest else 0))
    await query.answer(t("admin_ticket_closed", lang))
    return await _tickets(update, context, lang, [])


# -------------------------------------------------------------------- settings
async def _settings(update, context, lang, rest):
    await update.callback_query.answer()
    db = get_db()
    text = t("admin_settings_title", lang,
             free_limit=db.get_int_setting("free_message_limit", 10),
             free_tokens=db.get_int_setting("free_token_limit", 100000),
             quota_mode=_quota_label(db.get_setting("default_quota_mode", "messages"), 0, lang),
             free_days=db.get_int_setting("free_period_days", 30),
             rl_msgs=db.get_int_setting("rate_limit_messages", 5),
             rl_secs=db.get_int_setting("rate_limit_seconds", 60),
             streaming=t("on" if db.get_bool_setting("ai_streaming", True) else "off", lang),
             shop=t("on" if db.get_bool_setting("shop_enabled", True) else "off", lang),
             support=t("on" if db.get_bool_setting("support_enabled", True) else "off", lang),
             history=db.get_int_setting("ai_max_history", 8))
    return await safe_edit(update.callback_query, text,
                           kb.admin_settings_menu(lang,
                                                  db.get_bool_setting("shop_enabled", True),
                                                  db.get_bool_setting("support_enabled", True),
                                                  db.get_bool_setting("ai_streaming", True)))


async def _set(update, context, lang, rest):
    query = update.callback_query
    key = rest[0] if rest else ""
    if key not in NUMERIC_SETTINGS and key not in ("ai_system_prompt", "default_quota_mode", "default_model_scope"):
        await query.answer(t("unknown_action", lang), show_alert=True)
        return None
    await query.answer()
    set_flow(context, "admin_setting", step=key)
    prompt = "admin_ask_text" if key in ("ai_system_prompt", "default_quota_mode", "default_model_scope") else "admin_ask_number"
    return await safe_edit(query, t(prompt, lang), kb.cancel_only(lang))


async def _toggle(update, context, lang, rest):
    query = update.callback_query
    key = rest[0] if rest else ""
    if key not in ("shop_enabled", "support_enabled", "ai_streaming"):
        await query.answer(t("unknown_action", lang), show_alert=True)
        return None
    db = get_db()
    db.set_setting(key, "0" if db.get_bool_setting(key, True) else "1")
    await query.answer(t("admin_setting_saved", lang))
    return await _settings(update, context, lang, rest)


async def _bcast(update, context, lang, rest):
    await update.callback_query.answer()
    set_flow(context, "admin_bcast")
    return await safe_edit(update.callback_query, t("admin_ask_broadcast", lang),
                           kb.cancel_only(lang))


_ROUTES = {
    "home": _home, "stats": _stats,
    "users": _users, "user": _user, "usearch": _usearch, "quota": _quota, "policy": _policy,
    "ban": _ban, "grant": _grant, "grantp": _grantp, "dm": _dm,
    "models": _models, "model": _model, "addmodel": _addmodel, "medit": _medit,
    "mtest": _mtest, "mdefault": _mdefault, "mtoggle": _mtoggle, "mdel": _mdel,
    "products": _products, "product": _product, "addproduct": _addproduct,
    "pedit": _pedit, "ptoggle": _ptoggle, "pdel": _pdel,
    "payments": _payments, "payment": _payment, "papprove": _papprove,
    "preject": _preject, "payset": _payset, "setcard": _setcard,
    "setholder": _setholder, "gwtoggle": _gwtoggle,
    "tickets": _tickets, "ticket": _ticket, "tkreply": _tkreply, "tkclose": _tkclose,
    "settings": _settings, "set": _set, "toggle": _toggle, "bcast": _bcast,
}

ADMIN_ACTIONS = frozenset(_ROUTES)


# ============================================================================
# Text input for admin flows. Called by the router in handlers/router.py.
# ============================================================================
async def handle_admin_text(update, context, flow):
    lang = lang_of(update, context)
    if not is_admin(update.effective_user.id):
        clear_flow(context)
        return await reply(update, t("not_authorized", lang))

    name = flow.get("name")
    step = flow.get("step")
    data = flow.get("data") or {}
    raw = (update.effective_message.text or "").strip()
    db = get_db()

    try:
        if name == "admin_usearch":
            matches = db.find_users(raw)
            clear_flow(context)
            if not matches:
                return await reply(update, t("admin_user_not_found", lang),
                                   kb.admin_back(lang, "adm:users:0"))
            if len(matches) == 1:
                uid = matches[0]["user_id"]
                return await reply(update, _user_detail_text(lang, uid),
                                   kb.admin_user_menu(lang, uid, db.is_banned(uid)))
            return await reply(update, t("admin_users_title", lang, page=1, pages=1),
                               kb.admin_users_menu(lang, matches, 0, False, False))

        if name == "admin_quota":
            limit = validate_int(raw, minimum=0, maximum=10_000_000)
            subscription_manager.set_quota(data["user_id"], limit)
            clear_flow(context)
            uid = data["user_id"]
            return await reply(update, _user_detail_text(lang, uid),
                               kb.admin_user_menu(lang, uid, db.is_banned(uid)))

        if name == "admin_user_policy":
            if step == "mode":
                update_flow(context, step="tokens", quota_mode=_normalize_quota_mode(raw))
                return await reply(update, t("admin_ask_token_limit", lang), kb.cancel_only(lang))
            if step == "tokens":
                update_flow(context, step="scope", token_limit=validate_int(raw, 0, 1_000_000_000))
                return await reply(update, t("admin_ask_model_scope", lang), kb.cancel_only(lang))
            if step == "scope":
                scope = validate_text(raw, 1, 500)
                subscription_manager.set_policy(
                    data["user_id"], quota_mode=data.get("quota_mode"),
                    token_limit=data.get("token_limit"), model_scope=scope)
                clear_flow(context)
                uid = data["user_id"]
                return await reply(update, t("admin_policy_saved", lang),
                                   kb.admin_user_menu(lang, uid, db.is_banned(uid)))

        if name == "admin_dm":
            text = validate_text(raw, 1, 3000)
            clear_flow(context)
            try:
                await context.bot.send_message(data["user_id"], esc(text), parse_mode="HTML")
                return await reply(update, t("admin_dm_sent", lang),
                                   kb.admin_back(lang, "adm:user:%s" % data["user_id"]))
            except Exception:
                return await reply(update, t("admin_dm_failed", lang),
                                   kb.admin_back(lang, "adm:user:%s" % data["user_id"]))

        if name == "admin_add_model":
            return await _flow_add_model(update, context, lang, step, data, raw)

        if name == "admin_medit":
            value = _validate_model_field(step, raw)
            if step == "name" and db.get_ai_model_by_name(value):
                raise ValidationError("v_duplicate_name")
            db.update_ai_model(data["model_pk"], **{step: value})
            clear_flow(context)
            return await reply(update, t("admin_setting_saved", lang),
                               kb.admin_model_menu(lang, data["model_pk"]))

        if name == "admin_add_product":
            return await _flow_add_product(update, context, lang, step, data, raw)

        if name == "admin_pedit":
            value = _validate_product_field(step, raw)
            db.update_product(data["product_id"], **{step: value})
            clear_flow(context)
            return await reply(update, t("admin_setting_saved", lang),
                               kb.admin_product_menu(lang, data["product_id"]))

        if name == "admin_setcard":
            db.set_setting("card_number", validate_card(raw))
            clear_flow(context)
            return await reply(update, t("admin_setting_saved", lang),
                               kb.admin_back(lang, "adm:payset"))

        if name == "admin_setholder":
            db.set_setting("card_holder", validate_text(raw, 2, 80))
            clear_flow(context)
            return await reply(update, t("admin_setting_saved", lang),
                               kb.admin_back(lang, "adm:payset"))

        if name == "admin_setting":
            if step == "ai_system_prompt":
                db.set_setting(step, validate_text(raw, 1, 1000))
            elif step == "default_quota_mode":
                db.set_setting(step, _normalize_quota_mode(raw))
            elif step == "default_model_scope":
                db.set_setting(step, validate_text(raw, 1, 500))
            else:
                low, high = NUMERIC_SETTINGS[step]
                db.set_setting(step, validate_int(raw, low, high))
            clear_flow(context)
            return await reply(update, t("admin_setting_saved", lang),
                               kb.admin_back(lang, "adm:settings"))

        if name == "admin_tkreply":
            text = validate_text(raw, 1, 3000)
            ticket_id = data["ticket_id"]
            ticket = db.get_ticket(ticket_id)
            db.add_ticket_message(ticket_id, update.effective_user.id, text, is_admin=True)
            clear_flow(context)
            if ticket:
                try:
                    user_lang = db.get_language(ticket["user_id"])
                    await context.bot.send_message(
                        ticket["user_id"],
                        t("support_admin_reply", user_lang,
                          ticket_id=ticket_id, message=esc(text)),
                        parse_mode="HTML")
                except Exception as exc:
                    logger.warning("ticket reply delivery failed: %s", exc)
            return await reply(update, t("admin_reply_sent", lang),
                               kb.admin_back(lang, "adm:tickets"))

        if name == "admin_bcast":
            text = validate_text(raw, 1, 3000)
            clear_flow(context)
            sent = failed = 0
            for uid in db.all_user_ids():
                try:
                    await context.bot.send_message(uid, esc(text), parse_mode="HTML")
                    sent += 1
                except Exception:
                    failed += 1
            return await reply(update, t("admin_broadcast_done", lang, sent=sent, failed=failed),
                               kb.admin_back(lang))

    except ValidationError as exc:
        return await reply(update, t("invalid_input", lang, reason=exc.message(lang)),
                           kb.cancel_only(lang))

    clear_flow(context)
    return await reply(update, t("unknown_action", lang), kb.admin_back(lang))


def _validate_model_field(field, raw):
    if field == "api_url":
        return validate_url(raw)
    if field == "api_key":
        return validate_api_key(raw)
    return validate_text(raw, 1, MAX_NAME_CHARS)


def _validate_product_field(field, raw):
    if field == "price":
        return validate_int(raw, 0, 10_000_000_000)
    if field == "duration_days":
        return validate_int(raw, 1, 3650)
    if field == "messages_count":
        return validate_int(raw, 0, 10_000_000)
    if field == "token_count":
        return validate_int(raw, 0, 1_000_000_000)
    if field == "quota_mode":
        return _normalize_quota_mode(raw)
    if field == "model_scope":
        return validate_text(raw, 1, 500)
    if field == "description":
        return "" if raw == "-" else validate_text(raw, 1, MAX_DESC_CHARS)
    return validate_text(raw, 1, MAX_NAME_CHARS)


async def _flow_add_model(update, context, lang, step, data, raw):
    db = get_db()
    if step == "name":
        name = validate_text(raw, 1, MAX_NAME_CHARS)
        if db.get_ai_model_by_name(name):
            raise ValidationError("v_duplicate_name")
        update_flow(context, step="api_url", name=name)
        return await reply(update, t("admin_model_ask_url", lang), kb.cancel_only(lang))
    if step == "api_url":
        update_flow(context, step="api_key", api_url=validate_url(raw))
        return await reply(update, t("admin_model_ask_key", lang), kb.cancel_only(lang))
    if step == "api_key":
        update_flow(context, step="model_id", api_key=validate_api_key(raw))
        return await reply(update, t("admin_model_ask_id", lang), kb.cancel_only(lang))
    if step == "model_id":
        model_id = validate_text(raw, 1, 120)
        model_pk = admin_ops.add_ai_model(
            update.effective_user.id, data["name"], data["api_url"], data["api_key"], model_id)
        clear_flow(context)
        return await reply(update, t("admin_model_saved", lang, name=esc(data["name"])),
                           kb.admin_model_menu(lang, model_pk))
    clear_flow(context)
    return await reply(update, t("unknown_action", lang), kb.admin_back(lang))


async def _flow_add_product(update, context, lang, step, data, raw):
    if step == "name":
        update_flow(context, step="price", name=validate_text(raw, 1, MAX_NAME_CHARS))
        return await reply(update, t("admin_product_ask_price", lang), kb.cancel_only(lang))
    if step == "price":
        update_flow(context, step="duration_days", price=validate_int(raw, 0, 10_000_000_000))
        return await reply(update, t("admin_product_ask_days", lang), kb.cancel_only(lang))
    if step == "duration_days":
        update_flow(context, step="messages_count", duration_days=validate_int(raw, 1, 3650))
        return await reply(update, t("admin_product_ask_messages", lang), kb.cancel_only(lang))
    if step == "messages_count":
        update_flow(context, step="description", messages_count=validate_int(raw, 0, 10_000_000))
        return await reply(update, t("admin_product_ask_desc", lang), kb.cancel_only(lang))
    if step == "description":
        description = "" if raw == "-" else validate_text(raw, 1, MAX_DESC_CHARS)
        product_id = admin_ops.add_product(
            update.effective_user.id, data["name"], description, data["price"],
            data["duration_days"], data["messages_count"])
        clear_flow(context)
        return await reply(update, t("admin_product_saved", lang, name=esc(data["name"])),
                           kb.admin_product_menu(lang, product_id))
    clear_flow(context)
    return await reply(update, t("unknown_action", lang), kb.admin_back(lang))
