from __future__ import annotations

import asyncio
import logging
import re
import time

logger = logging.getLogger("harness.workflow.executor")

import app.util.status as sstat
from .errors import WorkflowError
from .nodes.registry import NodeContext
from .constants import CONTROL_TYPES, DEFAULT_NODE_VISITS, HUMAN_MODES, MAX_STEPS, MAX_SUBFLOW_DEPTH, pick_output
from .vars import _log_json_error, substitute, substitute_expr

pass
pass
_TRUNC_RE = re.compile(r"\.\.\.\[截断[^\]]*?共\s*(\d+)\s*字符\]|"
                        r"\[\.\.\.截断：原始长度\s*(\d+)\s*字符\]")


def _truncated_chars(text: str) -> int:
    m = _TRUNC_RE.search(text or "")
    if not m:
        return 0
    return int(m.group(1) or m.group(2) or 0)


pass
pass
pass
EXEC_TIMEOUT_GRACE_SEC = 15


def _declared_reads(node: dict) -> list[str]:
    from .preflight import COMMENTABLE, VAR_RE, _iter_strings, _strip_comment_lines, _var_key

    out: set[str] = set()
    for key, text in _iter_strings({k: v for k, v in node.items()
                                    if k not in ("id", "type")}):
        target = (_strip_comment_lines(text)
                  if key.split(".")[-1] in COMMENTABLE else text)
        for m in VAR_RE.finditer(target.replace("$${", "\0")):
            raw = _var_key(m.group(1))
            if not raw or "\0" in raw:
                continue
            out.add(raw if raw.startswith("inputs.") else raw.split(".")[0])
    return sorted(out)


def _outer_timeout(node_type, timeout: float) -> float | None:
    if node_type == "human":
        return None
    if node_type in ("exec", "code") and timeout > 0:
        return timeout + EXEC_TIMEOUT_GRACE_SEC
    return timeout


def _subgraph_from(start_node: str, nodes: dict, parents: dict,
                   children: dict) -> tuple[dict, dict, dict]:
    allowed = {start_node}
    stack = [start_node]
    while stack:
        cur = stack.pop()
        for nxt in children.get(cur, []):
            if nxt not in allowed:
                allowed.add(nxt)
                stack.append(nxt)
    out_nodes = {k: v for k, v in nodes.items() if k in allowed}
    out_parents = {k: [p for p in v if p in allowed]
                   for k, v in parents.items() if k in allowed}
    out_children = {k: [c for c in v if c in allowed]
                    for k, v in children.items() if k in allowed}
    return out_nodes, out_parents, out_children


class ExecutionMixin:

    async def _execute(self, wf: dict, inputs: dict, rec: RunRecord,
                       on_event, start_node: str | None = None,
                       preset_outputs: dict | None = None,
                       parallel_mode: str = "sequential",
                       human_mode: str = "ask") -> None:
        vars = {"inputs": inputs, "outputs": dict(preset_outputs or {}),
                "output_paths": {},
                # 图上合法的名字（节点 id + inputs）：运行时区分“拼错了”与“还没跑到”。
                # 回边/前向引用（condition 判下游节点）是合法写法，不能报错。
                "_known": {str(n.get("id")) for n in wf.get("nodes") or []} | {"inputs"}}
        rec.inputs = dict(inputs or {})
        rec.parallel_mode = parallel_mode
        nodes = {n["id"]: n for n in wf["nodes"]}
        steps = [0]
        pass
        visits: dict[str, int] = {}
        try:
            use_dag = (self._is_parallel_graph(wf)
                       and not any(n.get("type") in CONTROL_TYPES
                                   for n in wf["nodes"]))
            if use_dag:
                await self._execute_dag(wf, vars, rec, on_event,
                                        start_node=start_node,
                                        parallel_mode=parallel_mode)
            else:
                await self._traverse(start_node or wf["nodes"][0]["id"], nodes, vars, rec,
                                     on_event, set(), steps, visits,
                                     human_mode=human_mode,
                                     parallel_mode=parallel_mode)
                rec.final = vars["outputs"].get(
                    "__final__",
                    next(reversed(list(vars["outputs"].values())), ""))
            rec.status = sstat.DONE
        except asyncio.CancelledError:
            pass
            rec.status = "cancelled"
            rec.error = rec.error or "用户中止"
            pass
            for st in rec.node_states.values():
                if sstat.is_active(st.get("status") or ""):
                    st["status"] = "cancelled"
                    st["error"] = st.get("error") or "用户中止"
            raise
        except WorkflowError as e:
            rec.status = sstat.FAILED
            rec.error = str(e)
        except Exception as e:
            rec.status = sstat.FAILED
            rec.error = f"{type(e).__name__}: {e}"
        finally:
            rec.finished = time.time()
            pass
            self.human.clear(rec.id)
            if rec.final:
                try:
                    self.store.write_final(rec.id, rec.final)
                except OSError:
                    pass
            self._save_run_meta(rec)
            pass
            self._sessions_by_run.pop(rec.id, None)
            pass
            pass
            if rec.session and self.sessions is not None:
                try:
                    pass
                    busy = {r.session for r in self.runs.values()
                            if r.id != rec.id and sstat.is_active(r.status)}
                    self._purge_empty_run_session(rec.session, keep=busy)
                except Exception:
                    logger.debug("回收空工作流会话失败", exc_info=True)
            if on_event:
                on_event(rec)

    def _purge_empty_run_session(self, sid: str, keep: set[str]) -> None:
        if sid in keep or sid in self.sessions.wf_node_parents():
            return
        self.sessions.delete(sid)

    def _gate_callbacks(self, rec: RunRecord):
        def _open_gate(node_id: str, title: str = "", ask: str = "",
                       show: str = "", options: list[str] | None = None):
            pass
            rec.pending_human = {"node_id": node_id, "title": title,
                                 "ask": ask, "show": show,
                                 "options": list(options or [])}
            self._save_run_meta(rec)
            return self.human.open(rec.id, node_id, title=title, ask=ask,
                                   show=show, options=options)

        def _close_gate(node_id: str) -> None:
            self.human.close(rec.id, node_id)
            rec.pending_human = None
            self._save_run_meta(rec)

        return _open_gate, _close_gate

    def _warn_suppressed_parallel(self, rec: RunRecord, node: dict | None,
                                  slots: int, parallel_mode: str) -> None:
        if not (node and node.get("type") == "map"
                and slots == 1 and parallel_mode != "agent"):
            return
        try:
            want = int(node.get("concurrency") or 0)
        except (TypeError, ValueError):
            want = 0
        if want <= 1:
            return
        rec.warn("parallel-suppressed",
                 "map 节点的并发数被运行模式压成串行"
                 f"（parallel_mode={parallel_mode}，节点写的是 {want}）。"
                 "要真并行请在运行时选「真并行」或传 parallel=agent",
                 node=str(node.get("id") or ""))

    def _node_context(self, rec: RunRecord, vars: dict,
                      traverse=None, human_mode: str = "ask",
                      parallel_mode: str = "sequential",
                      node: dict | None = None) -> NodeContext:
        _open_gate, _close_gate = self._gate_callbacks(rec)

        pass
        expr_error: dict = {}
        pass
        slots = self.parallel_slots(node or {}, parallel_mode)
        self._warn_suppressed_parallel(rec, node, slots, parallel_mode)

        def _eval_cond(expr: str, v: dict) -> bool:
            ok, err = self.eval_expr(substitute_expr(expr, v), v)
            if err:
                expr_error["error"] = err
            return ok

        def _eval_value(expr: str, v: dict):
            value, err = self.eval_value(substitute_expr(expr, v), v)
            if err:
                expr_error["error"] = err
            return value

        return NodeContext(
            workspace=self.workspace,
            gateway=self.gateway,
            tools=self.registry,
            mcp=self.mcp,
            agent_runner=self.agent_runner,
            run_id=rec.id,
            wf_name=rec.wf_name,
            artifacts_dir=self.artifacts_dir,
            log_json_error=_log_json_error,
            substitute=substitute,
            eval_expr=_eval_cond,
            traverse=traverse,
            # 产出登记：节点/节点内调的工具写了文件 → 归到 rec.files，日志面板右侧直接用
            report_file=rec.add_file,
            node_id=str(node.get("id") or "") if node else "",
            # 运行告警回收口：截断/ stderr / 并发被压等“静默降级”全归到这里，
            # 最后由 run 结果的 warnings 带到前端与 workflow 工具的返回值。
            run_warn=rec.warn,
            extras={"human_mode": human_mode, "human_open": _open_gate,
                    "human_wait": self.human.wait, "human_close": _close_gate,
                    "run_id": rec.id, "wf_name": rec.wf_name,
                    # 本次运行的会话（可能为 None）：LLM 节点用它回放/落库自己的对话。
                    # 与 human_open 等一样是引擎注入的回调式能力，节点不依赖引擎内部对象。
                    "llm_session": self._sessions_by_run.get(rec.id),
                    # map 可用并发数：由全局 parallel_mode 与 wfMaxConcurrency 共同决定，
                    # 节点不自己读配置（否则每个节点都要重复一遍同样逻辑）。
                    "parallel_mode": parallel_mode,
                    "parallel_slots": slots,
                    # 子工作流调用：节点只拿到回调，不依赖引擎内部对象
                    "run_subflow": lambda name, inputs, output, node_id:
                        self.run_subflow(name, inputs, rec, node_id,
                                          human_mode=human_mode, output=output),
                    # 求值错误的回收口（condition 节点读它把错误写进输出）
                    "expr_error": expr_error,
                    # map 项级进度：读写归引擎（RunStore 是唯一落盘出口），
                    # 节点只拿两个回调，不自己去拼路径。同 run 内失败重跑就靠它。
                    "progress_read": lambda nid: self.store.read_progress(rec.id, nid),
                    "progress_append": lambda nid, row:
                        self.store.append_progress(rec.id, nid, row),
                    # map.items 用：与 condition 同一套表达式（!raw / json() / yaml()）
                    "eval_value": _eval_value},
        )

    async def _run_node(self, node: dict, vars: dict, rec: RunRecord,
                        on_event, traverse=None,
                        human_mode: str = "ask",
                        parallel_mode: str = "sequential",
                        state_key: str | None = None) -> tuple[str, str | None]:
        cur = str(node["id"])
        key = state_key or cur
        node_type = node.get("type")
        spec = self.nodes.get(node_type)
        if spec is None:
            raise WorkflowError(f"未知节点类型: {node_type}")
        t0 = time.time()
        rec.node_states[key] = {"status": sstat.RUNNING, "output": "", "ms": 0}
        self._save_run_meta(rec)
        if on_event:
            on_event(rec)
        ctx = self._node_context(rec, vars, traverse, human_mode=human_mode,
                                 parallel_mode=parallel_mode, node=node)
        attempts, outer_timeout = self._resolve_retry_timeout(node)
        out, nxt = await self._run_with_retry(spec, node, ctx, vars, rec, on_event,
                                              key=key, t0=t0, attempts=attempts,
                                              outer_timeout=outer_timeout)
        self._record_success(node, vars, rec, on_event, ctx, key, cur, t0, out)
        pass
        pass
        return out, (nxt or None)

    def _resolve_retry_timeout(self, node: dict) -> tuple[int, float | None]:
        try:
            retry = max(0, int(node.get("retry") or 0))
            timeout = float(node.get("timeout") or 0)
        except (TypeError, ValueError):
            retry, timeout = 0, 0.0
        return retry + 1, _outer_timeout(node.get("type"), timeout)

    async def _run_with_retry(self, spec, node: dict, ctx, vars: dict, rec: RunRecord,
                              on_event, key: str, t0: float, attempts: int,
                              outer_timeout: float | None) -> tuple[str, str | None]:
        for attempt in range(attempts):
            try:
                coro = spec.run(node, ctx, vars)
                if outer_timeout is not None and outer_timeout > 0:
                    return await asyncio.wait_for(coro, timeout=outer_timeout)
                return await coro
            except Exception as e:
                if attempt + 1 >= attempts:
                    rec.node_states[key] = {
                        "status": sstat.FAILED, "output": "",
                        "ms": int((time.time() - t0) * 1000),
                        "error": f"{type(e).__name__}: {e}",
                        "attempts": attempts}
                    self._save_run_meta(rec)
                    raise
                rec.node_states[key] = {
                    "status": sstat.RETRYING,
                    "output": f"第 {attempt + 1} 次失败: {type(e).__name__}: {e}",
                    "ms": int((time.time() - t0) * 1000)}
                if on_event:
                    on_event(rec)

    def _record_success(self, node: dict, vars: dict, rec: RunRecord, on_event,
                        ctx, key: str, cur: str, t0: float, out: str) -> None:
        pass
        meta = self.store.write_node(rec.id, key, out)
        pass
        pass
        cut = _truncated_chars(out)
        state = {"status": sstat.DONE, "output": out,
                 "ms": int((time.time() - t0) * 1000), **meta}
        pass
        pass
        state["reads"] = _declared_reads(node)
        state["writes"] = [cur]
        if cut:
            state["truncated"] = True
            state["original_chars"] = cut
            ctx.warn(f"节点输出被截断（原 {cut} 字符，已落盘的是截断后的内容）",
                     code="truncated", node=cur)
        rec.node_states[key] = state
        vars["outputs"][cur] = out
        vars.setdefault("output_paths", {})[cur] = meta["output_path"]
        pass
        pass
        if node.get("type") != "condition":
            vars["outputs"]["prev"] = out
        self._save_run_meta(rec)
        if on_event:
            on_event(rec)

    async def _traverse(self, cur, nodes: dict, vars: dict, rec: RunRecord,
                        on_event, stop_ids: set, steps: list,
                        visits: dict | None = None,
                        human_mode: str = "ask",
                        parallel_mode: str = "sequential",
                        state_suffix: str = "") -> None:
        pass
        pass
        joined = (vars.setdefault("_joined", set()) if parallel_mode else set())
        visits = visits if visits is not None else {}
        while cur is not None and cur not in stop_ids:
            if steps[0] >= MAX_STEPS:
                raise WorkflowError(f"超过最大步数 {MAX_STEPS}")
            steps[0] += 1
            node = nodes[cur]
            visits[cur] = visits.get(cur, 0) + 1
            limit = int(node.get("maxVisits") or 0) or DEFAULT_NODE_VISITS
            if visits[cur] > limit:
                pass
                pass
                pass
                pass
                rec.warn("max-visits",
                         f"节点 {cur} 已进入 {visits[cur]} 次，达到上限 {limit}"
                         f"（含首轮），按正常结束处理。如果这是死循环，检查 condition 的"
                         f" true/false 是否指回上游、是否缺终止条件",
                         node=cur)
                nxt_stop = node.get("false") if node.get("type") == "condition" else None
                cur = nxt_stop or None
                continue

            async def _body(start, body_stop, local_vars=None, suffix="",
                            _nodes=nodes, _rec=rec, _steps=steps,
                            _mode=human_mode, _pmode=parallel_mode) -> None:
                await self._traverse(start, _nodes, local_vars or vars, _rec,
                                     on_event, set(body_stop), _steps, {},
                                     human_mode=_mode, parallel_mode=_pmode,
                                     state_suffix=suffix or state_suffix)

            pass
            pass
            pass
            pass
            if node.get("type") == "join" and cur in joined:
                cur = str(node.get("next") or "") or None
                continue

            _, nxt = await self._run_node(node, vars, rec, on_event, _body,
                                          human_mode=human_mode,
                                          parallel_mode=parallel_mode,
                                          state_key=(cur + state_suffix) if state_suffix else None)
            if node.get("type") == "join":
                joined.add(cur)
            pass
            branches = node.get("parallel_next") or []
            if branches:
                cur = await self._run_branches(
                    branches, nodes, vars, rec, on_event, steps, visits,
                    human_mode=human_mode, parallel_mode=parallel_mode,
                    state_suffix=state_suffix, joined=joined)
                continue
            cur = nxt
