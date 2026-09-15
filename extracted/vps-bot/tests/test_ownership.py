"""Tests for server ownership isolation."""

from bot.db.database import init_db, engine, Base
from bot.db.repository import (
    create_server_record,
    get_server_by_provider_id,
    get_user_servers,
)


def setup_module():
    Base.metadata.drop_all(bind=engine)
    init_db()


def test_user_cannot_access_other_users_server():
    create_server_record(user_id=1001, provider_server_id="srv-aaa")
    # User 1002 must NOT see user 1001's server
    rec = get_server_by_provider_id("srv-aaa", user_id=1002)
    assert rec is None


def test_user_can_access_own_server():
    create_server_record(user_id=2001, provider_server_id="srv-bbb")
    rec = get_server_by_provider_id("srv-bbb", user_id=2001)
    assert rec is not None
    assert rec.provider_server_id == "srv-bbb"


def test_get_user_servers_isolated():
    create_server_record(user_id=3001, provider_server_id="srv-ccc")
    create_server_record(user_id=3002, provider_server_id="srv-ddd")
    servers = get_user_servers(3001)
    ids = [s.provider_server_id for s in servers]
    assert "srv-ccc" in ids
    assert "srv-ddd" not in ids
