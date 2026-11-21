from __future__ import annotations

import asyncio
import json
import logging
from typing import Awaitable, Callable

from ..util.jsonx import err
from ..agent.profile import AgentProfile
from ..store import layout
from ..tools import ToolContext


logger = logging.getLogger("harness.tool_context")








pass
_WF_ICON = {"running": "▶", "done": "✓", "failed": "✗",
            "cancelled": "⏹", "retrying": "↻", "skipped": "·"}
_WF_LABEL = {"running": "运行中", "done": "完成", "failed": "失败",
             "cancelled": "已中止", "retrying": "重试中", "skipped": "跳过"}


pass
pass
RUN_ID_TAG = "[run_id:{rid}]"


def run_id_marker(rid: str) -> str:
    return "\n\n" + RUN_ID_TAG.format(rid=rid)


class ContextMixin:
    pass
    pass
    pass
    @staticmethod
    def wf_inputs(user_input: str) -> dict:
        raw = "" if user_input is None else str(user_input)
        text = raw.strip()
        if text.startswith("{") and text.endswith("}"):
            try:
                data = json.loads(text)
            except ValueError:
                data = None
            if isinstance(data, dict) and data:
                out = {str(k): (v if isinstance(v, (dict, list)) else str(v))
                       for k, v in data.items()}
                out.setdefault("input", raw)
                return out
        return {"input": raw}

    def _build_context(self, cwd: str,
                       emit: Callable[[dict], Awaitable[None]],
                       depth: int, session_id: str,
                       profile: AgentProfile) -> ToolContext:
        pass
        pass
        project = ""
        try:
            if self.sessions is not None and session_id:
                project = self.sessions.session_project(session_id) or ""
        except Exception:
            logger.debug("读取会话所属项目失败: %s", session_id, exc_info=True)
        ctx = ToolContext(cwd, project=project)
        pass
        try:
            from ..project.scope import set_current_project
            set_current_project(project or cwd)
        except Exception:
            logger.debug("set_current_project 失败: %s", cwd, exc_info=True)
        ctx.session_id = session_id
        pass
        pass
        rt = self.session_rt.get(session_id) if self.session_rt is not None else None
        if rt is not None:
            if rt.bg_jobs is None:
                from .bg_jobs import JobRegistry
                rt.bg_jobs = JobRegistry()
            ctx.bg_jobs = rt.bg_jobs
        ctx.mcp = self.mcp
        pass
        pass
        ctx.registry = self.registry
        ctx.snapshot = lambda msg, paths=None: _snapshot(cwd, msg, paths)
        ctx.emit_stream = emit
        pass
        pass
        ctx.images_channel = True
        if self.envs is not None:
            ctx.env_rewrite = self.envs.rewrite
        if self.wf_engine is not None and depth == 0:
            pass
            pass
            pass
            ctx.workflow_start = lambda n, i, h, s="", p="", d=False, c=cwd, e=emit: \
                self._wf_start(n, i, c, h, s, p, emit=e)
            ctx.workflow_wait = lambda rid, t, detail=False: self.wait_wf(rid, t, detail)
            pass
            ctx.wf_edit = self._engine_for(cwd)
        if self.memory is not None and cwd:
         if self.memory is not None and cwd:
            ctx.save_memory = self._save_memory(cwd)
            ctx.memory_search = self._memory_search(cwd)
            ctx.memory_replace = self._memory_replace(cwd)
            ctx.memory_delete = self._memory_delete(cwd)
        if self.sessions is not None and session_id:
            ctx.history_get = self._history_get(session_id)
        pass
        pass
        from .subagent_access import SubAgentAccess
        pass
        ctx.subagents = SubAgentAccess(self.sessions, self.session_rt, cwd)
        ctx.subagent_parent = session_id or f"agent:{id(self)}"
        ctx.subagent_project = cwd
        pass
        pass
        ctx.extend = lambda sid, parent, rounds=0, task="", background=True: \
            self._extend_subagent(sid, parent, emit, depth, rounds,
                                  task=task, cwd=cwd, background=background)
        pass
        pass
        if depth < profile.max_spawn_depth:
            def _spawn_fn(task, c, t=None, bg=True, profile_prompt="", rounds=0,
                          hints=None, _outer=profile, _emit=emit, _depth=depth,
                          _sid=session_id):
                return self._spawn(
                    task, c, _emit, _depth, t, profile_prompt=profile_prompt,
                    parent_profile=_outer, background=bg,
                    parent_session=_sid, rounds=rounds, hints=hints)
            ctx.spawn = _spawn_fn
        return ctx

    def _engine_for(self, cwd: str):
        if self.wf_engine is None:
            return None
        router = getattr(self.wf_engine, "engine_for", None)
        if router is None:
            return self.wf_engine
        try:
            return router(cwd)
        except Exception:
            return None

    @staticmethod
    @staticmethod
    def _declaration_of(eng, name: str) -> dict | None:
        from ..chat.turns import declaration_of
        return declaration_of(eng, name)

    def _human_mode_for(self, name: str, cwd: str, asked: str) -> str:
        asked = (asked or "").strip().lower()
        if asked and asked != "deny":
            return asked
        declared = ""
        try:
            eng = self._engine_for(cwd)
            wf = self._declaration_of(eng, name)
            if wf:
                declared = str(wf.get("defaultHuman") or "").strip().lower()
        except Exception:
            declared = ""
        return declared or "deny"

    async def _wf_start(self, name: str, user_input: str, cwd: str,
                        human: str = "deny", start_node: str = "",
                        parallel: str = "", *, emit: Callable | None = None) -> str:
        inputs = self.wf_inputs(user_input)
        mode = self._human_mode_for(name, cwd, human)
        on_event = self._wf_progress(emit, name, cwd)
        try:
            rec = await self.wf_engine.start_for(
                name, inputs, cwd, human_mode=mode, start_node=start_node,
                parallel_mode=parallel, on_event=on_event)
        except Exception as e:
            return json.dumps({"error": f"工作流启动失败: {e}"},
                              ensure_ascii=False)
        return json.dumps({**rec.brief(), "ok": True,
                           "note": "已在后台运行。用 workflow(action=wait, id=<run_id>) 等结果，"
                                   "不要重复发起同一个工作流"},
                          ensure_ascii=False) + run_id_marker(rec.id)

    async def wait_wf(self, run_id: str, timeout: float,
                      detail: bool = False) -> str:
        try:
            data = await self.wf_engine.wait_for(run_id, timeout)
        except Exception as e:
            return json.dumps({"error": f"等待运行失败: {e}"},
                              ensure_ascii=False)
        if data.get("status") == "failed":
            return json.dumps({"error": f"工作流失败: {data.get('error') or ''}",
                               "run_id": run_id, "nodes": data.get("nodes") or []},
                              ensure_ascii=False)
        if data.get("status") != "done":
            return json.dumps(data, ensure_ascii=False)
        warns = data.get("warnings") or []
        if detail:
            return json.dumps({**data, "ok": True}, ensure_ascii=False)
        text = data.get("final") or "(工作流无输出)"
        if warns:
            pass
            text += "\n\n⚠ 告警（不影响完成，但可能少了东西）：\n" + "\n".join(
                f"  - {(w.get('node') or '')} {w.get('message')}" for w in warns)
        return text + run_id_marker(run_id)


    def _wf_progress(self, emit, workflow: str, project: str):
        if emit is None:
            return None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return None
        seen: dict[str, str] = {}
        state = {"started": False}

        def push(ev: dict) -> None:
            async def _go() -> None:
                try:
                    await emit(ev)
                except Exception:
                    logger.debug("推送工作流进度失败: %s", workflow, exc_info=True)
            try:
                loop.create_task(_go())
            except RuntimeError:
                pass

        def on_event(rec) -> None:
            if not state["started"]:
                state["started"] = True
                push({"type": "workflow_run", "phase": "start",
                      "run_id": rec.id, "workflow": workflow,
                      "project": project, "status": rec.status})
            lines = []
            for nid, st in (rec.node_states or {}).items():
                cur = str(st.get("status") or "")
                if seen.get(nid) == cur:
                    continue
                seen[nid] = cur
                line = f"{_WF_ICON.get(cur, '·')} {nid} · {_WF_LABEL.get(cur, cur)}"
                if cur in ("done", "failed") and st.get("ms"):
                    line += f"（{st['ms']}ms）"
                if st.get("error"):
                    line += f" · {str(st['error'])[:200]}"
                lines.append(line + "\n")
            if lines:
                push({"type": "tool_output", "name": "workflow",
                      "text": "".join(lines)})

        return on_event

    def _save_memory(self, cwd: str):
        async def _save(content: str) -> str:
            if not layout.project_agent_dir(cwd).is_dir():
                return json.dumps({"error": "当前目录不是项目，无法保存记忆"},
                                  ensure_ascii=False)
            from ..tools.builtin.memory import gate_memory
            keep, _ = await gate_memory(self.gateway, content)
            if not keep:
                return json.dumps({"rejected": "把关拒绝：临时性/时效性内容不入库"},
                                  ensure_ascii=False)
            try:
                self.memory.add(cwd, content)
                return json.dumps({"ok": True, "note": "已记入当前项目记忆"},
                                  ensure_ascii=False)
            except Exception as e:
                return err(str(e))
        return _save

    def _history_get(self, sid: str):
        async def _get(ids: list[int]) -> str:
            try:
                sess = self.sessions.get(sid)
                if sess is None:
                    return json.dumps({"error": "会话不存在"}, ensure_ascii=False)
                msgs = sess.get("messages", [])
                out = []
                for i in ids:
                    if not (0 <= i < len(msgs)):
                        out.append(f"=== msg#{i} === 不存在（会话共 {len(msgs)} 条，编号 0..{len(msgs)-1}）")
                        continue
                    m = msgs[i]
                    c = m.get("content")
                    if isinstance(c, list):
                        c = " ".join(p.get("text", "") for p in c if isinstance(p, dict))
                    body = str(c or "")[:4000]
                    if m.get("tool_calls"):
                        body += "\n[该消息发起的调用] " + json.dumps(
                            m["tool_calls"], ensure_ascii=False)[:1500]
                    out.append(f"=== msg#{i} ({m.get('role')}) ===\n{body}")
                return "\n\n".join(out) or "(无内容)"
            except Exception as e:
                return err(str(e))
        return _get

    def _memory_search(self, cwd: str):
        async def _search(query: str, limit: int = 10) -> str:
            try:
                hits = self.memory.search(cwd, query, limit)
                if not hits:
                    return json.dumps({"results": [], "note": "无相关记忆"},
                                      ensure_ascii=False)
                pass
                return json.dumps(
                    {"results": [{"id": e["id"], "content": e["content"]}
                                 for e in hits]},
                    ensure_ascii=False)
            except Exception as e:
                return err(str(e))
        return _search

    def _memory_replace(self, cwd: str):
        async def _replace(mid: str, content: str) -> str:
            if not layout.project_agent_dir(cwd).is_dir():
                return json.dumps({"error": "当前目录不是项目，无法修改记忆"},
                                  ensure_ascii=False)
            from ..tools.builtin.memory import gate_memory
            keep, _ = await gate_memory(self.gateway, content)
            if not keep:
                return json.dumps({"rejected": "把关拒绝：临时性/时效性内容不入库"},
                                  ensure_ascii=False)
            try:
                e = self.memory.replace(cwd, mid, content)
                if e is None:
                    return json.dumps(
                        {"error": f"当前项目没有 id={mid} 的记忆（父级继承的不可改）"},
                        ensure_ascii=False)
                return json.dumps({"ok": True, "id": e["id"],
                                   "note": "已覆盖该条记忆"},
                                  ensure_ascii=False)
            except Exception as e:
                return err(str(e))
        return _replace

    def _memory_delete(self, cwd: str):
        async def _delete(mid: str) -> str:
            if not layout.project_agent_dir(cwd).is_dir():
                return json.dumps({"error": "当前目录不是项目，无法删除记忆"},
                                  ensure_ascii=False)
            try:
                if not self.memory.delete(cwd, mid):
                    return json.dumps(
                        {"error": f"当前项目没有 id={mid} 的记忆（父级继承的不可删）"},
                        ensure_ascii=False)
                return json.dumps({"ok": True, "note": "已删除该条记忆"},
                                  ensure_ascii=False)
            except Exception as e:
                return err(str(e))
        return _delete


def _snapshot(cwd: str, message: str,
              paths: "list[str] | None" = None) -> None:
    from ..checkpoints import snapshot as git_snapshot
    git_snapshot(cwd, f"agent:{message}", paths)
