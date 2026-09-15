"""
Encrypt / decrypt sensitive strings (VPS passwords) using Fernet.
If ENCRYPTION_KEY is not set, passwords are NOT stored at all.
"""

import logging
from cryptography.fernet import Fernet, InvalidToken

from bot.config import ENCRYPTION_KEY

logger = logging.getLogger(__name__)

_fernet = Fernet(ENCRYPTION_KEY.encode()) if ENCRYPTION_KEY else None


def encrypt(plaintext: str) -> str:
    """Return base64-encoded ciphertext, or empty string if encryption is unavailable."""
    if not _fernet or not plaintext:
        return ""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Return plaintext, or empty string on failure / missing key."""
    if not _fernet or not ciphertext:
        return ""
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logger.warning("Failed to decrypt value — invalid token or wrong key")
        return ""
