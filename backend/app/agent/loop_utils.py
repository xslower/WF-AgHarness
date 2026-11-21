from __future__ import annotations

import asyncio
import re
import time
from typing import Optional

from ..util.jsonx import parse_tool_args_report, scene_for_tool

pass
pass
PLAN_TEXT_RE = re.compile(r"(实施计划|执行计划|改动计划|修改计划|计划如下|方案如下)")

pass
pass
pass
BUDGET_WRAPUP_PROMPT = (
    "[工具轮额度已用尽] 本轮起你**不能再调用任何工具**，请立即基于上面的完整历史"
    "给出一份**阶段总结**（不要再试工具、不要只说「未完成」）：\n"
    "1. 已查明：把已经确认的事实、关键片段与 文件路径:行号 列出来；\n"
    "2. 已完成/未完成：任务拆成哪几块，哪些已经做完、哪些还差一步；\n"
    "3. 下一步建议：明确写出「接着读哪个文件的哪一段、或查哪个关键词」最可能出结果；\n"
    "4. 父级要你继续做，可用 subagent(action=extend, id=..., task=新目标) 追加额度，"
    "会复用本次已落盘的完整历史、不用重做；主 LLM 也可直接据此自己接力。\n"
    "按输出协议把这份总结放进唯一一个 ```json / ```text / ```md 围栏内。"
    "围栏内不要放过程复述、不要放整段工具输出。"
)


class RoundState:

    __slots__ = ("escalation", "plan_blocked", "notice_sent")

    def __init__(self) -> None:
        self.escalation: dict = {"files": set(), "escalated": False}
        self.plan_blocked = False
        self.notice_sent = False


def plan_age(snap: dict, now: float) -> float:
    try:
        return now - float(snap.get("savedAt") or 0)
    except (TypeError, ValueError):
        return 0.0


def turn_meta(prompt: int, completion: int, cost: float) -> dict:
    return {
        "ts": round(time.time(), 3),
        "usage_total": ({"prompt_tokens": prompt, "completion_tokens": completion}
                        if (prompt or completion) else None),
        "cost": round(cost, 6),
    }


def round_gap_note(stop_check, interject_check, control) -> Optional[str]:
    hard_stop = bool(stop_check and stop_check())
    interjected = bool(interject_check and interject_check())
    if control is not None and control.stop_requested:
        return "⏸ 已按父级要求中止子 Agent。"
    if interjected and not hard_stop:
        return "⏸ 收到插队消息，本轮已中止。"
    if hard_stop or interjected:
        return "⏸ 收到新消息，本轮已中止。"
    return None


pass
def parse_args(tc: dict) -> tuple[dict, str, str]:
    fn = tc.get("function") or {}
    return parse_tool_args_report(fn.get("arguments") or "",
                                  scene=scene_for_tool(fn.get("name")))


def budget_note(depth: int, left: int, total: int) -> str:
    if depth <= 0:
        return ""
    if left <= 0:
        return ("[工具轮额度] 已用尽（累计上限 %d）。接下来会禁止工具并要你给"
                "「阶段总结」：已查明的片段与 路径:行号、已完成/未完成、"
                "下一步读哪里最有希望出结果。别把额度耗在逐条试探上。" % total)
    if left == 1:
        return ("[工具轮额度] 只剩 1 次 / 累计上限 %d；这一批请把剩余独立操作"
                "合并完，用完即进入阶段总结（届时禁止工具）。" % total)
    return f"[工具轮额度] 剩 {max(0, left)} 次 / 累计上限 {total}；请合并操作，别把额度耗在逐条试探上。"


def aborted_tool_msg(tc: dict, messages: list[dict]) -> dict:
    msg = {"role": "tool", "tool_call_id": tc["id"],
           "content": "⏸ 用户中止，本次工具调用已放弃"}
    messages.append(msg)
    return msg


async def wait_tool_or_abort(task, abort_event) -> bool:
    waiter = asyncio.create_task(abort_event.wait())
    try:
        done, _pending = await asyncio.wait(
            {task, waiter}, return_when=asyncio.FIRST_COMPLETED)
    finally:
        waiter.cancel()
    return task in done


pass
def last_model_spec(self) -> str:
    return getattr(self.gateway, "last_spec", "") or ""


def cost_of(self, spec: str, prompt: int, completion: int) -> float:
    from ..provider.registry import ModelRegistry
    cfg = getattr(self.gateway, "config", None)
    price_in, price_out = ModelRegistry(cfg).unit_price(spec)
    return (prompt * price_in + completion * price_out) / 1_000_000


pass
async def emit_done(emit, model: str, usage, meta: dict | None = None,
                    interrupted: bool = False) -> None:
    payload: dict = {"type": "done", "model": model, "usage": usage}
    if meta:
        payload.update(meta)
    if interrupted:
        payload["interrupted"] = True
    await emit(payload)


async def close_turn(self, emit, content: str,
                     meta: dict | None = None,
                     notice: str | None = None) -> dict:
    if notice:
        await emit({"type": "notice", "text": notice})
    await self._emit_done(emit, "", None, interrupted=True)
    msg = {"role": "assistant", "content": content, "model": "",
           "usage": None, "interrupted": True}
    if meta:
        msg.update(meta)
    return msg
