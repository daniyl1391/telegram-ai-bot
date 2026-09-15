"""Tests for input sanitisation."""

from bot.handlers.status import _sanitize_server_id


def test_valid_id():
    assert _sanitize_server_id("srv-abc123") == "srv-abc123"


def test_invalid_id_with_dots():
    assert _sanitize_server_id("../../etc/passwd") is None


def test_invalid_id_with_spaces():
    assert _sanitize_server_id("hello world") is None


def test_empty():
    assert _sanitize_server_id("") is None


def test_too_long():
    assert _sanitize_server_id("a" * 200) is None
