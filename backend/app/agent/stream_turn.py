from __future__ import annotations

from typing import Awaitable, Callable, Optional

from ..agent.profile import AgentProfile
from ..chat.msgs import last_user_text
from ..tools import ToolContext
from .loop_utils import PLAN_TEXT_RE
from .plan import PlanState

__all__ = ["prepare_turn", "emit_request_debug", "finish_text_round",
           "tool_round", "drain_control", "drain_bg_jobs", "finish_plan_round"]

async def prepare_turn(self, messages: list[dict], cwd: str,
                       emit: Callable[[dict], Awaitable[None]], depth: int,
                       session_id: str, profile: AgentProfile,
                       project_context: str, plan_mode: str,
                       allowed_tools: Optional[list[str]],
                       stop_check=None, policy_mode: str = ""):
    from ..security.wiring import wire_policy
    pass
    self._escalation = {"files": set(), "escalated": False}
    pass
    self._plan_blocked = False
    self._plan_notice_sent = False
    ctx = self._build_context(cwd, emit, depth, session_id, profile)
    pass
    pass
    ctx.stop_check = stop_check
    wire_policy(ctx, cwd, emit, messages, self.policy, self.approvals,
                self.gateway, mode=policy_mode)
    system = await self._build_system(profile, messages, depth, emit,
                                      session_id, plan_mode)
    messages = self._apply_prompt_template(
        [{"role": "system", "content": system}] + messages)
    pass
    pass
    pass
    if project_context:
        messages = messages + [{"role": "system", "content": project_context}]
    pass
    return ctx, messages, self._build_schemas(profile, allowed_tools, cwd=cwd)

async def emit_request_debug(self, round_no: int, model: str,
                             messages: list[dict],
                             emit: Callable[[dict], Awaitable[None]]) -> None:
    await emit({"type": "debug", "debug": {
        "event": "request",
        "round": round_no,
        "model": model,
        "message_count": len(messages),
        "last_user_msg": last_user_text(messages)[:500],
    }})

async def finish_text_round(self, round_no: int, acc_text: str, acc_reason: str,
                            usage, turn_meta: dict,
                            emit: Callable[[dict], Awaitable[None]]) -> dict:
    plan_round = await self._finish_plan_round(acc_text, acc_reason, emit)
    model_used = self._last_model_spec()
    msg = {"role": "assistant", "content": acc_text or acc_reason or "(空回复)",
           "model": model_used, "usage": usage,
           "reasoning": acc_reason, **turn_meta}
    pass
    pass
    pass
    msg["turn_complete"] = not plan_round
    await emit({"type": "debug", "debug": {
        "event": "response",
        "round": round_no,
        "model": model_used,
        "usage": usage,
        "has_tool_calls": False,
        "text_preview": (acc_text or "")[:500],
    }})
    await self._emit_done(emit, model_used, usage, meta=turn_meta)
    return msg

async def tool_round(self, round_no: int, acc_text: str, acc_reason: str,
                     tool_calls: list[dict], usage, ctx: ToolContext,
                     messages: list[dict], depth: int,
                     emit: Callable[[dict], Awaitable[None]], boost,
                     abort_event=None, budget_left: int = 0,
                     budget_total: int = 0):
    messages.append({
        "role": "assistant",
        "content": acc_text or None,
        "tool_calls": tool_calls,
    })
    pass
    pass
    pass
    yield {"role": "assistant", "content": acc_text or None,
           "reasoning": acc_reason or None,
           "tool_calls": tool_calls}
    await emit({"type": "debug", "debug": {
        "event": "response",
        "round": round_no,
        "model": self._last_model_spec(),
        "usage": usage,
        "has_tool_calls": True,
        "tool_calls": [{"name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"][:300]}
                       for tc in tool_calls],
    }})
    async for tool_msg in self._execute_tools(
            tool_calls, ctx, messages, depth, emit,
            abort_event=abort_event, budget_left=budget_left,
            budget_total=budget_total):
        yield tool_msg
    pass
    pass
    pass
    if boost is not None and boost is getattr(ctx, "suggested_tools", None):
        ctx.suggested_tools = None

async def drain_control(self, control, messages: list[dict],
                        emit: Callable[[dict], Awaitable[None]]) -> Optional[str]:
    if control is None:
        return None
    for instruction in control.drain_instructions():
        messages.append({
            "role": "user",
            "_sys": "subagent",
            "content": f"[父级追加指令]\n{instruction}",
        })

        await emit({"type": "notice",
                    "text": "收到父级追加指令，将在下一轮生效"})
    if control.stop_requested:
        return "⏸ 已按父级要求中止子 Agent。"
    return None

async def drain_bg_jobs(self, session_id: str, messages: list[dict],
                        emit: Callable[[dict], Awaitable[None]]) -> list[dict]:
    added: list[dict] = []
    rt = self.session_rt.get(session_id) if self.session_rt is not None else None
    jobs = rt.bg_jobs if rt is not None else None
    done = jobs.drain_done(session_id) if jobs is not None else []
    for job in done:
        msg = {
            "role": "user",
            "content": job.result_text(),
            "_bg_job": job.job_id,
            "_sys": "bg_job",
        }

        messages.append(msg)
        added.append(msg)
        await emit({"type": "notice",
                    "text": f"后台命令 {job.job_id} 已结束（{job.status}"
                            + (f"/exit {job.exit}" if job.exit is not None else "")
                            + "），结果已随下一轮送回模型"})
    return added

async def finish_plan_round(self, text: str, reason: str,
                            emit: Callable[[dict], Awaitable[None]]) -> bool:
    if self.plan_ctrl.state != PlanState.planning:
        return False
    body = (text or reason or "").strip()
    if not getattr(self, "_plan_blocked", False) and not PLAN_TEXT_RE.search(body[:2000]):
        self.plan_ctrl.reset()
        return False
    self.plan_ctrl.on_plan_complete(body)
    await emit({"type": "plan_ready", "text": body})
    return True
