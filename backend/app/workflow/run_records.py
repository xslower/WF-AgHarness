from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional

import app.util.status as wstat
from .errors import not_found
from .expr import evaluate, evaluate_value, safe_env as _expr_env
from .record import RunRecord

logger = logging.getLogger("harness.workflow.engine")


def _node_chars(st: dict) -> int:
    if st.get("output_chars") is not None:
        return int(st.get("output_chars") or 0)
    return len(str(st.get("output") or ""))


class RunRecordsMixin:
    pass

    async def redo(self, run_id: str, from_node: str = "",
                   note: str = "") -> RunRecord:
        view = self.load_run(run_id)
        if not view:
            raise not_found(f"运行不存在: {run_id}")
        wf = self.get(view.get("workflow", ""))
        if not wf:
            raise not_found(f"工作流不存在: {view.get('workflow')}")
        states = view.get("nodes") or {}
        start = from_node or self._first_undone(wf, states)
        ids = {str(n["id"]) for n in wf.get("nodes") or []}
        if start not in ids:
            raise not_found(f"节点不存在: {start}")

        scope = self._descendants(wf, start) | {start}
        kept = {nid: st for nid, st in states.items() if nid not in scope}
        preset = self._preset_outputs(kept)
        stale = self._stash_nodes(run_id, scope)

        rec = await self.execute_definition(
            wf, (view.get("inputs") or {}), start_node=start,
            preset_outputs=preset, session=view.get("session") or "new")
        rec.warn("redo",
                 f"定点重跑：从 {start} 起（作废 {', '.join(sorted(scope))}"
                 + (f"；作废旧产出 {len(stale)} 个" if stale else "")
                 + (f"；原因：{note}" if note else "") + "）", node=start)
        self._save_run_meta(rec)
        pass
        self.store.carry_gates(run_id, rec.id)
        self.store.carry_progress(run_id, rec.id)
        return rec

    @staticmethod
    def _descendants(wf: dict, start: str) -> set[str]:
        from .validate import ValidateMixin
        children: dict[str, list[str]] = {str(n["id"]): []
                                          for n in wf.get("nodes") or []}
        for src, dst in ValidateMixin._graph_edges(wf.get("nodes"), wf.get("edges")):
            children.setdefault(src, []).append(dst)
        pass
        from .nodes.human import parse_options
        for n in wf.get("nodes") or []:
            if n.get("type") != "human":
                continue
            for _label, target in parse_options(n.get("options")):
                if target:
                    children.setdefault(str(n["id"]), []).append(target)
        seen: set[str] = set()
        stack = list(children.get(start, []))
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(children.get(cur, []))
        return seen

    def _stash_nodes(self, run_id: str, node_ids: set[str]) -> list[str]:
        moved: list[str] = []
        for nid in node_ids:
            try:
                moved += self.store.stash_node(run_id, nid)
            except OSError:
                continue
        return moved

    pass

    def why(self, run_id: str, node: str = "", key: str = "",
            grep: str = "") -> dict:
        view = self.load_run(run_id)
        if not view:
            raise not_found(f"运行不存在: {run_id}")
        nodes = view.get("nodes") or {}
        if node:
            st = nodes.get(node)
            if not st:
                raise not_found(f"这次运行里没有节点: {node}")
            return {"query": "node", "node": node,
                    "reads": list(st.get("reads") or []),
                    "writes": list(st.get("writes") or []),
                    "status": st.get("status"),
                    "chars": _node_chars(st),
                    "ms": st.get("ms"),
                    "path": st.get("output_path") or "",
                    "preview": st.get("output_preview") or ""}
        if key:
            writers = [nid for nid, st in nodes.items()
                       if key in (st.get("writes") or [])]
            readers = [nid for nid, st in nodes.items()
                       if key in (st.get("reads") or [])]
            return {"query": "key", "key": key,
                    "writers": sorted(writers), "readers": sorted(readers)}
        if grep:
            hits = self._grep_nodes(view, grep)
            return {"query": "grep", "grep": grep, "hits": hits}
        return {"query": "overview", "workflow": view.get("workflow"),
                "status": view.get("status"),
                "nodes": [self._node_digest(nid, st)
                          for nid, st in nodes.items()]}

    @staticmethod
    def _node_digest(nid: str, st: dict) -> dict:
        chars = _node_chars(st)
        ok = wstat.is_ok(str(st.get("status") or ""))
        return {"node": nid, "status": st.get("status"),
                "chars": chars, "empty": bool(ok and chars == 0),
                "reads": list(st.get("reads") or []),
                "writes": list(st.get("writes") or []),
                "ms": st.get("ms"),
                "error": st.get("error") or ""}

    def _grep_nodes(self, view: dict, kw: str, limit: int = 2000) -> list[dict]:
        rid = str(view.get("id") or "")
        out: list[dict] = []
        for nid, st in (view.get("nodes") or {}).items():
            text = str(st.get("output") or "")[:limit]
            if not text and st.get("output_path"):
                try:
                    data = self.store.read_node(rid, nid, 0, limit)
                    text = str(data.get("content") or "")
                except Exception:
                    text = ""
            if kw and kw in text:
                idx = text.find(kw)
                out.append({"node": nid, "chars": _node_chars(st),
                            "at": idx,
                            "snippet": text[max(0, idx - 60): idx + 140]})
        return out

    def load_run(self, run_id: str) -> Optional[dict]:
        rec = self.runs.get(run_id)
        return rec.to_dict() if rec else self.store.load_run(run_id)

    async def wait_run(self, run_id: str, timeout: float = 0) -> dict:
        rec = self.runs.get(run_id)
        task = self._tasks.get(run_id)
        if rec is None:
            pass
            view = self.store.load_run(run_id)
            if not view:
                raise not_found(f"运行不存在: {run_id}")
            return {"run_id": run_id, "workflow": view.get("workflow", ""),
                    "status": view.get("status"), "error": view.get("error") or "",
                    "nodes": [], "warnings": view.get("warnings") or [],
                    "final": view.get("final") or "",
                    "final_chars": view.get("final_chars") or 0,
                    "final_preview": view.get("final_preview") or "",
                    "pending_human": view.get("pending_human"),
                    "timed_out": False}
        if task is not None and not task.done():
            pass
            await asyncio.wait({task}, timeout=timeout)
        out = rec.brief(timed_out=task is not None and not task.done())
        if rec.status == "done":
            out["final"] = rec.final or ""
        return out

    async def resume(self, run_id: str, start_node: str = "") -> RunRecord:
        view = self.load_run(run_id)
        if not view:
            raise not_found(f"运行不存在: {run_id}")
        wf = self.get(view.get("workflow", ""))
        if not wf:
            raise not_found(f"工作流不存在: {view.get('workflow')}")
        states = view.get("nodes") or {}
        preset = self._preset_outputs(states)
        if not start_node:
            start_node = self._first_undone(wf, states)
        rec = await self.execute_definition(
            wf, (view.get("inputs") or {}), start_node=start_node,
            preset_outputs=preset, session=view.get("session") or "new")
        pass
        pass
        self.store.carry_gates(run_id, rec.id)
        pass
        self.store.carry_progress(run_id, rec.id)
        return rec

    @staticmethod
    def _preset_outputs(states: dict) -> dict[str, str]:
        out: dict[str, str] = {}
        for nid, st in states.items():
            if st.get("status") != wstat.DONE:
                continue
            path = st.get("output_path") or ""
            text = ""
            if path and Path(path).is_file():
                try:
                    text = Path(path).read_text("utf-8", errors="replace")
                except OSError:
                    text = ""
            out[nid] = text if path else (st.get("output") or "")
        return out

    @staticmethod
    def _first_undone(wf: dict, states: dict) -> str:
        for n in wf["nodes"]:
            if (states.get(str(n["id"])) or {}).get("status") != wstat.DONE:
                return str(n["id"])
        return str(wf["nodes"][0]["id"])

    def list_runs(self, workflow: str = "", limit: int = 50) -> list[dict]:
        merged: dict[str, dict] = {}
        for item in self.store.list_runs(workflow=workflow, limit=10_000):
            merged[item["id"]] = item
        for rid, rec in self.runs.items():
            if workflow and rec.wf_name != workflow:
                continue
            merged[rid] = {
                "id": rid, "workflow": rec.wf_name, "status": rec.status,
                "started": rec.started, "finished": rec.finished,
                "error": rec.error, "final_preview": rec.final[:200],
                "nodes": {nid: {"status": st.get("status"),
                                "ms": st.get("ms"),
                                "error": st.get("error", "")}
                          for nid, st in rec.node_states.items()},
            }
        items = sorted(merged.values(), key=lambda x: x.get("started") or 0,
                       reverse=True)
        return items[:max(1, int(limit))]

    def _save_run_meta(self, rec: RunRecord) -> None:
        data = rec.to_meta()
        try:
            self.store.write_meta(rec.id, data)
        except OSError:
            return
        try:
            from ..event.bus import HUB
            HUB.publish("workflow.run", {
                "project": str(self.workspace or ""),
                "workflow": str(data.get("workflow") or ""),
                "run": rec.id,
                "status": str(data.get("status") or ""),
            })
        except Exception:
            logger.debug("publish workflow.run 失败: %s", rec.id, exc_info=True)

    @staticmethod
    def eval_expr(expr: str, vars: dict) -> tuple[bool, str]:
        values = {**{k: v for k, v in vars["inputs"].items()},
                  **vars["outputs"]}
        return evaluate(expr, _expr_env(), values)

    @staticmethod
    def eval_value(expr: str, vars: dict) -> tuple[object, str]:
        values = {**{k: v for k, v in vars["inputs"].items()},
                  **vars["outputs"]}
        return evaluate_value(expr, _expr_env(), values)
