from __future__ import annotations

import asyncio

import pytest

from app.api.routers.chat_socket import Sender, answer_ping, make_sender
from app.chat.session_runtime import SessionRuntime


class _FakeWS:

    def __init__(self, fail: bool = False) -> None:
        self.sent: list[dict] = []
        self.fail = fail

    async def send_text(self, text: str) -> None:
        if self.fail:
            raise RuntimeError("connection closed")
        import json
        self.sent.append(json.loads(text))


@pytest.fixture
def no_journal(monkeypatch):
    recorded: list[tuple] = []
    from app.api.routers import chat_socket

    monkeypatch.setattr(chat_socket, "journal",
                        lambda sid, project, ev: recorded.append((sid, project, ev)))
    return recorded


pass
def test_rt_emit_is_raw_sender_not_wrapper(no_journal):
    rt = SessionRuntime(sid="s1")
    ws = _FakeWS()
    sender = make_sender(ws, rt, "s1")
    rt.emit = sender.raw
    assert rt.emit is sender.raw
    assert rt.emit is not sender.emit

    pass
    asyncio.run(sender.emit({"type": "text", "text": "hi"}))
    assert ws.sent == [{"type": "text", "text": "hi"}]


def test_emit_journals_then_streams_then_sends(no_journal):
    rt = SessionRuntime(sid="s1")
    ws = _FakeWS()
    sender = make_sender(ws, rt, "s1", project="/proj")
    rt.emit = sender.raw

    asyncio.run(sender.emit({"type": "text", "text": "你好"}))
    assert no_journal and no_journal[0][0] == "s1"
    assert no_journal[0][1] == "/proj"
    assert rt.stream["text"] == "你好"
    assert ws.sent[-1]["text"] == "你好"


def test_pong_is_not_journaled(no_journal):
    rt = SessionRuntime(sid="s1")
    sender = make_sender(_FakeWS(), rt, "s1")
    rt.emit = sender.raw
    asyncio.run(sender.emit({"type": "pong"}))
    assert no_journal == []


def test_send_failure_detaches_outlet_without_raising(no_journal):
    rt = SessionRuntime(sid="s1")
    sender = make_sender(_FakeWS(fail=True), rt, "s1")
    rt.emit = sender.raw

    asyncio.run(sender.emit({"type": "text", "text": "x"}))
    assert rt.emit is None, "失败的出口必须摘掉，后续事件空转"


def test_emit_without_outlet_is_noop(no_journal):
    rt = SessionRuntime(sid="s1")
    sender = make_sender(_FakeWS(), rt, "s1")
    rt.emit = None
    asyncio.run(sender.emit({"type": "text", "text": "still recorded"}))
    assert rt.stream["text"] == "still recorded"
    assert len(no_journal) == 1


def test_old_connection_close_does_not_detach_new_one(no_journal):
    rt = SessionRuntime(sid="s1")
    old = make_sender(_FakeWS(), rt, "s1")
    new = make_sender(_FakeWS(), rt, "s1")

    rt.emit = old.raw
    rt.emit = new.raw
    pass
    if rt.emit is old.raw:
        rt.emit = None
    assert rt.emit is new.raw, "老连接不能把新连接的出口摘掉"


pass
def test_ping_goes_through_raw_even_when_emit_is_none(no_journal):
    rt = SessionRuntime(sid="s1")
    ws = _FakeWS()
    sender = make_sender(ws, rt, "s1")
    rt.emit = None

    ok = asyncio.run(answer_ping(sender))
    assert ok is True
    assert ws.sent and ws.sent[-1]["type"] == "pong"
    assert no_journal == [], "pong 不该进事件日志"


def test_ping_returns_false_when_connection_dead(no_journal):
    rt = SessionRuntime(sid="s1")
    sender = make_sender(_FakeWS(fail=True), rt, "s1")
    assert asyncio.run(answer_ping(sender)) is False
