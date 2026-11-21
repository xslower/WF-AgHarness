from __future__ import annotations

from typing import Awaitable, Callable

from .loop_utils import BUDGET_WRAPUP_PROMPT
from .stream import normalize_outcome


async def budget_wrapup(self, messages: list[dict], spec: str,
                        session_id: str, emit: Callable[[dict], Awaitable[None]],
                        stop_check=None, abort_event=None,
                        turn_prompt: int = 0, turn_completion: int = 0,
                        turn_cost: float = 0.0) -> tuple[dict, dict]:
    wrap_messages = messages + [
        {"role": "user", "content": BUDGET_WRAPUP_PROMPT}]
    try:
        w = normalize_outcome(await self._consume_stream(
            wrap_messages, [], spec, session_id, emit,
            stop_check=stop_check, abort_event=abort_event))
        w_text, w_reason, w_usage = w.text, w.reason, w.usage
    except Exception:
        w_text, w_reason, w_usage = "", "", None
    if w_usage:
        wu = (int(w_usage.get("prompt_tokens") or 0),
              int(w_usage.get("completion_tokens") or 0))
        turn_prompt += wu[0]
        turn_completion += wu[1]
        turn_cost += self._cost_of(self._last_model_spec(), wu[0], wu[1])
    meta = self._turn_meta(turn_prompt, turn_completion, turn_cost)
    body = (w_text or w_reason or "").strip()
    if not body:
        from .limits import SUB_ROUND_LIMIT
        body = (f"[阶段总结] 已用尽工具轮额度（上限 {SUB_ROUND_LIMIT}），"
                "收尾请求未产出文本。已完成的工具结果与 路径:行号 都在本会话历史里；"
                "父级可用 subagent(action=extend, id=..., task=新目标) 追加额度，"
                "会复用已落盘的完整历史、不用重做；也可自己接力。")
    await self._emit_done(emit, self._last_model_spec(), w_usage, meta=meta)
    pass
    msg = {"role": "assistant", "content": body,
           "model": self._last_model_spec(), "usage": w_usage,
           "reasoning": w_reason, "turn_complete": True, **meta}
    return msg, w_usage or {}
