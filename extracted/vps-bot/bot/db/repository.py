"""
Repository helpers — thin wrappers around DB queries.
"""

import datetime
import logging
from typing import Optional

from bot.db.database import get_session, ServerRecord, AuditLog

logger = logging.getLogger(__name__)


# ── Server CRUD ──────────────────────────────────────────

def create_server_record(
    user_id: int,
    provider_server_id: str,
    server_name: str = "",
    region: str = "",
    plan: str = "",
) -> ServerRecord:
    with get_session() as s:
        rec = ServerRecord(
            telegram_user_id=user_id,
            provider_server_id=provider_server_id,
            server_name=server_name,
            region=region,
            plan=plan,
            status="creating",
        )
        s.add(rec)
        s.flush()
        s.refresh(rec)
        # Detach from session so caller can use outside context
        s.expunge(rec)
        return rec


def update_server_status(
    provider_server_id: str,
    status: str,
    ip_address: str = "",
    encrypted_password: str = "",
) -> None:
    with get_session() as s:
        rec = (
            s.query(ServerRecord)
            .filter_by(provider_server_id=provider_server_id)
            .first()
        )
        if rec:
            rec.status = status
            if ip_address:
                rec.ip_address = ip_address
            if encrypted_password:
                rec.encrypted_password = encrypted_password


def mark_server_deleted(provider_server_id: str) -> None:
    with get_session() as s:
        rec = (
            s.query(ServerRecord)
            .filter_by(provider_server_id=provider_server_id)
            .first()
        )
        if rec:
            rec.status = "deleted"
            rec.deleted_at = datetime.datetime.utcnow()


def get_user_servers(user_id: int) -> list[ServerRecord]:
    with get_session() as s:
        recs = (
            s.query(ServerRecord)
            .filter_by(telegram_user_id=user_id)
            .filter(ServerRecord.status != "deleted")
            .order_by(ServerRecord.created_at.desc())
            .all()
        )
        s.expunge_all()
        return recs


def get_server_by_provider_id(
    provider_server_id: str, user_id: int
) -> Optional[ServerRecord]:
    with get_session() as s:
        rec = (
            s.query(ServerRecord)
            .filter_by(provider_server_id=provider_server_id, telegram_user_id=user_id)
            .first()
        )
        if rec:
            s.expunge(rec)
        return rec


def count_active_servers(user_id: int) -> int:
    with get_session() as s:
        return (
            s.query(ServerRecord)
            .filter_by(telegram_user_id=user_id)
            .filter(ServerRecord.status.in_(["creating", "active"]))
            .count()
        )


# ── Audit ────────────────────────────────────────────────

def log_audit(user_id: int, action: str, target_server_id: str = "", detail: str = "") -> None:
    with get_session() as s:
        s.add(
            AuditLog(
                telegram_user_id=user_id,
                action=action,
                target_server_id=target_server_id,
                detail=detail,
            )
        )
