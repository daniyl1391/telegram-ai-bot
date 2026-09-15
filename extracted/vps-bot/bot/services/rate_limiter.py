"""
Simple in-memory rate limiter.
For multi-instance deployments, swap this for a Redis-backed implementation.
"""

import time
import logging
from collections import defaultdict

from bot.config import CREATE_RATE_LIMIT_SECONDS

logger = logging.getLogger(__name__)

_last_create: dict[int, float] = defaultdict(float)


def check_rate_limit(user_id: int) -> tuple[bool, int]:
    """
    Returns (allowed, seconds_remaining).
    If allowed is False, the user must wait *seconds_remaining* more seconds.
    """
    now = time.time()
    elapsed = now - _last_create[user_id]
    if elapsed < CREATE_RATE_LIMIT_SECONDS:
        remaining = int(CREATE_RATE_LIMIT_SECONDS - elapsed)
        return False, remaining
    return True, 0


def record_create(user_id: int) -> None:
    _last_create[user_id] = time.time()
