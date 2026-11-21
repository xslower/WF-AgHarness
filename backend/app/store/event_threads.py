from __future__ import annotations

import logging
import queue
import threading
from typing import Callable

logger = logging.getLogger("harness.events")

pass
WRITE_BATCH = 64
pass
WRITE_WAIT = 0.2
pass
FLUSH_INTERVAL = 0.5
pass
pass


class Writer:

    def __init__(self, write_one: Callable[[tuple], None]) -> None:
        self._write_one = write_one
        self._q: "queue.Queue[tuple]" = queue.Queue()
        self._started = False
        self._lock = threading.Lock()

    def put(self, item: tuple) -> None:
        try:
            self._q.put_nowait(item)
        except Exception:
            logger.debug("event enqueue failed", exc_info=True)

    def drain(self) -> None:
        while True:
            try:
                item = self._q.get_nowait()
            except queue.Empty:
                return
            self._write_one(item)

    def ensure_started(self) -> None:
        if self._started:
            return
        with self._lock:
            if self._started:
                return
            threading.Thread(target=self._loop, daemon=True,
                             name="events-writer").start()
            self._started = True

    def _loop(self) -> None:
        while True:
            try:
                try:
                    first = self._q.get(timeout=WRITE_WAIT)
                except queue.Empty:
                    continue
                self._write_one(first)
                n = 1
                while n < WRITE_BATCH:
                    try:
                        self._write_one(self._q.get_nowait())
                    except queue.Empty:
                        break
                    n += 1
            except Exception:
                logger.debug("event writer error", exc_info=True)


class Flusher:

    def __init__(self, *, all_dbs: Callable[[], list],
                 flush_locked: Callable[[object], None],
                 interval: float = FLUSH_INTERVAL) -> None:
        self._all_dbs = all_dbs
        self._flush_locked = flush_locked
        self.interval = interval
        self._started = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def ensure_started(self) -> None:
        if self._started:
            return
        with self._lock:
            if self._started:
                return
            self._stop = threading.Event()
            self._started = True
            self._thread = threading.Thread(
                target=self._loop, args=(self._stop,), daemon=True,
                name="events-flusher")
            self._thread.start()

    def pause(self, timeout: float = 2.0) -> None:
        self._stop.set()
        t = self._thread
        if t is not None and t.is_alive() and t is not threading.current_thread():
            t.join(timeout)
        with self._lock:
            self._thread = None
            self._started = False

    def resume(self) -> None:
        self.ensure_started()

    def _loop(self, stop: threading.Event) -> None:
        while not stop.is_set():
            try:
                if stop.wait(self.interval):
                    return
                for d in self._all_dbs():
                    if d.pending <= 0:
                        continue
                    with d.lock:
                        if d.pending > 0:
                            self._flush_locked(d)
            except Exception:
                logger.debug("event flusher error", exc_info=True)
