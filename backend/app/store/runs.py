from __future__ import annotations

import json
import logging
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import layout
from ..util import pathx
from ..util.jsonx import append_jsonl, write_json
from ..util.fsx import ensure_parent, write_text
import app.util.status as status

logger = logging.getLogger("harness.store.runs")

pass
STALE_RUN_ERROR = "进程重启，运行已中断（可点 ↻ 续跑）"



def safe_component(value: str, fallback: str = "item") -> str:
    text = re.sub(r"[^0-9A-Za-z_.\-\u4e00-\u9fff]+", "_", str(value or ""))
    return text.strip("._") or fallback


@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @classmethod
    def for_workspace(cls, workspace: str = "") -> "ProjectPaths":
        if workspace:
            pass
            pass
            pass
            root = pathx.project_dir(workspace)
        else:
            pass
            pass
            root = layout.global_workspace()
        return cls(root=root)

    @property
    def agent(self) -> Path:
        return layout.project_agent_dir(self.root)

    @property
    def workflows(self) -> Path:
        return layout.project_workflows_dir(self.root)

    @property
    def runs(self) -> Path:
        pass
        pass
        return layout.project_runs_dir(self.root)

    @property
    def subagents(self) -> Path:
        return layout.project_subagents_dir(self.root)

    @property
    def artifacts(self) -> Path:
        return self.agent / layout.ARTIFACTS_DIR_NAME

    def ensure(self) -> "ProjectPaths":
        is_project = (self.root == layout.global_workspace()
                      or layout.is_project(self.root))
        if not is_project:
            return self
        for p in (self.agent, self.workflows, self.runs,
                  self.subagents, self.artifacts):
            p.mkdir(parents=True, exist_ok=True)
        return self

    def run_dir(self, run_id: str) -> Path:
        return self.runs / safe_component(run_id, "run")

    def subagent_dir(self, subagent_id: str) -> Path:
        return self.subagents / safe_component(subagent_id, "subagent")


def _read_meta(d: Path) -> dict[str, Any] | None:
    meta_path = d / "meta.json"
    if not meta_path.is_file():
        return None
    try:
        data = json.loads(meta_path.read_text("utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


class RunStore:

    def __init__(self, workspace: str = "") -> None:
        self.workspace = workspace
        self.paths = ProjectPaths.for_workspace(workspace).ensure()

    def prepare(self, run_id: str, workflow: str) -> Path:
        d = self.paths.run_dir(run_id)
        (d / "nodes").mkdir(parents=True, exist_ok=True)
        meta = d / "meta.json"
        if not meta.exists():
            self.write_meta(run_id, {
                "id": run_id, "workflow": workflow, "status": "running",
                "started": time.time(), "finished": None,
                "nodes": {}, "final": "", "error": "",
            })
        return d

    def write_meta(self, run_id: str, data: dict[str, Any]) -> None:
        write_json(self.paths.run_dir(run_id) / "meta.json", data)

    def write_node(self, run_id: str, node_id: str, text: str) -> dict[str, Any]:
        d = self.paths.run_dir(run_id) / "nodes"
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{safe_component(node_id, 'node')}.md"
        ensure_parent(p)
        pass
        write_text(p, text)
        return {"output_path": str(p), "output_bytes": len(text.encode("utf-8"))}

    def read_node(self, run_id: str, node_id: str,
                  offset: int = 0, limit: int = 12000) -> dict[str, Any]:
        p = self.paths.run_dir(run_id) / "nodes" / f"{safe_component(node_id, 'node')}.md"
        if not p.is_file():
            return {"error": f"节点输出不存在: {node_id}"}
        text = p.read_text("utf-8", errors="replace")
        total = len(text)
        start = max(0, int(offset))
        end = start + max(0, int(limit)) if limit else total
        return {"node_id": node_id, "path": str(p), "total_chars": total,
                "offset": start, "content": text[start:end],
                "next_offset": end if end < total else None}

    def write_final(self, run_id: str, text: str) -> str:
        p = self.paths.run_dir(run_id) / "final.md"
        ensure_parent(p)
        write_text(p, text)
        return str(p)

    pass

    def stash_node(self, run_id: str, node_id: str) -> list[str]:
        d = self.paths.run_dir(run_id) / "nodes"
        p = d / f"{safe_component(node_id, 'node')}.md"
        if not p.is_file():
            return []
        stale = self.paths.run_dir(run_id) / "stale"
        stale.mkdir(parents=True, exist_ok=True)
        pass
        target = stale / f"{safe_component(node_id, 'node')}.{int(time.time())}.md"
        try:
            p.replace(target)
        except OSError:
            return []
        return [str(target)]

    def gates_dir(self, run_id: str) -> Path:
        return self.paths.run_dir(run_id) / "gates"

    def carry_gates(self, src_run_id: str, dst_run_id: str) -> int:
        if not src_run_id or src_run_id == dst_run_id:
            return 0
        src = self.gates_dir(src_run_id)
        if not src.is_dir():
            return 0
        dst = self.gates_dir(dst_run_id)
        dst.mkdir(parents=True, exist_ok=True)
        n = 0
        for p in src.glob("*.json"):
            try:
                shutil.copyfile(p, dst / p.name)
                n += 1
            except OSError:
                continue
        return n

    pass

    def progress_dir(self, run_id: str) -> Path:
        return self.paths.run_dir(run_id) / "progress"

    def progress_path(self, run_id: str, node_id: str) -> Path:
        return self.progress_dir(run_id) / f"{safe_component(node_id, 'node')}.jsonl"

    def append_progress(self, run_id: str, node_id: str, row: dict[str, Any]) -> None:
        append_jsonl(self.progress_path(run_id, node_id), row)

    def read_progress(self, run_id: str, node_id: str) -> dict[str, str]:
        p = self.progress_path(run_id, node_id)
        if not p.is_file():
            return {}
        out: dict[str, str] = {}
        try:
            for line in p.read_text("utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(row, dict):
                    continue
                digest = row.get("item_digest")
                if isinstance(digest, str) and digest:
                    out[digest] = str(row.get("result") or "")
        except OSError:
            return {}
        return out

    def carry_progress(self, src_run_id: str, dst_run_id: str) -> int:
        if not src_run_id or src_run_id == dst_run_id:
            return 0
        src = self.progress_dir(src_run_id)
        if not src.is_dir():
            return 0
        dst = self.progress_dir(dst_run_id)
        dst.mkdir(parents=True, exist_ok=True)
        n = 0
        for p in src.glob("*.jsonl"):
            try:
                shutil.copyfile(p, dst / p.name)
                n += 1
            except OSError:
                continue
        return n

    def load_run(self, run_id: str) -> dict[str, Any] | None:
        d = self.paths.run_dir(run_id)
        meta_path = d / "meta.json"
        if not meta_path.is_file():
            return None
        try:
            meta = json.loads(meta_path.read_text("utf-8"))
        except (OSError, ValueError):
            return None
        final_path = d / "final.md"
        if final_path.is_file():
            meta["final"] = final_path.read_text("utf-8", errors="replace")
        nodes = meta.get("nodes") or {}
        for nid, item in nodes.items():
            p = Path(item.get("output_path", ""))
            if p.is_file():
                item["output"] = p.read_text("utf-8", errors="replace")
            else:
                item.setdefault("output", item.get("output_preview", ""))
        meta["nodes"] = nodes
        return meta

    def sweep_stale(self, live_ids: set[str] | None = None) -> int:
        live = live_ids or set()
        changed = 0
        runs = self.paths.runs
        if not runs.is_dir():
            return 0
        for d in runs.iterdir():
            meta = _read_meta(d)
            if meta is None:
                continue
            rid = str(meta.get("id") or d.name)
            if rid in live:
                continue
            touched = False
            for st in (meta.get("nodes") or {}).values():
                if status.is_active(str(st.get("status") or "")):
                    st["status"] = status.CANCELLED
                    st["error"] = st.get("error") or STALE_RUN_ERROR
                    touched = True
                st.pop("output", None)
            if status.is_active(str(meta.get("status") or "")):
                meta["status"] = status.CANCELLED
                meta["error"] = meta.get("error") or STALE_RUN_ERROR
                meta["finished"] = meta.get("finished") or time.time()
                touched = True
            meta.pop("final", None)
            if not touched:
                continue
            try:
                self.write_meta(rid, meta)
            except OSError:
                continue
            changed += 1
        return changed

    def purge_legacy_runs(self, live_sessions: set[str] | None = None) -> int:
        removed = 0
        runs = self.paths.runs
        if not runs.is_dir():
            return 0
        for d in runs.iterdir():
            meta = _read_meta(d)
            if meta is None:
                continue
            sid = str(meta.get("session") or "").strip()
            if sid and (live_sessions is None or sid in live_sessions):
                continue
            try:
                shutil.rmtree(d)
            except OSError:
                continue
            removed += 1
        return removed

    def list_runs(self, workflow: str = "", limit: int = 50) -> list[dict]:
        out: list[dict] = []
        runs = self.paths.runs
        if not runs.is_dir():
            return out
        for d in runs.iterdir():
            meta = _read_meta(d)
            if meta is None:
                continue
            if workflow and meta.get("workflow") != workflow:
                continue
            nodes = meta.get("nodes") or {}
            out.append({
                "id": meta.get("id") or d.name,
                "workflow": meta.get("workflow", ""),
                "status": meta.get("status", ""),
                "started": meta.get("started"),
                "finished": meta.get("finished"),
                "error": meta.get("error", ""),
                "final_preview": meta.get("final_preview", ""),
                "nodes": {nid: {"status": it.get("status"),
                                "ms": it.get("ms"),
                                "error": it.get("error", "")}
                          for nid, it in nodes.items()},
            })
        out.sort(key=lambda x: x.get("started") or 0, reverse=True)
        return out[:max(1, int(limit))]
