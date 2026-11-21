from __future__ import annotations

import asyncio

import pytest


class _ToolResult:
    def __init__(self, text: str = "ok") -> None:
        class _Block:
            type = "text"
            text = ""
        b = _Block()
        b.text = text
        self.content = [b]
        self.isError = False


class _Session:

    def __init__(self) -> None:
        self.calls = 0

    async def call_tool(self, short: str, args: dict) -> _ToolResult:
        self.calls += 1
        return _ToolResult(f"{short}:{args.get('x')}")


def _conn(tool_count: int = 3):
    from app.mcp.manager import _Conn
    c = _Conn.__new__(_Conn)
    c.name = "srv"
    c.tools = {f"mcp__srv__t{i}": {} for i in range(tool_count)}
    c.call_count = 0
    c.last_call_time = 0.0
    return c


@pytest.mark.parametrize("times", [15, 40, 200])
def test_repeated_calls_never_get_rejected(times):
    from app.mcp.manager import MCPManager

    async def go():
        mgr = MCPManager.__new__(MCPManager)
        conn, sess = _conn(), _Session()
        got = []
        for i in range(times):
            fut = asyncio.get_running_loop().create_future()
            await mgr._do_call(conn, sess, {"name": "mcp__srv__t0",
                                            "args": {"x": i}}, fut)
            got.append(fut.result())
        return got

    out = asyncio.run(go())
    assert len(out) == times
    assert out == [f"t0:{i}" for i in range(times)]


def test_call_count_still_tracked_for_status():
    from app.mcp.manager import MCPManager

    async def go():
        mgr = MCPManager.__new__(MCPManager)
        conn, sess = _conn(), _Session()
        for i in range(5):
            fut = asyncio.get_running_loop().create_future()
            await mgr._do_call(conn, sess, {"name": "mcp__srv__t0",
                                            "args": {"x": i}}, fut)
        return conn.call_count

    assert asyncio.run(go()) == 5


def test_failure_still_propagates():
    from app.mcp.manager import MCPManager

    class _Boom(_Session):
        async def call_tool(self, short, args):
            raise RuntimeError("sdk 挂了")

    async def go():
        mgr = MCPManager.__new__(MCPManager)
        fut = asyncio.get_running_loop().create_future()
        await mgr._do_call(_conn(), _Boom(), {"name": "mcp__srv__t0",
                                              "args": {}}, fut)
        return fut.exception()

    assert isinstance(asyncio.run(go()), RuntimeError)
