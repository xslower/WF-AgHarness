from __future__ import annotations

import asyncio
import logging
import time

from ....util.jsonx import read_json, write_json
from .paths import logs_dir

logger = logging.getLogger("harness.tools.web_pacing")

pass
COOLDOWN_SEC = 30.0
pass
WAIT_IF_NEAR_SEC = 5.0
pass
MAX_WAIT_SEC = 6.0
_LOG_NAME = "pacing.json"


def _path():
    d = logs_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / _LOG_NAME


def _load() -> dict:
    data = read_json(_path(), default={})
    return data if isinstance(data, dict) else {}


def last_access(engine_id: str, now: float | None = None) -> float:
    v = _load().get(engine_id, 0)
    return float(v) if isinstance(v, (int, float)) else 0.0


def mark(engine_id: str, now: float | None = None) -> None:
    rows = _load()
    rows[engine_id] = time.time() if now is None else float(now)
    write_json(_path(), rows)


def remaining(engine_id: str, now: float | None = None,
              cooldown: float = COOLDOWN_SEC) -> float:
    t = time.time() if now is None else float(now)
    return max(0.0, last_access(engine_id, now=t) + cooldown - t)


async def gate(engine, now: float | None = None,
               cooldown: float = COOLDOWN_SEC) -> str:
    if not getattr(engine, "pace", False):
        return "go"
    left = remaining(engine.id, now=now, cooldown=cooldown)
    if left <= 0:
        return "go"
    if left < WAIT_IF_NEAR_SEC:
        await asyncio.sleep(min(left, MAX_WAIT_SEC))
        return "wait"
    return "skip"


def note(engine_id: str, decision: str) -> str:
    return f"频控跳过：距上次访问不足 {int(COOLDOWN_SEC)} 秒（{decision}）"
