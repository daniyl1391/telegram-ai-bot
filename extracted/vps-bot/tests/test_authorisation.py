"""Tests for user access control."""

import importlib
import bot.config as cfg


def _reload_with_admins(monkeypatch, admin_ids: str):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("ADMIN_USER_IDS", admin_ids)
    importlib.reload(cfg)


def test_authorised_user(monkeypatch):
    _reload_with_admins(monkeypatch, "100,200")
    assert 100 in cfg.ADMIN_USER_IDS


def test_unauthorised_user(monkeypatch):
    _reload_with_admins(monkeypatch, "100,200")
    assert 999 not in cfg.ADMIN_USER_IDS
