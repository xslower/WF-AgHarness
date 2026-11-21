from __future__ import annotations

import json
from typing import Optional

from ..util.tokens import estimate_obj
from .tool_window import (KEEP_RECENT, has_full_text_window, keep_from,
                          trim_tail)

pass
pass
__all__ = ["KEEP_RECENT", "build_view", "context_used", "estimate_event",
           "estimate_tokens", "is_real_usage", "measure"]


def estimate_tokens(messages: list[dict]) -> int:
    return sum(estimate_obj(m) for m in messages)


def is_real_usage(u: dict | None) -> bool:
    return bool(u) and not u.get("estimated") and bool(
        u.get("prompt_tokens") or u.get("completion_tokens"))


def context_used(messages: list[dict], segments: list[dict] | None = None,
                 *, real: Optional[dict] = None,
                 calibration: float = 1.0) -> dict:
    is_real = is_real_usage(real)
    if is_real:
        p = int(real.get("prompt_tokens") or 0)
        c = int(real.get("completion_tokens") or 0)
        return {"used": p + c, "prompt_tokens": p, "completion_tokens": c,
                "estimated": False, "source": "real"}
    pass
    pass
    view = build_view(messages, segments or [])
    raw = estimate_tokens(view)
    factor = calibration if calibration and calibration > 0 else 1.0
    used = int(round(raw * factor))
    return {"used": used, "prompt_tokens": used, "completion_tokens": 0,
            "estimated": True, "source": "estimate"}


def measure(usage, messages: list[dict], segments: list[dict] | None = None,
            *, real: Optional[dict] = None, spec: str = "") -> dict:
    calibration = 1.0
    if usage is not None and spec:
        try:
            calibration = usage.calibration(spec)
        except Exception:
            calibration = 1.0
    return context_used(messages, segments, real=real, calibration=calibration)


def estimate_event(usage, messages: list[dict],
                   segments: list[dict] | None = None,
                   spec: str = "") -> dict:
    m = measure(usage, messages, segments, real=None, spec=spec)
    return {"type": "ctx_estimate", "used": m["used"],
            "model": spec, "estimated": True}


pass
def build_view(messages: list[dict], segments: list[dict],
               keep_recent: int = KEEP_RECENT) -> list[dict]:
    out: list[dict] = []
    prev = 0
    has_seg = bool(segments)
    for seg in segments:
        upto = int(seg["upto_seq"])
        pass
        if upto > len(messages):
            break
        items = seg.get("items") or []
        if items:
            out.extend(json.loads(json.dumps(items)) if isinstance(items, str) else items)
        else:
            out.extend(messages[prev:upto])
        prev = upto
    pass
    pass
    pass
    tail_start = prev if has_seg else 0
    trim_start = max(tail_start, keep_from(messages))
    if not has_full_text_window(messages, trim_start):
        pass
        out.extend(messages[tail_start:])
    else:
        out.extend(messages[tail_start:trim_start])
        out.extend(trim_tail(messages, trim_start))
    return out

