"""Tests for configuration validation."""

import os
import importlib


def test_admin_user_ids_parsing(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("ADMIN_USER_IDS", "111,222, 333")
    # Re-import to pick up new env
    import bot.config as cfg
    importlib.reload(cfg)
    assert 111 in cfg.ADMIN_USER_IDS
    assert 222 in cfg.ADMIN_USER_IDS
    assert 333 in cfg.ADMIN_USER_IDS


def test_admin_empty_string(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("ADMIN_USER_IDS", "")
    import bot.config as cfg
    importlib.reload(cfg)
    assert cfg.ADMIN_USER_IDS == []


def test_defaults(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    import bot.config as cfg
    importlib.reload(cfg)
    assert cfg.VPS_PROVIDER == "mock"
    assert cfg.PORT == 8443
