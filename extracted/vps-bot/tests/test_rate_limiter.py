"""Tests for rate limiting."""

from bot.services.rate_limiter import check_rate_limit, record_create


def test_first_request_allowed():
    allowed, remaining = check_rate_limit(user_id=99999)
    assert allowed is True
    assert remaining == 0


def test_second_request_blocked():
    uid = 88888
    record_create(uid)
    allowed, remaining = check_rate_limit(uid)
    assert allowed is False
    assert remaining > 0
