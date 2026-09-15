"""
GenericRESTProvider — talks to a REST-based VPS API.

Adapt the endpoint paths, request bodies, and response parsing
to match your actual provider's API documentation.

See README.md § "Adapting the Generic Provider" for details.
"""

import logging
from typing import Any

try:
    import httpx
except ImportError:
    httpx = None

from bot.config import VPS_API_BASE_URL, VPS_API_TOKEN
from bot.services.provider import VPSProvider, ServerInfo

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0


class GenericRESTProvider(VPSProvider):

    def __init__(self) -> None:
        if not httpx:
            raise ImportError("httpx is required for GenericRESTProvider. Install with: pip install httpx")
        
        self._base = VPS_API_BASE_URL.rstrip("/") if VPS_API_BASE_URL else ""
        self._token = VPS_API_TOKEN
        
        if not self._base or not self._token:
            logger.warning("GenericRESTProvider configured but VPS_API_BASE_URL or VPS_API_TOKEN is missing")
        
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ── helpers ───────────────────────────────────────────

    async def _request(
        self, method: str, path: str, json: dict | None = None
    ) -> dict[str, Any]:
        """Execute an HTTP request with error handling."""
        if not self._base:
            raise RuntimeError("VPS_API_BASE_URL is not configured")
        
        url = f"{self._base}{path}"
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.request(
                    method, url, headers=self._headers, json=json
                )
                resp.raise_for_status()
                data = resp.json()
                if not isinstance(data, dict):
                    raise ValueError(f"Expected dict response, got {type(data).__name__}")
                return data
        except httpx.TimeoutException:
            logger.error("Request timeout for %s %s", method, path)
            raise TimeoutError(f"API request timed out: {method} {path}")
        except httpx.ConnectError as e:
            logger.error("Connection error: %s", e)
            raise ConnectionError(f"Could not connect to VPS API: {e}")
        except httpx.HTTPStatusError as e:
            logger.error("HTTP %d: %s", e.response.status_code, e.response.text[:200])
            raise ValueError(f"API returned {e.response.status_code}")
        except Exception as e:
            logger.error("Request failed: %s", type(e).__name__)
            raise

    @staticmethod
    def _parse_server(data: dict) -> ServerInfo:
        """
        ╔══════════════════════════════════════════════════╗
        ║  ADAPT THIS to your provider's response shape.  ║
        ╚══════════════════════════════════════════════════╝
        
        Example for Vultr API:
        {
          "server": {
            "id": "abc123",
            "label": "my-server",
            "status": "active",
            "main_ip": "203.0.113.1",
            "os": "Windows Server 2022",
            ...
          }
        }
        """
        return ServerInfo(
            server_id=str(data.get("id", data.get("server_id", ""))),
            name=data.get("name", data.get("label", "")),
            status=data.get("status", "unknown"),
            ip_address=data.get("main_ip", data.get("ip_address", data.get("ip", ""))),
            username=data.get("default_username", data.get("username", "Administrator")),
            password=data.get("default_password", data.get("password", "")),
            region=data.get("region", data.get("region_id", "")),
            plan=data.get("plan", data.get("plan_id", "")),
            os_label=data.get("os", data.get("os_label", "Windows Server")),
        )

    # ── interface ─────────────────────────────────────────

    async def create_server(
        self, name: str, region: str, plan_id: str, image_id: str
    ) -> ServerInfo:
        """
        POST /servers  (adapt path & body to your provider)
        
        Example for Vultr:
        POST /servers
        {
          "label": "my-server",
          "region": "ewr",
          "plan": "vc2-2c-4gb",
          "os_id": 477  # Windows Server 2022
        }
        """
        body = {
            "label": name,
            "region": region,
            "plan": plan_id,
            "os_id": image_id,
        }
        data = await self._request("POST", "/servers", json=body)
        server_data = data.get("server", data)
        return self._parse_server(server_data)

    async def get_server_status(self, server_id: str) -> ServerInfo:
        """GET /servers/{id}"""
        try:
            data = await self._request("GET", f"/servers/{server_id}")
            server_data = data.get("server", data)
            return self._parse_server(server_data)
        except Exception as e:
            logger.error("Failed to get server status: %s", e)
            return ServerInfo(server_id=server_id, name="", status="error")

    async def get_server_ip(self, server_id: str) -> str:
        """Return the public IPv4 address."""
        try:
            info = await self.get_server_status(server_id)
            return info.ip_address
        except Exception:
            return ""

    async def get_initial_password(self, server_id: str) -> str:
        """
        Return the initial password. Some providers return it in the create response.
        Others require a separate password-reset call.
        
        For Vultr, you'd typically call:
        POST /servers/{id}/create-image or similar
        """
        try:
            info = await self.get_server_status(server_id)
            if info.password:
                return info.password
            
            # Attempt password reset endpoint (provider-specific)
            data = await self._request("POST", f"/servers/{server_id}/reset-password")
            return data.get("password", data.get("new_password", ""))
        except Exception as exc:
            logger.warning("Password retrieval failed for %s: %s", server_id, exc)
            return ""

    async def reboot_server(self, server_id: str) -> bool:
        """POST /servers/{id}/reboot"""
        try:
            await self._request("POST", f"/servers/{server_id}/reboot")
            logger.info("Rebooted server %s", server_id)
            return True
        except Exception as exc:
            logger.error("Reboot failed for %s: %s", server_id, exc)
            return False

    async def delete_server(self, server_id: str) -> bool:
        """DELETE /servers/{id}"""
        try:
            await self._request("DELETE", f"/servers/{server_id}")
            logger.info("Deleted server %s", server_id)
            return True
        except Exception as exc:
            logger.error("Delete failed for %s: %s", server_id, exc)
            return False
