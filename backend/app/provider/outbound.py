from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Callable, Optional

logger = logging.getLogger("harness.outbound")


pass

class OutboundRequest:
    __slots__ = (
        "kind", "provider", "model", "method", "url", "headers", "body",
        "request", "timeout", "transport", "file_path",
    )

    def __init__(
        self,
        *,
        kind: str,
        provider: Any,
        model: Any,
        method: str = "",
        url: str = "",
        headers: Optional[dict] = None,
        body: Optional[dict] = None,
        request: Optional[dict] = None,
        timeout: float = 120.0,
        transport: Any = None,
        file_path: str = "",
    ):
        self.kind = kind
        self.provider = provider
        self.model = model
        self.method = method
        self.url = url
        self.headers = headers or {}
        self.body = body or {}
        self.request = request or {}
        self.timeout = timeout
        self.transport = transport
        self.file_path = file_path


class OutboundResponse:
    __slots__ = ("stream", "data")

    def __init__(
        self,
        *,
        stream: Optional[AsyncIterator[dict]] = None,
        data: Any = None,
    ):
        self.stream = stream
        self.data = data


pass

pass
OutboundHandler = Callable[[OutboundRequest], ...]


pass

class OutboundSwitch:

    def __init__(self) -> None:
        self._handlers: dict[str, OutboundHandler] = {}

    def register(self, plugin_id: str, handler: OutboundHandler) -> None:
        self._handlers[plugin_id] = handler
        logger.info("outbound switch plugin=%s registered", plugin_id)

    def unregister(self, plugin_id: str) -> None:
        self._handlers.pop(plugin_id, None)
        logger.info("outbound switch plugin=%s unregistered", plugin_id)

    def lookup(self, plugin_id: str) -> Optional[OutboundHandler]:
        return self._handlers.get(plugin_id or "")

    def clear(self) -> None:
        self._handlers.clear()

    @property
    def active(self) -> dict[str, OutboundHandler]:
        return dict(self._handlers)


OUTBOUND = OutboundSwitch()
