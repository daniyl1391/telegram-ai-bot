"""
MockProvider — returns fake data so you can test the full bot flow
without a real VPS API. Perfect for development and CI.
"""

import asyncio
import uuid
import logging
from bot.services.provider import VPSProvider, ServerInfo

logger = logging.getLogger(__name__)

_fake_servers: dict[str, ServerInfo] = {}


class MockProvider(VPSProvider):

    async def create_server(
        self, name: str, region: str, plan_id: str, image_id: str
    ) -> ServerInfo:
        sid = f"mock-{uuid.uuid4().hex[:8]}"
        info = ServerInfo(
            server_id=sid,
            name=name,
            status="creating",
            region=region,
            plan=plan_id,
            os_label="Windows Server 2022 (Mock)",
            username="Administrator",
            password=f"Mock-{uuid.uuid4().hex[:12]}",
        )
        _fake_servers[sid] = info
        logger.info("MockProvider: created server %s", sid)
        # Simulate provisioning delay
        await asyncio.sleep(2)
        info.status = "active"
        info.ip_address = "203.0.113.42"
        return info

    async def get_server_status(self, server_id: str) -> ServerInfo:
        info = _fake_servers.get(server_id)
        if not info:
            return ServerInfo(server_id=server_id, name="", status="not_found")
        return info

    async def get_server_ip(self, server_id: str) -> str:
        info = _fake_servers.get(server_id)
        return info.ip_address if info else ""

    async def get_initial_password(self, server_id: str) -> str:
        info = _fake_servers.get(server_id)
        return info.password if info else ""

    async def reboot_server(self, server_id: str) -> bool:
        if server_id in _fake_servers:
            logger.info("MockProvider: rebooted %s", server_id)
            return True
        return False

    async def delete_server(self, server_id: str) -> bool:
        if server_id in _fake_servers:
            _fake_servers[server_id].status = "deleted"
            logger.info("MockProvider: deleted %s", server_id)
            return True
        return False
