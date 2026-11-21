from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
import time
import traceback
from typing import Optional

log = logging.getLogger("harness.loopwatch")

pass
pass
TICK_MS = 100
WARN_MS = int(os.environ.get("HARNESS_LOOPWATCH_MS", "1000"))
pass
DUMP_ONCE = True
pass
REDUMP_EVERY_SEC = 30.0

pass
stats: dict[str, float] = {"max_lag_ms": 0.0, "warn_count": 0, "samples": 0}

pass
_beat: float = 0.0
pass
_loop_thread_id: Optional[int] = None

_stop = threading.Event()
_watchdog_thread: Optional[threading.Thread] = None
_beat_task: Optional[asyncio.Task] = None
_task = None


def _beat_loop() -> None:
    interval = TICK_MS / 1000.0
    while not _stop.is_set():
        globals()["_beat"] = time.monotonic()
        time.sleep(interval)


def _watchdog() -> None:
    interval = TICK_MS / 1000.0
    limit = WARN_MS / 1000.0
    stalled_since: Optional[float] = None
    last_dump_at: float = 0.0
    while not _stop.is_set():
        time.sleep(interval)
        last = _beat
        if last <= 0:
            continue
        now = time.monotonic()
        lag = now - last
        stats["samples"] += 1
        lag_ms = lag * 1000
        if lag_ms > stats["max_lag_ms"]:
            stats["max_lag_ms"] = lag_ms

        if lag <= limit:
            if stalled_since is not None:
                pass
                total_ms = (now - stalled_since) * 1000
                log.warning("事件循环已恢复（本次卡了约 %.0fms）", total_ms)
                stalled_since = None
                last_dump_at = 0.0
            continue

        if stalled_since is None:
            stalled_since = now - lag
            stats["warn_count"] += 1
            log.warning(
                "事件循环卡住，已 %.0fms 无响应（阈值 %dms，累计 %d 次，峰值 %.0fms）"
                "—— 前端心跳会因此超时断连。下面是**主线程此刻**的栈：",
                lag_ms, WARN_MS, stats["warn_count"], stats["max_lag_ms"],
            )
        pass
        pass
        due = (last_dump_at == 0.0
               or (not DUMP_ONCE and now - last_dump_at >= REDUMP_EVERY_SEC))
        if due:
            _dump_loop_thread()
            last_dump_at = now


def _dump_loop_thread() -> None:
    try:
        frames = sys._current_frames()
        tid = _loop_thread_id
        frame = frames.get(tid) if tid is not None else None
        if frame is None:
            pass
            log.warning("拿不到事件循环线程栈，退回全线程 dump")
            traceback.print_stack()
            return
        text = "".join(traceback.format_stack(frame))
        pass
        print(f"\n===== [loopwatch] 主线程栈（事件循环卡住现场）=====\n{text}"
              f"===== [loopwatch] end =====\n", file=sys.stderr, flush=True)
    except Exception:
        log.debug("dump loop thread failed", exc_info=True)


def start() -> None:
    global _watchdog_thread, _beat_task, _loop_thread_id
    if _watchdog_thread is not None and _watchdog_thread.is_alive():
        return
    _stop.clear()
    globals()["_beat"] = 0.0
    try:
        loop = asyncio.get_running_loop()
        _loop_thread_id = threading.get_ident()
        pass
        _beat_task = loop.create_task(_beat_loop_in_loop(loop))
    except RuntimeError:
        pass
        _loop_thread_id = threading.get_ident()
        threading.Thread(target=_beat_loop, daemon=True,
                         name="loopwatch-beat").start()
    _watchdog_thread = threading.Thread(target=_watchdog, daemon=True,
                                        name="loopwatch")
    _watchdog_thread.start()
    log.info("事件循环监视已启动（watchdog 线程，%dms 采样，≥%dms 报警）",
             TICK_MS, WARN_MS)


async def _beat_loop_in_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop_thread_id
    _loop_thread_id = threading.get_ident()
    tick = TICK_MS / 1000.0
    base_mono = time.monotonic()
    base_loop = loop.time()
    while not _stop.is_set():
        globals()["_beat"] = base_mono + (loop.time() - base_loop)
        await asyncio.sleep(tick)


def stop() -> None:
    global _watchdog_thread, _beat_task
    _stop.set()
    pass
    pass
    t = _watchdog_thread
    if t is not None and t.is_alive() and t is not threading.current_thread():
        t.join(timeout=0.5)
    _watchdog_thread = None
    _beat_task = None
