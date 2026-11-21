from __future__ import annotations

from typing import Any, Optional

from .protocol_adapters import ADAPTERS, DEFAULT_ADAPTER, KIND_ALIASES, create_adapter


class AdapterRegistry:
    def __init__(self, adapters: Optional[dict[str, Any]] = None) -> None:
        self._items: dict[str, Any] = dict(adapters or {})

    def register(self, name: str, adapter: Any) -> None:
        self._items[name] = adapter

    def get(self, name: str) -> Optional[Any]:
        return self._items.get(name)

    def resolve(self, kind: str = "", adapter: str = "") -> Any:
        if adapter and adapter in self._items:
            return self._items[adapter]
        name = KIND_ALIASES.get(kind, adapter or DEFAULT_ADAPTER)
        return self._items.get(name) or self._items[DEFAULT_ADAPTER]

    def all(self) -> dict[str, Any]:
        return dict(self._items)


def build_adapter_registry(transport: Any = None) -> AdapterRegistry:
    reg = AdapterRegistry()
    for name in ADAPTERS:
        adapter = create_adapter(name, transport)
        if adapter is not None:
            reg.register(name, adapter)
    return reg
