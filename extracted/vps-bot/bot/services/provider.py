"""
Abstract VPS Provider interface.
Every concrete provider must implement these methods.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ServerInfo:
    """Standardised server representation across providers."""
    server_id: str
    name: str
    status: str          # creating | active | stopped | deleted | error
    ip_address: str = ""
    username: str = "Administrator"
    password: str = ""   # Only populated right after creation or password reset
    region: str = ""
    plan: str = ""
    os_label: str = "Windows Server"


class VPSProvider(ABC):
    """Public interface that every VPS provider must satisfy."""

    @abstractmethod
    async def create_server(
        self,
        name: str,
        region: str,
        plan_id: str,
        image_id: str,
    ) -> ServerInfo:
        """Provision a new Windows VPS. Returns initial ServerInfo."""
        ...

    @abstractmethod
    async def get_server_status(self, server_id: str) -> ServerInfo:
        """Return current status and metadata for *server_id*."""
        ...

    @abstractmethod
    async def get_server_ip(self, server_id: str) -> str:
        """Return the public IPv4 address (empty string if not yet assigned)."""
        ...

    @abstractmethod
    async def get_initial_password(self, server_id: str) -> str:
        """
        Return the initial / root password.
        If the provider does not expose it, trigger a reset and return the new one.
        """
        ...

    @abstractmethod
    async def reboot_server(self, server_id: str) -> bool:
        """Reboot the server. Returns True on success."""
        ...

    @abstractmethod
    async def delete_server(self, server_id: str) -> bool:
        """Destroy / terminate the server. Returns True on success."""
        ...
