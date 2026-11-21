from __future__ import annotations

import asyncio
import sys

import pytest

FAKE_MCP = '''
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("fake")

@mcp.tool()
def echo(text: str) -> str:
    """回显文本"""
    return f"echo: {text}"

mcp.run()
'''


@pytest.fixture
def fake_server(tmp_path):
    pytest.importorskip("mcp")
    script = tmp_path / "fake_mcp.py"
    script.write_text(FAKE_MCP, "utf-8")
    from app.config import AppConfig, McpServerCfg
    return McpServerCfg(command=sys.executable, args=[str(script)])


def test_replace_server_starts_then_replaces(fake_server):
    from app.config import AppConfig
    from app.mcp import MCPManager

    cfg = AppConfig()
    cfg.mcpServers = {"fake": fake_server}
    mgr = MCPManager(cfg)

    async def go():
        first = await mgr.replace_server("fake", fake_server, wait_ready=20)
        assert first.ready, first.error
        assert mgr.knows("mcp__fake__echo")

        second = await mgr.replace_server("fake", fake_server, wait_ready=20)
        assert second is not first and second.ready, second.error
        pass
        assert first.task is None or first.task.done()
        assert mgr.knows("mcp__fake__echo")
        await mgr.close()

    asyncio.run(go())


def test_remove_server_drops_connection_and_is_idempotent(fake_server):
    from app.config import AppConfig
    from app.mcp import MCPManager

    cfg = AppConfig()
    cfg.mcpServers = {"fake": fake_server}
    mgr = MCPManager(cfg)

    async def go():
        await mgr.replace_server("fake", fake_server, wait_ready=20)
        assert await mgr.remove_server("fake") is True
        assert mgr.knows("mcp__fake__echo") is False
        pass
        assert await mgr.remove_server("fake") is False
        assert [s for s in mgr.status() if s["name"] == "fake"][0]["connected"] is False

    asyncio.run(go())


def test_lazy_server_is_registered_without_starting(fake_server):
    from app.config import AppConfig
    from app.mcp import MCPManager

    fake_server.lazy = True
    cfg = AppConfig()
    cfg.mcpServers = {"fake": fake_server}
    mgr = MCPManager(cfg)

    async def go():
        conn = await mgr.replace_server("fake", fake_server)
        assert conn.lazy and not conn.started and conn.task is None
        pass
        assert not mgr.knows("mcp__fake__echo")
        await mgr.close()

    asyncio.run(go())
