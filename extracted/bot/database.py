"""SQLite data layer.

Design notes (these fix real bugs from the previous version):

* ONE long-lived connection guarded by a re-entrant lock. The old code opened a
  new connection per call, so `payment.confirm_payment()` opened a second
  connection while its own write transaction was still open and SQLite raised
  "database is locked". With a single connection + RLock, nested calls join the
  outer transaction instead of deadlocking against it.
* `tx()` is an atomic context manager: commit on success, rollback on error.
  Nested `tx()` blocks are safe (savepoint-free re-entrancy via depth counter),
  so a partly-applied payment can no longer happen.
* All timestamps are stored as explicit UTC ISO-8601 strings. The old code mixed
  Python-adapted naive local datetimes with SQLite's UTC CURRENT_TIMESTAMP and
  compared them, which silently mis-expired subscriptions. It also relied on the
  sqlite3 datetime adapters that are deprecated in Python 3.12.
* Newest-row lookups order by `id DESC`, not `created_at DESC`. CURRENT_TIMESTAMP
  only has second resolution, so two rows created in the same second sorted
  nondeterministically and a freshly purchased plan could lose to the old free
  row, i.e. a paying customer got nothing.
* Indexes and foreign keys are declared, and a tiny migration runner adds
  columns to databases created by the old version.
"""
import os
import sqlite3
import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 2


# --------------------------------------------------------------------- helpers
def utcnow():
    return datetime.now(timezone.utc)


def iso(dt):
    """Serialise an aware datetime to a UTC ISO-8601 string."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_iso(value):
    """Parse a stored timestamp into an aware UTC datetime, or None."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip().replace(" ", "T", 1)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        logger.warning("Unparseable timestamp in DB: %r", value)
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._lock = threading.RLock()
        self._depth = 0
        self._conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA busy_timeout=30000")
        self.init_db()

    # -------------------------------------------------------------- plumbing
    @contextmanager
    def tx(self):
        """Atomic, re-entrant transaction."""
        with self._lock:
            self._depth += 1
            outermost = self._depth == 1
            try:
                yield self._conn
            except Exception:
                if outermost:
                    self._conn.rollback()
                raise
            else:
                if outermost:
                    self._conn.commit()
            finally:
                self._depth -= 1

    def query(self, sql, params=()):
        with self._lock:
            return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def query_one(self, sql, params=()):
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def scalar(self, sql, params=(), default=0):
        with self._lock:
            row = self._conn.execute(sql, params).fetchone()
        if not row or row[0] is None:
            return default
        return row[0]

    def execute(self, sql, params=()):
        with self.tx() as conn:
            cur = conn.execute(sql, params)
            return cur.lastrowid

    def close(self):
        with self._lock:
            self._conn.close()

    # ---------------------------------------------------------------- schema
    def init_db(self):
        with self.tx() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id     INTEGER PRIMARY KEY,
                    username    TEXT,
                    first_name  TEXT,
                    language    TEXT    DEFAULT 'fa',
                    is_banned   INTEGER DEFAULT 0,
                    created_at  TEXT    NOT NULL,
                    last_seen   TEXT
                );

                CREATE TABLE IF NOT EXISTS subscriptions (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id       INTEGER NOT NULL,
                    plan          TEXT    NOT NULL DEFAULT 'free',
                    message_limit INTEGER NOT NULL DEFAULT 10,
                    message_used  INTEGER NOT NULL DEFAULT 0,
                    expire_date   TEXT,
                    created_at    TEXT    NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_subs_user ON subscriptions(user_id, id DESC);

                CREATE TABLE IF NOT EXISTS ai_models (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    name       TEXT UNIQUE NOT NULL,
                    api_url    TEXT NOT NULL,
                    api_key    TEXT NOT NULL,
                    model_id   TEXT NOT NULL,
                    status     INTEGER DEFAULT 1,
                    is_default INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS products (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    name           TEXT NOT NULL,
                    description    TEXT DEFAULT '',
                    price          INTEGER NOT NULL DEFAULT 0,
                    duration_days  INTEGER NOT NULL DEFAULT 30,
                    messages_count INTEGER NOT NULL DEFAULT 0,
                    status         INTEGER DEFAULT 1,
                    created_at     TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS payments (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id        INTEGER NOT NULL,
                    product_id     INTEGER,
                    amount         INTEGER NOT NULL DEFAULT 0,
                    payment_method TEXT,
                    status         TEXT DEFAULT 'pending',
                    receipt_type   TEXT,
                    receipt_value  TEXT,
                    created_at     TEXT NOT NULL,
                    reviewed_at    TEXT,
                    reviewed_by    INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_pay_status ON payments(status, id DESC);
                CREATE INDEX IF NOT EXISTS idx_pay_user ON payments(user_id, id DESC);

                CREATE TABLE IF NOT EXISTS support_tickets (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER NOT NULL,
                    subject    TEXT,
                    status     TEXT DEFAULT 'open',
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_tickets_status ON support_tickets(status, id DESC);

                CREATE TABLE IF NOT EXISTS support_messages (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id  INTEGER NOT NULL,
                    user_id    INTEGER,
                    message    TEXT,
                    is_admin   INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (ticket_id) REFERENCES support_tickets(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_tmsg_ticket ON support_messages(ticket_id, id);

                CREATE TABLE IF NOT EXISTS ai_usage (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER NOT NULL,
                    model_name TEXT,
                    ok         INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_usage_user ON ai_usage(user_id, id DESC);

                CREATE TABLE IF NOT EXISTS settings (
                    key        TEXT PRIMARY KEY,
                    value      TEXT,
                    updated_at TEXT
                );
                """
            )
        self._migrate()

    def _migrate(self):
        """Bring databases made by the old version up to the current schema."""
        current = int(self.get_setting("schema_version") or 0)
        # Old schema used ai_models.model_name; new code uses model_id.
        cols = {r["name"] for r in self.query("PRAGMA table_info(ai_models)")}
        if "model_id" not in cols and "model_name" in cols:
            logger.info("Migrating ai_models.model_name -> model_id")
            with self.tx() as conn:
                conn.execute("ALTER TABLE ai_models RENAME COLUMN model_name TO model_id")
        for table, column, ddl in (
            ("users", "language", "TEXT DEFAULT 'fa'"),
            ("users", "is_banned", "INTEGER DEFAULT 0"),
            ("users", "last_seen", "TEXT"),
            ("payments", "receipt_type", "TEXT"),
            ("payments", "receipt_value", "TEXT"),
            ("payments", "reviewed_at", "TEXT"),
            ("payments", "reviewed_by", "INTEGER"),
            ("support_tickets", "updated_at", "TEXT"),
        ):
            existing = {r["name"] for r in self.query("PRAGMA table_info(%s)" % table)}
            if existing and column not in existing:
                logger.info("Migrating: adding %s.%s", table, column)
                with self.tx() as conn:
                    conn.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table, column, ddl))
        if current != SCHEMA_VERSION:
            self.set_setting("schema_version", str(SCHEMA_VERSION))

    def seed_settings(self, defaults):
        with self.tx() as conn:
            for key, value in defaults.items():
                conn.execute(
                    "INSERT INTO settings(key, value, updated_at) VALUES (?, ?, ?) "
                    "ON CONFLICT(key) DO NOTHING",
                    (key, value, iso(utcnow())),
                )

    # ----------------------------------------------------------------- users
    def add_user(self, user_id, username, first_name, language=None):
        """Insert or refresh a user. Returns True when the row is brand new."""
        now = iso(utcnow())
        with self.tx() as conn:
            existing = conn.execute(
                "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE users SET username = ?, first_name = ?, last_seen = ? "
                    "WHERE user_id = ?",
                    (username, first_name, now, user_id),
                )
                return False
            conn.execute(
                "INSERT INTO users (user_id, username, first_name, language, "
                "is_banned, created_at, last_seen) VALUES (?, ?, ?, ?, 0, ?, ?)",
                (user_id, username, first_name, language or "fa", now, now),
            )
            return True

    def get_user(self, user_id):
        return self.query_one("SELECT * FROM users WHERE user_id = ?", (user_id,))

    def set_language(self, user_id, language):
        self.execute("UPDATE users SET language = ? WHERE user_id = ?", (language, user_id))

    def get_language(self, user_id):
        row = self.query_one("SELECT language FROM users WHERE user_id = ?", (user_id,))
        return (row or {}).get("language") or "fa"

    def set_banned(self, user_id, banned):
        self.execute(
            "UPDATE users SET is_banned = ? WHERE user_id = ?",
            (1 if banned else 0, user_id),
        )

    def is_banned(self, user_id):
        row = self.query_one("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
        return bool((row or {}).get("is_banned"))

    def count_users(self):
        return int(self.scalar("SELECT COUNT(*) FROM users"))

    def list_users(self, limit=8, offset=0):
        return self.query(
            "SELECT * FROM users ORDER BY created_at DESC, user_id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )

    def all_user_ids(self):
        return [r["user_id"] for r in self.query(
            "SELECT user_id FROM users WHERE is_banned = 0")]

    def find_users(self, term):
        term = (term or "").strip().lstrip("@")
        if not term:
            return []
        if term.isdigit():
            row = self.get_user(int(term))
            if row:
                return [row]
        return self.query(
            "SELECT * FROM users WHERE username LIKE ? OR first_name LIKE ? LIMIT 10",
            ("%" + term + "%", "%" + term + "%"),
        )

    # --------------------------------------------------------- subscriptions
    def get_subscription(self, user_id):
        # id DESC, not created_at DESC -- see module docstring.
        return self.query_one(
            "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        )

    def create_subscription(self, user_id, plan, message_limit, duration_days=30):
        expire = iso(utcnow() + timedelta(days=int(duration_days))) if duration_days else None
        return self.execute(
            "INSERT INTO subscriptions (user_id, plan, message_limit, message_used, "
            "expire_date, created_at) VALUES (?, ?, ?, 0, ?, ?)",
            (user_id, plan, int(message_limit), expire, iso(utcnow())),
        )

    def set_message_limit(self, subscription_id, limit):
        self.execute(
            "UPDATE subscriptions SET message_limit = ? WHERE id = ?",
            (int(limit), subscription_id),
        )

    def increment_message_used(self, subscription_id):
        self.execute(
            "UPDATE subscriptions SET message_used = message_used + 1 WHERE id = ?",
            (subscription_id,),
        )

    def count_active_subscriptions(self):
        now = iso(utcnow())
        return int(self.scalar(
            "SELECT COUNT(DISTINCT user_id) FROM subscriptions "
            "WHERE plan != 'free' AND (expire_date IS NULL OR expire_date > ?)",
            (now,),
        ))

    # ------------------------------------------------------------- ai models
    def add_ai_model(self, name, api_url, api_key, model_id, make_default=False):
        with self.tx() as conn:
            cur = conn.execute(
                "INSERT INTO ai_models (name, api_url, api_key, model_id, status, "
                "is_default, created_at) VALUES (?, ?, ?, ?, 1, 0, ?)",
                (name, api_url, api_key, model_id, iso(utcnow())),
            )
            model_id_pk = cur.lastrowid
            has_default = conn.execute(
                "SELECT COUNT(*) FROM ai_models WHERE is_default = 1"
            ).fetchone()[0]
            if make_default or not has_default:
                conn.execute("UPDATE ai_models SET is_default = 0")
                conn.execute("UPDATE ai_models SET is_default = 1 WHERE id = ?", (model_id_pk,))
                conn.execute(
                    "INSERT INTO settings(key, value, updated_at) VALUES ('default_ai_model', ?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                    "updated_at = excluded.updated_at",
                    (name, iso(utcnow())),
                )
            return model_id_pk

    def update_ai_model(self, model_pk, **fields):
        allowed = {"name", "api_url", "api_key", "model_id", "status"}
        sets, params = [], []
        for key, value in fields.items():
            if key in allowed:
                sets.append("%s = ?" % key)
                params.append(value)
        if not sets:
            return
        params.append(model_pk)
        self.execute("UPDATE ai_models SET %s WHERE id = ?" % ", ".join(sets), tuple(params))

    def delete_ai_model(self, model_pk):
        with self.tx() as conn:
            row = conn.execute(
                "SELECT name, is_default FROM ai_models WHERE id = ?", (model_pk,)
            ).fetchone()
            conn.execute("DELETE FROM ai_models WHERE id = ?", (model_pk,))
            if row and row["is_default"]:
                nxt = conn.execute(
                    "SELECT id, name FROM ai_models WHERE status = 1 ORDER BY id LIMIT 1"
                ).fetchone()
                new_default = nxt["name"] if nxt else ""
                if nxt:
                    conn.execute("UPDATE ai_models SET is_default = 1 WHERE id = ?", (nxt["id"],))
                conn.execute(
                    "INSERT INTO settings(key, value, updated_at) VALUES ('default_ai_model', ?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                    "updated_at = excluded.updated_at",
                    (new_default, iso(utcnow())),
                )

    def set_default_ai_model(self, model_pk):
        with self.tx() as conn:
            row = conn.execute(
                "SELECT name FROM ai_models WHERE id = ?", (model_pk,)
            ).fetchone()
            if not row:
                return None
            conn.execute("UPDATE ai_models SET is_default = 0")
            conn.execute(
                "UPDATE ai_models SET is_default = 1, status = 1 WHERE id = ?", (model_pk,)
            )
            conn.execute(
                "INSERT INTO settings(key, value, updated_at) VALUES ('default_ai_model', ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                "updated_at = excluded.updated_at",
                (row["name"], iso(utcnow())),
            )
            return row["name"]

    def get_ai_models(self, only_active=True):
        sql = "SELECT * FROM ai_models"
        if only_active:
            sql += " WHERE status = 1"
        return self.query(sql + " ORDER BY is_default DESC, id")

    def get_ai_model(self, model_pk):
        return self.query_one("SELECT * FROM ai_models WHERE id = ?", (model_pk,))

    def get_ai_model_by_name(self, name):
        return self.query_one("SELECT * FROM ai_models WHERE name = ?", (name,))

    def get_default_ai_model(self):
        row = self.query_one("SELECT * FROM ai_models WHERE is_default = 1 AND status = 1")
        if row:
            return row
        return self.query_one("SELECT * FROM ai_models WHERE status = 1 ORDER BY id LIMIT 1")

    # -------------------------------------------------------------- products
    def create_product(self, name, description, price, duration_days, messages_count=0):
        return self.execute(
            "INSERT INTO products (name, description, price, duration_days, "
            "messages_count, status, created_at) VALUES (?, ?, ?, ?, ?, 1, ?)",
            (name, description or "", int(price), int(duration_days),
             int(messages_count), iso(utcnow())),
        )

    def update_product(self, product_id, **fields):
        allowed = {"name", "description", "price", "duration_days", "messages_count", "status"}
        sets, params = [], []
        for key, value in fields.items():
            if key in allowed:
                sets.append("%s = ?" % key)
                params.append(value)
        if not sets:
            return
        params.append(product_id)
        self.execute("UPDATE products SET %s WHERE id = ?" % ", ".join(sets), tuple(params))

    def delete_product(self, product_id):
        self.execute("DELETE FROM products WHERE id = ?", (product_id,))

    def get_products(self, only_active=True):
        sql = "SELECT * FROM products"
        if only_active:
            sql += " WHERE status = 1"
        return self.query(sql + " ORDER BY price, id")

    def get_product(self, product_id):
        return self.query_one("SELECT * FROM products WHERE id = ?", (product_id,))

    # -------------------------------------------------------------- payments
    def create_payment(self, user_id, product_id, amount, method):
        return self.execute(
            "INSERT INTO payments (user_id, product_id, amount, payment_method, "
            "status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)",
            (user_id, product_id, int(amount), method, iso(utcnow())),
        )

    def attach_receipt(self, payment_id, receipt_type, receipt_value):
        self.execute(
            "UPDATE payments SET receipt_type = ?, receipt_value = ? WHERE id = ?",
            (receipt_type, receipt_value, payment_id),
        )

    def get_payment(self, payment_id):
        return self.query_one("SELECT * FROM payments WHERE id = ?", (payment_id,))

    def latest_open_payment(self, user_id):
        return self.query_one(
            "SELECT * FROM payments WHERE user_id = ? AND status = 'pending' "
            "ORDER BY id DESC LIMIT 1",
            (user_id,),
        )

    def list_payments(self, status=None, limit=10, offset=0):
        if status:
            return self.query(
                "SELECT * FROM payments WHERE status = ? ORDER BY id DESC LIMIT ? OFFSET ?",
                (status, limit, offset),
            )
        return self.query(
            "SELECT * FROM payments ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
        )

    def count_payments(self, status=None):
        if status:
            return int(self.scalar(
                "SELECT COUNT(*) FROM payments WHERE status = ?", (status,)))
        return int(self.scalar("SELECT COUNT(*) FROM payments"))

    def total_revenue(self):
        return int(self.scalar(
            "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status = 'confirmed'"))

    # --------------------------------------------------------------- support
    def create_ticket(self, user_id, subject, message):
        now = iso(utcnow())
        with self.tx() as conn:
            cur = conn.execute(
                "INSERT INTO support_tickets (user_id, subject, status, created_at, "
                "updated_at) VALUES (?, ?, 'open', ?, ?)",
                (user_id, subject, now, now),
            )
            ticket_id = cur.lastrowid
            conn.execute(
                "INSERT INTO support_messages (ticket_id, user_id, message, is_admin, "
                "created_at) VALUES (?, ?, ?, 0, ?)",
                (ticket_id, user_id, message, now),
            )
            return ticket_id

    def add_ticket_message(self, ticket_id, user_id, message, is_admin=False):
        now = iso(utcnow())
        with self.tx() as conn:
            conn.execute(
                "INSERT INTO support_messages (ticket_id, user_id, message, is_admin, "
                "created_at) VALUES (?, ?, ?, ?, ?)",
                (ticket_id, user_id, message, 1 if is_admin else 0, now),
            )
            conn.execute(
                "UPDATE support_tickets SET status = ?, updated_at = ? WHERE id = ?",
                ("answered" if is_admin else "open", now, ticket_id),
            )

    def get_ticket(self, ticket_id):
        return self.query_one("SELECT * FROM support_tickets WHERE id = ?", (ticket_id,))

    def get_ticket_messages(self, ticket_id):
        return self.query(
            "SELECT * FROM support_messages WHERE ticket_id = ? ORDER BY id", (ticket_id,)
        )

    def list_tickets(self, user_id=None, open_only=False, limit=10, offset=0):
        clauses, params = [], []
        if user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)
        if open_only:
            clauses.append("status != 'closed'")
        sql = "SELECT * FROM support_tickets"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return self.query(sql, tuple(params))

    def count_tickets(self, open_only=True):
        if open_only:
            return int(self.scalar(
                "SELECT COUNT(*) FROM support_tickets WHERE status != 'closed'"))
        return int(self.scalar("SELECT COUNT(*) FROM support_tickets"))

    def close_ticket(self, ticket_id):
        self.execute(
            "UPDATE support_tickets SET status = 'closed', updated_at = ? WHERE id = ?",
            (iso(utcnow()), ticket_id),
        )

    # ----------------------------------------------------------------- usage
    def log_ai_usage(self, user_id, model_name, ok=True):
        self.execute(
            "INSERT INTO ai_usage (user_id, model_name, ok, created_at) VALUES (?, ?, ?, ?)",
            (user_id, model_name, 1 if ok else 0, iso(utcnow())),
        )

    def count_ai_messages(self):
        return int(self.scalar("SELECT COUNT(*) FROM ai_usage WHERE ok = 1"))

    def count_users_since(self, since_dt):
        return int(self.scalar(
            "SELECT COUNT(*) FROM users WHERE created_at >= ?", (iso(since_dt),)))

    # -------------------------------------------------------------- settings
    def get_setting(self, key, default=None):
        row = self.query_one("SELECT value FROM settings WHERE key = ?", (key,))
        if not row or row.get("value") is None:
            return default
        return row["value"]

    def get_int_setting(self, key, default=0):
        try:
            return int(str(self.get_setting(key, default)).strip())
        except (TypeError, ValueError):
            return default

    def get_bool_setting(self, key, default=False):
        value = self.get_setting(key)
        if value is None:
            return default
        return str(value).strip().lower() in ("1", "true", "yes", "on")

    def set_setting(self, key, value):
        self.execute(
            "INSERT INTO settings(key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
            "updated_at = excluded.updated_at",
            (key, str(value), iso(utcnow())),
        )


# --------------------------------------------------------------------- singleton
_db = None


def get_db():
    """Lazy singleton. Avoids the old import-time side effect that created a
    stray bot.db in whatever directory the process happened to start in."""
    global _db
    if _db is None:
        from bot.config import DB_PATH, DEFAULT_SETTINGS
        _db = Database(DB_PATH)
        _db.seed_settings(DEFAULT_SETTINGS)
    return _db


def reset_db_for_tests(path):
    global _db
    if _db is not None:
        try:
            _db.close()
        except Exception:
            pass
    _db = Database(path)
    from bot.config import DEFAULT_SETTINGS
    _db.seed_settings(DEFAULT_SETTINGS)
    return _db
