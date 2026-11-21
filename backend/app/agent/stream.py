from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Optional

from ..provider.errors import EmptyResponseError, StreamFrameError
from ..provider.gateway import ToolCallAcc
from ..util.jsonx import fix_stats
from .profile import with_system
from .stream_outcome import StreamOutcome, normalize_outcome
from .stream_tools import execute_one, execute_tools
from .stream_turn import (
    drain_bg_jobs, drain_control, emit_request_debug, finish_plan_round,
    finish_text_round, prepare_turn, tool_round,
)

__all__ = ["StreamOutcome", "normalize_outcome", "run_stream",
           "prepare_turn", "emit_request_debug", "finish_text_round",
           "tool_round", "drain_control", "drain_bg_jobs", "consume_stream",
           "execute_tools", "execute_one", "finish_plan_round"]

async def run_stream(self, messages: list[dict], cwd: str,
                     emit: Callable[[dict], Awaitable[None]], spec: str = "",
                     depth: int = 0, stop_check=None,
                     session_id: str = "", project_context: str = "",
                     allowed_tools: Optional[list[str]] = None,
                     profile_id: str = "", control=None,
                     interject_check=None, plan_mode: str = "",
                     abort_event=None, policy_mode: str = "",
                     system_override=None):
    profile = with_system(self._profile(profile_id), system_override)
    spec = spec or profile.spec
    ctx, messages, base_schemas = await self._prepare_turn(
        messages, cwd, emit, depth, session_id, profile,
        project_context, plan_mode, allowed_tools, stop_check,
        policy_mode=policy_mode)
    pass
    pass
    turn_prompt = turn_completion = 0
    turn_cost = 0.0
    pass
    pass
    budget = getattr(control, "record", None) if depth > 0 else None
    max_rounds = self._max_rounds(
        profile, depth, round_budget=budget.rounds_left if budget else 0)
    pass
    pass
    pass
    corrupt_tries = 0
    for _round in range(max_rounds):
        stop_note = await self._drain_control(control, messages, emit)
        if stop_note is not None:
            pass
            yield await self._close_turn(emit, stop_note, notice=stop_note)
            return
        pass
        pass
        for _bg_msg in await self._drain_bg_jobs(session_id, messages, emit):
            yield _bg_msg
        pass
        pass
        boost = getattr(ctx, "suggested_tools", None)
        await self._emit_request_debug(_round, spec, messages, emit)
        res = normalize_outcome(await self._consume_stream(
            messages, boost if boost else base_schemas, spec,
            session_id, emit, stop_check=stop_check, abort_event=abort_event))
        acc_text, acc_reason, tool_calls, usage = res.text, res.reason, res.calls, res.usage
        if usage:
            used = (int(usage.get("prompt_tokens") or 0),
                    int(usage.get("completion_tokens") or 0))
            turn_prompt += used[0]
            turn_completion += used[1]
            turn_cost += self._cost_of(self._last_model_spec(), used[0], used[1])
        turn_meta = self._turn_meta(turn_prompt, turn_completion, turn_cost)
        if res.status == "aborted" or (stop_check and stop_check()):
            pass
            pass
            pass
            note = "⏸ 已中止当前回复。"
            yield await self._close_turn(
                emit, (acc_text + "\n\n" + note) if acc_text else note, turn_meta)
            return
        if res.status == "empty":
            pass
            pass
            why = res.error or "上游返回空响应"
            await emit({"type": "error", "text":
                        f"本轮没有产出：{why}（未切换模型，可原样重发）"})
            yield await self._close_turn(
                emit,
                "⛔ 本轮没有产出：模型返回了空响应（既无正文、也无工具调用），"
                f"原因：{why}。已保留原样、未切换模型；直接说「继续」可原样重发。",
                turn_meta)
            return
        if res.status == "corrupt" and not tool_calls:
            pass
            pass
            pass
            corrupt_tries += 1
            if corrupt_tries <= 1:
                _note = {
                    "role": "user",
                    "_sys": "tool_frame_corrupt",
                    "content": (
                        "[系统] 你上一条回复里的**工具调用没能传过来**："
                        f"{res.error or '帧损坏'}\n"
                        "这次调用已被丢弃、没有执行，也没有任何副作用。"
                        "请重新发起这次调用，并把参数写短一些 —— 大段文本请先用"
                        "文件写入工具落盘，再在参数里引用路径，不要塞进 arguments。"
                    ),
                }
                messages.append(_note)
                await emit({"type": "notice", "text":
                            "⚠ 工具调用参数在传输中损坏，已把原因回喂给同一模型重发"
                            "（未切换模型）"})
                yield _note
                continue
            await emit({"type": "error", "text":
                        f"工具调用连续两次损坏，本轮已停止：{res.error or '帧损坏'}"})
            yield await self._close_turn(
                emit,
                "⛔ 工具调用参数连续两次在传输中损坏，本轮已停止（未切换模型）。"
                f"最后一次原因：{res.error or '帧损坏'}",
                turn_meta)
            return
        if not tool_calls:
            yield await self._finish_text_round(
                _round, acc_text, acc_reason, usage, turn_meta, emit)
            return
        if budget is not None:
            budget.rounds_used += 1
            _left = budget.rounds_left
            _total = budget.rounds_limit
        else:
            _left = _total = 0
        async for item in self._tool_round(
                _round, acc_text, acc_reason, tool_calls, usage, ctx,
                messages, depth, emit, boost, abort_event=abort_event,
                budget_left=_left, budget_total=_total):
            yield item
        pass
        gap_note = self._round_gap_note(stop_check, interject_check, control)
        if gap_note is not None:
            yield await self._close_turn(emit, gap_note, turn_meta, gap_note)
            return
        pass
        pass
    if budget is not None and budget.rounds_used >= budget.rounds_limit:
        from .budget_wrapup import budget_wrapup
        msg, _usage = await budget_wrapup(
            self, messages, spec, session_id, emit,
            stop_check=stop_check, abort_event=abort_event,
            turn_prompt=turn_prompt, turn_completion=turn_completion,
            turn_cost=turn_cost)
        yield msg
        return
    _meta = self._turn_meta(turn_prompt, turn_completion, turn_cost)
    pass
    await self._emit_done(emit, self._last_model_spec(), None, meta=_meta)
    yield {"role": "assistant",
           "content": f"已达单轮最大工具调用轮数（{max_rounds}），本轮强制停止。"
                      "任务没做完就直接说「继续」，或在设置里调大「单轮工具轮数上限」。",
           "turn_complete": True, **_meta}

async def consume_stream(self, messages: list[dict], tools: list[dict],
                         spec: str, session_id: str,
                         emit: Callable[[dict], Awaitable[None]],
                         stop_check=None, abort_event=None) -> StreamOutcome:
    acc_text = ""
    acc_reason = ""
    tool_acc = ToolCallAcc()
    usage = None
    aborted = False
    saw_end = False
    corrupt: Optional[StreamFrameError] = None
    blank: Optional[EmptyResponseError] = None
    agen = self.gateway.chat_stream(
        messages, tools=tools, spec=spec, session_id=session_id,
    ).__aiter__()
    while True:
        if stop_check and stop_check():
            aborted = True
            break
        chunk = None
        if abort_event is not None:
            pass
            next_task = asyncio.ensure_future(agen.__anext__())
            abort_task = asyncio.ensure_future(abort_event.wait())
            try:
                done, _pending = await asyncio.wait(
                    {next_task, abort_task}, return_when=asyncio.FIRST_COMPLETED)
            finally:
                abort_task.cancel()
            if next_task not in done:
                pass
                aborted = True
                next_task.cancel()
                try:
                    await next_task
                except (asyncio.CancelledError, StopAsyncIteration, Exception):
                    pass
                break
            try:
                chunk = next_task.result()
            except StopAsyncIteration:
                break
            except StreamFrameError as e:
                corrupt = e
                break
            except EmptyResponseError as e:
                blank = e
                break
        else:
            try:
                chunk = await agen.__anext__()
            except StopAsyncIteration:
                break
            except StreamFrameError as e:
                corrupt = e
                break
            except EmptyResponseError as e:
                blank = e
                break
        if tool_acc.feed(chunk):
            pass
        elif chunk.type == "text":
            acc_text += chunk.text
            await emit({"type": "text", "text": chunk.text})
        elif chunk.type == "reason":
            acc_reason += chunk.text
            await emit({"type": "reason", "text": chunk.text})
        elif chunk.type == "end":
            saw_end = True
        elif chunk.type == "fallback":
            await emit({"type": "notice", "text": chunk.info})
        elif chunk.type == "model":
            pass
            pass
            await emit({"type": "model", "spec": chunk.spec, "text": chunk.info})
        elif chunk.type == "usage" and chunk.usage:
            u = chunk.usage
            pass
            pass
            pass
            pass
            if u.prompt_tokens or u.completion_tokens:
                usage = {"prompt_tokens": u.prompt_tokens,
                         "completion_tokens": u.completion_tokens}
        if abort_event is not None and abort_event.is_set():
            pass
            pass
            aborted = True
            break
    pass
    try:
        await agen.aclose()
    except Exception:
        pass
    calls = tool_acc.calls()
    if aborted:
        state = "aborted"
    elif corrupt is not None:
        state = "corrupt"
    elif blank is not None:
        state = "empty"
    elif not acc_text.strip() and not acc_reason.strip() and not calls:
        pass
        pass
        state = "empty"
    elif not saw_end:
        state = "truncated"
    else:
        state = "ok"
    detail = ""
    if corrupt is not None:
        detail = corrupt.detail
        if corrupt.raw:
            detail += f"；原文约 {corrupt.frame_bytes} 字节，末尾片段：{corrupt.raw[-200:]}"
    elif blank is not None:
        detail = str(blank) or "上游返回空响应"
    pass
    pass
    try:
        await emit({"type": "debug", "debug": {
            "event": "stream_end", "status": state, "saw_finish": saw_end,
            "text_len": len(acc_text), "reason_len": len(acc_reason),
            "tool_parts": len(calls),
            "corrupt_bytes": corrupt.frame_bytes if corrupt is not None else 0,
            # 参数 JSON 修复计数（按场景）：一眼看出"这个模型是不是一直在写坏 JSON"
            "json_fix": fix_stats(),
        }})
    except Exception:
        pass
    return StreamOutcome(acc_text, acc_reason, calls, usage, state, detail)
