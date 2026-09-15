"""Quota and subscription rules.

The old version compared a naive local datetime against a UTC-ish string, and
read the newest row with ORDER BY created_at which could return the stale free
plan. Both are fixed in the data layer; this module now only holds the rules.
"""
import logging

from bot.database import get_db, parse_iso, utcnow

logger = logging.getLogger(__name__)

OK = "ok"
NO_SUB = "no_subscription"
EXPIRED = "expired"
EXHAUSTED = "exhausted"


class SubscriptionManager:
    def ensure_subscription(self, user_id):
        """Every user always has a subscription row. Creates the free one once."""
        db = get_db()
        sub = db.get_subscription(user_id)
        if sub:
            return sub
        db.create_subscription(
            user_id,
            "free",
            db.get_int_setting("free_message_limit", 10),
            db.get_int_setting("free_period_days", 30),
        )
        return db.get_subscription(user_id)

    def status(self, user_id):
        """Returns (state, subscription_dict)."""
        sub = self.ensure_subscription(user_id)
        if not sub:
            return NO_SUB, None
        expire = parse_iso(sub.get("expire_date"))
        if expire and expire < utcnow():
            return EXPIRED, sub
        if int(sub.get("message_used") or 0) >= int(sub.get("message_limit") or 0):
            return EXHAUSTED, sub
        return OK, sub

    def can_send(self, user_id):
        return self.status(user_id)[0] == OK

    def remaining(self, user_id):
        sub = self.ensure_subscription(user_id)
        if not sub:
            return 0
        return max(0, int(sub.get("message_limit") or 0) - int(sub.get("message_used") or 0))

    def consume(self, user_id):
        """Charge one message. Returns True when it was charged."""
        state, sub = self.status(user_id)
        if state != OK or not sub:
            return False
        get_db().increment_message_used(sub["id"])
        return True

    def grant_plan(self, user_id, plan, message_limit, duration_days):
        db = get_db()
        db.create_subscription(user_id, plan, message_limit, duration_days)
        return db.get_subscription(user_id)

    def set_quota(self, user_id, limit):
        sub = self.ensure_subscription(user_id)
        if sub:
            get_db().set_message_limit(sub["id"], limit)
        return self.ensure_subscription(user_id)


subscription_manager = SubscriptionManager()
