from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Optional

logger = logging.getLogger("harness.hub")

pass
SLOW_MS = 50.0

Handler = Callable[[dict], None]
Unsubscribe = Callable[[], None]


def envelope(seq: int, topic: str, payload: Optional[dict] = None) -> dict:
    return {"seq": seq, "topic": topic, "ts": time.time(),
            "payload": payload or {}}


def match_topic(pattern: str, topic: str) -> bool:
    if pattern == "*" or pattern == topic:
        return True
    if "*" not in pattern:
        return False
    a, b = pattern.split("."), topic.split(".")
    if len(a) != len(b):
        return False
    return all(x == "*" or x == y for x, y in zip(a, b))


class EventHub:

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subs: dict[str, list[tuple[str, Handler]]] = {}
        self._seq = 0
        self._errors = 0
        self._slow = 0

    pass
    def on(self, topic: str, handler: Handler, key: str = "") -> Unsubscribe:
        if not callable(handler):
            raise TypeError("handler 必须可调用")
        with self._lock:
            bucket = self._subs.setdefault(topic, [])
            if key:
                bucket[:] = [(k, h) for k, h in bucket if k != key]
            bucket.append((key, handler))
        return lambda: self.off(topic, handler)

    def off(self, topic: str, handler: Optional[Handler] = None,
            key: str = "") -> None:
        from ._sub import unsubscribe_in
        with self._lock:
            unsubscribe_in(self._subs, topic, handler, key)

    def clear(self, topic: Optional[str] = None) -> None:
        with self._lock:
            if topic is None:
                self._subs.clear()
            else:
                self._subs.pop(topic, None)

    pass
    def publish(self, topic: str, payload: Optional[dict] = None) -> dict:
        with self._lock:
            self._seq += 1
            ev: dict[str, Any] = envelope(self._seq, topic, payload)
            snapshot: list[tuple[str, str, Handler]] = []
            for pattern, bucket in self._subs.items():
                if not match_topic(pattern, topic):
                    continue
                for k, h in bucket:
                    snapshot.append((pattern, k, h))
        for pattern, k, handler in snapshot:
            t0 = time.perf_counter()
            try:
                handler(ev)
            except Exception:
                with self._lock:
                    self._errors += 1
                logger.exception("hub handler failed: %s <- %s", k or pattern, topic)
            elapsed = (time.perf_counter() - t0) * 1000
            if elapsed > SLOW_MS:
                with self._lock:
                    self._slow += 1
                logger.warning("slow hub handler %.0fms: %s <- %s",
                               elapsed, k or pattern, topic)
        return ev

    pass
    def topics(self) -> list[dict]:
        with self._lock:
            return [{"topic": t, "handlers": [k or getattr(h, "__name__", "handler")
                                             for k, h in bucket]}
                    for t, bucket in sorted(self._subs.items())]

    def stats(self) -> dict:
        with self._lock:
            return {"subscriptions": sum(len(b) for b in self._subs.values()),
                    "topics": len(self._subs),
                    "published": self._seq, "errors": self._errors, "slow": self._slow}


pass
HUB = EventHub()
