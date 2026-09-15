"""Configuration.

Only TWO values come from the environment: TELEGRAM_BOT_TOKEN and ADMIN_USER_IDS.
Everything else lives in the `settings` table and is edited from the in-Telegram
admin panel.
"""
import os
import sys
import logging
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # dotenv optional at runtime (Railway injects real env vars)
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- environment
TELEGRAM_BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()


def _parse_admin_ids(raw):
    ids = []
    for chunk in (raw or "").replace(";", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            ids.append(int(chunk))
        except ValueError:
            logger.warning("Ignoring invalid ADMIN_USER_IDS entry: %r", chunk)
    return ids


ADMIN_USER_IDS = _parse_admin_ids(os.getenv("ADMIN_USER_IDS", ""))

# ---------------------------------------------------------------------- paths
# On Railway attach a Volume mounted at /data so the SQLite file survives
# redeploys. Falls back to ./data when /data is not writable (local dev).
BASE_DIR = Path(__file__).resolve().parent.parent


def _resolve_data_dir():
    for candidate in (Path(os.getenv("DATA_DIR", "/data")), BASE_DIR / "data"):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return candidate
        except Exception:
            continue
    return BASE_DIR


DATA_DIR = _resolve_data_dir()
DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "bot.db"))

# ------------------------------------------------------------------- defaults
# Seeded into the settings table on first boot, editable from the admin panel.
DEFAULT_SETTINGS = {
    "free_message_limit": "10",
    "free_period_days": "30",
    "rate_limit_messages": "5",
    "rate_limit_seconds": "60",
    "antispam_duplicate_window": "20",
    "ai_timeout_seconds": "45",
    "ai_max_retries": "3",
    "ai_max_history": "8",
    "ai_system_prompt": "You are a helpful, concise assistant.",
    "default_ai_model": "",
    "card_number": "",
    "card_holder": "",
    "gateway_enabled": "0",
    "gateway_url": "",
    "gateway_token": "",
    "support_enabled": "1",
    "shop_enabled": "1",
}

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def validate_environment():
    """Return a list of fatal configuration problems (empty == good to go)."""
    problems = []
    if not TELEGRAM_BOT_TOKEN:
        problems.append(
            "TELEGRAM_BOT_TOKEN is missing. Get one from @BotFather and set it "
            "as an environment variable."
        )
    elif ":" not in TELEGRAM_BOT_TOKEN or not TELEGRAM_BOT_TOKEN.split(":")[0].isdigit():
        problems.append(
            "TELEGRAM_BOT_TOKEN looks malformed. Expected format: 123456789:AA..."
        )
    if not ADMIN_USER_IDS:
        problems.append(
            "ADMIN_USER_IDS is missing or empty. Set it to your numeric Telegram "
            "user ID (from @userinfobot). Comma-separate multiple admins."
        )
    return problems


def die_if_misconfigured():
    problems = validate_environment()
    if problems:
        sys.stderr.write("\n=== CONFIGURATION ERROR ===\n")
        for p in problems:
            sys.stderr.write("  - %s\n" % p)
        sys.stderr.write("===========================\n\n")
        raise SystemExit(1)
