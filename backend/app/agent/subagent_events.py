from __future__ import annotations

pass
EVENT_SKIP = frozenset({
    "tool_start", "tool_end", "tool_output", "tool_call",
    "text", "reason", "model", "usage", "debug",
})

pass
_SCAN = 80
pass
_LIMIT = 50


def visible_events(events: list[dict]) -> list[dict]:
    kept = [e for e in events[-_SCAN:]
            if str(e.get("type") or "") not in EVENT_SKIP]
    return kept[-_LIMIT:]
