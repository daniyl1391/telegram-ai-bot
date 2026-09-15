#!/usr/bin/env python3
"""Test suite for the Telegram AI Bot.

Run it with:  python tests.py

It exercises the real bot code end to end without touching the network:

  * every button's callback_data is matched by a registered handler pattern
  * the SQLite layer: atomic nested writes, newest-row ordering, migrations
  * quota / expiry rules
  * the full purchase flow: order -> receipt -> admin approval -> active plan
  * security: admin guard, rate limit, anti-spam, validation, secret masking
  * the AI client: request shape, response parsing, retries, key rotation
  * handler smoke tests for the user menu and every admin panel screen, in
    both Persian and English

If `python-telegram-bot` / `aiohttp` are not installed, lightweight stubs from
./tests_stubs are used so the suite still runs in a bare container.
"""
import os
import re
import sys
import asyncio
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Two admins, so admin-only paths are testable. Must be set before bot.config.
ADMIN_ID = 111111
USER_ID = 222222
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456789:TEST-TOKEN-FOR-UNIT-TESTS")
os.environ["ADMIN_USER_IDS"] = str(ADMIN_ID)
_TMP = tempfile.mkdtemp(prefix="tgbot_tests_")
os.environ["DATA_DIR"] = _TMP
os.environ["DB_PATH"] = os.path.join(_TMP, "test.db")

try:  # real libraries win; stubs are the offline fallback
    import telegram  # noqa: F401
    import telegram.ext  # noqa: F401
    import aiohttp  # noqa: F401
    USING_STUBS = False
except ImportError:
    sys.path.insert(0, os.path.join(HERE, "tests_stubs"))
    import telegram  # noqa: F401
    import telegram.ext  # noqa: F401
    import aiohttp  # noqa: F401
    USING_STUBS = True

from telegram import InlineKeyboardMarkup  # noqa: E402

# ---------------------------------------------------------------------------
# Tiny test runner
# ---------------------------------------------------------------------------
PASSED, FAILED = [], []


def test(name):
    def decorator(func):
        func._test_name = name
        return func
    return decorator


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def run_all(namespace):
    tests = [v for v in namespace.values()
             if callable(v) and getattr(v, "_test_name", None)]
    for func in tests:
        name = func._test_name
        try:
            result = func()
            if asyncio.iscoroutine(result):
                asyncio.run(result)
            PASSED.append(name)
            print("  \033[92mPASS\033[0m  %s" % name)
        except Exception as exc:
            FAILED.append((name, exc))
            print("  \033[91mFAIL\033[0m  %s\n        %s: %s"
                  % (name, type(exc).__name__, exc))
            if os.environ.get("TEST_VERBOSE"):
                traceback.print_exc()


# ---------------------------------------------------------------------------
# Fakes for the Telegram objects handlers receive
# ---------------------------------------------------------------------------
class FakeUser:
    def __init__(self, uid, first_name="Tester", username="tester"):
        self.id = uid
        self.first_name = first_name
        self.username = username


class FakeMessage:
    def __init__(self, text=None, chat_id=1, photo=None, document=None):
        self.text = text
        self.chat_id = chat_id
        self.photo = photo or []
        self.document = document
        self.replies = []
        self.edits = []

    async def reply_text(self, text, reply_markup=None, **kw):
        sent = FakeMessage(text=text, chat_id=self.chat_id)
        sent.reply_markup = reply_markup
        self.replies.append(sent)
        return sent

    async def edit_text(self, text, reply_markup=None, **kw):
        self.edits.append(text)
        self.text = text
        self.reply_markup = reply_markup
        return self


class FakeCallbackQuery:
    def __init__(self, data, user, message=None):
        self.data = data
        self.from_user = user
        self.message = message or FakeMessage("original")
        self.answers = []
        self.edited = []

    async def answer(self, text=None, show_alert=False):
        self.answers.append({"text": text, "alert": show_alert})

    async def edit_message_text(self, text, reply_markup=None, **kw):
        self.edited.append({"text": text, "markup": reply_markup})
        return self.message


class FakeBot:
    def __init__(self):
        self.sent = []
        self.actions = []

    async def send_message(self, chat_id, text, **kw):
        self.sent.append({"chat_id": chat_id, "text": text, "kw": kw})
        return FakeMessage(text=text)

    async def send_photo(self, chat_id, photo, caption=None, **kw):
        self.sent.append({"chat_id": chat_id, "photo": photo, "text": caption, "kw": kw})
        return FakeMessage(text=caption)

    async def send_document(self, chat_id, document, caption=None, **kw):
        self.sent.append({"chat_id": chat_id, "document": document, "text": caption, "kw": kw})
        return FakeMessage(text=caption)

    async def send_chat_action(self, chat_id, action):
        self.actions.append(action)


class FakeContext:
    def __init__(self, bot=None, user_data=None):
        self.bot = bot or FakeBot()
        self.user_data = user_data if user_data is not None else {}
        self.error = None


class FakeUpdate:
    def __init__(self, user, message=None, callback_query=None):
        self._user = user
        self.message = message
        self.callback_query = callback_query

    @property
    def effective_user(self):
        return self._user

    @property
    def effective_message(self):
        if self.message is not None:
            return self.message
        if self.callback_query is not None:
            return self.callback_query.message
        return None


def text_update(uid, text, **kw):
    return FakeUpdate(FakeUser(uid, **kw), message=FakeMessage(text))


def cb_update(uid, data, **kw):
    user = FakeUser(uid, **kw)
    return FakeUpdate(user, callback_query=FakeCallbackQuery(data, user))


def last_reply(update):
    msg = update.effective_message
    return msg.replies[-1].text if msg and msg.replies else None


def cb_text(update):
    query = update.callback_query
    if query.edited:
        return query.edited[-1]["text"]
    if query.message.replies:
        return query.message.replies[-1].text
    return None


def cb_markup(update):
    query = update.callback_query
    if query.edited and query.edited[-1]["markup"] is not None:
        return query.edited[-1]["markup"]
    if query.message.replies:
        return getattr(query.message.replies[-1], "reply_markup", None)
    return None


# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------
import main as main_module                                    # noqa: E402
from bot import config, i18n, keyboards as kb, security       # noqa: E402
from bot.database import (                                     # noqa: E402
    Database, get_db, reset_db_for_tests, parse_iso, iso, utcnow,
)
from bot.admin import panel as admin_ops                       # noqa: E402
from bot.handlers import admin as admin_handlers               # noqa: E402
from bot.handlers import ai_chat, router, shop, support        # noqa: E402
from bot.handlers import start as start_handlers               # noqa: E402
from bot.handlers.common import clear_flow, get_flow           # noqa: E402
from bot.services.ai_manager import (                          # noqa: E402
    ai_manager, AIError, _extract_reply, _split_keys,
)
from bot.services.payment import payment_manager, PaymentError  # noqa: E402
from bot.services.subscription import subscription_manager, OK, EXPIRED, EXHAUSTED  # noqa: E402


def fresh_db():
    """A clean database for a single test."""
    path = os.path.join(_TMP, "t_%s.db" % os.urandom(4).hex())
    db = reset_db_for_tests(path)
    security.rate_limiter.reset()
    security.anti_spam.reset()
    ai_manager._history.clear()
    db.add_user(ADMIN_ID, "admin", "Admin")
    db.add_user(USER_ID, "user", "User")
    subscription_manager.ensure_subscription(ADMIN_ID)
    subscription_manager.ensure_subscription(USER_ID)
    return db


def seed_model(db, name="GPT", url="https://api.example.com/v1/chat/completions",
               key="sk-secret-key-value", model_id="gpt-4o-mini"):
    return db.add_ai_model(name, url, key, model_id, make_default=True)


def seed_product(db, name="Pro", price=50000, days=30, messages=1000):
    return db.create_product(name, "A plan", price, days, messages)


# ===========================================================================
# 1. Structure / wiring
# ===========================================================================
@test("all modules import cleanly")
def t_imports():
    import bot.config, bot.database, bot.i18n, bot.keyboards, bot.security  # noqa
    import bot.admin.panel, bot.services.ai_manager, bot.services.payment  # noqa
    import bot.services.subscription, bot.handlers.common, bot.handlers.errors  # noqa
    import bot.handlers.router, bot.handlers.start, bot.handlers.ai_chat  # noqa
    import bot.handlers.shop, bot.handlers.support, bot.handlers.admin  # noqa
    check(callable(main_module.build_application), "build_application missing")


@test("environment validation rejects a missing token and a bad admin list")
def t_env_validation():
    saved_token, saved_admins = config.TELEGRAM_BOT_TOKEN, config.ADMIN_USER_IDS
    try:
        config.TELEGRAM_BOT_TOKEN = ""
        check(any("TELEGRAM_BOT_TOKEN" in p for p in config.validate_environment()),
              "missing token not reported")
        config.TELEGRAM_BOT_TOKEN = "not-a-token"
        check(any("malformed" in p for p in config.validate_environment()),
              "malformed token not reported")
        config.TELEGRAM_BOT_TOKEN = saved_token
        config.ADMIN_USER_IDS = []
        check(any("ADMIN_USER_IDS" in p for p in config.validate_environment()),
              "missing admin list not reported")
        config.ADMIN_USER_IDS = saved_admins
        check(config.validate_environment() == [], "valid config reported as broken")
    finally:
        config.TELEGRAM_BOT_TOKEN, config.ADMIN_USER_IDS = saved_token, saved_admins


@test("only TELEGRAM_BOT_TOKEN and ADMIN_USER_IDS are read from the environment")
def t_env_surface():
    source = open(os.path.join(HERE, "bot", "config.py"), encoding="utf-8").read()
    found = set(re.findall(r'os\.getenv\(\s*"([A-Z_]+)"', source))
    allowed = {"TELEGRAM_BOT_TOKEN", "ADMIN_USER_IDS", "DATA_DIR", "DB_PATH", "LOG_LEVEL"}
    check(found <= allowed, "config reads unexpected env vars: %s" % (found - allowed))
    # Business settings must not come from the environment anywhere in bot/.
    for folder, _dirs, files in os.walk(os.path.join(HERE, "bot")):
        for filename in files:
            if not filename.endswith(".py"):
                continue
            body = open(os.path.join(folder, filename), encoding="utf-8").read()
            for var in ("CARD_NUMBER", "OPENAI_API_KEY", "AI_API_KEY", "DATABASE_URL"):
                check(var not in body, "%s still references %s" % (filename, var))


@test("every button's callback_data is handled by a registered pattern")
def t_no_dead_buttons():
    db = fresh_db()
    seed_model(db)
    seed_product(db)
    app = main_module.build_application(token="123456789:TEST")

    patterns = [h.pattern for h in app.handlers if getattr(h, "pattern", None)]
    compiled = []
    for pattern in patterns:
        compiled.append(re.compile(pattern if isinstance(pattern, str) else pattern.pattern))

    lang = "fa"
    products = db.get_products()
    models = db.get_ai_models()
    tickets = [{"id": 1, "status": "open", "user_id": USER_ID}]
    users = db.list_users()
    payments = [{"id": 1, "amount": 1000, "user_id": USER_ID}]

    markups = [
        kb.language_menu(), kb.main_menu(lang, True), kb.back_to_main(lang),
        kb.ai_menu(lang, True), kb.ai_model_picker(lang, models, "GPT"),
        kb.shop_menu(lang, products), kb.product_detail_menu(lang, 1),
        kb.payment_method_menu(lang, 1, True), kb.cancel_only(lang),
        kb.support_menu(lang), kb.ticket_list_menu(lang, tickets),
        kb.ticket_view_menu(lang, 1), kb.ticket_view_menu(lang, 1, True),
        kb.account_menu(lang), kb.admin_home(lang), kb.admin_back(lang),
        kb.admin_users_menu(lang, users, 1, True, True),
        kb.admin_user_menu(lang, USER_ID, False),
        kb.admin_models_menu(lang, models), kb.admin_model_menu(lang, 1),
        kb.admin_products_menu(lang, products), kb.admin_product_menu(lang, 1),
        kb.admin_payments_menu(lang, payments), kb.admin_payment_menu(lang, 1),
        kb.admin_payment_settings_menu(lang, True), kb.admin_tickets_menu(lang, tickets),
        kb.admin_settings_menu(lang, True, True),
        kb.admin_grant_menu(lang, USER_ID, products),
    ]

    all_data = []
    for markup in markups:
        check(isinstance(markup, InlineKeyboardMarkup), "not a markup: %r" % markup)
        for row in markup.inline_keyboard:
            for button in row:
                if button.callback_data:
                    all_data.append(button.callback_data)

    check(len(all_data) > 60, "expected many buttons, found %s" % len(all_data))
    dead = [d for d in all_data if not any(rx.match(d) for rx in compiled)]
    check(not dead, "unhandled callback_data: %s" % sorted(set(dead)))


@test("every adm: action produced by a keyboard exists in the admin router")
def t_admin_routes_complete():
    db = fresh_db()
    seed_model(db)
    seed_product(db)
    lang = "en"
    markups = [
        kb.admin_home(lang), kb.admin_users_menu(lang, db.list_users(), 0, False, False),
        kb.admin_user_menu(lang, USER_ID, False), kb.admin_models_menu(lang, db.get_ai_models()),
        kb.admin_model_menu(lang, 1), kb.admin_products_menu(lang, db.get_products()),
        kb.admin_product_menu(lang, 1), kb.admin_payments_menu(lang, []),
        kb.admin_payment_menu(lang, 1), kb.admin_payment_settings_menu(lang, False),
        kb.admin_tickets_menu(lang, []), kb.admin_settings_menu(lang, True, True),
        kb.admin_grant_menu(lang, USER_ID, db.get_products()), kb.admin_back(lang),
    ]
    actions = set()
    for markup in markups:
        for row in markup.inline_keyboard:
            for button in row:
                data = button.callback_data or ""
                if data.startswith("adm:"):
                    actions.add(data.split(":")[1])
    missing = actions - admin_handlers.ADMIN_ACTIONS
    check(not missing, "admin router is missing: %s" % sorted(missing))


@test("a text MessageHandler and an error handler are registered")
def t_message_handler_registered():
    app = main_module.build_application(token="123456789:TEST")
    has_message_handler = any(
        getattr(h, "filters", None) is not None and getattr(h, "callback", None) is not None
        for h in app.handlers)
    check(has_message_handler, "no MessageHandler registered: AI chat would be dead")
    check(app.error_handlers, "no error handler registered")
    commands = {h.command for h in app.handlers if getattr(h, "command", None)}
    for expected in ("start", "admin", "shop", "support", "account", "help", "language"):
        check(expected in commands, "/%s not registered" % expected)


# ===========================================================================
# 2. i18n
# ===========================================================================
@test("every string exists in both Persian and English")
def t_i18n_complete():
    gaps = i18n.missing_translations()
    check(not gaps, "untranslated: %s" % gaps[:10])
    check(len(i18n.STRINGS) > 150, "string table looks too small")


@test("i18n never raises on a missing key or a bad placeholder")
def t_i18n_safe():
    check(i18n.t("no_such_key_at_all", "fa") == "no_such_key_at_all", "missing key not echoed")
    check("{" in i18n.t("welcome", "fa") or True, "sanity")
    # missing placeholder must not raise
    i18n.t("welcome", "fa")
    i18n.t("welcome", "xx", name="a", plan="b", remaining=1)


@test("keyboards render in both languages")
def t_keyboards_bilingual():
    fresh_db()
    for lang in ("fa", "en"):
        markup = kb.main_menu(lang, True)
        labels = [b.text for row in markup.inline_keyboard for b in row]
        check(len(labels) >= 5, "main menu too small in %s" % lang)
        check(any(ord(c) > 0x1F000 for label in labels for c in label),
              "no emoji in the %s menu" % lang)
    fa = [b.text for row in kb.main_menu("fa").inline_keyboard for b in row]
    en = [b.text for row in kb.main_menu("en").inline_keyboard for b in row]
    check(fa != en, "Persian and English menus are identical")


# ===========================================================================
# 3. Database
# ===========================================================================
@test("a nested write inside an open transaction does not deadlock")
def t_nested_tx():
    db = fresh_db()
    pid = db.create_payment(USER_ID, None, 1000, "card")
    with db.tx() as conn:
        conn.execute("UPDATE payments SET status='confirmed' WHERE id=?", (pid,))
        db.create_subscription(USER_ID, "premium", 1000, 30)  # used to raise "database is locked"
    check(db.get_payment(pid)["status"] == "confirmed", "outer write lost")
    check(db.get_subscription(USER_ID)["plan"] == "premium", "nested write lost")


@test("a failed transaction rolls back completely")
def t_tx_rollback():
    db = fresh_db()
    before = db.count_payments()
    try:
        with db.tx() as conn:
            conn.execute("INSERT INTO payments (user_id, amount, created_at) VALUES (?,?,?)",
                         (USER_ID, 1, iso(utcnow())))
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    check(db.count_payments() == before, "rollback did not undo the insert")


@test("the newest subscription wins even when rows share a timestamp")
def t_subscription_ordering():
    db = fresh_db()
    db.create_subscription(USER_ID, "free", 10, 30)
    db.create_subscription(USER_ID, "premium", 5000, 30)
    sub = db.get_subscription(USER_ID)
    check(sub["plan"] == "premium",
          "stale plan returned (%s): a paying customer would get nothing" % sub["plan"])
    check(sub["message_limit"] == 5000, "wrong limit: %s" % sub["message_limit"])


@test("timestamps round-trip as timezone-aware UTC")
def t_timestamps():
    db = fresh_db()
    db.create_subscription(USER_ID, "premium", 100, 30)
    sub = db.get_subscription(USER_ID)
    expire = parse_iso(sub["expire_date"])
    check(expire is not None, "expire_date did not parse")
    check(expire.tzinfo is not None, "expire_date is naive: expiry comparisons would drift")
    check(expire > utcnow(), "a 30-day plan is already expired")
    check(parse_iso("2026-01-01 10:00:00") is not None, "old space-separated format rejected")
    check(parse_iso("2026-01-01T10:00:00Z") is not None, "Z suffix rejected")
    check(parse_iso(None) is None and parse_iso("") is None, "empty value not handled")


@test("a database written by the old version is migrated in place")
def t_migration():
    import sqlite3
    path = os.path.join(_TMP, "legacy.db")
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            is_admin BOOLEAN DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        INSERT INTO users (user_id, username, first_name) VALUES (5, 'legacy', 'Legacy');
        CREATE TABLE ai_models (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE,
            api_url TEXT, api_key TEXT, model_name TEXT, status BOOLEAN DEFAULT 1,
            is_default BOOLEAN DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        INSERT INTO ai_models (name, api_url, api_key, model_name)
            VALUES ('legacy', 'https://x/y', 'k', 'gpt-3.5-turbo');
    """)
    conn.commit()
    conn.close()

    migrated = Database(path)
    model = migrated.get_ai_model_by_name("legacy")
    check(model is not None, "legacy model row lost")
    check(model["model_id"] == "gpt-3.5-turbo", "model_name was not migrated to model_id")
    columns = {r["name"] for r in migrated.query("PRAGMA table_info(users)")}
    check({"language", "is_banned", "last_seen"} <= columns, "user columns not added")
    check(migrated.get_user(5)["user_id"] == 5, "legacy user lost")
    migrated.close()


@test("settings are typed and defaulted safely")
def t_settings():
    db = fresh_db()
    check(db.get_int_setting("free_message_limit") == 10, "default not seeded")
    db.set_setting("free_message_limit", "not-a-number")
    check(db.get_int_setting("free_message_limit", 7) == 7, "bad int not defaulted")
    db.set_setting("shop_enabled", "1")
    check(db.get_bool_setting("shop_enabled") is True, "bool parse failed")
    db.set_setting("shop_enabled", "0")
    check(db.get_bool_setting("shop_enabled") is False, "bool parse failed")
    check(db.get_setting("nope", "fallback") == "fallback", "default not returned")


# ===========================================================================
# 4. Subscription rules
# ===========================================================================
@test("quota is consumed, then exhausted, then blocks")
def t_quota():
    db = fresh_db()
    db.set_setting("free_message_limit", "3")
    db.create_subscription(USER_ID, "free", 3, 30)
    check(subscription_manager.remaining(USER_ID) == 3, "wrong starting quota")
    for _ in range(3):
        check(subscription_manager.consume(USER_ID) is True, "consume failed too early")
    check(subscription_manager.remaining(USER_ID) == 0, "quota did not reach zero")
    check(subscription_manager.consume(USER_ID) is False, "consumed beyond the limit")
    state, _ = subscription_manager.status(USER_ID)
    check(state == EXHAUSTED, "state should be exhausted, got %s" % state)


@test("an expired plan is detected and blocks sending")
def t_expiry():
    db = fresh_db()
    sub_id = db.create_subscription(USER_ID, "premium", 100, 30)
    db.execute("UPDATE subscriptions SET expire_date = ? WHERE id = ?",
               (iso(utcnow().replace(year=utcnow().year - 1)), sub_id))
    state, _ = subscription_manager.status(USER_ID)
    check(state == EXPIRED, "expired plan not detected, got %s" % state)
    check(subscription_manager.can_send(USER_ID) is False, "expired user can still send")


@test("a free subscription is created exactly once per user")
def t_free_sub_once():
    db = fresh_db()
    db.add_user(999, "n", "N")
    first = subscription_manager.ensure_subscription(999)
    second = subscription_manager.ensure_subscription(999)
    check(first["id"] == second["id"], "duplicate free subscription created")


# ===========================================================================
# 5. Payments
# ===========================================================================
@test("purchase flow: order, receipt, approval, active plan")
async def t_payment_flow():
    db = fresh_db()
    product_id = seed_product(db, price=99000, days=30, messages=2500)
    db.set_setting("card_number", "1234567812345678")
    db.set_setting("card_holder", "Daniel")

    payment_id, product = payment_manager.start_payment(USER_ID, product_id, "card")
    check(db.get_payment(payment_id)["status"] == "pending", "order not pending")
    payment_manager.attach_receipt(payment_id, "text", "REF-123")

    payment, prod, sub = payment_manager.approve(payment_id, ADMIN_ID)
    check(db.get_payment(payment_id)["status"] == "confirmed", "order not confirmed")
    check(sub["plan"] == "premium", "plan not upgraded")
    check(sub["message_limit"] == 2500, "wrong quota: %s" % sub["message_limit"])
    check(sub["message_used"] == 0, "new plan starts used")
    check(subscription_manager.can_send(USER_ID) is True, "paid user cannot send")
    check(db.total_revenue() == 99000, "revenue not counted: %s" % db.total_revenue())


@test("a payment cannot be approved twice or after rejection")
def t_payment_double_spend():
    db = fresh_db()
    product_id = seed_product(db, messages=500)
    payment_id, _ = payment_manager.start_payment(USER_ID, product_id, "card")
    payment_manager.approve(payment_id, ADMIN_ID)
    try:
        payment_manager.approve(payment_id, ADMIN_ID)
        raise AssertionError("double approval was allowed: quota could be granted twice")
    except PaymentError:
        pass
    other, _ = payment_manager.start_payment(USER_ID, product_id, "card")
    payment_manager.reject(other, ADMIN_ID)
    try:
        payment_manager.approve(other, ADMIN_ID)
        raise AssertionError("a rejected payment was approved")
    except PaymentError:
        pass


@test("card details and the gateway toggle come from settings, not the environment")
def t_payment_settings():
    db = fresh_db()
    check(payment_manager.card_details() == ("", ""), "card should start unset")
    check(payment_manager.gateway_enabled() is False, "gateway should start off")
    db.set_setting("card_number", "6037991122334455")
    db.set_setting("card_holder", "Daniel K")
    card, holder = payment_manager.card_details()
    check(card == "6037991122334455" and holder == "Daniel K", "card details not stored")
    check(security.format_card(card) == "6037-9911-2233-4455", "card formatting wrong")
    db.set_setting("gateway_enabled", "1")
    db.set_setting("gateway_url", "https://pay.example.com/start")
    check(payment_manager.gateway_enabled() is True, "gateway not enabled")
    url = payment_manager.gateway_url_for(7, 1000)
    check("order=7" in url and "amount=1000" in url, "gateway url malformed: %s" % url)


# ===========================================================================
# 6. Security
# ===========================================================================
@test("admin rights come only from ADMIN_USER_IDS, never from the database")
def t_admin_source():
    db = fresh_db()
    check(security.is_admin(ADMIN_ID) is True, "configured admin not recognised")
    check(security.is_admin(USER_ID) is False, "random user is admin")
    # Even a DB that claims otherwise must not grant access.
    try:
        db.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    except Exception:
        pass
    db.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (USER_ID,))
    check(security.is_admin(USER_ID) is False, "a DB flag granted admin rights")


@test("the admin guard blocks non-admins and answers the callback")
async def t_admin_guard():
    fresh_db()

    @security.admin_only
    async def protected(update, context):
        return "reached"

    update = cb_update(USER_ID, "adm:home")
    result = await protected(update, FakeContext())
    check(result is None, "non-admin reached an admin handler")
    check(update.callback_query.answers, "callback never answered: the client would spin forever")
    check(update.callback_query.answers[-1]["alert"] is True, "refusal was not shown to the user")

    allowed = cb_update(ADMIN_ID, "adm:home")
    check(await protected(allowed, FakeContext()) == "reached", "admin was blocked")


@test("a non-admin cannot reach the admin panel by replaying callback data")
async def t_admin_callback_replay():
    db = fresh_db()
    seed_model(db)
    for data in ("adm:home", "adm:models", "adm:users:0", "adm:payments",
                 "adm:settings", "adm:mdel:1", "adm:papprove:1"):
        update = cb_update(USER_ID, data)
        await admin_handlers.admin_callback(update, FakeContext())
        check(not update.callback_query.edited,
              "non-admin rendered %s" % data)
        check(update.callback_query.answers, "%s left the client spinning" % data)
    check(db.get_ai_model_by_name("GPT") is not None,
          "a non-admin deleted a model via replayed callback data")


@test("privileged operations reject non-admin callers directly")
def t_panel_permissions():
    db = fresh_db()
    for call in (
        lambda: admin_ops.add_ai_model(USER_ID, "x", "https://a/b", "keykeykey", "m"),
        lambda: admin_ops.add_product(USER_ID, "x", "", 1, 1, 1),
        lambda: admin_ops.set_setting(USER_ID, "card_number", "1"),
        lambda: admin_ops.set_user_banned(USER_ID, ADMIN_ID, True),
    ):
        try:
            call()
            raise AssertionError("a privileged op ran for a non-admin")
        except admin_ops.PermissionDenied:
            pass
    check(len(db.get_ai_models(only_active=False)) == 0, "model created by a non-admin")
    try:
        admin_ops.set_user_banned(ADMIN_ID, ADMIN_ID, True)
        raise AssertionError("an admin was bannable")
    except admin_ops.PermissionDenied:
        pass


@test("API keys are masked and never rendered in full")
async def t_key_masking():
    db = fresh_db()
    secret = "sk-proj-SUPER-SECRET-abcdef123456"
    model_pk = seed_model(db, key=secret)
    check(secret not in security.mask_secret(secret), "mask_secret leaked the key")
    check(security.mask_secret(secret).endswith("3456"), "mask lost the tail hint")
    check(security.mask_secret("") == "-", "empty key not handled")

    update = cb_update(ADMIN_ID, "adm:model:%s" % model_pk)
    await admin_handlers.admin_callback(update, FakeContext())
    rendered = cb_text(update)
    check(rendered, "model screen rendered nothing")
    check(secret not in rendered, "the admin model screen printed the raw API key")
    check("•" in rendered, "key was not masked on screen")


@test("the rate limiter throttles users and exempts admins")
def t_rate_limit():
    db = fresh_db()
    db.set_setting("rate_limit_messages", "3")
    db.set_setting("rate_limit_seconds", "60")
    for i in range(3):
        allowed, _ = security.check_flood(USER_ID)
        check(allowed, "throttled too early at message %s" % (i + 1))
    allowed, retry = security.check_flood(USER_ID)
    check(not allowed, "rate limit never triggered")
    check(retry > 0, "no retry-after returned")
    for _ in range(10):
        allowed, _ = security.check_flood(ADMIN_ID)
        check(allowed, "an admin was rate limited")


@test("anti-spam rejects an immediately repeated message")
def t_anti_spam():
    db = fresh_db()
    db.set_setting("antispam_duplicate_window", "60")
    check(security.check_duplicate(USER_ID, "hello") is True, "first message rejected")
    check(security.check_duplicate(USER_ID, "hello") is False, "duplicate accepted")
    check(security.check_duplicate(USER_ID, "something else") is True, "new message rejected")
    check(security.check_duplicate(ADMIN_ID, "x") and security.check_duplicate(ADMIN_ID, "x"),
          "an admin was blocked by anti-spam")


@test("input validation accepts good values and rejects bad ones")
def t_validation():
    check(security.validate_int("42") == 42, "plain int failed")
    check(security.validate_int("۱۲۳۴") == 1234, "Persian digits rejected")
    check(security.validate_int("50,000") == 50000, "thousands separator rejected")
    for bad in ("abc", "", "12abc", "1.5"):
        try:
            security.validate_int(bad)
            raise AssertionError("accepted a bad int: %r" % bad)
        except security.ValidationError:
            pass
    try:
        security.validate_int("5", minimum=10)
        raise AssertionError("range not enforced")
    except security.ValidationError:
        pass

    check(security.validate_url("https://api.openai.com/v1/chat/completions"),
          "valid url rejected")
    for bad in ("api.openai.com", "ftp://x/y", "", "https://a b"):
        try:
            security.validate_url(bad)
            raise AssertionError("accepted a bad url: %r" % bad)
        except security.ValidationError:
            pass

    check(security.validate_card("6037-9911-2233-4455") == "6037991122334455",
          "card with dashes rejected")
    for bad in ("123", "60379911223344556677", "abcd"):
        try:
            security.validate_card(bad)
            raise AssertionError("accepted a bad card: %r" % bad)
        except security.ValidationError:
            pass

    try:
        security.validate_text("x" * 5000, 1, 100)
        raise AssertionError("over-long text accepted")
    except security.ValidationError:
        pass


@test("user text is HTML-escaped before it reaches a message")
def t_escaping():
    payload = "<script>alert(1)</script> & <b>bold</b>"
    escaped = security.esc(payload)
    check("<script>" not in escaped, "script tag survived escaping")
    check("&lt;script&gt;" in escaped, "escaping did not encode angle brackets")
    check("&amp;" in escaped, "ampersand not escaped")


@test("a banned user is turned away by the message router")
async def t_banned_user():
    db = fresh_db()
    seed_model(db)
    db.set_banned(USER_ID, True)
    update = text_update(USER_ID, "hello there")
    await router.route_message(update, FakeContext())
    reply = last_reply(update)
    check(reply and ("محدود" in reply or "restricted" in reply), "banned user was served: %r" % reply)


# ===========================================================================
# 7. AI client
# ===========================================================================
class FakeResponse:
    def __init__(self, status, payload=None, text=""):
        self.status = status
        self._payload = payload
        self._text = text

    async def json(self, content_type=None):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload

    async def text(self):
        return self._text or ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeSession:
    """Records requests and replays a scripted list of responses.

    The script is shared (not copied) because the client opens a fresh session
    per request, exactly like aiohttp does.
    """

    def __init__(self, script):
        self.script = script

    def post(self, url, json=None, headers=None):
        RECORDER.append({"url": url, "payload": json, "headers": headers or {}})
        item = self.script.pop(0) if self.script else FakeResponse(200, {"choices": []})
        if isinstance(item, Exception):
            raise item
        return item

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


RECORDER = []


def session_factory(script):
    shared = list(script)   # one mutable script across every session it hands out

    def factory(timeout=None):
        return FakeSession(shared)
    return factory


@test("the request body is the OpenAI chat-completions shape")
async def t_ai_request_shape():
    db = fresh_db()
    seed_model(db, model_id="gpt-4o-mini", key="sk-abc12345")
    db.set_setting("ai_system_prompt", "You are terse.")
    RECORDER.clear()
    reply, model_name = await ai_manager.chat(
        USER_ID, "سلام",
        session_factory=session_factory([FakeResponse(200, {
            "choices": [{"message": {"role": "assistant", "content": "درود"}}]})]),
    )
    check(reply == "درود", "reply not parsed: %r" % reply)
    check(model_name == "GPT", "wrong model reported")
    sent = RECORDER[-1]
    check(sent["url"].endswith("/chat/completions"), "wrong url")
    check(sent["payload"]["model"] == "gpt-4o-mini",
          "model id not sent: %r" % sent["payload"].get("model"))
    messages = sent["payload"].get("messages")
    check(isinstance(messages, list), "payload has no messages list (the old bug)")
    check(messages[0]["role"] == "system" and "terse" in messages[0]["content"],
          "system prompt missing")
    check(messages[-1] == {"role": "user", "content": "سلام"}, "user turn malformed")
    check(sent["headers"].get("Authorization") == "Bearer sk-abc12345", "auth header missing")


@test("replies are parsed from every common provider shape")
def t_ai_response_shapes():
    shapes = [
        ({"choices": [{"message": {"content": "openai"}}]}, "openai"),
        ({"choices": [{"text": "legacy"}]}, "legacy"),
        ({"choices": [{"message": {"content": [{"type": "text", "text": "blocks"}]}}]}, "blocks"),
        ({"content": [{"type": "text", "text": "anthropic"}]}, "anthropic"),
        ({"candidates": [{"content": {"parts": [{"text": "gemini"}]}}]}, "gemini"),
        ({"response": "custom"}, "custom"),
        ({"answer": "custom2"}, "custom2"),
        ({"message": {"content": "nested"}}, "nested"),
        ("plain string", "plain string"),
    ]
    for payload, expected in shapes:
        got = _extract_reply(payload)
        check(got == expected, "shape %r parsed as %r" % (payload, got))
    for empty in (None, {}, {"choices": []}, {"choices": [{"message": {"content": ""}}]}):
        check(_extract_reply(empty) is None, "junk parsed as a reply: %r" % empty)


@test("a 429 is retried and then succeeds")
async def t_ai_retry():
    db = fresh_db()
    seed_model(db)
    db.set_setting("ai_max_retries", "3")
    RECORDER.clear()
    script = [
        FakeResponse(429, {"error": {"message": "rate limited"}}),
        FakeResponse(200, {"choices": [{"message": {"content": "second try"}}]}),
    ]
    reply, _ = await ai_manager.chat(USER_ID, "hi", session_factory=session_factory(script))
    check(reply == "second try", "retry did not recover: %r" % reply)
    check(len(RECORDER) == 2, "expected 2 attempts, made %s" % len(RECORDER))


@test("a rejected API key rotates to the next configured key")
async def t_ai_key_rotation():
    db = fresh_db()
    seed_model(db, key="sk-dead-key-1, sk-live-key-2")
    check(_split_keys("a, b\nc") == ["a", "b", "c"], "key splitting wrong")
    RECORDER.clear()
    script = [
        FakeResponse(401, {"error": {"message": "invalid key"}}),
        FakeResponse(200, {"choices": [{"message": {"content": "ok via key 2"}}]}),
    ]
    reply, _ = await ai_manager.chat(USER_ID, "hi", session_factory=session_factory(script))
    check(reply == "ok via key 2", "key rotation failed: %r" % reply)
    check(RECORDER[0]["headers"]["Authorization"] == "Bearer sk-dead-key-1", "wrong first key")
    check(RECORDER[1]["headers"]["Authorization"] == "Bearer sk-live-key-2", "did not rotate")


@test("a provider failure raises AIError with a readable reason and costs no quota")
async def t_ai_failure():
    db = fresh_db()
    seed_model(db)
    db.set_setting("ai_max_retries", "1")
    db.create_subscription(USER_ID, "free", 10, 30)
    before = subscription_manager.remaining(USER_ID)

    script = [FakeResponse(500, {"error": {"message": "upstream exploded"}})]
    try:
        await ai_manager.chat(USER_ID, "hi", session_factory=session_factory(script))
        raise AssertionError("a 500 did not raise")
    except AIError as exc:
        check("500" in str(exc), "status missing from the error: %s" % exc)
    check(subscription_manager.remaining(USER_ID) == before,
          "the user was charged for a failed request")

    try:
        await ai_manager.chat(USER_ID, "hi",
                              session_factory=session_factory([asyncio.TimeoutError()]))
        raise AssertionError("a timeout did not raise")
    except AIError as exc:
        check("timeout" in str(exc).lower(), "timeout not reported: %s" % exc)


@test("with no model configured, chat fails cleanly instead of crashing")
async def t_ai_no_model():
    fresh_db()
    check(ai_manager.list_models() == [], "models should be empty")
    try:
        await ai_manager.chat(USER_ID, "hi", session_factory=session_factory([]))
        raise AssertionError("chat succeeded without a model")
    except AIError:
        pass


@test("a model added at runtime is picked up without a restart")
def t_ai_no_stale_cache():
    db = fresh_db()
    check(ai_manager.resolve_model() is None, "a model appeared out of nowhere")
    seed_model(db, name="Fresh")
    resolved = ai_manager.resolve_model()
    check(resolved and resolved["name"] == "Fresh",
          "a newly added model is invisible: the old cache bug is back")


@test("conversation history is kept, capped and clearable")
async def t_ai_history():
    db = fresh_db()
    seed_model(db)
    db.set_setting("ai_max_history", "2")
    RECORDER.clear()
    for i in range(4):
        await ai_manager.chat(
            USER_ID, "q%s" % i,
            session_factory=session_factory([FakeResponse(200, {
                "choices": [{"message": {"content": "a%s" % i}}]})]),
        )
    messages = RECORDER[-1]["payload"]["messages"]
    check(any(m["content"] == "a2" for m in messages), "recent history not sent")
    check(not any(m["content"] == "q0" for m in messages), "history was not capped")
    ai_manager.clear_history(USER_ID)
    check(ai_manager.get_history(USER_ID) == [], "history not cleared")


@test("the admin connection test reports success and failure")
async def t_ai_test_connection():
    db = fresh_db()
    model_pk = seed_model(db)
    ok, detail, ms = await ai_manager.test_connection(
        model_pk, session_factory=session_factory([FakeResponse(200, {
            "choices": [{"message": {"content": "OK"}}]})]))
    check(ok is True and "OK" in detail, "a healthy model was reported as broken")
    ok, detail, ms = await ai_manager.test_connection(
        model_pk, session_factory=session_factory([FakeResponse(401, {
            "error": {"message": "bad key"}})]))
    check(ok is False and "401" in detail, "a broken model was reported as healthy")


# ===========================================================================
# 8. Handler smoke tests
# ===========================================================================
@test("/start greets a new user with a language picker, then the main menu")
async def t_start():
    db = fresh_db()
    context = FakeContext()
    db.execute("DELETE FROM users WHERE user_id = ?", (USER_ID,))
    update = text_update(USER_ID, "/start")
    await start_handlers.start(update, context)
    first = last_reply(update)
    check(first and ("زبان" in first or "language" in first.lower()),
          "no language picker for a new user: %r" % first)

    again = text_update(USER_ID, "/start")
    await start_handlers.start(again, FakeContext())
    second = last_reply(again)
    check(second and ("خوش آمدید" in second or "Welcome" in second),
          "returning user did not get the menu: %r" % second)


@test("choosing a language persists it and both languages render")
async def t_language_switch():
    db = fresh_db()
    context = FakeContext()
    update = cb_update(USER_ID, "lang:en")
    await start_handlers.language_set(update, context)
    check(db.get_language(USER_ID) == "en", "language not saved")
    check("Welcome" in (cb_text(update) or ""), "English menu not rendered")

    update = cb_update(USER_ID, "lang:fa")
    await start_handlers.language_set(update, FakeContext())
    check(db.get_language(USER_ID) == "fa", "language not saved back to Persian")
    check("خوش آمدید" in (cb_text(update) or ""), "Persian menu not rendered")


@test("the account screen shows the real plan, usage and expiry")
async def t_account():
    db = fresh_db()
    db.create_subscription(USER_ID, "premium", 500, 30)
    subscription_manager.consume(USER_ID)
    update = cb_update(USER_ID, "acct:view")
    await start_handlers.account(update, FakeContext())
    body = cb_text(update)
    check(body and "499" in body, "remaining messages wrong: %r" % body)
    check("500" in body, "limit not shown")


@test("a plain message reaches the AI and is charged exactly once")
async def t_chat_end_to_end():
    db = fresh_db()
    seed_model(db)
    db.create_subscription(USER_ID, "free", 5, 30)

    import bot.services.ai_manager as ai_module
    original = ai_module.ai_manager._request

    async def fake_request(model, messages, timeout_s, max_retries, session_factory=None):
        return "پاسخ آزمایشی"

    ai_module.ai_manager._request = fake_request
    try:
        update = text_update(USER_ID, "یک سوال")
        await router.route_message(update, FakeContext())
        texts = [m.text for m in update.effective_message.replies]
        edits = update.effective_message.replies[0].edits if texts else []
        combined = " ".join(texts + edits)
        check("پاسخ آزمایشی" in combined, "the AI answer never reached the user: %r" % combined)
        check(subscription_manager.remaining(USER_ID) == 4,
              "quota after one message = %s" % subscription_manager.remaining(USER_ID))
    finally:
        ai_module.ai_manager._request = original


@test("an out-of-quota user is told to buy a plan instead of being ignored")
async def t_chat_quota_block():
    db = fresh_db()
    seed_model(db)
    db.create_subscription(USER_ID, "free", 1, 30)
    subscription_manager.consume(USER_ID)
    update = text_update(USER_ID, "another question")
    await router.route_message(update, FakeContext())
    reply = last_reply(update)
    check(reply and ("سهمیه" in reply or "used all" in reply), "no quota notice: %r" % reply)


@test("the shop lists products, opens one and starts a card payment")
async def t_shop_flow():
    db = fresh_db()
    product_id = seed_product(db, name="Gold", price=120000)
    db.set_setting("card_number", "6037991122334455")
    db.set_setting("card_holder", "Daniel")
    context = FakeContext()

    update = cb_update(USER_ID, "shop:list")
    await shop.shop_list(update, context)
    check("Gold" in str(cb_markup(update).all_callback_data() if hasattr(cb_markup(update), "all_callback_data") else "")
          or "Gold" in str([b.text for row in cb_markup(update).inline_keyboard for b in row]),
          "product not listed")

    update = cb_update(USER_ID, "shop:item:%s" % product_id)
    await shop.shop_item(update, context)
    check("120,000" in (cb_text(update) or ""), "price not shown: %r" % cb_text(update))

    update = cb_update(USER_ID, "shop:buy:%s" % product_id)
    await shop.shop_buy(update, context)
    check("Gold" in (cb_text(update) or ""), "checkout screen missing the product")

    update = cb_update(USER_ID, "pay:card:%s" % product_id)
    await shop.pay_card(update, context)
    body = cb_text(update) or ""
    check("6037-9911-2233-4455" in body, "card number not shown: %r" % body)
    check(get_flow(context)["name"] == "await_receipt", "receipt flow not started")
    check(db.latest_open_payment(USER_ID) is not None, "no pending order created")


@test("a receipt notifies every admin with approve/reject buttons")
async def t_receipt_notifies_admin():
    db = fresh_db()
    product_id = seed_product(db)
    db.set_setting("card_number", "6037991122334455")
    context = FakeContext()

    await shop.pay_card(cb_update(USER_ID, "pay:card:%s" % product_id), context)
    payment_id = db.latest_open_payment(USER_ID)["id"]

    update = text_update(USER_ID, "REF-99887766")
    await router.route_message(update, context)

    check(context.bot.sent, "no admin notification was sent")
    notice = context.bot.sent[-1]
    check(notice["chat_id"] == ADMIN_ID, "notice went to %s" % notice["chat_id"])
    buttons = [b.callback_data for row in notice["kw"]["reply_markup"].inline_keyboard
               for b in row]
    check("adm:papprove:%s" % payment_id in buttons, "no approve button: %s" % buttons)
    check("adm:preject:%s" % payment_id in buttons, "no reject button")
    check(db.get_payment(payment_id)["receipt_value"] == "REF-99887766", "receipt not stored")


@test("an admin approval activates the plan and notifies the buyer")
async def t_admin_approves_payment():
    db = fresh_db()
    product_id = seed_product(db, messages=3000, days=60)
    payment_id, _ = payment_manager.start_payment(USER_ID, product_id, "card")
    payment_manager.attach_receipt(payment_id, "text", "REF")

    context = FakeContext()
    update = cb_update(ADMIN_ID, "adm:papprove:%s" % payment_id)
    await admin_handlers.admin_callback(update, context)

    check(db.get_payment(payment_id)["status"] == "confirmed", "payment not confirmed")
    sub = db.get_subscription(USER_ID)
    check(sub["plan"] == "premium" and sub["message_limit"] == 3000,
          "plan not activated: %s" % sub)
    buyer_notices = [m for m in context.bot.sent if m["chat_id"] == USER_ID]
    check(buyer_notices, "the buyer was never told their payment was approved")


@test("support: a ticket is created, the admin replies, the user is notified")
async def t_support_flow():
    db = fresh_db()
    user_ctx = FakeContext()

    await support.support_open(cb_update(USER_ID, "sup:open"), user_ctx)
    await support.support_new(cb_update(USER_ID, "sup:new"), user_ctx)
    check(get_flow(user_ctx)["name"] == "support_new", "ticket flow not started")

    update = text_update(USER_ID, "ربات پاسخ نمی‌دهد")
    await router.route_message(update, user_ctx)
    tickets = db.list_tickets(user_id=USER_ID)
    check(tickets, "no ticket was created")
    ticket_id = tickets[0]["id"]
    check(any(m["chat_id"] == ADMIN_ID for m in user_ctx.bot.sent),
          "admins were not notified about the ticket")

    admin_ctx = FakeContext()
    await admin_handlers.admin_callback(cb_update(ADMIN_ID, "adm:tkreply:%s" % ticket_id),
                                        admin_ctx)
    check(get_flow(admin_ctx)["name"] == "admin_tkreply", "admin reply flow not started")
    reply_update = text_update(ADMIN_ID, "بررسی شد، لطفاً دوباره امتحان کنید")
    await router.route_message(reply_update, admin_ctx)

    messages = db.get_ticket_messages(ticket_id)
    check(len(messages) == 2, "expected 2 messages, got %s" % len(messages))
    check(messages[-1]["is_admin"] == 1, "the reply was not marked as admin")
    check(db.get_ticket(ticket_id)["status"] == "answered", "ticket status not updated")
    check(any(m["chat_id"] == USER_ID for m in admin_ctx.bot.sent),
          "the user was not notified of the reply")


@test("a user cannot open someone else's ticket")
async def t_ticket_isolation():
    db = fresh_db()
    ticket_id = db.create_ticket(ADMIN_ID, "private", "admin's own ticket")
    update = cb_update(USER_ID, "sup:view:%s" % ticket_id)
    await support.support_view(update, FakeContext())
    check(not update.callback_query.edited, "another user's ticket was rendered")
    check(update.callback_query.answers[-1]["alert"] is True, "no refusal shown")


# ===========================================================================
# 9. Admin panel screens and flows
# ===========================================================================
@test("every admin panel screen renders for an admin")
async def t_admin_screens():
    db = fresh_db()
    model_pk = seed_model(db)
    product_id = seed_product(db)
    payment_id, _ = payment_manager.start_payment(USER_ID, product_id, "card")
    ticket_id = db.create_ticket(USER_ID, "hi", "hello")

    screens = [
        "adm:home", "adm:stats", "adm:users:0", "adm:user:%s" % USER_ID,
        "adm:models", "adm:model:%s" % model_pk,
        "adm:products", "adm:product:%s" % product_id,
        "adm:payments", "adm:payment:%s" % payment_id, "adm:payset",
        "adm:tickets", "adm:ticket:%s" % ticket_id,
        "adm:settings", "adm:grant:%s" % USER_ID,
    ]
    for data in screens:
        update = cb_update(ADMIN_ID, data)
        await admin_handlers.admin_callback(update, FakeContext())
        body = cb_text(update)
        check(body, "%s rendered nothing" % data)
        check(len(body) > 5, "%s rendered a stub: %r" % (data, body))


@test("admin flow: add an AI model step by step, then test and default it")
async def t_admin_add_model_flow():
    db = fresh_db()
    context = FakeContext()

    await admin_handlers.admin_callback(cb_update(ADMIN_ID, "adm:addmodel"), context)
    check(get_flow(context)["name"] == "admin_add_model", "flow not started")

    for value in ("Claude", "https://api.anthropic.com/v1/messages",
                  "sk-ant-secret-key-1234", "claude-3-5-sonnet"):
        update = text_update(ADMIN_ID, value)
        await router.route_message(update, context)

    model = db.get_ai_model_by_name("Claude")
    check(model is not None, "the model was not created")
    check(model["api_url"] == "https://api.anthropic.com/v1/messages", "url wrong")
    check(model["model_id"] == "claude-3-5-sonnet", "model id wrong")
    check(model["is_default"] == 1, "the first model should become the default")
    check(get_flow(context) is None, "flow not cleared")


@test("admin flow: bad input is rejected with a reason and the flow survives")
async def t_admin_validation_flow():
    db = fresh_db()
    context = FakeContext()
    await admin_handlers.admin_callback(cb_update(ADMIN_ID, "adm:addmodel"), context)
    await router.route_message(text_update(ADMIN_ID, "MyModel"), context)

    update = text_update(ADMIN_ID, "not-a-url")
    await router.route_message(update, context)
    reply = last_reply(update)
    check(reply and ("نامعتبر" in reply or "Invalid" in reply), "bad url accepted: %r" % reply)
    check(get_flow(context)["step"] == "api_url", "flow lost after a validation error")

    await router.route_message(text_update(ADMIN_ID, "https://api.example.com/v1/chat"), context)
    check(get_flow(context)["step"] == "api_key", "flow did not advance after a fix")


@test("admin flow: create a product, then edit its price")
async def t_admin_product_flow():
    db = fresh_db()
    context = FakeContext()
    await admin_handlers.admin_callback(cb_update(ADMIN_ID, "adm:addproduct"), context)
    for value in ("Starter", "۴۹۰۰۰", "30", "1000", "پلن شروع"):
        await router.route_message(text_update(ADMIN_ID, value), context)

    products = [p for p in db.get_products() if p["name"] == "Starter"]
    check(products, "product not created")
    product = products[0]
    check(product["price"] == 49000, "Persian digits not parsed: %s" % product["price"])
    check(product["messages_count"] == 1000, "message count wrong")

    await admin_handlers.admin_callback(
        cb_update(ADMIN_ID, "adm:pedit:price:%s" % product["id"]), context)
    await router.route_message(text_update(ADMIN_ID, "59000"), context)
    check(db.get_product(product["id"])["price"] == 59000, "price not updated")


@test("admin flow: change a user's free quota")
async def t_admin_quota_flow():
    db = fresh_db()
    context = FakeContext()
    await admin_handlers.admin_callback(cb_update(ADMIN_ID, "adm:quota:%s" % USER_ID), context)
    await router.route_message(text_update(ADMIN_ID, "250"), context)
    check(db.get_subscription(USER_ID)["message_limit"] == 250,
          "quota not changed: %s" % db.get_subscription(USER_ID)["message_limit"])


@test("admin flow: set the card number, rejecting a malformed one first")
async def t_admin_card_flow():
    db = fresh_db()
    context = FakeContext()
    await admin_handlers.admin_callback(cb_update(ADMIN_ID, "adm:setcard"), context)

    update = text_update(ADMIN_ID, "1234")
    await router.route_message(update, context)
    check(not db.get_setting("card_number"), "a 4-digit card was accepted")
    check(get_flow(context) is not None, "flow dropped after a validation error")

    await router.route_message(text_update(ADMIN_ID, "6037-9911-2233-4455"), context)
    check(db.get_setting("card_number") == "6037991122334455", "card not saved")


@test("admin can ban and unban a user, but never an admin")
async def t_admin_ban_flow():
    db = fresh_db()
    context = FakeContext()
    await admin_handlers.admin_callback(cb_update(ADMIN_ID, "adm:ban:%s" % USER_ID), context)
    check(db.is_banned(USER_ID) is True, "user not banned")
    await admin_handlers.admin_callback(cb_update(ADMIN_ID, "adm:ban:%s" % USER_ID), context)
    check(db.is_banned(USER_ID) is False, "user not unbanned")

    update = cb_update(ADMIN_ID, "adm:ban:%s" % ADMIN_ID)
    await admin_handlers.admin_callback(update, context)
    check(db.is_banned(ADMIN_ID) is False, "an admin was banned")


@test("admin toggles: shop, support and the payment gateway")
async def t_admin_toggles():
    db = fresh_db()
    context = FakeContext()
    for key, data in (("shop_enabled", "adm:toggle:shop_enabled"),
                      ("support_enabled", "adm:toggle:support_enabled")):
        before = db.get_bool_setting(key, True)
        await admin_handlers.admin_callback(cb_update(ADMIN_ID, data), context)
        check(db.get_bool_setting(key, True) is not before, "%s did not toggle" % key)

    before = db.get_bool_setting("gateway_enabled")
    await admin_handlers.admin_callback(cb_update(ADMIN_ID, "adm:gwtoggle"), context)
    check(db.get_bool_setting("gateway_enabled") is not before, "gateway did not toggle")


@test("disabling the shop actually closes it to users")
async def t_shop_disabled():
    db = fresh_db()
    seed_product(db)
    db.set_setting("shop_enabled", "0")
    update = cb_update(USER_ID, "shop:list")
    await shop.shop_list(update, FakeContext())
    body = cb_text(update) or ""
    check("غیرفعال" in body or "disabled" in body, "the shop stayed open: %r" % body)


@test("admin broadcast reaches every non-banned user")
async def t_admin_broadcast():
    db = fresh_db()
    db.add_user(333333, "c", "C")
    db.add_user(444444, "d", "D")
    db.set_banned(444444, True)
    context = FakeContext()
    await admin_handlers.admin_callback(cb_update(ADMIN_ID, "adm:bcast"), context)
    await router.route_message(text_update(ADMIN_ID, "پیام همگانی"), context)
    recipients = {m["chat_id"] for m in context.bot.sent}
    check(333333 in recipients, "an active user was skipped")
    check(444444 not in recipients, "a banned user received the broadcast")


@test("an unknown admin action is refused instead of crashing")
async def t_unknown_action():
    fresh_db()
    update = cb_update(ADMIN_ID, "adm:definitely_not_a_real_action")
    await admin_handlers.admin_callback(update, FakeContext())
    check(update.callback_query.answers, "unknown action left the client spinning")
    check(update.callback_query.answers[-1]["alert"] is True, "no alert shown")


@test("cancel clears any in-progress flow")
async def t_cancel():
    fresh_db()
    context = FakeContext()
    await admin_handlers.admin_callback(cb_update(ADMIN_ID, "adm:addmodel"), context)
    check(get_flow(context) is not None, "flow not started")
    await start_handlers.nav(cb_update(ADMIN_ID, "nav:cancel"), context)
    check(get_flow(context) is None, "cancel did not clear the flow")


# ===========================================================================
# 10. Deployment readiness
# ===========================================================================
@test("deployment files are present and consistent")
def t_deploy_files():
    for filename in ("Dockerfile", "railway.toml", "requirements.txt", ".env.example",
                     "README.md", ".gitignore", ".dockerignore", "Procfile"):
        path = os.path.join(HERE, filename)
        check(os.path.exists(path), "%s is missing" % filename)

    env_example = open(os.path.join(HERE, ".env.example"), encoding="utf-8").read()
    keys = {line.split("=")[0].strip() for line in env_example.splitlines()
            if "=" in line and not line.strip().startswith("#")}
    check(keys == {"TELEGRAM_BOT_TOKEN", "ADMIN_USER_IDS"},
          ".env.example should list exactly the two required vars, found %s" % keys)

    requirements = open(os.path.join(HERE, "requirements.txt"), encoding="utf-8").read().lower()
    for dead in ("sqlalchemy", "pydantic"):
        check(dead not in requirements, "%s is listed but never imported" % dead)
    for needed in ("python-telegram-bot", "aiohttp", "python-dotenv"):
        check(needed in requirements, "%s missing from requirements" % needed)

    dockerfile = open(os.path.join(HERE, "Dockerfile"), encoding="utf-8").read()
    check("PYTHONUNBUFFERED" in dockerfile, "logs would be buffered on Railway")
    check("USER " in dockerfile, "the container runs as root")

    gitignore = open(os.path.join(HERE, ".gitignore"), encoding="utf-8").read()
    check(".env" in gitignore, ".env is not gitignored: secrets could be committed")


@test("the database lives on a writable path outside the code tree")
def t_data_path():
    check(os.path.isabs(config.DB_PATH), "DB_PATH is relative: it would move with the CWD")
    parent = os.path.dirname(config.DB_PATH)
    check(os.path.isdir(parent), "the data directory was not created")
    check(os.access(parent, os.W_OK), "the data directory is not writable")


@test("no source file still contains the old broken patterns")
def t_no_regressions():
    offenders = []
    for folder, _dirs, files in os.walk(HERE):
        if any(part in folder for part in ("tests_stubs", "__pycache__", ".git")):
            continue
        for filename in files:
            if not filename.endswith(".py") or filename == "tests.py":
                continue
            path = os.path.join(folder, filename)
            body = open(path, encoding="utf-8").read()
            if '{"message": message' in body:
                offenders.append("%s: old non-standard AI payload" % filename)
            if "ORDER BY created_at DESC LIMIT 1" in body:
                offenders.append("%s: nondeterministic newest-row query" % filename)
            if re.search(r"^db = Database\(", body, re.M):
                offenders.append("%s: DB created at import time" % filename)
            if "datetime.utcnow()" in body:
                offenders.append("%s: deprecated naive utcnow()" % filename)
    check(not offenders, "regressions found: %s" % offenders)


# ===========================================================================
if __name__ == "__main__":
    print("=" * 74)
    print(" Telegram AI Bot -- test suite")
    print(" telegram/aiohttp: %s" % ("offline stubs" if USING_STUBS else "real packages"))
    print("=" * 74)
    run_all(dict(globals()))
    print("=" * 74)
    print(" %s passed, %s failed" % (len(PASSED), len(FAILED)))
    if FAILED:
        print("\n Failures:")
        for name, exc in FAILED:
            print("  - %s\n      %s" % (name, exc))
    print("=" * 74)
    sys.exit(1 if FAILED else 0)
