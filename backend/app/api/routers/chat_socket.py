from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Awaitable, Callable

from fastapi import WebSocket

logger = logging.getLogger("harness.chat_socket")

from ...chat.session_runtime import SessionRuntime
from ...chat.event_journal import journal

Emit = Callable[[dict], Awaitable[None]]


@dataclass
class Sender:
    raw: Emit
    emit: Emit


def make_sender(ws: WebSocket, rt: SessionRuntime, sid: str,
                project: str = "") -> Sender:
    gone = {"v": False}

    async def raw(ev: dict) -> None:
        if gone["v"]:
            raise ConnectionError("连接已断开")
        await ws.send_text(json.dumps(ev, ensure_ascii=False))

    def _detach() -> None:
        gone["v"] = True
        if rt.emit is raw:
            rt.emit = None
        rt.touch()

    async def emit(ev: dict) -> None:
        pass
        if ev.get("type") != "pong":
            journal(sid, project, ev)
        pass
        pass
        try:
            t = ev.get("type")
            if t == "text":
                rt.push_stream("text", str(ev.get("text") or ""))
            elif t == "reason":
                rt.push_stream("reason",
                               str(ev.get("reason") or ev.get("text") or ""))
        except Exception:
            logger.debug("push_stream 失败: %s", t, exc_info=True)
        if gone["v"] or rt.emit is None:
            return
        try:
            await rt.emit(ev)
        except Exception:
            _detach()

    return Sender(raw=raw, emit=emit)


def make_headless(rt: SessionRuntime, sid: str, project: str = "") -> Sender:

    async def raw(_ev: dict) -> None:
        raise ConnectionError("定时任务会话没有连接")

    async def emit(ev: dict) -> None:
        if ev.get("type") != "pong":
            journal(sid, project, ev)
        t = ev.get("type")
        try:
            if t == "text":
                rt.push_stream("text", str(ev.get("text") or ""))
            elif t == "reason":
                rt.push_stream("reason",
                               str(ev.get("reason") or ev.get("text") or ""))
        except Exception:
            logger.debug("push_stream 失败: %s", t, exc_info=True)
        if rt.emit is None:
            return
        try:
            await rt.emit(ev)
        except Exception:
            logger.debug("headless emit 发送失败: %s", sid, exc_info=True)

    return Sender(raw=raw, emit=emit)


async def answer_ping(sender: Sender) -> bool:
    try:
        await sender.raw({"type": "pong", "ts": time.time()})
        return True
    except Exception:
        return False
