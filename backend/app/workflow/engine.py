from __future__ import annotations

import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import Callable, Optional

import app.util.status as wstat
from .errors import WorkflowError, not_found
from .nodes.registry import NodeRegistry
from ..store.runs import ProjectPaths, RunStore
from .constants import CONTROL_TYPES, MAX_STEPS, MAX_SUBFLOW_DEPTH, default_nodes, pick_output
pass
from .executor import ExecutionMixin
from .dag import DagMixin
from .human import HumanGate
from .record import RunRecord
from .run_records import RunRecordsMixin
from .store import StoreMixin
from .validate import ValidateMixin

logger = logging.getLogger("harness.workflow.engine")



class WorkflowEngine(StoreMixin, ValidateMixin, ExecutionMixin, DagMixin, RunRecordsMixin):

    def __init__(self, gateway=None, registry=None, agent_runner=None, mcp=None,
                 workspace: str = "", workflows_dir: Path | None = None,
                 nodes: NodeRegistry | None = None,
                 max_concurrency: int | Callable[[], int] | None = None,
                 global_dir: Path | None = None, sessions=None,
                 extra_dirs: list[Path] | None = None) -> None:
        self.gateway = gateway
        self.registry = registry
        self.agent_runner = agent_runner
        self.mcp = mcp
        self.workspace = workspace
        pass
        pass
        pass
        self.sessions = sessions

        pass
        pass
        self.nodes = nodes or default_nodes()
        pass
        self._max_concurrency = max_concurrency
        self.runs: dict[str, RunRecord] = {}
        pass
        pass
        pass
        pass
        self.human = HumanGate(run_dir=lambda rid: self.store.run_dir(rid))
        pass
        pass
        self._tasks: dict[str, asyncio.Task] = {}
        if workflows_dir:
            self.dir = Path(workflows_dir)
        else:
            pass
            from . import WORKFLOWS_DIR
            self.dir = Path(WORKFLOWS_DIR)
        self.dir.mkdir(parents=True, exist_ok=True)
        pass
        self.extra_dirs = [Path(d) for d in (extra_dirs or [])]
        pass
        pass
        self.global_dir = Path(global_dir) if global_dir else None
        if self.global_dir is not None and self.global_dir.resolve() == self.dir.resolve():
            self.global_dir = None
        self.paths = ProjectPaths.for_workspace(workspace).ensure()
        self.store = RunStore(workspace)
        self.artifacts_dir = self.paths.artifacts
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        pass
        self._sessions_by_run: dict[str, object] = {}

    def _llm_session(self, workflow: str, want: str = ""):
        if self.sessions is None:
            return None
        from .llm_session import LLMSession
        ls = LLMSession(self.sessions, self.workspace, workflow)
        ls.resolve(want)
        return ls

    def _bind_session(self, rec: RunRecord, workflow: str, want: str = "") -> None:
        if self.sessions is None:
            return
        ls = self._llm_session(workflow, want)
        active = next((r for r in self.runs.values()
                       if r.session == ls.sid and wstat.is_active(r.status)), None)
        if active is not None:
            if want and want != "new":
                pass
                raise WorkflowError(
                    f"会话 {want} 已有运行在进行中（{active.id}），等它结束再跑")
            pass
            ls = self._llm_session(workflow, "new")
            rec.warn("session-busy",
                     f"上次的会话仍在运行（{active.id}），本次已另开新会话", node="")
        rec.session = ls.sid
        self._sessions_by_run[rec.id] = ls

    pass

    def max_concurrency(self) -> int:
        raw = self._max_concurrency
        try:
            value = raw() if callable(raw) else raw
            return max(1, int(value if value is not None else 3))
        except (TypeError, ValueError):
            return 3

    def parallel_slots(self, node: dict, parallel_mode: str) -> int:
        if parallel_mode != "agent":
            return 1
        cap = self.max_concurrency()
        try:
            want = int(node.get("concurrency") or 0)
        except (TypeError, ValueError):
            want = 0
        return cap if want <= 0 else min(want, cap)

    def resolve_parallel_mode(self, wf: dict, requested: str | None) -> str:
        mode = str(requested or "").strip().lower()
        if mode in ("agent", "sequential"):
            return mode
        saved = str((wf or {}).get("parallel_mode") or "").strip().lower()
        return saved if saved in ("agent", "sequential") else "sequential"

    pass
    pass
    pass
    pass

    def preflight(self, wf: dict, inputs: dict | None = None,
                  human_mode: str = "ask",
                  preset_outputs: dict | None = None) -> list[str]:
        from .preflight import check_workflow
        return check_workflow(wf, inputs=inputs, nodes=self.nodes,
                              workspace=self.workspace,
                              resolve=self.resolve_workflow,
                              global_dir=self.global_dir,
                              human_mode=human_mode,
                              config=getattr(self.gateway, "config", None),
                              preset_outputs=preset_outputs)

    pass

    def start(self, wf_name: str, inputs: dict | None = None,
              on_event: Optional[Callable] = None,
              start_node: str = "", preset_outputs: dict | None = None,
              parallel_mode: str = "",
              human_mode: str = "ask", session: str = "") -> RunRecord:
        wf = self.get(wf_name)
        if not wf:
            raise not_found(f"工作流不存在: {wf_name}")
        return self.start_definition(
            wf, inputs, on_event, start_node=start_node,
            preset_outputs=preset_outputs, parallel_mode=parallel_mode,
            human_mode=human_mode, session=session)

    def start_definition(self, wf: dict, inputs: dict | None = None,
                         on_event: Optional[Callable] = None,
                         start_node: str = "",
                         preset_outputs: dict | None = None,
                         parallel_mode: str = "",
                         human_mode: str = "ask",
                         session: str = "") -> RunRecord:
        rec, mode = self._prepare_run(wf, inputs, human_mode, preset_outputs,
                                      parallel_mode, session, start_node)
        task = asyncio.get_running_loop().create_task(
            self._execute(wf, inputs or {}, rec, on_event,
                          start_node=start_node or None,
                          preset_outputs=preset_outputs,
                          parallel_mode=mode, human_mode=human_mode))
        self._tasks[rec.id] = task
        task.add_done_callback(lambda _t, r=rec.id: self._tasks.pop(r, None))
        return rec

    def _gate(self, wf: dict, inputs: dict | None, human_mode: str,
              preset_outputs: dict | None = None) -> list[str]:
        issues = self.preflight(wf, inputs=inputs, human_mode=human_mode,
                                preset_outputs=preset_outputs)
        pass
        from .preflight import is_warning
        blocking = [x for x in issues if not is_warning(x)]
        if blocking:
            raise WorkflowError(
                "启动前检查未通过（未执行任何节点）：\n  - " + "\n  - ".join(blocking))
        return [x for x in issues if is_warning(x)]

    def _prepare_run(self, wf: dict, inputs: dict | None, human_mode: str,
                     preset_outputs: dict | None, parallel_mode: str,
                     session: str | None, start_node: str = "",
                     wf_name: str = "") -> tuple[RunRecord, str]:
        self.validate(wf, self.nodes)
        ids = {str(n["id"]) for n in wf.get("nodes") or []}
        if start_node and start_node not in ids:
            raise WorkflowError(f"起始节点不存在: {start_node}")
        warnings = self._gate(wf, inputs, human_mode, preset_outputs)
        mode = self.resolve_parallel_mode(wf, parallel_mode)
        rec = RunRecord(uuid.uuid4().hex[:10],
                        wf_name or str(wf.get("name") or "_inline"),
                        self.workspace)
        pass
        for text in warnings:
            rec.warn("preflight", text)
        if session is not None:
            self._bind_session(rec, rec.wf_name, session)
        self.runs[rec.id] = rec
        self.store.prepare(rec.id, rec.wf_name)
        return rec, mode

    def cancel(self, run_id: str) -> dict:
        rec = self.runs.get(run_id)
        task = self._tasks.get(run_id)
        if rec is None and task is None:
            pass
            pass
            view = self.store.load_run(run_id)
            if view:
                st = str(view.get("status") or "")
                if wstat.is_active(st):
                    return self._cancel_stale(run_id, view)
                pass
                return {"ok": False, "reason": f"运行已结束（{st}）", "status": st}
            return {"ok": False, "reason": "运行不存在", "status": ""}

        if rec is not None and not wstat.is_active(rec.status):
            return {"ok": False, "reason": f"运行已结束（{rec.status}）",
                    "status": rec.status}
        if task is None:
            return {"ok": False,
                    "reason": "该运行不在本进程的后台任务里（同步运行无法从外部中止）",
                    "status": rec.status if rec else ""}
        if task.done():
            return {"ok": False, "reason": "运行已结束",
                    "status": rec.status if rec else ""}
        task.cancel()
        pass
        self.human.clear(run_id)
        if rec is not None:
            rec.status = "cancelled"
            rec.error = rec.error or "用户中止"
            rec.finished = rec.finished or time.time()
            rec.pending_human = None
            self._save_run_meta(rec)
        return {"ok": True, "reason": "", "status": "cancelled"}

    def _cancel_stale(self, run_id: str, view: dict) -> dict:
        nodes = view.get("nodes") or {}
        for st in nodes.values():
            if wstat.is_active(str(st.get("status") or "")):
                st["status"] = "cancelled"
                st["error"] = st.get("error") or "用户中止"
            pass
            st.pop("output", None)
        view.update({"status": "cancelled", "error": view.get("error") or "用户中止",
                     "finished": view.get("finished") or time.time()})
        view.pop("final", None)
        try:
            self.store.write_meta(run_id, view)
        except OSError:
            pass
        return {"ok": True, "reason": "", "status": "cancelled"}

    async def execute_definition(self, wf: dict, inputs: dict | None = None,
                                 start_node: str = "",
                                 preset_outputs: dict | None = None,
                                 parallel_mode: str = "",
                                 human_mode: str = "ask",
                                 session: str = "") -> RunRecord:
        rec, mode = self._prepare_run(wf, inputs, human_mode, preset_outputs,
                                      parallel_mode, session, start_node)
        await self._execute(wf, inputs or {}, rec, None,
                            start_node=start_node or None,
                            preset_outputs=preset_outputs,
                            parallel_mode=mode, human_mode=human_mode)
        return rec

    async def run_single(self, wf_name: str, node_id: str,
                         inputs: dict | None = None,
                         preset_outputs: dict | None = None) -> RunRecord:
        wf = self.get(wf_name)
        if not wf:
            raise not_found(f"工作流不存在: {wf_name}")
        pass
        pass
        self.validate_structure(wf)
        node = next((n for n in wf["nodes"] if n["id"] == node_id), None)
        if node is None:
            raise WorkflowError(f"节点不存在: {node_id}")
        spec = self.nodes.get(node.get("type"))
        if spec is None:
            raise WorkflowError(f"未知节点类型: {node.get('type')}")
        for key in spec.required:
            if not node.get(key):
                raise WorkflowError(f"{node.get('type')} 节点 {node_id} 缺少 {key}")
        import copy
        single = copy.deepcopy(node)
        for k in ("next", "true", "false", "body", "parallel_next"):
            single.pop(k, None)
        wf_single = {**wf, "nodes": [single], "edges": []}
        rec = RunRecord(uuid.uuid4().hex[:10], wf_name, self.workspace)
        self.runs[rec.id] = rec
        self.store.prepare(rec.id, wf_name)
        await self._execute(wf_single, inputs or {}, rec, None,
                            preset_outputs=preset_outputs)
        return rec

    async def execute_sync(self, wf_name: str, inputs: dict | None = None,
                           parallel_mode: str = "",
                           human_mode: str = "deny",
                           start_node: str = "",
                           session: str = "new",
                           on_event=None) -> RunRecord:
        wf = self.get(wf_name)
        if not wf and self.global_dir is not None:
            pass
            wf = self.resolve_workflow(wf_name)
        if not wf:
            raise not_found(f"工作流不存在: {wf_name}")
        rec, mode = self._prepare_run(wf, inputs, human_mode, None,
                                      parallel_mode, session, start_node,
                                      wf_name=wf_name)
        await self._execute(wf, inputs or {}, rec, on_event,
                            start_node=start_node or None,
                            parallel_mode=mode, human_mode=human_mode)
        return rec

    pass

    async def run_subflow(self, name: str, inputs: dict, parent: RunRecord,
                          node_id: str, human_mode: str = "ask",
                          output: str = "final") -> str:
        name = (name or "").strip()
        chain = list(parent.call_stack) + [parent.wf_name]
        if len(parent.call_stack) >= MAX_SUBFLOW_DEPTH:
            raise WorkflowError(
                f"workflow 节点 {node_id}: 子工作流嵌套超过 {MAX_SUBFLOW_DEPTH} 层"
                f"（调用链: {' → '.join(chain)}）")
        if name in parent.call_stack:
            raise WorkflowError(
                f"workflow 节点 {node_id}: 检测到循环调用「{name}」"
                f"（调用链: {' → '.join(chain)}）")
        wf = self.resolve_workflow(name)
        if not wf:
            raise WorkflowError(
                f"workflow 节点 {node_id}: 工作流不存在: {name}"
                f"（已在本项目与全局目录中查找）")
        self.validate(wf, self.nodes)

        rec = RunRecord(uuid.uuid4().hex[:10], name, self.workspace)
        rec.parent_run = parent.id
        rec.parent_node = node_id
        rec.call_stack = list(parent.call_stack) + [parent.wf_name]
        self.runs[rec.id] = rec
        self.store.prepare(rec.id, name)
        await self._execute(wf, inputs or {}, rec, None, human_mode=human_mode)
        if rec.status != wstat.DONE:
            raise WorkflowError(
                f"workflow 节点 {node_id}: 子工作流「{name}」{rec.status}"
                f"（运行 {rec.id}）: {rec.error or '无错误信息'}")
        return pick_output(rec, output)

