from __future__ import annotations

from pathlib import Path

from .nodes.registry import NodeRegistry
from .engine import WorkflowEngine
from .errors import not_found


class WorkflowRouter:

    def __init__(self, gateway=None, registry=None, agent_runner=None, mcp=None,
                 global_dir=None, nodes: NodeRegistry | None = None,
                 max_concurrency=None, sessions=None, installs=None) -> None:
        self.deps = dict(gateway=gateway, registry=registry,
                         agent_runner=agent_runner, mcp=mcp, nodes=nodes,
                         max_concurrency=max_concurrency, sessions=sessions)
        self.global_dir = Path(global_dir) if global_dir else _workflows_dir()
        self.installs = installs
        self._cache: dict = {}

    def invalidate(self) -> None:
        self._cache.clear()

    def engine_for(self, project: str) -> WorkflowEngine:
        key = project or "__global__"
        eng = self._cache.get(key)
        if eng is None:
            if project:
                from ..project.manager import MARKER
                from ..plugins.workflow_roots import workflow_dirs
                pdir = Path(project) / MARKER / "workflows"
                pass
                extra = workflow_dirs(self.installs, project) if self.installs else []
                pass
                pkg_wf = Path(project) / "workflows"
                if pkg_wf.is_dir():
                    pdir = pkg_wf
                eng = WorkflowEngine(workspace=project, workflows_dir=pdir,
                                     global_dir=self.global_dir, extra_dirs=extra,
                                     **self.deps)
            else:
                eng = WorkflowEngine(workspace=project, workflows_dir=self.global_dir,
                                     **self.deps)
            self._cache[key] = eng
        return eng

    async def run_for(self, name: str, inputs: dict, project: str,
                      human_mode: str = "deny", start_node: str = "",
                      parallel_mode: str = "", session: str = "new",
                      on_event=None):
        pass
        eng = self.engine_for(project)
        try:
            return await eng.execute_sync(
                name, inputs, human_mode=human_mode, start_node=start_node,
                parallel_mode=parallel_mode, session=session,
                on_event=on_event)
        except TypeError:
            pass
            pass
            return await eng.execute_sync(
                name, inputs, human_mode=human_mode, start_node=start_node,
                parallel_mode=parallel_mode, session=session)

    def find_run(self, run_id: str) -> WorkflowEngine | None:
        if not run_id:
            return None
        for eng in self._cache.values():
            if run_id in eng.runs:
                return eng
        return None

    async def start_for(self, name: str, inputs: dict, project: str,
                        human_mode: str = "deny", start_node: str = "",
                        parallel_mode: str = "", session: str = "new",
                        on_event=None):
        eng = self.engine_for(project)
        wf = eng.get(name) or eng.resolve_workflow(name)
        if not wf:
            raise not_found(f"工作流不存在: {name}")
        pass
        pass
        return eng.start_definition(
            wf, inputs, on_event, start_node=start_node,
            parallel_mode=parallel_mode, human_mode=human_mode, session=session)

    async def wait_for(self, run_id: str, timeout: float) -> dict:
        eng = self.find_run(run_id)
        if eng is None:
            raise not_found(f"运行不存在: {run_id}")
        return await eng.wait_run(run_id, timeout)

    def pending_humans(self) -> list[dict]:
        out: list[dict] = []
        for key, eng in self._cache.items():
            try:
                gates = eng.human.list_pending()
            except Exception:
                continue
            for g in gates:
                rec = eng.runs.get(g.get("run_id") or "")
                wf_name = rec.wf_name if rec else ""
                pass
                pass
                pass
                root = self._root_wf_name(eng, rec)
                out.append({
                    "project": eng.workspace,
                    "workflow": root or wf_name,
                    "sub_workflow": wf_name if root and root != wf_name else "",
                    "run": g.get("run_id") or "",
                    "node": g.get("node_id") or "",
                    "title": g.get("title") or "",
                    "ask": g.get("ask") or "",
                    "options": list(g.get("options") or []),
                    "created": g.get("created") or 0,
                    "scope": "workflow",
                })
        return out

    @staticmethod
    def _root_wf_name(eng, rec) -> str:
        seen = set()
        cur = rec
        name = rec.wf_name if rec is not None else ""
        for _ in range(8):
            if cur is None or not getattr(cur, "parent_run", ""):
                break
            if cur.id in seen:
                break
            seen.add(cur.id)
            cur = eng.runs.get(cur.parent_run)
            if cur is not None and cur.wf_name:
                name = cur.wf_name
        return name


def _workflows_dir() -> Path:
    from . import WORKFLOWS_DIR
    return Path(WORKFLOWS_DIR)
