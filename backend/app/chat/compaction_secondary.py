from __future__ import annotations

import logging

from .compaction import MEMO_SECTIONS
from .compaction_kit import (Emit, load_state, notice, report_after,
                             save_state, session_data)
from .context_view import measure

logger = logging.getLogger("harness.compact.secondary")

pass
KEEP_RECENT_SEGS = 2
pass
CONDENSE_NEXT_SEGS = 3
pass
RECOMPACT_LADDER = (0.50, 0.55, 0.60, 0.65)

pass
SHORT_SECTION_CHARS = 160
pass
LEGACY_CHARS = 400

DROP_SECTIONS = ("[建议]",)
SHORT_SECTIONS = ("[已完成]", "[进行中]")


def _condense_text(text: str) -> str:
    lines = str(text or "").splitlines()
    if not any(ln.lstrip().startswith(MEMO_SECTIONS) for ln in lines):
        flat = str(text or "").strip()
        return flat[:LEGACY_CHARS] + ("…" if len(flat) > LEGACY_CHARS else "")
    out: list[str] = []
    for ln in lines:
        s = ln.lstrip()
        if any(s.startswith(tag) for tag in DROP_SECTIONS):
            continue
        if any(s.startswith(tag) for tag in SHORT_SECTIONS):
            ln = (ln[:SHORT_SECTION_CHARS] + "…"
                  if len(ln) > SHORT_SECTION_CHARS else ln)
        out.append(ln)
    return "\n".join(out).strip()


def condense_items(items: list[dict]) -> list[dict]:
    out: list[dict] = []
    for m in items or []:
        d = dict(m)
        content = d.get("content")
        if isinstance(content, str):
            d["content"] = _condense_text(content)
        elif isinstance(content, list):
            d["content"] = [
                {**p, "text": _condense_text(p.get("text", ""))}
                if isinstance(p, dict) and isinstance(p.get("text"), str) else p
                for p in content
            ]
        out.append(d)
    return out


def plan_secondary(
        segments: list[dict]) -> tuple[list[tuple[int, list[dict]]], int]:
    n = len(segments)
    if n <= KEEP_RECENT_SEGS:
        return [], 0
    cut = max(0, n - KEEP_RECENT_SEGS - CONDENSE_NEXT_SEGS)
    delete_before = int(segments[cut]["upto_seq"]) if cut else 0
    updates = [
        (int(s["upto_seq"]), condense_items(s.get("items") or []))
        for s in segments[cut:n - KEEP_RECENT_SEGS]
    ]
    return updates, delete_before


def decide(sid: str, used: int, limit: int) -> tuple[dict, str]:
    state = load_state(sid)
    steps = int(state.get("steps") or 0)
    if not limit or steps >= len(RECOMPACT_LADDER):
        if (limit and used >= limit * RECOMPACT_LADDER[-1]
                and not state.get("nagged")):
            state["nagged"] = True
            save_state(sid, state)
            return state, "nag"
        return state, "idle"
    if used < limit * RECOMPACT_LADDER[steps]:
        return state, "idle"
    return state, "recompact"


def used_text(used: int, measured: dict) -> str:
    return f"~{used}" if measured.get("estimated") else str(used)


class SecondaryStrategy:
    name = "secondary"

    async def compact(self, c, sid: str, emit: Emit, *,
                      session: dict | None = None, model: str = "") -> None:
        ctx = session_data(c, sid, session=session, model=model)
        if ctx is None:
            return
        measured = measure(c.usage, ctx.msgs, ctx.segments,
                           real=ctx.session.get("last_usage"), spec=ctx.spec)
        used = measured["used"]
        state, action = decide(sid, used, ctx.limit)
        if action == "nag":
            await notice(emit, f"上下文已达 {used_text(used, measured)}/{ctx.limit}，"
                               f"二次压缩已达上限（{len(RECOMPACT_LADDER)} 次），"
                               "建议开启新会话以释放上下文。")
            return
        if action != "recompact":
            return
        pass
        segments = c.sessions.get_compactions(ctx.project, sid)
        updates, delete_before = plan_secondary(segments)
        if not updates and not delete_before:
            return
        await notice(emit, f"上下文已达 {used_text(used, measured)}/{ctx.limit}，"
                           "正在精简旧任务纪要…")
        for upto, new_items in updates:
            c.sessions.set_compaction_items(ctx.project, sid, upto, new_items)
        if delete_before:
            c.sessions.delete_compactions_before(ctx.project, sid, delete_before)
        state["steps"] = int(state.get("steps") or 0) + 1
        save_state(sid, state)
        await report_after(c, ctx, emit)
