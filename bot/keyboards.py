"""All inline keyboards.

Every callback_data string produced here is registered in main.py's router.
tests.py asserts that fact, so a dead button cannot ship again.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.i18n import t, LANGUAGES


def _rows(*rows):
    return InlineKeyboardMarkup([r for r in rows if r])


def language_menu(prefix="lang"):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data="%s:%s" % (prefix, code))]
         for code, label in LANGUAGES.items()]
    )


def main_menu(lang, is_admin_user=False, shop_on=True, support_on=True):
    rows = [[InlineKeyboardButton(t("btn_ai_chat", lang), callback_data="ai:open")]]
    if shop_on:
        rows.append([InlineKeyboardButton(t("btn_shop", lang), callback_data="shop:list")])
    row = [InlineKeyboardButton(t("btn_account", lang), callback_data="acct:view")]
    if support_on:
        row.append(InlineKeyboardButton(t("btn_support", lang), callback_data="sup:open"))
    rows.append(row)
    rows.append([InlineKeyboardButton(t("btn_language", lang), callback_data="lang:menu")])
    if is_admin_user:
        rows.append([InlineKeyboardButton(t("btn_admin_panel", lang), callback_data="adm:home")])
    return InlineKeyboardMarkup(rows)


def back_to_main(lang):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t("btn_main_menu", lang), callback_data="nav:main")]]
    )


def ai_menu(lang, has_multiple_models):
    rows = []
    if has_multiple_models:
        rows.append([InlineKeyboardButton(t("btn_choose_model", lang), callback_data="ai:models")])
    rows.append([InlineKeyboardButton(t("btn_clear_history", lang), callback_data="ai:clear")])
    rows.append([InlineKeyboardButton(t("btn_main_menu", lang), callback_data="nav:main")])
    return InlineKeyboardMarkup(rows)


def ai_model_picker(lang, models, active_name):
    rows = []
    for model in models:
        mark = "✅ " if model["name"] == active_name else "▫️ "
        rows.append([InlineKeyboardButton(
            mark + model["name"], callback_data="ai:use:%s" % model["id"])])
    rows.append([InlineKeyboardButton(t("btn_back", lang), callback_data="ai:open")])
    return InlineKeyboardMarkup(rows)


def shop_menu(lang, products):
    rows = [[InlineKeyboardButton(
        "🛍 %s — %s" % (p["name"], "{:,}".format(p["price"])),
        callback_data="shop:item:%s" % p["id"])] for p in products]
    rows.append([InlineKeyboardButton(t("btn_main_menu", lang), callback_data="nav:main")])
    return InlineKeyboardMarkup(rows)


def product_detail_menu(lang, product_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_buy", lang), callback_data="shop:buy:%s" % product_id)],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="shop:list")],
    ])


def payment_method_menu(lang, product_id, gateway_on):
    rows = [[InlineKeyboardButton(t("btn_pay_card", lang),
                                  callback_data="pay:card:%s" % product_id)]]
    if gateway_on:
        rows.append([InlineKeyboardButton(t("btn_pay_gateway", lang),
                                          callback_data="pay:gw:%s" % product_id)])
    rows.append([InlineKeyboardButton(t("btn_back", lang),
                                      callback_data="shop:item:%s" % product_id)])
    return InlineKeyboardMarkup(rows)


def cancel_only(lang):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t("btn_cancel", lang), callback_data="nav:cancel")]]
    )


def support_menu(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_new_ticket", lang), callback_data="sup:new")],
        [InlineKeyboardButton(t("btn_my_tickets", lang), callback_data="sup:mine")],
        [InlineKeyboardButton(t("btn_main_menu", lang), callback_data="nav:main")],
    ])


def ticket_list_menu(lang, tickets, back="sup:open"):
    rows = [[InlineKeyboardButton(
        "🎫 #%s — %s" % (ti["id"], t("status_" + (ti["status"] or "open"), lang)),
        callback_data="sup:view:%s" % ti["id"])] for ti in tickets]
    rows.append([InlineKeyboardButton(t("btn_back", lang), callback_data=back)])
    return InlineKeyboardMarkup(rows)


def ticket_view_menu(lang, ticket_id, is_admin_view=False):
    if is_admin_view:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(t("btn_reply_ticket", lang),
                                  callback_data="adm:tkreply:%s" % ticket_id)],
            [InlineKeyboardButton(t("btn_close_ticket", lang),
                                  callback_data="adm:tkclose:%s" % ticket_id)],
            [InlineKeyboardButton(t("btn_back", lang), callback_data="adm:tickets")],
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_reply_ticket", lang),
                              callback_data="sup:reply:%s" % ticket_id)],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="sup:mine")],
    ])


def account_menu(lang, shop_on=True):
    rows = []
    if shop_on:
        rows.append([InlineKeyboardButton(t("btn_shop", lang), callback_data="shop:list")])
    rows.append([InlineKeyboardButton(t("btn_main_menu", lang), callback_data="nav:main")])
    return InlineKeyboardMarkup(rows)


# ------------------------------------------------------------------ admin side
def admin_home(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_admin_users", lang), callback_data="adm:users:0"),
         InlineKeyboardButton(t("btn_admin_models", lang), callback_data="adm:models")],
        [InlineKeyboardButton(t("btn_admin_products", lang), callback_data="adm:products"),
         InlineKeyboardButton(t("btn_admin_payments", lang), callback_data="adm:payments")],
        [InlineKeyboardButton(t("btn_admin_tickets", lang), callback_data="adm:tickets"),
         InlineKeyboardButton(t("btn_admin_stats", lang), callback_data="adm:stats")],
        [InlineKeyboardButton(t("btn_admin_settings", lang), callback_data="adm:settings"),
         InlineKeyboardButton(t("btn_admin_broadcast", lang), callback_data="adm:bcast")],
        [InlineKeyboardButton(t("btn_main_menu", lang), callback_data="nav:main")],
    ])


def admin_back(lang, target="adm:home"):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t("btn_back", lang), callback_data=target)]]
    )


def admin_users_menu(lang, users, page, has_prev, has_next):
    rows = [[InlineKeyboardButton(
        "👤 %s%s" % (u.get("first_name") or u["user_id"], " 🚫" if u.get("is_banned") else ""),
        callback_data="adm:user:%s" % u["user_id"])] for u in users]
    nav = []
    if has_prev:
        nav.append(InlineKeyboardButton(t("btn_prev", lang), callback_data="adm:users:%s" % (page - 1)))
    if has_next:
        nav.append(InlineKeyboardButton(t("btn_next", lang), callback_data="adm:users:%s" % (page + 1)))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(t("btn_search", lang), callback_data="adm:usearch")])
    rows.append([InlineKeyboardButton(t("btn_back", lang), callback_data="adm:home")])
    return InlineKeyboardMarkup(rows)


def admin_user_menu(lang, user_id, banned):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_set_quota", lang), callback_data="adm:quota:%s" % user_id),
         InlineKeyboardButton(t("btn_grant", lang), callback_data="adm:grant:%s" % user_id)],
        [InlineKeyboardButton(t("btn_set_policy", lang), callback_data="adm:policy:%s" % user_id)],
        [InlineKeyboardButton(t("btn_message_user", lang), callback_data="adm:dm:%s" % user_id)],
        [InlineKeyboardButton(
            t("btn_unban", lang) if banned else t("btn_ban", lang),
            callback_data="adm:ban:%s" % user_id)],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="adm:users:0")],
    ])


def admin_models_menu(lang, models):
    rows = [[InlineKeyboardButton(
        "%s%s %s" % ("⭐️ " if m["is_default"] else "", "🟢" if m["status"] else "🔴", m["name"]),
        callback_data="adm:model:%s" % m["id"])] for m in models]
    rows.append([InlineKeyboardButton(t("btn_add_model", lang), callback_data="adm:addmodel")])
    rows.append([InlineKeyboardButton(t("btn_back", lang), callback_data="adm:home")])
    return InlineKeyboardMarkup(rows)


def admin_model_menu(lang, model_pk):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_test_model", lang), callback_data="adm:mtest:%s" % model_pk)],
        [InlineKeyboardButton(t("btn_edit_name", lang), callback_data="adm:medit:name:%s" % model_pk),
         InlineKeyboardButton(t("btn_edit_url", lang), callback_data="adm:medit:api_url:%s" % model_pk)],
        [InlineKeyboardButton(t("btn_edit_key", lang), callback_data="adm:medit:api_key:%s" % model_pk),
         InlineKeyboardButton(t("btn_edit_model_id", lang), callback_data="adm:medit:model_id:%s" % model_pk)],
        [InlineKeyboardButton(t("btn_make_default", lang), callback_data="adm:mdefault:%s" % model_pk),
         InlineKeyboardButton(t("btn_toggle_status", lang), callback_data="adm:mtoggle:%s" % model_pk)],
        [InlineKeyboardButton(t("btn_delete", lang), callback_data="adm:mdel:%s" % model_pk)],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="adm:models")],
    ])


def admin_products_menu(lang, products):
    rows = [[InlineKeyboardButton(
        "%s %s — %s" % ("🟢" if p["status"] else "🔴", p["name"], "{:,}".format(p["price"])),
        callback_data="adm:product:%s" % p["id"])] for p in products]
    rows.append([InlineKeyboardButton(t("btn_add_product", lang), callback_data="adm:addproduct")])
    rows.append([InlineKeyboardButton(t("btn_back", lang), callback_data="adm:home")])
    return InlineKeyboardMarkup(rows)


def admin_product_menu(lang, product_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_edit_name", lang), callback_data="adm:pedit:name:%s" % product_id),
         InlineKeyboardButton(t("btn_edit_price", lang), callback_data="adm:pedit:price:%s" % product_id)],
        [InlineKeyboardButton(t("btn_edit_days", lang), callback_data="adm:pedit:duration_days:%s" % product_id),
         InlineKeyboardButton(t("btn_edit_messages", lang), callback_data="adm:pedit:messages_count:%s" % product_id)],
        [InlineKeyboardButton(t("btn_edit_desc", lang), callback_data="adm:pedit:description:%s" % product_id)],
        [InlineKeyboardButton(t("btn_set_quota_mode", lang), callback_data="adm:pedit:quota_mode:%s" % product_id),
         InlineKeyboardButton(t("btn_set_product_tokens", lang), callback_data="adm:pedit:token_count:%s" % product_id)],
        [InlineKeyboardButton(t("btn_set_model_scope", lang), callback_data="adm:pedit:model_scope:%s" % product_id)],
        [InlineKeyboardButton(t("btn_toggle_status", lang), callback_data="adm:ptoggle:%s" % product_id),
         InlineKeyboardButton(t("btn_delete", lang), callback_data="adm:pdel:%s" % product_id)],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="adm:products")],
    ])


def admin_payments_menu(lang, payments):
    rows = [[InlineKeyboardButton(
        "🧾 #%s — %s" % (p["id"], "{:,}".format(p["amount"])),
        callback_data="adm:payment:%s" % p["id"])] for p in payments]
    rows.append([InlineKeyboardButton(t("btn_payment_settings", lang), callback_data="adm:payset")])
    rows.append([InlineKeyboardButton(t("btn_back", lang), callback_data="adm:home")])
    return InlineKeyboardMarkup(rows)


def admin_payment_menu(lang, payment_id, pending=True):
    rows = []
    if pending:
        rows.append([
            InlineKeyboardButton(t("btn_confirm", lang), callback_data="adm:papprove:%s" % payment_id),
            InlineKeyboardButton(t("btn_reject", lang), callback_data="adm:preject:%s" % payment_id),
        ])
    rows.append([InlineKeyboardButton(t("btn_back", lang), callback_data="adm:payments")])
    return InlineKeyboardMarkup(rows)


def admin_payment_settings_menu(lang, gateway_on):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_set_card", lang), callback_data="adm:setcard")],
        [InlineKeyboardButton(t("btn_set_holder", lang), callback_data="adm:setholder")],
        [InlineKeyboardButton(
            "%s %s" % (t("btn_toggle_gateway", lang), "🟢" if gateway_on else "🔴"),
            callback_data="adm:gwtoggle")],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="adm:payments")],
    ])


def admin_tickets_menu(lang, tickets):
    rows = [[InlineKeyboardButton(
        "🎫 #%s — %s" % (ti["id"], t("status_" + (ti["status"] or "open"), lang)),
        callback_data="adm:ticket:%s" % ti["id"])] for ti in tickets]
    rows.append([InlineKeyboardButton(t("btn_back", lang), callback_data="adm:home")])
    return InlineKeyboardMarkup(rows)


def admin_settings_menu(lang, shop_on, support_on, streaming_on=True):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_set_free_limit", lang), callback_data="adm:set:free_message_limit"),
         InlineKeyboardButton(t("btn_set_free_tokens", lang), callback_data="adm:set:free_token_limit")],
        [InlineKeyboardButton(t("btn_set_quota_mode", lang), callback_data="adm:set:default_quota_mode"),
         InlineKeyboardButton(t("btn_set_model_scope", lang), callback_data="adm:set:default_model_scope")],
        [InlineKeyboardButton(t("btn_set_free_days", lang), callback_data="adm:set:free_period_days")],
        [InlineKeyboardButton(t("btn_set_rate_limit", lang), callback_data="adm:set:rate_limit_messages"),
         InlineKeyboardButton(t("btn_set_history", lang), callback_data="adm:set:ai_max_history")],
        [InlineKeyboardButton(t("btn_set_stream_interval", lang), callback_data="adm:set:stream_edit_interval_ms"),
         InlineKeyboardButton(t("btn_set_output_tokens", lang), callback_data="adm:set:ai_max_output_tokens")],
        [InlineKeyboardButton(t("btn_set_file_size", lang), callback_data="adm:set:max_file_mb"),
         InlineKeyboardButton(t("btn_set_prompt", lang), callback_data="adm:set:ai_system_prompt")],
        [InlineKeyboardButton(
            "%s %s" % (t("btn_toggle_streaming", lang), "🟢" if streaming_on else "🔴"),
            callback_data="adm:toggle:ai_streaming")],
        [InlineKeyboardButton(
            "%s %s" % (t("btn_toggle_shop", lang), "🟢" if shop_on else "🔴"),
            callback_data="adm:toggle:shop_enabled"),
         InlineKeyboardButton(
             "%s %s" % (t("btn_toggle_support", lang), "🟢" if support_on else "🔴"),
             callback_data="adm:toggle:support_enabled")],
        [InlineKeyboardButton(t("btn_back", lang), callback_data="adm:home")],
    ])


def admin_grant_menu(lang, user_id, products):
    rows = [[InlineKeyboardButton(
        "🎁 %s" % p["name"], callback_data="adm:grantp:%s:%s" % (user_id, p["id"]))]
        for p in products]
    rows.append([InlineKeyboardButton(t("btn_back", lang), callback_data="adm:user:%s" % user_id)])
    return InlineKeyboardMarkup(rows)
