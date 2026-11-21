from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("harness.workflow.human")

pass
pass
POLL_INTERVAL_SEC = 0.2


def _gate_dir(run_dir: Optional[Path]) -> Optional[Path]:
    if run_dir is None:
        return None
    d = Path(run_dir) / "gates"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        logger.debug("建闸门目录失败: %s", d, exc_info=True)
        return None
    return d


@dataclass
class PendingGate:

    run_id: str
    node_id: str
    title: str = ""
    ask: str = ""
    show: str = ""
    options: list[str] = field(default_factory=list)
    created: float = field(default_factory=time.time)
    event: asyncio.Event = field(default_factory=asyncio.Event)
    choice: str = ""
    comment: str = ""
    decided: bool = False
    pass
    path: Optional[Path] = None

    def view(self) -> dict:
        return {"run_id": self.run_id, "node_id": self.node_id,
                "title": self.title, "ask": self.ask, "show": self.show,
                "options": list(self.options), "created": self.created}

    pass

    def _snapshot(self) -> dict:
        return {"run_id": self.run_id, "node_id": self.node_id,
                "title": self.title, "ask": self.ask, "show": self.show,
                "options": list(self.options), "created": self.created,
                "choice": self.choice, "comment": self.comment,
                "decided": self.decided,
                "decided_at": time.time() if self.decided else None}

    def save(self) -> None:
        if self.path is None:
            return
        try:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._snapshot(), ensure_ascii=False),
                           "utf-8")
            tmp.replace(self.path)
        except OSError:
            logger.debug("写闸门文件失败: %s", self.path, exc_info=True)

    def apply_record(self, data: dict) -> bool:
        if not isinstance(data, dict) or not data.get("decided"):
            return False
        self.choice = str(data.get("choice") or "")
        self.comment = str(data.get("comment") or "")
        self.decided = True
        return True

    def reload_if_decided(self) -> bool:
        if self.decided or self.path is None:
            return self.decided
        try:
            data = json.loads(self.path.read_text("utf-8"))
        except (OSError, ValueError):
            return False
        if self.apply_record(data):
            self.event.set()
            return True
        return False


class HumanGate:

    def __init__(self, run_dir=None) -> None:
        self._pending: dict[str, dict[str, PendingGate]] = {}
        self._run_dir = run_dir

    def _dir_for(self, run_id: str) -> Optional[Path]:
        if self._run_dir is None:
            return None
        try:
            return _gate_dir(self._run_dir(run_id))
        except Exception:
            logger.debug("解析运行目录失败: %s", run_id, exc_info=True)
            return None

    def open(self, run_id: str, node_id: str, title: str = "", ask: str = "",
             show: str = "", options: list[str] | None = None) -> PendingGate:
        d = self._dir_for(run_id)
        gate = PendingGate(run_id=run_id, node_id=node_id, title=title,
                           ask=ask, show=show, options=list(options or []),
                           path=(d / f"{node_id}.json") if d else None)
        self._pending.setdefault(run_id, {})[node_id] = gate
        pass
        pass
        if not gate.reload_if_decided():
            gate.save()
        pass
        _notify(run_id, node_id, "human-open")
        return gate

    def pending(self, run_id: str) -> dict | None:
        for gate in (self._pending.get(run_id) or {}).values():
            if not gate.decided:
                return gate.view()
        return None

    def list_pending(self) -> list[dict]:
        out: list[dict] = []
        for run_id, gates in self._pending.items():
            for gate in gates.values():
                if not gate.decided:
                    out.append(gate.view())
        return out

    def decide(self, run_id: str, node_id: str, choice: str,
               comment: str = "") -> bool:
        gate = (self._pending.get(run_id) or {}).get(node_id)
        if gate is None:
            pass
            pass
            gate = self._rehydrate(run_id, node_id)
        if gate is None or gate.decided:
            return False
        if gate.options and choice not in gate.options:
            pass
            pass
            logger.warning("闸门选项不在允许范围: %s 不在 %s", choice, gate.options)
            return False
        gate.choice = choice
        gate.comment = comment
        gate.decided = True
        pass
        gate.save()
        gate.event.set()
        _notify(run_id, node_id, "human-decided")
        return True

    def _rehydrate(self, run_id: str, node_id: str) -> Optional[PendingGate]:
        d = self._dir_for(run_id)
        if d is None:
            return None
        p = d / f"{node_id}.json"
        try:
            data = json.loads(p.read_text("utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict):
            return None
        gate = PendingGate(
            run_id=run_id, node_id=node_id,
            title=str(data.get("title") or ""),
            ask=str(data.get("ask") or ""),
            show=str(data.get("show") or ""),
            options=list(data.get("options") or []),
            created=float(data.get("created") or time.time()),
            path=p)
        gate.apply_record(data)
        self._pending.setdefault(run_id, {})[node_id] = gate
        return gate

    async def wait(self, gate: PendingGate, timeout: float = 0) -> PendingGate:
        if gate.decided:
            return gate
        if gate.path is None:
            return await self._wait_event(gate, timeout)
        return await self._wait_file(gate, timeout)

    async def _wait_event(self, gate: PendingGate, timeout: float) -> PendingGate:
        try:
            if timeout > 0:
                await asyncio.wait_for(gate.event.wait(), timeout=timeout)
            else:
                await gate.event.wait()
        except asyncio.TimeoutError:
            gate.decided = False
            return gate
        return gate

    async def _wait_file(self, gate: PendingGate, timeout: float) -> PendingGate:
        deadline = (time.monotonic() + timeout) if timeout > 0 else None
        while True:
            if gate.decided:
                return gate
            if gate.reload_if_decided():
                return gate
            if deadline is not None and time.monotonic() >= deadline:
                gate.decided = False
                return gate
            try:
                await asyncio.wait_for(gate.event.wait(), POLL_INTERVAL_SEC)
                if gate.decided:
                    return gate
            except asyncio.TimeoutError:
                continue

    def close(self, run_id: str, node_id: str) -> None:
        pass
        pass
        self._pending.get(run_id, {}).pop(node_id, None)

    def clear(self, run_id: str) -> None:
        had = bool(self._pending.get(run_id))
        for gate in (self._pending.pop(run_id, {}) or {}).values():
            gate.decided = True
            gate.event.set()
        if had:
            _notify(run_id, "", "human-clear")


def _notify(run_id: str, node_id: str, reason: str) -> None:
    try:
        from ..event.attention import notify
        notify("", reason, run=run_id, node=node_id)
    except Exception:
        logger.debug("广播 human 闸门状态失败: %s %s", run_id, reason, exc_info=True)
