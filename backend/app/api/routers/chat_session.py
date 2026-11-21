from __future__ import annotations

import asyncio
import logging

from fastapi import HTTPException

import app.event.attention as attention
from ...agent.plan import decide_plan, modify_note, try_parse_intent
from ...chat.session_runtime import SessionRuntime
from .chat_input import normalize_input, resume_message
from .chat_mode import resolve_cwd, resolve_spec, resolve_plan_mode
from .chat_turn_exec import execute_turn, schedule_suggestions
from ...chat.turns import MAX_QUEUE, apply_queue_action, queue_payload, run_workflow
from ...chat.compaction_policy import maybe_compact

log = logging.getLogger("harness.chat_ws")


class SessionTurn:

    def __init__(self, c, s: dict, sid: str, rt: SessionRuntime, emit) -> None:
        self.c = c
        self.s = s
        self.sid = sid
        self.rt = rt
        self.emit = emit

    pass
    async def emit_queue(self) -> None:
        await self.emit({"type": "queue", "max": MAX_QUEUE,
                         "items": queue_payload(self.rt.queue)})

    async def handle_queue_action(self, req: dict) -> None:
        action = str(req.get("action") or "")
        qid = str(req.get("id") or "")
        new_items, notice = apply_queue_action(self.rt.queue, action, qid,
                                               self.rt.running)
        if new_items is not self.rt.queue:
            self.rt.queue = new_items
            await self.emit_queue()
        if notice:
            await self.emit({"type": "notice", "text": notice})

    pass
    async def run_turn(self, req: dict, qid: str = "", from_queue: bool = False,
                       resume: bool = False, resume_note: str = "") -> None:
        pass
        if req.get("_cancel_plan"):
            await self.emit({"type": "plan_cancelled", "text": "计划已取消"})
            await self.emit({"type": "done", "model": "", "usage": None})
            return
        pass
        pass
        pass
        if req.get("_plan_approved_nl"):
            await self.emit({"type": "plan_approved", "text": "计划已确认，开始执行..."})
        note_from_nl = req.get("_resume_note")
        if note_from_nl is not None:
            resume, resume_note = True, str(note_from_nl)

        await self._announce_turn_start(req, qid, from_queue, resume)
        self._refresh_session()
        cwd = resolve_cwd(req, self.s, self.c)
        try:
            spec = self._resolve_spec(req)
        except HTTPException as e:
            pass
            await self.emit({"type": "error", "text": f"模型不可用：{e.detail}"})
            await self.emit({"type": "done", "model": "", "usage": None})
            return
        raw_content = await self._append_user_message(req, resume, resume_note,
                                                      spec=spec)
        project_context = self._project_context(cwd)
        pass
        wf_name = req.get("workflow") or ""
        if wf_name:
            await run_workflow(self.c, self.s, wf_name, raw_content, spec, self.emit)
        else:
            await self._execute(cwd, spec, project_context,
                                req, from_queue, resume)
        pass
        pass
        pass
        await self._compact(spec)

    async def _announce_turn_start(self, req: dict, qid: str,
                                   from_queue: bool, resume: bool = False) -> None:
        c, sid = self.c, self.sid
        await self.emit({"type": "turn_start", "id": qid, "from_queue": from_queue,
                         "resume": resume, "content": str(req.get("content") or "")})
        pass
        pass
        attention.notify(sid, "turn-start")

    def _refresh_session(self) -> None:
        c, s, sid = self.c, self.s, self.sid
        try:
            fresh = c.sessions.get(sid)
            if not fresh:
                return
            keep_usage = s.get("last_usage")
            s.clear()
            s.update(fresh)
            if keep_usage:
                s["last_usage"] = keep_usage
        except Exception:
            log.warning("刷新会话失败，沿用连接持有的旧数据: %s", sid, exc_info=True)

    def _resolve_spec(self, req: dict) -> str:
        spec = resolve_spec(req, self.c)
        log.info("模型：%s", spec or "(自动/父队列)")
        return spec

    async def _append_user_message(self, req: dict, resume: bool,
                                   resume_note: str, spec: str = "") -> str:
        c, s = self.c, self.s
        norm = await normalize_input(req, gateway=c.gateway,
                                     history=s.get("messages"), spec=spec)
        if resume:
            pass
            s["messages"].append(resume_message(resume_note))
        else:
            s["messages"].append({"role": "user", "content": norm.model_content})
        raw_content = norm.raw_text
        pass
        if s.get("title") in ("新任务", "", None) and raw_content.strip():
            s["title"] = raw_content.strip().splitlines()[0][:30]
        pass
        pass
        await c.sessions.save_async(s)
        return raw_content

    def _project_context(self, cwd: str) -> str:
        s = self.s
        project = s.get("project") or cwd
        try:
            mem_ctx = (self.c.memory.context_for(project)
                       if s.get("project") else "")
        except Exception:
            log.warning("读取项目记忆失败: %s", s.get("project"), exc_info=True)
            mem_ctx = ""
        head = (f"[项目目录]\n{project}\n"
                "文件类工具的**相对路径都锚在这个目录**（如 backend/app/x.py 即 "
                f"{project}/backend/app/x.py）；要看当前项目目录就用它，"
                "不要靠猜父目录或找 .agent 标记。")
        if cwd and cwd != project:
            head += f"\n[额外工作目录]\n{cwd}"
        return head + (f"\n\n{mem_ctx}" if mem_ctx else "")

    async def _compact(self, spec: str) -> None:
        try:
            await maybe_compact(self.c, self.s, spec, self.emit)
        except Exception:
            log.warning("上下文压缩失败，本轮按未压缩继续", exc_info=True)

    async def _execute(self, cwd: str, spec: str,
                       project_context: str, req: dict, from_queue: bool,
                       resume: bool) -> None:
        c, s, sid, rt, emit = self.c, self.s, self.sid, self.rt, self.emit
        pass
        plan_mode = resolve_plan_mode(sess=s, sid=sid, c=c, req=req,
                                      from_queue=from_queue, resume=resume)
        pass
        pass
        policy_mode = str(req.get("policy") or "").strip()
        pass
        pass
        system_override = self._bot_system_override()
        pass
        await execute_turn(c=c, s=s, sid=sid, cwd=cwd, emit=emit, rt=rt,
                           spec=spec, plan_mode=plan_mode,
                           project_context=project_context,
                           policy_mode=policy_mode,
                           system_override=system_override)
        pass
        schedule_suggestions(c=c, s=s, sid=sid, emit=emit)

    def _bot_system_override(self):
        s = self.s
        if str(s.get("kind") or "") != "bot":
            return None
        pid = str(s.get("origin") or "").strip()
        if not pid:
            return None
        try:
            from ...plugins import bot_prompt
            from ...agent.profile import SystemOverride

            got = bot_prompt.current(self.c.installs, pid,
                                    s.get("project") or "")
        except Exception:
            log.warning("读取 bot 提示词失败，按系统默认跑: %s", pid, exc_info=True)
            return None
        if not got:
            return None
        return SystemOverride(mode=got.get("mode") or "append",
                              text=got.get("text") or "")

    async def drive(self, req: dict, qid: str, from_queue: bool,
                    resume: bool = False, note: str = "") -> None:
        rt = self.rt
        while True:
            ok = True
            nxt = None
            try:
                await self.run_turn(req, qid=qid, from_queue=from_queue,
                                    resume=resume, resume_note=note)
            except BaseException:
                pass
                ok = False
                raise
            finally:
                async with rt.turn_lock:
                    rt.end_turn()
                    if ok and rt.queue:
                        nxt = rt.queue.pop(0)
                        rt.begin_turn()
            if nxt is None:
                return
            await self.emit_queue()
            await self.emit({"type": "notice", "text": "▶ 发送排队消息"})
            req, qid, from_queue = nxt["req"], nxt["id"], True
            resume, note = False, ""

    async def resume(self, req: dict, note: str) -> None:
        async with self.rt.turn_lock:
            if self.rt.running or not self.rt.claim_turn():
                pass
                return
        await self.drive(req, "", False, resume=True, note=note)

    async def handle(self, req: dict) -> None:
        rt = self.rt
        qid = str(req.get("qid") or "")
        queued = full = False
        async with rt.turn_lock:
            if rt.running:
                if len(rt.queue) >= MAX_QUEUE:
                    full = True
                else:
                    rt.enqueue(req, qid)
                    queued = True
            else:
                rt.claim_turn()
        if full:
            pass
            await self.emit({"type": "queue_full", "max": MAX_QUEUE,
                             "text": f"队列已满（{MAX_QUEUE} 条）：先删掉或撤回一条，"
                                     f"把内容合并到后面统一发送"})
            return
        if queued:
            pass
            await self.emit_queue()
            return
        await self.drive(req, qid, False)

    async def handle_plan_decision(self, req: dict) -> None:
        rt, sid, c, emit = self.rt, self.sid, self.c, self.emit
        pass
        plan = c.plan_of(sid)
        pass
        pass
        pass
        log.info("计划决策 sid=%s decision=%s 当前状态=%s running=%s",
                 sid, req.get("decision", ""),
                 plan.state.value if plan is not None else "(无)", rt.running)
        if plan is None:
            await emit({"type": "notice", "text": "当前会话不支持计划模式"})
            return
        pass
        pass
        pass
        pass
        if not plan.awaiting_approval:
            log.info("计划决策去重 sid=%s decision=%s 已处于 %s，丢弃重复帧",
                     sid, req.get("decision", ""), plan.state.value)
            return
        etype, text, note = decide_plan(
            plan, req.get("decision", ""), str(req.get("feedback") or "").strip())
        await emit({"type": etype, "text": text})
        if etype == "plan_cancelled":
            pass
            pass
            pass
            if not rt.running:
                await emit({"type": "done"})
            return
        if note is None:
            return
        if rt.running:
            pass
            if etype == "plan_approved":
                await emit({"type": "notice",
                            "text": "当前仍在输出，稍后自动执行已确认的计划"})
            return
        self.spawn(self.resume(req, note), "计划续跑")

    pass
    def spawn(self, coro, why: str = "turn") -> asyncio.Task:
        task = asyncio.create_task(coro)
        self.rt.task = task

        def _done(t: asyncio.Task) -> None:
            if t.cancelled():
                return
            exc = t.exception()
            if exc is None:
                return
            log.error("会话 %s 的%s执行异常：%r", self.sid, why, exc, exc_info=exc)
            if self.rt.emit is not None:
                asyncio.create_task(self._apologize(exc))

        task.add_done_callback(_done)
        return task

    async def _apologize(self, exc: BaseException) -> None:
        self.rt.end_turn()
        await self.emit({"type": "error", "text": f"{type(exc).__name__}: {exc}"})
        await self.emit({"type": "done", "model": "", "usage": None})

    pass
    def interpret_plan_intent(self, req: dict) -> dict:
        content = str(req.get("content") or "")
        if not content.strip():
            return req
        if req.get("plan") is False:
            return req
        pass
        if req.get("attachments") or req.get("images") or req.get("audio"):
            return req
        c = self.c
        plan = c.plan_of(self.sid)
        if plan is None:
            return req
        intent = try_parse_intent(content, plan.state)
        if intent is None:
            return req
        log.info("计划决策 sid=%s decision=%s 来源=自然语言 当前状态=%s",
                 self.sid, intent, plan.state.value)
        if intent == "approve":
            plan.approve()
            pass
            pass
            pass
            return {**req, "content": "", "plan": False, "workflow": "",
                    "_resume_note": "", "_plan_approved_nl": True}
        if intent == "cancel":
            plan.cancel()
            return {**req, "content": "", "plan": False, "workflow": "",
                    "_cancel_plan": True}
        pass
        plan.modify(content)
        return {**req, "content": "", "workflow": "",
                "plan": True,
                "_resume_note": modify_note(content)}
