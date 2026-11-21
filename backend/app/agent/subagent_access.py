from __future__ import annotations

from pathlib import Path

import app.util.status as st

from ..store.runs import ProjectPaths
from ..util.jsonx import read_json, read_jsonl
from .subagents import SubAgentRecord


class SubAgentAccess:

    def __init__(self, sessions, session_rt, project: str = "") -> None:
        self._sessions = sessions
        self._rt = session_rt
        pass
        pass
        self._project = project or ""

    pass
    def _dir_for(self, sid: str) -> "Path | None":
        if not self._project or not sid:
            return None
        return ProjectPaths.for_workspace(self._project).subagent_dir(sid)

    def _load_from_disk(self, sid: str, parent_id: str = "") -> "SubAgentRecord | None":
        d = self._dir_for(sid)
        if d is None or not (d / "meta.json").is_file():
            return None
        meta = read_json(d / "meta.json", None)
        if not isinstance(meta, dict):
            return None
        if parent_id and meta.get("parent_id") != parent_id:
            return None
        rec = SubAgentRecord(
            id=str(meta.get("id") or sid),
            parent_id=str(meta.get("parent_id") or ""),
            project=str(meta.get("project") or self._project),
            task=str(meta.get("task") or ""),
            child_session_id=str(meta.get("child_session_id") or ""),
            status=str(meta.get("status") or st.DONE),
            created_at=float(meta.get("created_at") or 0),
            finished_at=meta.get("finished_at"),
            result_path=str(meta.get("result_path") or ""),
            error=str(meta.get("error") or ""),
            protocol=str(meta.get("protocol") or ""),
            raw_chars=int(meta.get("raw_chars") or 0),
            rounds_used=int(meta.get("rounds_used") or 0),
            rounds_limit=int(meta.get("rounds_limit") or 0),
            paused=bool(meta.get("paused")),
            profile_prompt=str(meta.get("profile_prompt") or meta.get("profile_id") or ""),
            profile_base=str(meta.get("profile_base") or ""),
            tools=(list(meta["tools"]) if isinstance(meta.get("tools"), list)
                   else None),
            instructions=(list(meta["pending_instructions"])
                          if isinstance(meta.get("pending_instructions"), list)
                          else []),
        )
        rec.from_disk = True
        pass
        pass
        rec.legacy_params = not rec.profile_prompt and rec.tools is None
        pass
        for item in read_jsonl(d / "transcript.jsonl"):
            if not isinstance(item, dict):
                continue
            kind = item.get("kind")
            if kind == "message" and isinstance(item.get("message"), dict):
                rec.messages.append(item["message"])
            elif kind == "event" and isinstance(item.get("event"), dict):
                rec.events.append(item["event"])
        pass
        pass
        pass
        result_file = d / "result.md"
        if not result_file.is_file() and rec.result_path:
            result_file = Path(rec.result_path)
        if result_file.is_file():
            try:
                rec.result = result_file.read_text("utf-8", errors="replace")
            except OSError:
                pass
        return rec

    def _disk_ids(self) -> "list[str]":
        if not self._project:
            return []
        d = ProjectPaths.for_workspace(self._project).subagents
        if not d.is_dir():
            return []
        return [p.name for p in d.iterdir() if p.is_dir()
                and (p / "meta.json").is_file()]

    pass
    def _find(self, sid: str, parent_id: str = "") -> "SubAgentRecord | None":
        if self._rt is not None:
            for _sid, rt in self._rt.items():
                sa = rt.subagent
                if sa is None or sa.id != sid:
                    continue
                if parent_id and sa.parent_id != parent_id:
                    continue
                return sa
        return self._load_from_disk(sid, parent_id)

    pass
    def list(self, parent_id: str = "", project: str = "") -> list[dict]:
        pass
        found: "dict[str, SubAgentRecord]" = {}
        if self._rt is not None:
            for _sid, rt in self._rt.items():
                sa = rt.subagent
                if sa is None:
                    continue
                if parent_id and sa.parent_id != parent_id:
                    continue
                if project and sa.project != project:
                    continue
                found[sa.id] = sa
        for sid in self._disk_ids():
            if sid in found:
                continue
            rec = self._load_from_disk(sid, parent_id)
            if rec is None:
                continue
            if project and rec.project != project:
                continue
            found[sid] = rec
        items = [sa.to_dict() for sa in found.values()]
        return sorted(items, key=lambda x: x["created_at"], reverse=True)

    def get(self, sid: str, parent_id: str = "") -> "SubAgentRecord | None":
        return self._find(sid, parent_id)

    def read(self, sid: str, parent_id: str = "",
             offset: int = 0, limit: int = 100) -> dict | None:
        rec = self._find(sid, parent_id)
        return rec.read_messages(offset, limit) if rec else None

    def message(self, sid: str, text: str, parent_id: str = "") -> dict:
        rec = self._find(sid, parent_id)
        if not rec:
            return {"error": f"子 Agent 不存在: {sid}"}
        pass
        pass
        if st.is_active(rec.status):
            rec.add_instruction(text)
            return {"ok": True, "id": rec.id, "queued": text.strip()}
        if rec.status != st.DONE and not rec.paused:
            return {"error": f"子 Agent 已结束: {rec.status}"}
        rec.add_instruction(text)
        return {"ok": True, "id": rec.id, "queued": text.strip(),
                "hint": "追加成功；用 subagent(action=extend, id=...) 基于历史继续跑"}

    def stop(self, sid: str, parent_id: str = "", force: bool = True) -> dict:
        rec = self._find(sid, parent_id)
        if not rec:
            return {"error": f"子 Agent 不存在: {sid}"}
        if rec.from_disk:
            return {"error": f"子 Agent {sid} 是历史记录（只读、无运行体），无需停止",
                    "id": sid}
        rec.control.request_stop()
        if force:
            pass
            pass
            handle = rec.task_handle
            if handle is not None and not handle.done():
                handle.cancel()
        return {"ok": True, "id": rec.id, "status": rec.status,
                "force": force}

    async def wait(self, sid: str, parent_id: str = "",
                   timeout: float = 0) -> dict:
        import asyncio as _asyncio
        rec = self._find(sid, parent_id)
        if not rec:
            return {"error": f"子 Agent 不存在: {sid}"}
        handle = rec.task_handle
        if handle is not None and not handle.done():
            try:
                if timeout and timeout > 0:
                    pass
                    await _asyncio.wait_for(_asyncio.shield(handle), timeout)
                else:
                    await handle
            except _asyncio.TimeoutError:
                return {**rec.brief(), "timed_out": True,
                        "hint": "等待超时，子 Agent 仍在运行；可再 wait / get 查看，"
                                "或 stop 中止，不要重开新子任务"}
            except _asyncio.CancelledError:
                rec.finish(st.STOPPED, rec.result, rec.error or "已中止")
            except Exception as e:
                rec.finish(st.FAILED, rec.result, f"{type(e).__name__}: {e}")
        return rec.brief()
