from __future__ import annotations

from typing import Any

from ..util.jsonx import append_jsonl
from ..util.timeutil import clock, fmt_stamp
from .model import Event, plain

SAFE_DETAIL_KEYS = frozenset({
    "code", "source", "seed", "signal", "action", "reason", "checkpoint",
    "records", "conflicts", "exit_code", "error_code", "phase", "metric",
})
SENSITIVE_MARK = "[REDACTED]"


def event_id(run_id: str, seq: int) -> str:
    return f"ev_{run_id}_{seq:04d}"


def stamp(ts: float | None = None) -> str:
    return fmt_stamp(clock() if ts is None else ts)


def make_event(run_id: str, case_id: str, role: str, seq: int,
               phase: str, detail: dict[str, Any] | None = None,
               subject: dict[str, Any] | None = None,
               trace: dict[str, Any] | None = None) -> Event:
    if phase not in ("start", "running", "paused", "resumed", "failed", "stopped"):
        raise ValueError(f"未知 phase: {phase}")
    raw = detail or {}
    safe = {k: v for k, v in raw.items() if k in SAFE_DETAIL_KEYS}
    if len(safe) != len(raw):
        safe["redacted"] = len(raw) - len(safe)
    return Event(
        event_id=event_id(run_id, seq), run_id=run_id, case_id=case_id,
        version_role=role, ts=stamp(), phase=phase,
        subject=subject or {}, detail=safe, trace=trace or {},
    )


def snapshot_events(run_id: str, case_id: str, role: str,
                    raw_events: tuple[dict[str, Any], ...],
                    offset: int = 0) -> tuple[Event, ...]:
    return tuple(
        make_event(run_id, case_id, role, offset + i + 1,
                   str(e.get("phase", "running")), e.get("detail"))
        for i, e in enumerate(raw_events)
    )


def persist_events(path: str, events: tuple[Event, ...]) -> bool:
    return append_jsonl(path, [plain(e) for e in events])


def metric_from(snapshot: Any, metric: str) -> float | None:
    if metric == "heartbeat_gap_ms":
        times = snapshot.heartbeat_times
        if len(times) < 2:
            return None
        gaps = [b - a for a, b in zip(times, times[1:])]
        return max(0.0, max(gaps) * 1000.0)
    if hasattr(snapshot, metric):
        value = getattr(snapshot, metric)
        return float(value) if isinstance(value, (int, float)) else None
    value = (snapshot.resource or {}).get(metric)
    return float(value) if isinstance(value, (int, float)) else None
