"""Payments: card-to-card with manual approval, plus an optional gateway hook.

Fixes versus the old implementation:

* confirm_payment() used to open a second SQLite connection while its own write
  transaction was still open, which raised "database is locked" every single
  time. It is now one atomic transaction via db.tx().
* Nothing ever called create_payment/confirm_payment: the whole purchase flow
  was dead code. It is now wired to the shop handlers and the admin panel.
* Approving twice used to be possible; status is now checked inside the
  transaction so double-crediting cannot happen.
"""
import logging

from bot.database import get_db, iso, utcnow

logger = logging.getLogger(__name__)

METHOD_CARD = "card"
METHOD_GATEWAY = "gateway"

PENDING = "pending"
CONFIRMED = "confirmed"
REJECTED = "rejected"


class PaymentError(Exception):
    pass


class PaymentManager:
    def start_payment(self, user_id, product_id, method):
        db = get_db()
        product = db.get_product(product_id)
        if not product or not product["status"]:
            raise PaymentError("product unavailable")
        payment_id = db.create_payment(user_id, product_id, product["price"], method)
        logger.info("payment %s opened user=%s product=%s", payment_id, user_id, product_id)
        return payment_id, product

    def attach_receipt(self, payment_id, receipt_type, receipt_value):
        get_db().attach_receipt(payment_id, receipt_type, receipt_value)

    def card_details(self):
        db = get_db()
        return db.get_setting("card_number") or "", db.get_setting("card_holder") or ""

    def gateway_enabled(self):
        db = get_db()
        return db.get_bool_setting("gateway_enabled") and bool(db.get_setting("gateway_url"))

    def approve(self, payment_id, admin_id):
        """Atomically confirm a payment and activate the subscription."""
        db = get_db()
        with db.tx() as conn:
            row = conn.execute(
                "SELECT * FROM payments WHERE id = ?", (payment_id,)
            ).fetchone()
            if not row:
                raise PaymentError("payment not found")
            if row["status"] != PENDING:
                raise PaymentError("payment already %s" % row["status"])

            product = conn.execute(
                "SELECT * FROM products WHERE id = ?", (row["product_id"],)
            ).fetchone()
            if not product:
                raise PaymentError("product no longer exists")

            conn.execute(
                "UPDATE payments SET status = ?, reviewed_at = ?, reviewed_by = ? WHERE id = ?",
                (CONFIRMED, iso(utcnow()), admin_id, payment_id),
            )
            # Nested call joins this same transaction instead of deadlocking.
            messages = int(product["messages_count"] or 0)
            if messages <= 0:
                messages = db.get_int_setting("free_message_limit", 10) * 10
            db.create_subscription(
                row["user_id"], "premium", messages, int(product["duration_days"] or 30)
            )

        sub = db.get_subscription(row["user_id"])
        logger.info("payment %s approved by %s", payment_id, admin_id)
        return dict(row), dict(product), sub

    def reject(self, payment_id, admin_id):
        db = get_db()
        with db.tx() as conn:
            row = conn.execute(
                "SELECT * FROM payments WHERE id = ?", (payment_id,)
            ).fetchone()
            if not row:
                raise PaymentError("payment not found")
            if row["status"] != PENDING:
                raise PaymentError("payment already %s" % row["status"])
            conn.execute(
                "UPDATE payments SET status = ?, reviewed_at = ?, reviewed_by = ? WHERE id = ?",
                (REJECTED, iso(utcnow()), admin_id, payment_id),
            )
        logger.info("payment %s rejected by %s", payment_id, admin_id)
        return dict(row)

    def gateway_url_for(self, payment_id, amount):
        db = get_db()
        base = (db.get_setting("gateway_url") or "").rstrip("/")
        if not base:
            return None
        token = db.get_setting("gateway_token") or ""
        sep = "&" if "?" in base else "?"
        url = "%s%samount=%s&order=%s" % (base, sep, int(amount), payment_id)
        if token:
            url += "&token=%s" % token
        return url


payment_manager = PaymentManager()
