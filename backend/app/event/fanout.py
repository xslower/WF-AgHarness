from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field

from .bus import HUB, EventHub


pass
QUEUE_MAX = 512


@dataclass(eq=False)
class Sink:

    loop: asyncio.AbstractEventLoop
    q: "asyncio.Queue[dict]" = field(default_factory=asyncio.Queue)
    dropped: int = 0


class EventFanout:

    def __init__(self, hub: EventHub | None = None) -> None:
        self._hub = hub if hub is not None else HUB
        self._lock = threading.Lock()
        self._sinks: set[Sink] = set()
        self._attached = False

    pass
    def attach(self) -> None:
        if self._attached:
            return
        self._hub.on("*", self._on_event, key="fanout")
        self._attached = True

    def detach(self) -> None:
        self._hub.off("*", key="fanout")
        self._attached = False

    def reset(self) -> None:
        with self._lock:
            self._sinks.clear()
        self._attached = False

    pass
    def register(self) -> Sink:
        sink = Sink(loop=asyncio.get_running_loop(),
                    q=asyncio.Queue(maxsize=QUEUE_MAX))
        with self._lock:
            self._sinks.add(sink)
        return sink

    def unregister(self, sink: Sink) -> None:
        with self._lock:
            self._sinks.discard(sink)

    def count(self) -> int:
        with self._lock:
            return len(self._sinks)

    def dropped(self) -> int:
        with self._lock:
            return sum(s.dropped for s in self._sinks)

    pass
    def _on_event(self, ev: dict) -> None:
        with self._lock:
            sinks = list(self._sinks)
        for sink in sinks:
            try:
                sink.loop.call_soon_threadsafe(self._offer, sink, ev)
            except RuntimeError:
                pass
                continue

    @staticmethod
    def _offer(sink: Sink, ev: dict) -> None:
        try:
            sink.q.put_nowait(ev)
        except asyncio.QueueFull:
            try:
                sink.q.get_nowait()
                sink.dropped += 1
            except asyncio.QueueEmpty:
                pass
            try:
                sink.q.put_nowait(ev)
            except asyncio.QueueFull:
                sink.dropped += 1


pass
fanout = EventFanout()
