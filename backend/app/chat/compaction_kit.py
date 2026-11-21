from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Protocol

from ..provider.spec import QUEUE_SUMMARY
from ..store.kv import KVStore
from .compaction import l1_fold, keep_from, plan_batch

logger = logging.getLogger("harness.compact.kit")

Emit = Callable[[dict], Awaitable[None]]

pass
STATE_PREFIX = "compact.state."

pass
MIN_MESSAGES = 10

pass
pass
pass
FALLBACK_UNFINISHED_TURNS = 3


def is_complete_assistant(msg: dict) -> bool:
    if not isinstance(msg, dict) or msg.get("role") != "assistant":
        return False
    if msg.get("tool_calls") or msg.get("interrupted"):
        return False
    if "turn_complete" in msg:
        return bool(msg.get("turn_complete"))
    return bool(str(msg.get("content") or "").strip())


def unfinished_turns(msgs: list) -> int:
    count = 0
    for m in reversed(msgs or []):
        if not isinstance(m, dict):
            continue
        if is_complete_assistant(m):
            break
        if m.get("role") == "user":
            count += 1
    return count


class CompactionStrategy(Protocol):

    name: str

    async def compact(self, c, sid: str, emit: Emit, *,
                      session: dict | None = None, model: str = "") -> None: ...


@dataclass
class Ctx:

    sid: str
    project: str
    session: dict
    msgs: list
    segments: list
    spec: str
    limit: int


pass
def resolve_model(c, model: str) -> tuple[str, int]:
    from ..provider.registry import ModelRegistry
    from ..provider.selection import effective_spec
    spec = effective_spec(c.store.config, model)
    info = ModelRegistry(c.store.config).model_of(spec)
    return spec, int(getattr(info, "contextLength", 0) or 0)


def session_data(c, sid: str, *, session: dict | None = None,
                 model: str = "") -> Ctx | None:
    s = session if session is not None else c.sessions.get(sid)
    if not s:
        return None
    project = s.get("project", "")
    spec, limit = resolve_model(c, model)
    return Ctx(sid=sid, project=project, session=s,
               msgs=s.get("messages") or [],
               segments=segments_of(c, project, sid),
               spec=spec, limit=limit)


def segments_of(c, project: str, sid: str) -> list[dict]:
    try:
        return c.sessions.get_compactions(project, sid)
    except Exception:
        logger.warning("读取压缩分段失败: %s", sid, exc_info=True)
        return []


def plan_batch_scope(msgs: list, segments: list) -> tuple[int, int]:
    compacted_upto = segments[-1]["upto_seq"] if segments else 0
    return plan_batch(len(msgs), compacted_upto, end=keep_from(msgs))


def fold_batch(msgs: list, start: int, end: int) -> list[dict]:
    out: list[dict] = []
    for i in range(start, end):
        m = dict(msgs[i])
        m["_seq"] = i
        folded = l1_fold(m)
        if folded is not None:
            folded["_seq"] = i
            pass
            pass
            folded["_complete"] = (is_complete_assistant(msgs[i])
                                   if isinstance(msgs[i], dict) else False)
            out.append(folded)
    return out


pass
async def hedged_call(gateway, prompt: str, sid: str,
                      hedge_ms: int = 2500) -> str:
    specs = gateway._ordered_specs(QUEUE_SUMMARY)
    parts: list[str] = []
    async for chunk in gateway.stream_hedged(
            [{"role": "user", "content": prompt}], specs,
            hedge_ms=hedge_ms, session_id=sid):
        if chunk.type == "text":
            parts.append(chunk.text)
    text = "".join(parts).strip()
    if not text:
        raise RuntimeError("总结模型返回空")
    return text


async def call_twice(fn, label: str):
    for attempt in (1, 2):
        try:
            out = await fn()
            if out:
                return out
        except Exception:
            logger.warning("L2 %s 第 %d 次异常%s", label, attempt,
                           "，重试一次" if attempt == 1 else "，本批放弃压缩",
                           exc_info=True)
        else:
            logger.warning("L2 %s 第 %d 次返回空%s", label, attempt,
                           "，重试一次" if attempt == 1 else "，本批放弃压缩")
    return None


pass
def load_state(sid: str) -> dict:
    try:
        return KVStore().get_json(STATE_PREFIX + sid, {}) or {}
    except Exception:
        return {}


def save_state(sid: str, state: dict) -> None:
    try:
        KVStore().set_json(STATE_PREFIX + sid,
                           {k: v for k, v in state.items()
                            if not k.startswith("_")})
    except Exception:
        logger.warning("compact state save failed", exc_info=True)


async def notice(emit: Emit, text: str) -> None:
    await emit({"type": "notice", "text": text})


async def report_after(c, ctx: Ctx, emit: Emit) -> None:
    from .context_view import estimate_event
    segments = segments_of(c, ctx.project, ctx.sid)
    try:
        ev = estimate_event(c.usage, ctx.msgs, segments, ctx.spec)
    except Exception:
        logger.warning("ctx_estimate 计算失败", exc_info=True)
        return
    ctx.session["last_usage"] = {
        "prompt_tokens": ev["used"],
        "completion_tokens": 0, "estimated": True}
    try:
        await emit(ev)
    except Exception:
        logger.warning("ctx_estimate emit failed", exc_info=True)


pass
STRATEGIES = ("memo", "secondary", "legacy")


def get_strategy(name: str) -> CompactionStrategy:
    if name == "legacy":
        from .compaction_legacy import LegacyStrategy
        return LegacyStrategy()
    if name == "secondary":
        from .compaction_secondary import SecondaryStrategy
        return SecondaryStrategy()
    from .compaction_memo_strategy import MemoStrategy
    return MemoStrategy()
