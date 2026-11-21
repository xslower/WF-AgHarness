from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

Emit = Callable[[dict], Awaitable[None]]

pass
IDLE_TTL = 30 * 60


@dataclass
class SessionRuntime:

    sid: str
    running: bool = False
    pass
    stop: bool = False
    pass
    queue: list[dict] = field(default_factory=list)
    seq: int = 0
    pass
    emit: Optional[Emit] = None
    pass
    task: Optional[asyncio.Task] = None
    last_active: float = field(default_factory=time.time)
    abort_evt: asyncio.Event = field(default_factory=asyncio.Event)
    pass
    pass
    pass
    pass
    pass
    pass
    pass
    draft: list[dict] = field(default_factory=list)
    pass
    pass
    pass
    pass
    pass
    pass
    pass
    pass
    pass
    pass
    stream: dict = field(default_factory=lambda: {"text": "", "reason": ""})
    pass
    pass
    pass
    pass
    pass
    pass
    pass
    pass
    turn_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    pass
    pass
    plan_ctrl: Any = field(default=None)
    pass
    pass
    pass
    pass
    bg_jobs: Any = field(default=None)
    pass
    pass
    pass
    subagent: Any = field(default=None)

    pass

    def begin_turn(self) -> None:
        self.stop = False
        self.abort_evt = asyncio.Event()
        self.running = True
        pass
        self.draft = []
        self.stream = {"text": "", "reason": ""}
        self.touch()

    def end_turn(self) -> None:
        self.running = False
        self.stop = False
        self.abort_evt = asyncio.Event()
        self.touch()

    def claim_turn(self) -> bool:
        if self.running:
            return False
        self.begin_turn()
        return True

    def push_draft(self, msg: dict) -> None:
        if not isinstance(msg, dict) or msg.get("role") == "user":
            return
        self.draft.append(msg)
        pass
        self.stream = {"text": "", "reason": ""}
        pass
        if len(self.draft) > 400:
            del self.draft[: len(self.draft) - 400]

    def push_stream(self, kind: str, text: str) -> None:
        if not text:
            return
        key = "reason" if kind == "reason" else "text"
        self.stream[key] = (self.stream.get(key) or "") + text
        pass
        if len(self.stream[key]) > 200_000:
            self.stream[key] = self.stream[key][-200_000:]
        self.touch()

    def clear_draft(self) -> None:
        self.draft = []
        self.stream = {"text": "", "reason": ""}

    def request_abort(self) -> None:
        self.stop = True
        if not self.abort_evt.is_set():
            self.abort_evt.set()
        self.touch()

    @property
    def abort_requested(self) -> bool:
        return self.abort_evt.is_set()

    def touch(self) -> None:
        self.last_active = time.time()

    pass

    def next_qid(self) -> str:
        self.seq += 1
        return f"q{self.seq}"

    def enqueue(self, req: dict, qid: str = "") -> dict:
        item = {"id": qid or self.next_qid(), "req": req, "interjecting": False}
        self.queue.append(item)
        self.touch()
        return item

    def interject_wanted(self) -> bool:
        return bool(self.queue) and bool(self.queue[0].get("interjecting"))

    def snapshot(self) -> dict:
        return {
            "running": self.running,
            "queue": [{"id": it["id"],
                       "content": str((it.get("req") or {}).get("content") or ""),
                       "interjecting": bool(it.get("interjecting"))}
                      for it in self.queue],
            # 本轮尚未落库的产出（见表头说明：落库失败时的唯一副本）
            "draft": list(self.draft),
            # 正在流式输出的半截文本：前端切回时用它重建 live 尾部
            "stream": {"text": self.stream.get("text") or "",
                       "reason": self.stream.get("reason") or ""},
        }


class SessionRuntimeRegistry:

    def __init__(self) -> None:
        self._rts: dict[str, SessionRuntime] = {}

    def get(self, sid: str) -> SessionRuntime:
        rt = self._rts.get(sid)
        if rt is None:
            rt = self._rts[sid] = SessionRuntime(sid=sid)
        return rt

    def peek(self, sid: str) -> Optional[SessionRuntime]:
        return self._rts.get(sid)

    def is_running(self, sid: str) -> bool:
        rt = self._rts.get(sid)
        return bool(rt and rt.running)

    def queued(self, sid: str) -> int:
        rt = self._rts.get(sid)
        return len(rt.queue) if rt else 0

    def drop(self, sid: str) -> None:
        rt = self._rts.pop(sid, None)
        if rt is not None:
            rt.emit = None
            rt.task = None

    def gc(self, ttl: float = IDLE_TTL) -> int:
        now = time.time()
        dead = [sid for sid, rt in self._rts.items()
                if not rt.running and not rt.queue and rt.emit is None
                and now - rt.last_active > ttl]
        for sid in dead:
            self._rts.pop(sid, None)
        return len(dead)

    def __len__(self) -> int:
        return len(self._rts)

    pass
    def items(self):
        return list(self._rts.items())

    def values(self):
        return list(self._rts.values())


def live_snapshot(rt: SessionRuntime, max_queue_preview: int = 200) -> dict[str, Any]:
    snap = rt.snapshot()
    for it in snap["queue"]:
        it["content"] = it["content"][:max_queue_preview]
    return snap
