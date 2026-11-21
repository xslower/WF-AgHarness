import sys
from pathlib import Path

import anyio
import pytest
from mcp.shared.message import SessionMessage
from mcp.types import JSONRPCMessage
from pydantic import TypeAdapter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy" / "docker"))
mcp_bridge = pytest.importorskip("mcp_bridge")


def _msg(method: str, id_: int | None = None) -> SessionMessage:
    body = {"jsonrpc": "2.0", "method": method, "params": {}}
    if id_ is not None:
        body["id"] = id_
    return SessionMessage(TypeAdapter(JSONRPCMessage).validate_python(body))


def _key(m: SessionMessage) -> tuple:
    root = getattr(m.message, "root", m.message)
    return (root.method, getattr(root, "id", None))


async def _run_gate(inbound: list[SessionMessage]) -> list[tuple]:
    in_send, in_recv = anyio.create_memory_object_stream(100)
    out_send, out_recv = anyio.create_memory_object_stream(100)
    async with anyio.create_task_group() as tg:
        tg.start_soon(mcp_bridge._sse_init_gate, in_recv, out_send)
        async with in_send:
            for m in inbound:
                await in_send.send(m)
    return [_key(m) async for m in out_recv]


def test_tool_calls_posted_before_initialize_are_reordered():
    pass
    out = anyio.run(_run_gate, [
        _msg("tools/call", 1),
        _msg("tools/call", 2),
        _msg("tools/call", 3),
        _msg("initialize", 0),
        _msg("notifications/initialized"),
    ])
    assert out == [
        ("initialize", 0),
        ("notifications/initialized", None),
        ("tools/call", 1),
        ("tools/call", 2),
        ("tools/call", 3),
    ]


def test_well_behaved_client_is_passed_through_unchanged():
    seq = [
        _msg("initialize", 0),
        _msg("notifications/initialized"),
        _msg("tools/list", 1),
        _msg("tools/call", 2),
    ]
    out = anyio.run(_run_gate, seq)
    assert out == [_key(m) for m in seq]


def test_missing_handshake_is_flushed_after_timeout():
    pass
    async def body():
        in_send, in_recv = anyio.create_memory_object_stream(100)
        out_send, out_recv = anyio.create_memory_object_stream(100)
        async with anyio.create_task_group() as tg:
            tg.start_soon(mcp_bridge._sse_init_gate, in_recv, out_send, 0.2)
            await in_send.send(_msg("tools/call", 1))
            await in_send.send(_msg("tools/call", 2))
            with anyio.fail_after(2):
                got = [_key(await out_recv.receive()) for _ in range(2)]
            await in_send.aclose()
        return got

    assert anyio.run(body) == [("tools/call", 1), ("tools/call", 2)]


def test_disconnect_while_parked_drops_parked_messages():
    pass
    pass
    out = anyio.run(_run_gate, [_msg("tools/call", 1), _msg("tools/call", 2)])
    assert out == []
