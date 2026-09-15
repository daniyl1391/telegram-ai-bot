"""
Configuration module — reads all settings from environment variables.
No secrets are ever hard-coded.
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)


def _require(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        logger.critical("Missing required environment variable: %s", name)
        sys.exit(1)
    return val


def _optional(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


# ── Telegram ─────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")

# Parse admin IDs safely
ADMIN_USER_IDS_STR = _optional("ADMIN_USER_IDS", "")
ADMIN_USER_IDS: list[int] = []
if ADMIN_USER_IDS_STR:
    for uid in ADMIN_USER_IDS_STR.split(","):
        uid = uid.strip()
        if uid.isdigit():
            ADMIN_USER_IDS.append(int(uid))

# Railway sets PORT automatically; fallback to 8443
PORT: int = int(os.getenv("PORT", "8443"))

# Webhook URL — if set, use webhook; else polling
WEBHOOK_URL: str | None = _optional("WEBHOOK_URL") or None

# ── VPS Provider ─────────────────────────────────────────
VPS_API_BASE_URL: str = _optional("VPS_API_BASE_URL", "")
VPS_API_TOKEN: str = _optional("VPS_API_TOKEN", "")
VPS_PLAN_ID: str = _optional("VPS_PLAN_ID", "")
VPS_REGION: str = _optional("VPS_REGION", "")
VPS_IMAGE_ID: str = _optional("VPS_IMAGE_ID", "")
VPS_PROVIDER: str = _optional("VPS_PROVIDER", "mock")  # mock | generic

# ── Database ─────────────────────────────────────────────
# For Railway: use in-memory SQLite or PostgreSQL if DATABASE_URL is set
DATABASE_URL: str = _optional("DATABASE_URL", "sqlite:///:memory:")

# ── Rate Limits ──────────────────────────────────────────
CREATE_RATE_LIMIT_SECONDS: int = int(_optional("CREATE_RATE_LIMIT_SECONDS", "300"))
MAX_SERVERS_PER_USER: int = int(_optional("MAX_SERVERS_PER_USER", "3"))

# ── Encryption key for password storage
ENCRYPTION_KEY: str = _optional("ENCRYPTION_KEY", "")

logger.info("Config loaded: provider=%s, db=%s, webhook=%s", VPS_PROVIDER, DATABASE_URL, WEBHOOK_URL)
