from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Awaitable, Callable, Optional

import app.util.status as st

logger = logging.getLogger("harness.agent_spawn")

from ..agent.profile import AgentProfile, SystemOverride
from ..provider.spec import QUEUE_SUMMARY
from .limits import (SUB_ROUND_CAP, SUB_ROUND_EXTEND, SUB_ROUND_LIMIT)
from .plan import PlanState
from .subagent_result import extract_result, for_parent
from .subagent_access import SubAgentAccess
from .subagents import SubAgentRecord


class SpawnMixin:
    async def _spawn(self, task: str, cwd: str,
                     emit: Callable[[dict], Awaitable[None]], depth: int,
                     tools: Optional[list[str]] = None,
                     parent_profile: AgentProfile | None = None,
                     background: bool = True,
                     parent_session: str = "",
                     profile_prompt: str = "",
                     rounds: int = 0,
                     hints: list[str] | None = None) -> str:
        wanted = (profile_prompt or "").strip()
        sub_profile, override = self._sub_profile(wanted, parent_profile)
        base_id = sub_profile.id
        pass
        pass
        pass
        pass
        pass
        if self.plan_ctrl.state in (PlanState.planning, PlanState.awaiting_approval):
            sub_profile = self._profile("researcher")
            base_id = sub_profile.id
            pass
            wanted = ""
            tools = list(sub_profile.allowed_tools) if sub_profile.allowed_tools else []
        parent = parent_session or f"agent:{id(self)}"
        child_sid = "sub_" + uuid.uuid4().hex[:12]
        rec = SubAgentRecord(
            id="sa_" + uuid.uuid4().hex[:12],
            parent_id=parent, project=cwd, task=task,
            child_session_id=child_sid)
        rec.ensure()
        rec.persist()
        pass
        if self.session_rt is not None:
            self.session_rt.get(child_sid).subagent = rec
        rec.rounds_limit = max(1, int(rounds or SUB_ROUND_LIMIT))
        rec.rounds_used = 0
        rec.persist()
        pass
        pass
        pass
        prefix = ""
        try:
            from .code_map import render_for_spawn
            prefix = render_for_spawn(cwd, list(hints or []), project=cwd)
        except Exception:
            logger.debug("spawn 代码地图生成失败，退化为纯 task", exc_info=True)

        rec.profile_prompt = wanted
        rec.profile_base = base_id
        rec.tools = list(tools) if tools else None
        rec.ensure()
        rec.persist()
        self._attach_runner(rec, cwd, emit, depth, task, prefix)
        if background:
            rec.task_handle = asyncio.create_task(rec.control.run_child())
            return json.dumps({
                "subagent_id": rec.id, "status": st.RUNNING,
                "rounds_limit": rec.rounds_limit,
                "message": "子 Agent 已在后台启动；可用 action=get 查询（含剩余轮数）、"
                           "message 追加指令、stop 中止、wait 取回结果。",
            }, ensure_ascii=False)
        await rec.control.run_child()
        return self._spawn_result(rec)

    def _sub_profile(self, wanted: str,
                     parent_profile: AgentProfile | None,
                     base_id: str = "") -> tuple[AgentProfile, "SystemOverride | None"]:
        text = (wanted or "").strip()
        base_id = base_id or (parent_profile.subagent_profile if parent_profile
                              else None)
        if not text:
            return self._profile(base_id), None
        getter = getattr(self.profiles, "get", None)
        registered = getter(text) if getter else None
        if registered is not None:
            return registered, None
        return self._profile(base_id), SystemOverride(mode="replace", text=text)

    def _attach_runner(self, rec, cwd: str,
                       emit: Callable[[dict], Awaitable[None]], depth: int,
                       task: str, prefix: str = "") -> None:
        sub_profile, override = self._sub_profile(
            rec.profile_prompt, None, base_id=rec.profile_base)
        tools = rec.tools

        async def run_child(messages: Optional[list[dict]] = None,
                            fresh: bool = True) -> None:
            notes: list[str] = []
            result_text = ""

            async def sub_emit(ev: dict) -> None:
                rec.append_event(ev)
                if ev.get("type") in ("notice", "error"):
                    notes.append(ev.get("text", ""))
                await emit({"type": "subagent_event", "subagent_id": rec.id,
                            "event": ev})

            rec.status = st.RUNNING
            rec.paused = False
            rec.persist()
            try:
                if fresh:
                    await emit({"type": "subagent_start", "subagent_id": rec.id,
                                "parent_id": rec.parent_id, "task": task})
                pass
                pass
                if messages is not None:
                    history = messages
                else:
                    first = (prefix + "\n\n【任务】\n" + task) if prefix else task
                    history = [{"role": "user", "content": first}]
                async for msg in self.run(
                    history, cwd, sub_emit,
                    spec=QUEUE_SUMMARY, depth=depth + 1,
                    allowed_tools=tools or None,
                    profile_id=sub_profile.id,
                    system_override=override,
                    session_id=rec.child_session_id,
                    control=rec.control,
                ):
                    rec.append_message(msg)
                    if (msg.get("role") == "assistant" and msg.get("content")
                            and not msg["content"].startswith("[工具轮额度用尽]")):
                        result_text = msg["content"]
                pass
                rec.paused = False
                pass
                rec.paused = False
                conclusion, _fmt, protocol = extract_result(result_text)
                out = conclusion or (
                    f"[阶段总结] 已用 {rec.rounds_used} 次工具轮、本轮收尾。"
                    "已完成的工具结果与 路径:行号 都在本会话历史里；父级可用 "
                    "subagent(action=extend, id=...) 基于历史追加任务继续跑。")
                if notes and not st.is_ok(rec.status):
                    out += "\n[子Agent运行备注]\n" + "\n".join(notes[-3:])
                rec.finish(st.DONE, out, raw=result_text, protocol=protocol)
                await emit({"type": "subagent_done", "subagent_id": rec.id,
                            "status": rec.status, "result_path": rec.result_path,
                            "result_chars": len(rec.result),
                            "rounds_used": rec.rounds_used})
            except asyncio.CancelledError:
                rec.finish(st.STOPPED, rec.result, "子 Agent 已中止")
                await emit({"type": "subagent_done", "subagent_id": rec.id,
                            "status": rec.status, "result_path": rec.result_path})
            except Exception as e:
                rec.finish(st.FAILED, rec.result, f"{type(e).__name__}: {e}")
                await emit({"type": "subagent_done", "subagent_id": rec.id,
                            "status": rec.status, "result_path": rec.result_path,
                            "error": rec.error})

        rec.control.run_child = run_child

    @staticmethod
    def _spawn_result(rec) -> str:
        if rec.status == st.DONE:
            pass
            return for_parent(rec.result, rec.result_path)
        return json.dumps({"error": rec.error or rec.status,
                           "subagent_id": rec.id}, ensure_ascii=False)

    async def _extend_subagent(self, sid: str, parent: str,
                               emit: Callable[[dict], Awaitable[None]],
                               depth: int, rounds: int = 0,
                               task: str = "", cwd: str = "",
                               background: bool = True) -> str:
        pass
        pass
        pass
        project = cwd
        if not project and parent and self.sessions is not None:
            try:
                project = self.sessions.session_project(parent) or ""
            except Exception:
                project = ""
        rec = SubAgentAccess(self.sessions, self.session_rt, project).get(sid, parent)
        if rec is None:
            return json.dumps({"error": f"子 Agent 不存在: {sid}"}, ensure_ascii=False)
        pass
        pass
        if st.is_terminal(rec.status) and rec.status != st.DONE:
            return json.dumps({
                "error": f"子 Agent 当前状态 {rec.status}，无法续跑",
                "subagent_id": sid}, ensure_ascii=False)
        if rec.rounds_limit >= SUB_ROUND_CAP:
            return json.dumps({
                "error": f"已达累计硬顶 {SUB_ROUND_CAP} 轮，请拆分子任务或让用户介入",
                "subagent_id": sid, "rounds_limit": rec.rounds_limit,
            }, ensure_ascii=False)
        add = max(1, int(rounds or SUB_ROUND_EXTEND))
        rec.rounds_limit = min(SUB_ROUND_CAP, rec.rounds_limit + add)
        rec.paused = False
        rec.status = st.RUNNING

        pass
        pass
        pass
        history = [m for m in (rec.messages or [])
                   if isinstance(m, dict) and m.get("role") != "system"
                   and not str(m.get("content") or "").startswith("[阶段总结]")]
        pass
        pass
        pending = rec.drain_instructions()
        extra = [x for x in ([*pending, task.strip()] if task.strip() else pending) if x]
        if extra:
            history.append({"role": "user",
                            "content": "【追加任务】\n" + "\n".join(extra)})
        if not history:
            history.append({"role": "user", "content": task or rec.task})

        pass
        if rec.from_disk:
            pass
            pass
            pass
            if rec.legacy_params:
                safe = self._profile("researcher")
                rec.profile_prompt = rec.profile_prompt or "researcher"
                rec.profile_base = rec.profile_base or "researcher"
                rec.tools = list(safe.allowed_tools or ())
                rec.legacy_params = False
            rec.from_disk = False
            rec.paused_messages = []
            rec.ensure()
            if self.session_rt is not None and rec.child_session_id:
                self.session_rt.get(rec.child_session_id).subagent = rec
            pass
            pass
            self._attach_runner(rec, cwd or rec.project, emit, depth, rec.task)
        runner = getattr(rec.control, "run_child", None)
        if runner is None:
            return json.dumps({"error": "无法续跑：运行体已不存在且无法重建",
                               "subagent_id": sid}, ensure_ascii=False)
        rec.persist()
        await emit({"type": "subagent_extend", "subagent_id": sid,
                    "rounds_limit": rec.rounds_limit,
                    "history_messages": len(history),
                    "background": bool(background)})
        if background:
            pass
            pass
            rec.task_handle = asyncio.create_task(
                runner(messages=history, fresh=False))
            return json.dumps({
                "subagent_id": rec.id, "status": st.RUNNING,
                "background": True,
                "rounds_limit": rec.rounds_limit,
                "history_messages": len(history),
                "message": "已在后台基于历史续跑；用 action=wait 取回结果、"
                           "get 看进度、stop 中止。不要重开新子任务。",
            }, ensure_ascii=False)
        await runner(messages=history, fresh=False)
        return self._spawn_result(rec)
