"""Tests for encryption module."""

import os
import importlib


def test_encrypt_decrypt(monkeypatch):
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    monkeypatch.setenv("ENCRYPTION_KEY", key)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake")
    import bot.config
    importlib.reload(bot.config)
    import bot.services.encryption as enc
    importlib.reload(enc)

    cipher = enc.encrypt("SuperSecret123!")
    assert cipher != ""
    assert cipher != "SuperSecret123!"
    plain = enc.decrypt(cipher)
    assert plain == "SuperSecret123!"


def test_no_key_returns_empty(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY", "")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake")
    import bot.config
    importlib.reload(bot.config)
    import bot.services.encryption as enc
    importlib.reload(enc)

    assert enc.encrypt("hello") == ""
