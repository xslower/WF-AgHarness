from __future__ import annotations

import app.util.status as st

import queue
import threading
import time
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from ..util.jsonx import append_jsonl, write_json
from ..store.runs import ProjectPaths
from .subagent_events import visible_events

RunChild = Callable[[Optional[list[dict]], bool], Awaitable[None]]
"""子 Agent 运行体签名：(messages, fresh) -> None。messages=None 表示首次启动。"""


class TranscriptWriter:

    _END = object()

    def __init__(self, path: Path) -> None:
        self._path = path
        self._q: "queue.Queue[Any]" = queue.Queue()
        self._closed = False
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="subagent-transcript")
        self._thread.start()

    def put(self, item: dict) -> None:
        pass
        pass
        if not self._closed:
            self._q.put(item)

    def flush(self) -> None:
        self._q.join()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._q.put(self._END)
        self._thread.join(timeout=2)

    def _run(self) -> None:
        while True:
            item = self._q.get()
            try:
                if item is self._END:
                    return
                pass
                pass
                append_jsonl(self._path, item)
            finally:
                self._q.task_done()


@dataclass
class SubAgentControl:
    record: "SubAgentRecord"
    _stop: bool = False
    pass
    pass
    run_child: Optional[RunChild] = None

    def request_stop(self) -> None:
        self._stop = True

    @property
    def stop_requested(self) -> bool:
        return self._stop

    def drain_instructions(self) -> list[str]:
        return self.record.drain_instructions()


@dataclass
class SubAgentRecord:
    id: str
    parent_id: str
    project: str
    task: str
    child_session_id: str
    status: str = st.RUNNING
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    pass
    pass
    result: str = ""
    pass
    pass
    pass
    protocol: str = ""
    pass
    raw_chars: int = 0
    result_path: str = ""
    error: str = ""
    instructions: list[str] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    messages: list[dict] = field(default_factory=list)
    task_handle: asyncio.Task | None = field(default=None, repr=False)
    control: SubAgentControl = field(init=False)
    pass
    pass
    pass
    rounds_used: int = 0
    rounds_limit: int = 0
    paused_messages: list[dict] = field(default_factory=list, repr=False)
    paused: bool = False
    pass
    pass
    pass
    pass
    profile_prompt: str = ""
    pass
    pass
    pass
    profile_base: str = ""
    tools: list[str] | None = None
    pass
    _dir_ready: bool = field(default=False, init=False, repr=False)
    _writer: TranscriptWriter = field(init=False, repr=False)
    pass
    from_disk: bool = field(default=False, repr=False)
    pass
    pass
    legacy_params: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        self.control = SubAgentControl(self)

    @property
    def rounds_left(self) -> int:
        return max(0, self.rounds_limit - self.rounds_used)

    @cached_property
    def dir(self) -> Path:
        return ProjectPaths.for_workspace(self.project).subagent_dir(self.id)

    @property
    def transcript_path(self) -> Path:
        return self.dir / "transcript.jsonl"

    def ensure(self) -> None:
        pass
        if not self._dir_ready:
            self._writer = TranscriptWriter(self.transcript_path)
            self._dir_ready = True

    def append_message(self, msg: dict) -> None:
        self.messages.append(msg)
        self._append_jsonl({"kind": "message", "message": msg})

    def append_event(self, event: dict) -> None:
        pass
        if event.get("type") in ("text", "reason"):
            return
        self.events.append(event)
        self._append_jsonl({"kind": "event", "event": event})

    def _append_jsonl(self, item: dict) -> None:
        self.ensure()
        self._writer.put(item)

    def add_instruction(self, text: str) -> None:
        if text.strip():
            self.instructions.append(text.strip())
            self._append_jsonl({"kind": "instruction", "text": text.strip()})
            pass
            pass
            if self.from_disk:
                self.persist()

    def drain_instructions(self) -> list[str]:
        out, self.instructions = self.instructions, []
        return out

    def finish(self, status: str, result: str = "", error: str = "",
               raw: str = "", protocol: str = "") -> None:
        self.status = status
        self.finished_at = time.time()
        self.protocol = protocol
        full = raw or result
        if result or full:
            self.result = result or full
            self.raw_chars = len(full)
            self.result_path = str(self.dir / "result.md")
            self.dir.mkdir(parents=True, exist_ok=True)
            Path(self.result_path).write_text(self.result, "utf-8")
            raw_file = self.dir / "result.raw.md"
            if raw and raw != self.result:
                raw_file.write_text(raw, "utf-8")
            elif raw_file.is_file():
                raw_file.unlink(missing_ok=True)
        self.error = error
        if self._dir_ready and self.status != st.PAUSED and not self.paused:
            pass
            pass
            pass
            self._writer.close()
        self.persist()

    def persist(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        write_json(self.dir / "meta.json", {
            "id": self.id, "parent_id": self.parent_id,
            "project": self.project, "task": self.task,
            "child_session_id": self.child_session_id,
            "status": self.status, "created_at": self.created_at,
            "finished_at": self.finished_at, "result_path": self.result_path,
            "result_chars": len(self.result), "raw_chars": self.raw_chars,
            "protocol": self.protocol, "error": self.error,
            "paused": self.paused,
            "profile_prompt": self.profile_prompt,
            "profile_base": self.profile_base, "tools": self.tools,
            "pending_instructions": list(self.instructions),
        })

    def brief(self) -> dict:
        data = {"id": self.id, "status": self.status,
                "rounds_used": self.rounds_used,
                "rounds_left": self.rounds_left, "paused": self.paused}
        if self.error:
            data["error"] = self.error
        if self.protocol == "fallback":
            pass
            pass
            data["protocol"] = "fallback"
        if self.result:
            pass
            pass
            from ..tools.text_limit import TOOL_CONTEXT_LIMIT
            from .subagent_result import file_hint
            if len(self.result) > TOOL_CONTEXT_LIMIT:
                data["result"] = file_hint(len(self.result), self.result_path)
            else:
                data["result"] = self.result
        elif self.result_path:
            data["result_path"] = self.result_path
        pass
        pass
        pass
        if self.status == st.DONE or self.paused:
            data["resumable"] = True
            data["hint"] = ("本轮已收尾（done）。要继续做就用 "
                            "subagent(action=extend, id=..., rounds=N) 追加额度，"
                            "或在 task/message 里写新目标；会复用已落盘的完整历史，"
                            "不用重开、不用重做。服务重启后凭 id 同样可用。")
        if self.from_disk:
            data["from_disk"] = True
            data["hint"] = ("这是盘上历史记录（含服务重启后）；可用 "
                            "subagent(action=extend, id=...) 基于已落盘的历史"
                            "追加任务继续跑，不用重新 spawn")
        elif st.is_active(self.status):
            data["hint"] = "仍在运行；需要结果请再 wait 一次，不要贴整段记录"
        return data

    def to_dict(self, include_result: bool = False) -> dict:
        data = {
            "id": self.id, "parent_id": self.parent_id,
            "project": self.project, "task": self.task,
            "child_session_id": self.child_session_id,
            "status": self.status, "created_at": self.created_at,
            "finished_at": self.finished_at, "result_path": self.result_path,
            "result_chars": len(self.result), "raw_chars": self.raw_chars,
            "protocol": self.protocol, "error": self.error,
            "transcript_path": str(self.transcript_path),
            "message_count": len(self.messages),
            "rounds_used": self.rounds_used,
            "rounds_limit": self.rounds_limit,
            "rounds_left": self.rounds_left,
            "paused": self.paused,
        }
        if include_result:
            data["result"] = self.result
        return data

    def read_messages(self, offset: int = 0, limit: int = 100) -> dict:
        msgs = self.messages
        start = max(0, int(offset))
        end = start + max(0, int(limit)) if limit else len(msgs)
        return {"id": self.id, "status": self.status,
                "messages": msgs[start:end],
                # 只回"值得看"的事件：工具类事件的结构信息已在 messages 里，
                # 原样回会渲染成两遍且第二遍没有正文（见 subagent_events 模块注释）
                "events": visible_events(self.events),
                "next_offset": end if end < len(msgs) else None,
                "result_path": self.result_path}

