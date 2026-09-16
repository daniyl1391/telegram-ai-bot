"""Shop + checkout. Previously the shop button was dead and no purchase existed."""
import logging

from bot.config import ADMIN_USER_IDS
from bot.database import get_db
from bot.i18n import t
from bot.security import esc, format_card, check_flood
from bot.services.payment import payment_manager, PaymentError, METHOD_CARD, METHOD_GATEWAY
from bot.handlers.common import (
    lang_of, safe_edit, reply, parse_callback, set_flow, clear_flow, get_flow,
)
from bot import keyboards as kb

logger = logging.getLogger(__name__)


def _money(value):
    try:
        return "{:,}".format(int(value))
    except (TypeError, ValueError):
        return str(value)


async def shop_list(update, context):
    query = update.callback_query
    if query:
        await query.answer()
    lang = lang_of(update, context)
    db = get_db()
    clear_flow(context)

    if not db.get_bool_setting("shop_enabled", True):
        text, markup = t("shop_disabled", lang), kb.back_to_main(lang)
    else:
        products = db.get_products()
        if not products:
            text, markup = t("shop_empty", lang), kb.back_to_main(lang)
        else:
            text, markup = t("shop_title", lang), kb.shop_menu(lang, products)
    if query:
        return await safe_edit(query, text, markup)
    return await reply(update, text, markup)


async def shop_item(update, context):
    query = update.callback_query
    lang = lang_of(update, context)
    _, args = parse_callback(query.data)
    product = get_db().get_product(_int(args[-1]))
    if not product or not product["status"]:
        await query.answer(t("unknown_action", lang), show_alert=True)
        return await shop_list(update, context)
    await query.answer()
    text = t(
        "product_detail", lang,
        name=esc(product["name"]),
        description=esc(product["description"] or "-"),
        price=_money(product["price"]),
        days=product["duration_days"],
        messages=product["messages_count"],
        quota=(product.get("quota_mode") or "messages") +
              ((" / " + _money(product.get("token_count")) + " tokens")
               if int(product.get("token_count") or 0) else ""),
        models=esc(product.get("model_scope") or "all"),
    )
    return await safe_edit(query, text, kb.product_detail_menu(lang, product["id"]))


async def shop_buy(update, context):
    query = update.callback_query
    lang = lang_of(update, context)
    _, args = parse_callback(query.data)
    product = get_db().get_product(_int(args[-1]))
    if not product or not product["status"]:
        await query.answer(t("unknown_action", lang), show_alert=True)
        return await shop_list(update, context)
    await query.answer()
    text = t("pay_choose_method", lang,
             name=esc(product["name"]), price=_money(product["price"]))
    return await safe_edit(
        query, text,
        kb.payment_method_menu(lang, product["id"], payment_manager.gateway_enabled()),
    )


async def pay_card(update, context):
    query = update.callback_query
    lang = lang_of(update, context)
    _, args = parse_callback(query.data)
    product_id = _int(args[-1])

    card, holder = payment_manager.card_details()
    if not card:
        await query.answer(t("pay_card_not_configured", lang), show_alert=True)
        return None
    try:
        payment_id, product = payment_manager.start_payment(
            update.effective_user.id, product_id, METHOD_CARD
        )
    except PaymentError:
        await query.answer(t("unknown_action", lang), show_alert=True)
        return await shop_list(update, context)

    await query.answer()
    set_flow(context, "await_receipt", payment_id=payment_id)
    text = t("pay_card_instructions", lang,
             price=_money(product["price"]),
             card=format_card(card),
             holder=esc(holder or "-"),
             payment_id=payment_id)
    return await safe_edit(query, text, kb.cancel_only(lang))


async def pay_gateway(update, context):
    query = update.callback_query
    lang = lang_of(update, context)
    _, args = parse_callback(query.data)
    product_id = _int(args[-1])

    if not payment_manager.gateway_enabled():
        await query.answer(t("pay_gateway_not_configured", lang), show_alert=True)
        return None
    try:
        payment_id, product = payment_manager.start_payment(
            update.effective_user.id, product_id, METHOD_GATEWAY
        )
    except PaymentError:
        await query.answer(t("unknown_action", lang), show_alert=True)
        return await shop_list(update, context)

    await query.answer()
    url = payment_manager.gateway_url_for(payment_id, product["price"])
    set_flow(context, "await_receipt", payment_id=payment_id)
    return await safe_edit(query, t("pay_gateway_link", lang, url=esc(url)),
                           kb.cancel_only(lang))


async def handle_receipt(update, context):
    """Called by the router when the user is in the await_receipt flow.

    Accepts a photo/document receipt or a plain reference number, then notifies
    every admin with approve/reject buttons. Manual approval finally exists.
    """
    lang = lang_of(update, context)
    flow = get_flow(context) or {}
    payment_id = (flow.get("data") or {}).get("payment_id")
    db = get_db()
    user = update.effective_user
    message = update.effective_message

    payment = db.get_payment(payment_id) if payment_id else None
    if not payment or payment["status"] != "pending":
        clear_flow(context)
        return await reply(update, t("pay_no_pending", lang), kb.back_to_main(lang))

    allowed, retry_after = check_flood(user.id)
    if not allowed:
        return await reply(update, t("rate_limited", lang, seconds=retry_after))

    receipt_type, receipt_value = "text", (message.text or "").strip()
    if message.photo:
        receipt_type, receipt_value = "photo", message.photo[-1].file_id
    elif message.document:
        receipt_type, receipt_value = "document", message.document.file_id
    elif not receipt_value:
        return await reply(update, t("invalid_input", lang, reason=t("v_too_short", lang, min=1)))

    payment_manager.attach_receipt(payment_id, receipt_type, receipt_value)
    clear_flow(context)

    product = db.get_product(payment["product_id"])
    await _notify_admins(context, payment_id, user, product, payment["amount"], receipt_type,
                         receipt_value)
    return await reply(update, t("pay_receipt_received", lang, payment_id=payment_id),
                       kb.back_to_main(lang))


async def _notify_admins(context, payment_id, user, product, amount, receipt_type, receipt_value):
    for admin_id in ADMIN_USER_IDS:
        admin_lang = get_db().get_language(admin_id)
        caption = t("admin_payment_new", admin_lang,
                    payment_id=payment_id,
                    name=esc(user.first_name or user.id),
                    user_id=user.id,
                    product=esc((product or {}).get("name", "-")),
                    amount=_money(amount))
        markup = kb.admin_payment_menu(admin_lang, payment_id, pending=True)
        try:
            if receipt_type == "photo":
                await context.bot.send_photo(admin_id, receipt_value, caption=caption,
                                             parse_mode="HTML", reply_markup=markup)
            elif receipt_type == "document":
                await context.bot.send_document(admin_id, receipt_value, caption=caption,
                                                parse_mode="HTML", reply_markup=markup)
            else:
                await context.bot.send_message(
                    admin_id, caption + "\n\n🧾 <code>%s</code>" % esc(receipt_value),
                    parse_mode="HTML", reply_markup=markup)
        except Exception as exc:
            logger.warning("Could not notify admin %s: %s", admin_id, exc)


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
