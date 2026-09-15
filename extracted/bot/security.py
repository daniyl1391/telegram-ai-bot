"""Access control, rate limiting, anti-spam and input validation.

The previous version declared RATE_LIMIT_* constants and never used them, and
the README claimed "input validation on all handlers" where there was none.
Everything here is actually wired into the handlers.
"""
import time
import html
import logging
import functools
from collections import defaultdict, deque

from bot.config import ADMIN_USER_IDS
from bot.database import get_db
from bot.i18n import t

logger = logging.getLogger(__name__)

MAX_MESSAGE_CHARS = 4000
MAX_NAME_CHARS = 64
MAX_DESC_CHARS = 500


# ----------------------------------------------------------------- admin check
def is_admin(user_id):
    """The ONLY source of truth for admin rights: the env allow-list.
    Deliberately ignores any DB column so a compromised DB cannot mint admins."""
    return user_id in ADMIN_USER_IDS


# ------------------------------------------------------------------ escaping
def esc(value):
    """Escape user-supplied text before it goes into an HTML-parsed message."""
    if value is None:
        return ""
    return html.escape(str(value), quote=False)


def mask_secret(secret):
    """Never show a full API key, not even to an admin."""
    if not secret:
        return "-"
    secret = str(secret)
    if len(secret) <= 8:
        return secret[:2] + "•" * max(len(secret) - 2, 3)
    return secret[:4] + "•" * 8 + secret[-4:]


# -------------------------------------------------------------- rate limiting
class RateLimiter:
    """Sliding-window limiter. Admins are exempt."""

    def __init__(self):
        self._hits = defaultdict(deque)

    def check(self, user_id, max_messages, per_seconds):
        if is_admin(user_id) or max_messages <= 0 or per_seconds <= 0:
            return True, 0
        now = time.monotonic()
        window = self._hits[user_id]
        while window and now - window[0] > per_seconds:
            window.popleft()
        if len(window) >= max_messages:
            return False, max(1, int(per_seconds - (now - window[0])) + 1)
        window.append(now)
        return True, 0

    def reset(self, user_id=None):
        if user_id is None:
            self._hits.clear()
        else:
            self._hits.pop(user_id, None)


class AntiSpam:
    """Rejects the exact same text repeated inside a short window."""

    def __init__(self):
        self._last = {}

    def check(self, user_id, text, window_seconds):
        if is_admin(user_id) or not text:
            return True
        now = time.monotonic()
        previous = self._last.get(user_id)
        digest = text.strip().lower()
        if previous and previous[0] == digest and now - previous[1] < window_seconds:
            self._last[user_id] = (digest, now)
            return False
        self._last[user_id] = (digest, now)
        return True

    def reset(self, user_id=None):
        if user_id is None:
            self._last.clear()
        else:
            self._last.pop(user_id, None)


rate_limiter = RateLimiter()
anti_spam = AntiSpam()


def check_flood(user_id):
    """Returns (allowed, retry_after_seconds) using the admin-configured limits."""
    db = get_db()
    return rate_limiter.check(
        user_id,
        db.get_int_setting("rate_limit_messages", 5),
        db.get_int_setting("rate_limit_seconds", 60),
    )


def check_duplicate(user_id, text):
    db = get_db()
    return anti_spam.check(
        user_id, text, db.get_int_setting("antispam_duplicate_window", 20)
    )


# ------------------------------------------------------------------ decorator
def admin_only(func):
    """Guard for every admin handler.

    Critically, it *answers* the callback query before refusing. The old code
    did a bare `return`, which left the Telegram client spinning forever.
    """

    @functools.wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        user = update.effective_user
        uid = getattr(user, "id", None)
        lang = get_db().get_language(uid) if uid else "fa"
        if not is_admin(uid):
            logger.warning("Blocked admin-panel attempt by user_id=%s", uid)
            if getattr(update, "callback_query", None):
                await update.callback_query.answer(t("not_authorized", lang), show_alert=True)
            elif getattr(update, "message", None):
                await update.message.reply_text(t("not_authorized", lang))
            return None
        return await func(update, context, *args, **kwargs)

    return wrapper


# ----------------------------------------------------------------- validation
class ValidationError(Exception):
    def __init__(self, key, **params):
        super().__init__(key)
        self.key = key
        self.params = params

    def message(self, lang):
        return t(self.key, lang, **self.params)


def validate_int(raw, minimum=None, maximum=None):
    text = (raw or "").strip()
    # tolerate Persian/Arabic-Indic digits and thousands separators
    translation = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    text = text.translate(translation).replace(",", "").replace("،", "").replace(" ", "")
    if not text.lstrip("-").isdigit():
        raise ValidationError("v_not_a_number")
    value = int(text)
    if minimum is not None and value < minimum:
        raise ValidationError("v_out_of_range", min=minimum, max=maximum if maximum is not None else "∞")
    if maximum is not None and value > maximum:
        raise ValidationError("v_out_of_range", min=minimum if minimum is not None else 0, max=maximum)
    return value


def validate_url(raw):
    text = (raw or "").strip()
    if not text.lower().startswith(("http://", "https://")):
        raise ValidationError("v_bad_url")
    if len(text) < 12 or " " in text:
        raise ValidationError("v_bad_url")
    return text


def validate_text(raw, minimum=1, maximum=MAX_NAME_CHARS):
    text = (raw or "").strip()
    if len(text) < minimum:
        raise ValidationError("v_too_short", min=minimum)
    if len(text) > maximum:
        raise ValidationError("v_too_long", max=maximum)
    return text


def validate_card(raw):
    translation = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    digits = "".join(ch for ch in (raw or "").translate(translation) if ch.isdigit())
    if len(digits) != 16:
        raise ValidationError("v_bad_card")
    return digits


def format_card(card):
    if not card:
        return ""
    return "-".join(card[i:i + 4] for i in range(0, len(card), 4))


def validate_api_key(raw):
    return validate_text(raw, minimum=8, maximum=300)
