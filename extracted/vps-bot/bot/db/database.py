"""
Database layer using SQLAlchemy.
Supports SQLite (memory or file) and PostgreSQL for Railway.

Stores server records per user. Passwords are NEVER stored in plain text.
"""

import datetime
import logging
from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    BigInteger,
    String,
    DateTime,
    Text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import NullPool

from bot.config import DATABASE_URL

logger = logging.getLogger(__name__)

Base = declarative_base()


def _get_engine():
    """Create engine with Railway-friendly defaults."""
    # Disable connection pooling for Railway (which restarts containers)
    pool_class = NullPool if "postgresql" not in DATABASE_URL else None
    
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_class=pool_class,
        connect_args={
            "check_same_thread": False,
            "timeout": 10,
        } if "sqlite" in DATABASE_URL else {},
    )
    return engine


engine = _get_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class ServerRecord(Base):
    """Tracks every VPS provisioned through the bot."""

    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id = Column(BigInteger, nullable=False, index=True)
    provider_server_id = Column(String(256), nullable=False, unique=True, index=True)
    server_name = Column(String(256), default="")
    status = Column(String(64), default="creating", index=True)  # creating | active | deleted | error
    ip_address = Column(String(64), default="")
    region = Column(String(64), default="")
    plan = Column(String(64), default="")
    # Encrypted password (Fernet). Empty string means "not stored".
    encrypted_password = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    deleted_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    """Immutable audit trail for sensitive operations."""

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id = Column(BigInteger, nullable=False, index=True)
    action = Column(String(64), nullable=False, index=True)  # create | reboot | delete
    target_server_id = Column(String(256), default="", index=True)
    detail = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


def init_db() -> None:
    """Create tables if they do not exist."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialised: %s", DATABASE_URL[:50])
    except Exception as e:
        logger.error("Failed to initialise database: %s", e)
        raise


@contextmanager
def get_session():
    """Yield a transactional DB session with proper error handling."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error("Database error: %s", e)
        raise
    finally:
        session.close()
