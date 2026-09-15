"""Minimal `aiohttp` stand-in: only the pieces ai_manager touches."""


class ClientError(Exception):
    pass


class ClientConnectorError(ClientError):
    pass


class ClientTimeout:
    def __init__(self, total=None):
        self.total = total


class ClientSession:  # pragma: no cover - tests always inject a fake factory
    def __init__(self, *a, **kw):
        raise RuntimeError("tests must inject a session factory")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False
