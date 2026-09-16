"""The 50 individually configurable bot capabilities.

Every capability can be overridden globally, per shop product, or for the
user's current subscription. Product policy is copied to a subscription when a
plan is granted/approved, so a later product edit does not unexpectedly change
an already-paid user's contract.
"""
import json
from dataclasses import dataclass

from bot.database import get_db


@dataclass(frozen=True)
class Capability:
    key: str
    fa: str
    en: str
    kind: str = "bool"
    default: object = True
    presets: tuple = ()

    def label(self, lang="fa"):
        return self.fa if lang == "fa" else self.en


_CAPS = [
    ("chat", "🤖 چت AI", "🤖 AI chat", "bool", True),
    ("streaming", "✍️ پاسخ تدریجی", "✍️ Progressive streaming", "bool", True),
    ("deep_thinking", "🧠 فکر عمیق", "🧠 Deep thinking", "bool", True),
    ("web_search", "🔎 جست‌وجوی وب", "🔎 Web search", "bool", True),
    ("multi_source_research", "📚 تحقیق چندمنبعی", "📚 Multi-source research", "bool", True),
    ("fact_check", "✅ راستی‌آزمایی", "✅ Fact checking", "bool", True),
    ("url_analysis", "🌐 تحلیل لینک", "🌐 URL analysis", "bool", True),
    ("citations", "🔗 نمایش منابع", "🔗 Source citations", "bool", True),
    ("quick_tools", "🧰 ابزارهای سریع", "🧰 Quick tools", "bool", True),
    ("translation", "🌍 ترجمه", "🌍 Translation", "bool", True),
    ("summarization", "📝 خلاصه‌سازی", "📝 Summarization", "bool", True),
    ("rewriting", "✨ بازنویسی", "✨ Rewriting", "bool", True),
    ("coding_assistant", "💻 دستیار کدنویسی", "💻 Coding assistant", "bool", True),
    ("receipt_analysis", "🧾 تحلیل رسید", "🧾 Receipt analysis", "bool", True),
    ("email_writer", "✉️ نویسنده ایمیل", "✉️ Email writer", "bool", True),
    ("resume_builder", "👔 رزومه‌ساز", "👔 Resume builder", "bool", True),
    ("marketing_copy", "📣 محتوای تبلیغاتی", "📣 Marketing copy", "bool", True),
    ("smart_compare", "⚖️ مقایسه هوشمند", "⚖️ Smart comparison", "bool", True),
    ("json_output", "🧩 خروجی JSON", "🧩 JSON output", "bool", True),
    ("bullet_output", "📌 خروجی نکته‌ای", "📌 Bullet output", "bool", True),
    ("table_output", "📋 خروجی جدولی", "📋 Table output", "bool", True),
    ("calculator", "🧮 ماشین‌حساب", "🧮 Calculator", "bool", True),
    ("datetime_tool", "🕒 تاریخ و ساعت", "🕒 Date & time", "bool", True),
    ("chat_export", "📤 خروجی چت", "📤 Chat export", "bool", True),
    ("vision_images", "🖼 تحلیل تصویر", "🖼 Image vision", "bool", True),
    ("file_uploads", "📎 ارسال فایل", "📎 File uploads", "bool", True),
    ("pdf_files", "📄 فایل PDF", "📄 PDF files", "bool", True),
    ("docx_files", "📝 فایل DOCX", "📝 DOCX files", "bool", True),
    ("text_files", "📃 فایل متنی", "📃 Text files", "bool", True),
    ("zip_files", "🗜 فایل ZIP", "🗜 ZIP files", "bool", False),
    ("archive_extraction", "📦 استخراج آرشیو", "📦 Archive extraction", "bool", False),
    ("code_files", "🧑‍💻 فایل کد", "🧑‍💻 Code files", "bool", True),
    ("spreadsheet_files", "📊 فایل CSV", "📊 Spreadsheet files", "bool", True),
    ("max_file_mb", "📏 سقف حجم فایل (MB)", "📏 Max file size (MB)", "number", 10),
    ("max_archive_files", "🗃 سقف فایل داخل ZIP", "🗃 Max files in ZIP", "number", 20),
    ("max_extracted_chars", "🔤 سقف متن استخراجی", "🔤 Max extracted chars", "number", 30000),
    ("provider_fallback", "🔁 مدل جایگزین", "🔁 Provider fallback", "bool", True),
    ("key_rotation", "🔐 چرخش API Key", "🔐 API key rotation", "bool", True),
    ("conversation_memory", "🧠 حافظه گفتگو", "🧠 Conversation memory", "bool", True),
    ("max_history", "🧾 عمق حافظه", "🧾 Memory depth", "number", 8),
    ("custom_model_selection", "🎛 انتخاب مدل", "🎛 Model selection", "bool", True),
    ("model_scope", "🎯 محدودیت مدل پلن", "🎯 Plan model scope", "bool", True),
    ("token_quota", "🪙 سهمیه توکنی", "🪙 Token quota", "bool", True),
    ("message_quota", "💬 سهمیه پیامی", "💬 Message quota", "bool", True),
    ("both_quota", "🔒 سهمیه ترکیبی", "🔒 Combined quota", "bool", True),
    ("support_tickets", "🎫 تیکت پشتیبانی", "🎫 Support tickets", "bool", True),
    ("shop", "🛒 فروشگاه", "🛒 Shop", "bool", True),
    ("card_payment", "💳 کارت‌به‌کارت", "💳 Card payment", "bool", True),
    ("gateway_payment", "🌐 درگاه آنلاین", "🌐 Online gateway", "bool", False),
    ("admin_notifications", "🔔 اعلان مدیر", "🔔 Admin notifications", "bool", True),
]

FEATURES = tuple(
    Capability(key, fa, en, kind, default,
               (1, 5, 10, 25, 50) if key == "max_file_mb" else
               (5, 10, 20, 50, 100) if key == "max_archive_files" else
               (5000, 10000, 30000, 100000) if key == "max_extracted_chars" else
               (0, 4, 8, 16, 32) if key == "max_history" else ())
    for key, fa, en, kind, default in _CAPS
)
FEATURE_MAP = {item.key: item for item in FEATURES}
assert len(FEATURES) == 50


def _decode(value):
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    try:
        parsed = json.loads(str(value))
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


def _encode(policy):
    return json.dumps(policy or {}, ensure_ascii=False, separators=(",", ":"))


def normalize(key, value):
    cap = FEATURE_MAP[key]
    if cap.kind == "number":
        try:
            number = int(value)
        except (TypeError, ValueError):
            number = int(cap.default)
        return max(0, number)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on", "enabled")
    return bool(value)


def global_value(key):
    cap = FEATURE_MAP[key]
    override = get_db().get_feature_override("global", 0, key)
    return normalize(key, cap.default if override is None else override)


def product_value(product_id, key):
    cap = FEATURE_MAP[key]
    product = get_db().get_product(product_id) or {}
    policy = _decode(product.get("feature_policy"))
    if key in policy:
        return normalize(key, policy[key])
    return global_value(key)


def user_value(user_id, key):
    cap = FEATURE_MAP[key]
    sub = get_db().get_subscription(user_id) or {}
    policy = _decode(sub.get("feature_policy"))
    if key in policy:
        return normalize(key, policy[key])
    return global_value(key)


def value_for_user(user_id, key):
    if key not in FEATURE_MAP:
        return None
    return user_value(user_id, key)


def enabled(user_id, key):
    value = value_for_user(user_id, key)
    return bool(value) if key in FEATURE_MAP and FEATURE_MAP[key].kind == "bool" else bool(value)


def policy_for_product(product_id):
    return _decode((get_db().get_product(product_id) or {}).get("feature_policy"))


def set_global(key, value):
    if key not in FEATURE_MAP:
        raise KeyError(key)
    get_db().set_feature_override("global", 0, key, normalize(key, value))


def set_product(product_id, key, value):
    if key not in FEATURE_MAP:
        raise KeyError(key)
    db = get_db()
    product = db.get_product(product_id)
    policy = _decode((product or {}).get("feature_policy"))
    policy[key] = normalize(key, value)
    db.set_product_feature_policy(product_id, policy)


def set_user(user_id, key, value):
    if key not in FEATURE_MAP:
        raise KeyError(key)
    db = get_db()
    sub = db.get_subscription(user_id)
    if not sub:
        from bot.services.subscription import subscription_manager
        sub = subscription_manager.ensure_subscription(user_id)
    policy = _decode((sub or {}).get("feature_policy"))
    policy[key] = normalize(key, value)
    db.set_subscription_feature_policy((sub or {}).get("id"), policy)


def scope_value(scope, scope_id, key):
    if scope == "global":
        return global_value(key)
    if scope == "product":
        return product_value(scope_id, key)
    return user_value(scope_id, key)


def cycle_value(key, current):
    cap = FEATURE_MAP[key]
    if cap.kind == "bool":
        return not bool(current)
    values = cap.presets or (cap.default,)
    try:
        index = values.index(int(current))
        return values[(index + 1) % len(values)]
    except (ValueError, TypeError):
        return values[0]


def button_text(key, value, lang):
    cap = FEATURE_MAP[key]
    if cap.kind == "bool":
        return "%s %s" % ("✅" if value else "❌", cap.label(lang))
    return "🔢 %s: %s" % (cap.label(lang), format(int(value), ","))
