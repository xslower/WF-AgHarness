from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from ...event.bus import HUB, envelope
from ...event.fanout import Sink, fanout
from ...event.protocol import BusEvent
from ..deps import Container, get_container

logger = logging.getLogger("harness.events")

router = APIRouter()

pass
HEARTBEAT_SEC = 25.0


def _dumps(ev: dict) -> str:
    try:
        return BusEvent(**ev).model_dump_json()
    except Exception:
        return json.dumps(ev, ensure_ascii=False, default=str)


def _control(topic: str) -> str:
    return _dumps(envelope(0, topic))


async def _pump(ws: WebSocket, sink: Sink) -> None:
    while True:
        try:
            ev = await asyncio.wait_for(sink.q.get(), timeout=HEARTBEAT_SEC)
        except asyncio.TimeoutError:
            await ws.send_text(_control("sys.ping"))
            continue
        await ws.send_text(_dumps(ev))


async def _watch_close(ws: WebSocket) -> None:
    while True:
        await ws.receive_text()


@router.websocket("/ws/events")
async def ws_events(ws: WebSocket) -> None:
    await ws.accept()
    fanout.attach()
    sink = fanout.register()
    tasks = [asyncio.create_task(_pump(ws, sink)),
             asyncio.create_task(_watch_close(ws))]
    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
        for t in done:
            pass
            pass
            pass
            if t.cancelled():
                continue
            exc = t.exception()
            if exc and not isinstance(exc, (WebSocketDisconnect, asyncio.CancelledError)):
                logger.debug("ws/events closed: %s", exc)
    except Exception:
        logger.debug("ws/events closed unexpectedly", exc_info=True)
    finally:
        fanout.unregister(sink)
        for t in tasks:
            t.cancel()
        try:
            await ws.close()
        except Exception:
            logger.debug("ws.close 异常", exc_info=True)


@router.get("/api/events/topics")
def event_topics(c: Container = Depends(get_container)):
    hub = getattr(c, "hub", None) or HUB
    return {"topics": hub.topics(), "stats": hub.stats(),
            "connections": fanout.count(), "dropped": fanout.dropped()}
