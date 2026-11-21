from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional

from .core import Risk

logger = logging.getLogger("harness.policy")

__all__ = ["PendingApproval", "ApprovalManager", "build_file_hunks",
           "apply_file_hunks"]

def build_file_hunks(old: str, new: str, ctx_chars: int = 60) -> list[dict]:
    import difflib
    sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
    hunks = []
    hid = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        hunks.append({
            "id": hid, "tag": tag,
            "old": old[max(0, i1 - ctx_chars):i2 + ctx_chars],
            "new": new[max(0, j1 - ctx_chars):j2 + ctx_chars],
        })
        hid += 1
    return hunks


def apply_file_hunks(old: str, new: str, approved: list[int] | None) -> str:
    if approved is None:
        return new
    import difflib
    sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
    out = []
    hid = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out.append(old[i1:i2])
        else:
            out.append(new[j1:j2] if hid in approved else old[i1:i2])
            hid += 1
    return "".join(out)


@dataclass
class PendingApproval:
    id: str
    command: str
    risks: list[Risk]
    reason: str
    session_id: str = ""
    event: asyncio.Event = field(default_factory=asyncio.Event)
    approved: Optional[bool] = None
    kind: str = "command"
    file_diff: Optional[dict] = None
    approved_hunks: Optional[list[int]] = None


class ApprovalManager:

    TIMEOUT = 600

    def __init__(self) -> None:
        self._pending: dict[str, PendingApproval] = {}

    def create(self, command: str, risks: list[Risk], reason: str,
               session_id: str = "", kind: str = "command",
               file_diff: Optional[dict] = None) -> PendingApproval:
        pa = PendingApproval(uuid.uuid4().hex[:10], command, risks, reason, session_id,
                             kind=kind, file_diff=file_diff)
        self._pending[pa.id] = pa
        _notify_attention(session_id, "approval")
        return pa

    def list(self, session_id: str | None = None) -> list[dict]:
        return [{
            "id": p.id, "command": p.command, "reason": p.reason,
            "kind": p.kind, "file_diff": p.file_diff,
            "session_id": p.session_id,
            "risks": [{"target": r.target, "description": r.description,
                       "severity": r.severity} for r in p.risks],
        } for p in self._pending.values()
            if not session_id or p.session_id == session_id]

    def decide(self, pid: str, approved: bool,
               hunks: Optional[list[int]] = None) -> bool:
        p = self._pending.get(pid)
        if not p:
            return False
        p.approved = approved
        p.approved_hunks = hunks
        p.event.set()
        self._pending.pop(pid, None)
        _notify_attention(p.session_id, "approval-decided")
        return True

    async def wait(self, pa: PendingApproval, stop_check=None) -> bool:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.TIMEOUT
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                self._pending.pop(pa.id, None)
                return False
            try:
                await asyncio.wait_for(pa.event.wait(), timeout=min(0.5, remaining))
            except asyncio.TimeoutError:
                pass
                if stop_check is not None:
                    try:
                        if stop_check():
                            self._pending.pop(pa.id, None)
                            return False
                    except Exception:
                        logger.debug("stop_check 抛错，按未中止继续等待: %s", pa.id,
                                     exc_info=True)
                continue
            return bool(pa.approved)

    def cancel_session(self, session_id: str) -> int:
        if not session_id:
            return 0
        drop = [pid for pid, p in self._pending.items()
                if p.session_id == session_id]
        for pid in drop:
            p = self._pending.pop(pid)
            p.approved = False
            p.event.set()
        return len(drop)


def _notify_attention(session_id: str, reason: str) -> None:
    try:
        from ..event.attention import notify
        notify(session_id or "", reason)
    except Exception:
        logger.debug("广播审批通知失败: %s %s", session_id, reason, exc_info=True)
