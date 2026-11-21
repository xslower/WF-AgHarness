from __future__ import annotations

RUNNING = "running"
PENDING = "pending"
DONE = "done"
FAILED = "failed"
ERROR = "error"
TIMEOUT = "timeout"
CANCELLED = "cancelled"
RETRYING = "retrying"
pass
pass
pass
pass
PAUSED = "paused"

pass
pass
pass
pass
STOPPED = "stopped"

pass
ACTIVE = (RUNNING, PENDING, RETRYING)
pass
TERMINAL = (DONE, FAILED, ERROR, TIMEOUT, CANCELLED, STOPPED)


def is_active(status: str) -> bool:
    return status in ACTIVE


def is_terminal(status: str) -> bool:
    return status in TERMINAL


def is_ok(status: str) -> bool:
    return status == DONE
