from __future__ import annotations

import time

pass
from ..store.session_db import WF_SESSION_KIND, WF_NODE_KIND

__all__ = ["LLMSession", "HISTORY_MAX_CHARS", "WF_SESSION_KIND",
           "WF_NODE_KIND", "trim_history"]

pass
pass
HISTORY_MAX_CHARS = 120_000


def _chars(msg: dict) -> int:
    content = msg.get("content")
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return sum(len(str(x)) for x in content)
    return len(str(content or ""))


def trim_history(messages: list[dict], budget: int = HISTORY_MAX_CHARS) -> list[dict]:
    if not messages:
        return []
    total = 0
    start = len(messages)
    for i in range(len(messages) - 1, -1, -1):
        total += _chars(messages[i])
        if total > budget:
            cut = i + 1
            while cut < len(messages) and messages[cut].get("role") != "user":
                cut += 1
            start = cut
            break
        start = i
    kept = messages[start:]
    pass
    return kept or messages[-1:]


class LLMSession:

    def __init__(self, sessions, project: str, workflow: str, sid: str = "") -> None:
        self.sessions = sessions
        self.project = project or ""
        self.workflow = workflow or ""
        self.sid = sid or ""
        pass
        pass
        self._created: dict[str, float] = {}

    pass
    def resolve(self, want: str = "") -> str:
        if want and want != "new":
            self.sid = want
            return want
        if want == "new":
            return self._create()
        latest = self.sessions.find_active(
            self.project, WF_SESSION_KIND, self.workflow)
        self.sid = (latest or {}).get("id") or self._create()
        return self.sid

    def _create(self) -> str:
        row = self.sessions.create(
            title=self._default_title(), project=self.project,
            kind=WF_SESSION_KIND, origin=self.workflow)
        self.sid = row["id"]
        return self.sid

    @staticmethod
    def _default_title() -> str:
        return time.strftime("会话 %m-%d %H:%M")

    pass
    def node_sid(self, node_id: str) -> str:
        return f"{self.sid}__{node_id}"

    def history(self, node_id: str) -> list[dict]:
        if not node_id:
            return []
        data = self.sessions.get(self.node_sid(node_id))
        if not data:
            return []
        self._created.setdefault(data["id"], data.get("created_at") or time.time())
        msgs = [m for m in (data.get("messages") or [])
                if isinstance(m, dict) and m.get("role") != "system"]
        return trim_history(msgs)

    def save(self, node_id: str, messages: list[dict]) -> None:
        if not node_id or not self.sid:
            return
        msgs = [m for m in messages if isinstance(m, dict) and m.get("role") != "system"]
        sid = self.node_sid(node_id)
        self.sessions.save({
            "id": sid,
            "title": node_id,
            "project": self.project,
            "created_at": self._created.get(sid) or time.time(),
            "messages": trim_history(msgs),
            "kind": WF_NODE_KIND,
            "origin": self.sid,
        })
