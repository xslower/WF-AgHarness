from __future__ import annotations

from typing import NamedTuple, Optional

__all__ = ["StreamOutcome", "normalize_outcome"]

class StreamOutcome(NamedTuple):

    text: str
    reason: str
    calls: list[dict]
    usage: Optional[dict]
    status: str = "ok"
    error: str = ""

def normalize_outcome(res) -> StreamOutcome:
    if isinstance(res, StreamOutcome):
        return res
    text, reason, calls, usage = res
    state = "ok" if (text or reason or calls) else "empty"
    return StreamOutcome(text, reason, calls, usage, state, "")
