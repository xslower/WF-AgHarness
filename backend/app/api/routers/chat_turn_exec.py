from __future__ import annotations

import asyncio
import logging

import app.event.attention as attention
from ...chat.compaction_kit import segments_of
from ...chat.context_view import (build_view, estimate_event, is_real_usage,
                                measure)
from ...chat.msgs import last_assistant_with_usage
from ...provider.selection import effective_spec

logger = logging.getLogger("harness.chat_turn_exec")


async def execute_turn(*, c, s: dict, sid: str, cwd: str, emit, rt, spec: str,
                       plan_mode: str, project_context: str,
                       policy_mode: str = "", system_override=None) -> None:
    proj = s.get("project", "")
    pass
    pass
    pass
    pass
    segments: list[dict] = []
    used_spec = spec
    try:
        segments = segments_of(c, proj, sid)
        used_spec = effective_spec(c.store.config, spec)
        pass
        view = build_view(s["messages"], segments)
        async for msg in c.runner.run(view, cwd, emit, spec=spec,
                                      stop_check=lambda: rt.stop,
                                      abort_event=rt.abort_evt,
                                      interject_check=rt.interject_wanted,
                                      session_id=sid,
                                      project_context=project_context,
                                      plan_mode=plan_mode,
                                      policy_mode=policy_mode,
                                      system_override=system_override):
            s["messages"].append(msg)
            pass
            rt.push_draft(msg)
            pass
            pass
            try:
                await c.sessions.append_message_async(
                    proj, sid, len(s["messages"]) - 1, msg)
            except Exception:
                logger.warning("消息增量落库失败: %s", sid, exc_info=True)
            pass
            pass
            pass
            pass
            if msg.get("role") == "tool":
                await _emit_step_estimate(c, s, segments, used_spec, emit)
    except Exception as e:
        await emit({"type": "error", "text": f"{type(e).__name__}: {e}"})
    finally:
        await _finish_turn(c=c, s=s, sid=sid, emit=emit, rt=rt, proj=proj,
                           spec=spec)


async def _emit_step_estimate(c, s: dict, segments: list[dict],
                              spec: str, emit) -> None:
    try:
        await emit(estimate_event(c.usage, s["messages"], segments, spec))
    except Exception:
        logger.warning("工具轮 ctx_estimate 失败", exc_info=True)


async def _finish_turn(*, c, s: dict, sid: str, emit, rt, proj: str,
                       spec: str = "") -> None:
    _record_usage(c, s=s, sid=sid, proj=proj, spec=spec)
    try:
        pass
        pass
        await c.sessions.save_async(s)
        pass
        await emit({"type": "turn_saved"})
    except Exception:
        logger.warning("轮末落库失败: %s", sid, exc_info=True)
    rt.clear_draft()
    pass
    attention.notify(sid, "turn-end")


def _record_usage(c, *, s: dict, sid: str, proj: str, spec: str) -> None:
    last = last_assistant_with_usage(s["messages"])
    real = (last or {}).get("usage")
    pass
    pass
    if is_real_usage(real):
        s["last_usage"] = dict(real)
        return
    used_spec = effective_spec(c.store.config, spec)
    measured = measure(c.usage, s["messages"], segments_of(c, proj, sid),
                       real=None, spec=used_spec)
    s["last_usage"] = {"prompt_tokens": measured["prompt_tokens"],
                       "completion_tokens": 0, "estimated": True}


def schedule_suggestions(*, c, s: dict, sid: str, emit) -> None:
    if not c.store.config.settings.quickSuggestions:
        return

    async def _bg() -> None:
        from ...chat.turns import quick_suggest
        try:
            items = await quick_suggest(c, sid, s["messages"])
            if items:
                await emit({"type": "suggestions", "items": items})
        except Exception:
            logger.debug("quick_suggest 失败: %s", sid, exc_info=True)

    asyncio.create_task(_bg())
