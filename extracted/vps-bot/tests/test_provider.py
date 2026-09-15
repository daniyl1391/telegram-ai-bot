"""Tests for MockProvider and error handling."""

import asyncio
import pytest
from bot.services.mock_provider import MockProvider


@pytest.fixture
def provider():
    return MockProvider()


@pytest.mark.asyncio
async def test_create_server(provider):
    info = await provider.create_server("test", "us-east", "plan-1", "img-win")
    assert info.server_id.startswith("mock-")
    assert info.status == "active"
    assert info.ip_address != ""


@pytest.mark.asyncio
async def test_reboot_server(provider):
    info = await provider.create_server("test2", "eu", "plan-1", "img-win")
    ok = await provider.reboot_server(info.server_id)
    assert ok is True


@pytest.mark.asyncio
async def test_reboot_nonexistent(provider):
    ok = await provider.reboot_server("nonexistent-id")
    assert ok is False


@pytest.mark.asyncio
async def test_delete_server(provider):
    info = await provider.create_server("test3", "eu", "plan-1", "img-win")
    ok = await provider.delete_server(info.server_id)
    assert ok is True
    status = await provider.get_server_status(info.server_id)
    assert status.status == "deleted"


@pytest.mark.asyncio
async def test_get_password(provider):
    info = await provider.create_server("test4", "eu", "plan-1", "img-win")
    pw = await provider.get_initial_password(info.server_id)
    assert pw != ""
