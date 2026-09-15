"""
Provider factory — returns the configured VPSProvider implementation.
"""

from bot.config import VPS_PROVIDER
from bot.services.provider import VPSProvider


def get_provider() -> VPSProvider:
    if VPS_PROVIDER == "generic":
        from bot.services.generic_provider import GenericRESTProvider
        return GenericRESTProvider()
    # Default to mock
    from bot.services.mock_provider import MockProvider
    return MockProvider()
