"""Quota, expiry and per-subscription AI policy rules."""
import logging

from bot.database import get_db, parse_iso, utcnow
from bot.capabilities import enabled as capability_enabled

logger = logging.getLogger(__name__)

OK = "ok"
NO_SUB = "no_subscription"
EXPIRED = "expired"
EXHAUSTED = "exhausted"


class SubscriptionManager:
    def ensure_subscription(self, user_id):
        """Every user gets one free subscription, seeded from admin settings."""
        db = get_db()
        sub = db.get_subscription(user_id)
        if sub:
            return sub
        mode = db.get_setting("default_quota_mode", "messages")
        tokens = db.get_int_setting("free_token_limit", 100000)
        db.create_subscription(
            user_id,
            "free",
            db.get_int_setting("free_message_limit", 10),
            db.get_int_setting("free_period_days", 30),
            quota_mode=mode,
            token_limit=tokens,
            model_scope=db.get_setting("default_model_scope", "all"),
        )
        return db.get_subscription(user_id)

    def _mode(self, user_id, sub):
        mode = str((sub or {}).get("quota_mode") or "messages").lower()
        if mode not in ("messages", "tokens", "both"):
            mode = "messages"
        messages_on = capability_enabled(user_id, "message_quota")
        tokens_on = capability_enabled(user_id, "token_quota")
        if mode == "tokens" and not tokens_on:
            return "messages"
        if mode == "messages" and not messages_on and tokens_on:
            return "tokens"
        if mode == "both":
            if not capability_enabled(user_id, "both_quota"):
                mode = "messages" if messages_on else "tokens"
            elif messages_on and tokens_on:
                return "both"
            else:
                return "messages" if messages_on else "tokens"
        return mode

    def status(self, user_id):
        """Return ``(state, subscription)`` without mutating quota."""
        sub = self.ensure_subscription(user_id)
        if not sub:
            return NO_SUB, None
        expire = parse_iso(sub.get("expire_date"))
        if expire and expire < utcnow():
            return EXPIRED, sub

        mode = self._mode(user_id, sub)
        message_exhausted = int(sub.get("message_used") or 0) >= int(sub.get("message_limit") or 0)
        token_limit = int(sub.get("token_limit") or 0)
        token_exhausted = token_limit <= 0 or int(sub.get("token_used") or 0) >= token_limit
        if (mode == "messages" and message_exhausted) or \
                (mode == "tokens" and token_exhausted) or \
                (mode == "both" and (message_exhausted or token_exhausted)):
            return EXHAUSTED, sub
        return OK, sub

    def can_send(self, user_id):
        return self.status(user_id)[0] == OK

    def remaining(self, user_id):
        """Primary remaining unit, retained as an integer for old integrations."""
        sub = self.ensure_subscription(user_id)
        if not sub:
            return 0
        messages = max(0, int(sub.get("message_limit") or 0) - int(sub.get("message_used") or 0))
        tokens = max(0, int(sub.get("token_limit") or 0) - int(sub.get("token_used") or 0))
        mode = self._mode(user_id, sub)
        if mode == "tokens":
            return tokens
        if mode == "both":
            return min(messages, tokens)
        return messages

    def remaining_tokens(self, user_id):
        sub = self.ensure_subscription(user_id)
        if not sub:
            return 0
        return max(0, int(sub.get("token_limit") or 0) - int(sub.get("token_used") or 0))

    def consume(self, user_id, tokens=0):
        """Charge one successful AI turn and its measured/estimated tokens."""
        state, sub = self.status(user_id)
        if state != OK or not sub:
            return False
        db = get_db()
        token_count = max(1, int(tokens or 0))
        db.increment_usage(sub["id"], messages=1, tokens=token_count)
        return True

    def grant_plan(self, user_id, plan, message_limit, duration_days,
                   quota_mode="messages", token_limit=0, model_scope="all",
                   feature_policy=None):
        db = get_db()
        db.create_subscription(user_id, plan, message_limit, duration_days,
                               quota_mode=quota_mode, token_limit=token_limit,
                               model_scope=model_scope, feature_policy=feature_policy)
        return db.get_subscription(user_id)

    def set_quota(self, user_id, limit):
        sub = self.ensure_subscription(user_id)
        if sub:
            get_db().set_message_limit(sub["id"], limit)
        return self.ensure_subscription(user_id)

    def set_policy(self, user_id, quota_mode=None, token_limit=None, model_scope=None):
        sub = self.ensure_subscription(user_id)
        if sub:
            get_db().set_subscription_policy(sub["id"], quota_mode, token_limit, model_scope)
        return self.ensure_subscription(user_id)


subscription_manager = SubscriptionManager()
