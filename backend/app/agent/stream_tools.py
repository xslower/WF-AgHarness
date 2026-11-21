from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable

from ..chat.media_msg import ImageUnavailable, image_parts
from ..tools import ToolContext
from ..tools.cmd_output_filter import filter_for_llm
from ..tools.text_limit import for_context
from ..util.jsonx import err

__all__ = ["execute_tools", "execute_one"]

async def execute_tools(self, tool_calls: list[dict], ctx: ToolContext,
                        messages: list[dict], depth: int,
                        emit: Callable[[dict], Awaitable[None]],
                        abort_event=None, budget_left: int = 0,
                        budget_total: int = 0):
    pass
    pass
    note = (self._budget_note(depth, budget_left, budget_total)
            if depth > 0 else "")
    pass
    pass
    pass
    batch: list[dict] = []
    for i, tc in enumerate(tool_calls):
        name = tc["function"]["name"]
        pass
        pass
        parsed = tuple(self._parse_args(tc))
        args, arg_err = parsed[0], parsed[1] if len(parsed) > 1 else ""
        fix_note = parsed[2] if len(parsed) > 2 else ""
        await emit({"type": "tool_start", "name": name, "args": args})
        pass
        if abort_event is not None and abort_event.is_set():
            await emit({"type": "tool_end", "name": name, "args": args,
                        "result": "⏸ 已中止，本次调用未执行"})
            batch.extend(self._aborted_tool_msg(rest, messages)
                         for rest in tool_calls[i:])
            break
        task = asyncio.create_task(
            self._execute_one(tc, args, arg_err, ctx, messages, depth, emit,
                              fix_note))
        if abort_event is not None and not await self._wait_tool_or_abort(
                task, abort_event):
            pass
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
            await emit({"type": "tool_end", "name": name, "args": args,
                        "result": "⏸ 已中止，本次调用被放弃"})
            batch.extend(self._aborted_tool_msg(rest, messages)
                         for rest in tool_calls[i:])
            break
        try:
            result = await task if abort_event is None else task.result()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            pass
            pass
            pass
            pass
            pass
            result = err(f"工具 {name} 执行异常（已拦截，本轮继续）",
                         reason=f"{type(e).__name__}: {e}")
            await emit({"type": "tool_end", "name": name, "args": args,
                        "result": result})
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        _paths = args.get("path") if isinstance(args, dict) else None
        if _paths is None and isinstance(args, dict):
            _paths = args.get("paths")
        _nfiles = (len(_paths) if isinstance(_paths, (list, tuple))
                   and name == "f_read" else 1)
        content = for_context(filter_for_llm(result, name, args), name,
                              file_count=_nfiles)
        if note and i == len(tool_calls) - 1:
            content = f"{content}\n\n{note}"
        pass
        pass
        msg = {"role": "tool", "tool_call_id": tc["id"], "content": content}
        messages.append(msg)
        batch.append(msg)
    pass
    for msg in batch:
        yield msg
    pass
    pass
    for msg in await _image_message(ctx, getattr(self, "gateway", None),
                                    self._last_model_spec()):
        messages.append(msg)
        yield msg


async def _image_message(ctx: ToolContext, gateway, spec: str) -> list[dict]:
    pending = getattr(ctx, "pending_images", None) or []
    if not pending:
        return []
    ctx.pending_images = []
    try:
        parts = await image_parts(pending, gateway=gateway, spec=spec)
    except ImageUnavailable as e:
        return [{"role": "user", "_sys": "image",
                 "content": f"[发图失败] 这 {len(pending)} 张图没能提供给你：{e}"}]
    if not parts:
        return []
    return [{"role": "user", "_sys": "image",
             "content": [{"type": "text",
                          "text": f"[以下是上面工具读取的 {len(pending)} 张图片]"},
                         *parts]}]

async def execute_one(self, tc: dict, args: dict, arg_err: str,
                      ctx: ToolContext, messages: list[dict], depth: int,
                      emit: Callable[[dict], Awaitable[None]],
                      fix_note: str = "") -> str:
    name = tc["function"]["name"]
    t0 = time.perf_counter()
    if arg_err:
        result = err("工具参数 JSON 解析失败", reason=arg_err)
    elif await self._check_plan_block(name, args, emit, ctx):
        result = err(
            "plan_blocked",
            reason="当前为只读计划模式：请先在正文里给出实施计划，"
                   "等用户确认后系统会自动重新执行，不要重试写操作")
    elif self.mcp and self.mcp.knows(name, getattr(ctx, 'cwd', '') or ''):
        result = await self.mcp.call(name, args)
    else:
        result = await self.registry.execute(name, args, ctx)
    pass
    pass
    pass
    if not isinstance(result, str):
        try:
            from ..util.jsonx import dumps as _dumps
            result = _dumps(result)
        except Exception:
            result = repr(result)
    pass
    pass
    pass
    pass
    pass
    pass
    esc_note = await self._check_escalation(name, args, messages, depth, emit)
    if esc_note and isinstance(result, str):
        result += "\n\n" + esc_note
    pass
    pass
    if fix_note and isinstance(result, str):
        result = f"[参数 JSON 已自动修复：{fix_note}]\n" + result
    pass
    pass
    self._publish_tool_event(name, args, result, ctx, depth, t0)
    await emit({"type": "tool_end", "name": name,
                "args": args, "result": result})
    return result
