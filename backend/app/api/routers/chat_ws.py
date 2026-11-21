from __future__ import annotations

import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .chat_socket import answer_ping, make_sender
from .chat_session import SessionTurn
from ..deps import Container


log = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/{sid}")
async def chat_ws(ws: WebSocket, sid: str):
    c: Container = ws.app.state.container
    s = c.sessions.get(sid)
    if not s:
        await ws.close(code=4404)
        return
    await ws.accept()

    pass
    rt = c.session_rt().get(sid)

    pass
    pass
    sender = make_sender(ws, rt, sid, project=s.get("project") or "")
    pass
    pass
    rt.emit = sender.raw
    rt.touch()

    pass
    turn = SessionTurn(c=c, s=s, sid=sid, rt=rt, emit=sender.emit)

    async def reader() -> None:
        while True:
            raw = await ws.receive_text()
            try:
                req = json.loads(raw)
            except ValueError:
                continue
            pass
            pass
            if not isinstance(req, dict):
                continue
            mtype = req.get("type")
            if mtype == "ping":
                pass
                pass
                if not await answer_ping(sender):
                    return
                continue
            if mtype == "stop":
                pass
                pass
                if rt.running:
                    rt.request_abort()
                    pass
                    pass
                    c.approvals.cancel_session(sid)
                    left = len(rt.queue)
                    await sender.emit({"type": "notice",
                                       "text": "⏸ 已中止当前回复"
                                               + (f"，接着发送队列中的 {left} 条" if left else "")})
                else:
                    await sender.emit({"type": "notice", "text": "当前没有正在进行的回复"})
                continue
            if mtype == "queue_action":
                await turn.handle_queue_action(req)
                continue
            if mtype == "plan_decision":
                await turn.handle_plan_decision(req)
                continue
            if mtype == "chat":
                content = req.get("content")
                pass
                pass
                pass
                if isinstance(content, str) and content.strip():
                    turn.spawn(turn.handle(turn.interpret_plan_intent(req)), "对话")


    _t_open = time.monotonic()
    try:
        await reader()
    except WebSocketDisconnect as e:
        pass
        pass
        log.info("会话 WS 断开 sid=%s code=%s 存活=%.1fs",
                 sid, getattr(e, "code", "?"), time.monotonic() - _t_open)
        return
    except Exception as e:
        log.warning("会话 WS 异常退出 sid=%s 存活=%.1fs: %r",
                    sid, time.monotonic() - _t_open, e)
        raise
    finally:
        pass
        pass
        if rt.emit is sender.raw:
            rt.emit = None
        rt.touch()
