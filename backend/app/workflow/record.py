from __future__ import annotations

import os
import time
from typing import Optional

def node_rows_of(states: dict | None) -> list[dict]:
    rows = []
    for nid, st in (states or {}).items():
        row = {"id": nid, "status": st.get("status"), "ms": st.get("ms"),
               "chars": len(st.get("output") or ""),
               "path": st.get("output_path")}
        if st.get("error"):
            row["error"] = str(st["error"])[:300]
        if st.get("truncated"):
            row["truncated"] = True
            row["original_chars"] = st.get("original_chars")
        rows.append(row)
    return rows


class RunRecord:
    def __init__(self, rid: str, wf_name: str,
                 workspace: str = "") -> None:
        self.id = rid
        self.wf_name = wf_name
        self.workspace = workspace
        self.status = "running"
        self.started = time.time()
        self.finished: Optional[float] = None
        self.node_states: dict[str, dict] = {}
        self.final: str = ""
        self.error: str = ""
        pass
        pass
        pass
        pass
        self.warnings: list[dict] = []
        self.inputs: dict = {}
        pass
        self.files: list[dict] = []
        pass
        self.parent_run: str = ""
        self.parent_node: str = ""
        pass
        self.call_stack: list[str] = []
        pass
        self.parallel_mode: str = "sequential"
        pass
        self.pending_human: Optional[dict] = None
        pass
        pass
        self.session: str = ""


    def warn(self, code: str, message: str, node: str = "") -> None:
        if any(w.get("code") == code and w.get("node") == node
               for w in self.warnings):
            return
        self.warnings.append({"code": code, "node": node or "",
                              "message": str(message)})

    def add_file(self, path: str, node: str = "") -> None:
        if not path:
            return
        p = os.path.abspath(str(path))
        try:
            st = os.stat(p)
            size, mtime = st.st_size, st.st_mtime
        except OSError:
            return
        rel = self._rel(p)
        for item in self.files:
            if item.get("path") == p:
                item.update({"size": size, "mtime": mtime, "node": node or item.get("node", "")})
                return
        self.files.append({"path": p, "rel": rel, "name": os.path.basename(p),
                           "size": size, "mtime": mtime, "node": node})

    def _rel(self, p: str) -> str:
        if not self.workspace:
            return os.path.basename(p)
        try:
            rel = os.path.relpath(p, os.path.abspath(self.workspace))
            return rel.replace("\\", "/") if not rel.startswith("..") else os.path.basename(p)
        except (ValueError, OSError):
            return os.path.basename(p)

    def brief(self, timed_out: bool = False) -> dict:
        return {"run_id": self.id, "workflow": self.wf_name,
                "status": self.status, "error": self.error,
                "started": self.started, "finished": self.finished,
                "final_chars": len(self.final or ""),
                "final_preview": (self.final or "")[:2000],
                "nodes": node_rows_of(self.node_states),
                "warnings": list(self.warnings),
                "pending_human": self.pending_human,
                "timed_out": timed_out}

    def to_dict(self) -> dict:
        return {"id": self.id, "workflow": self.wf_name, "status": self.status,
                "started": self.started, "finished": self.finished,
                "nodes": self.node_states, "final": self.final,
                "error": self.error, "workspace": self.workspace,
                "inputs": self.inputs, "pending_human": self.pending_human,
                "files": list(self.files),
                "warnings": list(self.warnings),
                "session": self.session,
                "parent_run": self.parent_run or None,
                "parent_node": self.parent_node or None}

    def to_meta(self) -> dict:
        nodes = {}
        for nid, st in self.node_states.items():
            item = {k: v for k, v in st.items() if k != "output"}
            out = st.get("output") or ""
            item["output_preview"] = out[:500]
            item["output_chars"] = len(out)
            nodes[nid] = item
        return {"id": self.id, "workflow": self.wf_name, "status": self.status,
                "started": self.started, "finished": self.finished,
                "nodes": nodes, "final_preview": self.final[:1000],
                "final_chars": len(self.final), "error": self.error,
                "workspace": self.workspace, "inputs": self.inputs,
                "pending_human": self.pending_human,
                "files": list(self.files),
                "warnings": list(self.warnings),
                "session": self.session,
                "parent_run": self.parent_run or None,
                "parent_node": self.parent_node or None}
