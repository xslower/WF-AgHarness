from __future__ import annotations

import asyncio

from .errors import WorkflowError
from .record import RunRecord


class DagMixin:

    def _local_vars(self, vars: dict, node_id: str,
                    parents: dict[str, list[str]]) -> dict:
        local = {
            "inputs": vars.get("inputs", {}),
            "outputs": dict(vars.get("outputs", {})),
            "output_paths": dict(vars.get("output_paths", {})),
            "_known": vars.get("_known") or set(),
        }
        parent_ids = parents.get(node_id, [])
        if len(parent_ids) == 1:
            prev = local["outputs"].get(parent_ids[0], "")
        elif parent_ids:
            prev = "\n\n---\n\n".join(
                str(local["outputs"].get(p, "")) for p in parent_ids)
        else:
            prev = local["outputs"].get("prev", "")
        local["outputs"]["prev"] = prev
        return local

    async def _execute_dag(self, wf: dict, vars: dict, rec: RunRecord,
                           on_event, start_node: str | None = None,
                           parallel_mode: str = "sequential") -> None:
        from .executor import _subgraph_from

        mode = parallel_mode if parallel_mode in ("agent", "sequential") else "sequential"
        nodes = {str(n["id"]): n for n in wf["nodes"]}
        _, parents, children = self._topology(wf["nodes"], wf.get("edges"))
        if start_node:
            nodes, parents, children = _subgraph_from(
                start_node, nodes, parents, children)

        async def run_one(nid: str) -> None:
            pass
            pass
            local = self._local_vars(vars, nid, parents)
            await self._run_node(nodes[nid], local, rec, on_event)
            vars["outputs"].update(local["outputs"])
            vars.setdefault("output_paths", {}).update(local.get("output_paths", {}))
            vars["outputs"]["prev"] = local["outputs"].get("prev", "")

        await self._drain_dag(nodes, parents, run_one, rec, mode)
        self._finalize_sinks(wf, vars, children, rec)

    async def _drain_dag(self, nodes: dict, parents: dict, run_one, rec: RunRecord,
                         mode: str) -> None:
        remaining = set(nodes)
        done: set[str] = set()
        running: dict[str, asyncio.Task] = {}

        def _launch(ready: list[str]) -> None:
            for nid in ready:
                remaining.discard(nid)
                running[nid] = asyncio.create_task(run_one(nid))

        try:
            while remaining or running:
                ready = [nid for nid in nodes if nid in remaining
                         and all(p in done for p in parents.get(nid, []))]
                if not ready and not running:
                    raise WorkflowError("并行图无法继续：存在未满足的上游节点")
                _launch(ready[:1] if mode == "sequential" else ready)
                if not running:
                    continue
                finished, _ = await asyncio.wait(
                    running.values(), return_when=asyncio.FIRST_COMPLETED)
                for task in finished:
                    nid = self._settle_task(task, running)
                    done.add(nid)
                    self._save_run_meta(rec)
        finally:
            pass
            pass
            self._cancel_running(running)

    def _settle_task(self, task: asyncio.Task, running: dict[str, asyncio.Task]) -> str:
        nid = next(k for k, v in running.items() if v is task)
        running.pop(nid, None)
        if task.cancelled():
            raise WorkflowError(f"并行分支被取消: {nid}")
        err = task.exception()
        if err:
            self._cancel_running(running)
            raise err
        return nid

    def _finalize_sinks(self, wf: dict, vars: dict, children: dict,
                        rec: RunRecord) -> None:
        sink_ids = [str(n["id"]) for n in wf["nodes"]
                    if not children.get(str(n["id"]))]
        finals = [str(vars["outputs"].get(i, "")) for i in sink_ids
                  if vars["outputs"].get(i)]
        rec.final = vars["outputs"].get("__final__") or "\n\n---\n\n".join(finals)

    def _cancel_running(self, running: dict[str, asyncio.Task]) -> None:
        for task in running.values():
            if not task.done():
                task.cancel()

    async def _run_branches(self, branches: list, nodes: dict, vars: dict,
                            rec: RunRecord, on_event, steps: list, visits: dict,
                            human_mode: str, parallel_mode: str,
                            state_suffix: str, joined: set) -> str | None:
        targets = [str(b) for b in branches if b]
        stops = _join_ids(nodes)
        locals_: list[dict] = []

        async def _one(start: str, local: dict) -> None:
            await self._traverse(start, nodes, local, rec, on_event, stops,
                                 steps, visits, human_mode=human_mode,
                                 parallel_mode=parallel_mode,
                                 state_suffix=state_suffix)

        async def _branch(start: str) -> None:
            local = {"inputs": vars.get("inputs", {}),
                     "outputs": dict(vars.get("outputs", {})),
                     "output_paths": dict(vars.get("output_paths") or {}),
                     "_known": vars.get("_known") or set(),
                     "_joined": joined}
            locals_.append(local)
            await _one(start, local)

        pass
        pass
        if parallel_mode == "agent" and len(targets) > 1:
            await asyncio.gather(*[_branch(t) for t in targets])
        else:
            for t in targets:
                await _branch(t)

        for local in locals_:
            vars["outputs"].update(local["outputs"])
            vars.setdefault("output_paths", {}).update(local.get("output_paths", {}))

        pass
        for jid in stops:
            if jid in joined:
                return jid
        return None


def _join_ids(nodes: dict) -> set[str]:
    return {str(nid) for nid, n in nodes.items()
            if str(n.get("type") or "") == "join"}
