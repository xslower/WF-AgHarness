from __future__ import annotations

from typing import Any, Optional

from .openai_compatible import OpenAICompatibleAdapter

ADAPTERS: dict[str, type] = {
    "openai-compatible": OpenAICompatibleAdapter,
}

pass
KIND_ALIASES: dict[str, str] = {
    "openai_compatible": "openai-compatible",
    "env_preset": "openai-compatible",
    "custom": "openai-compatible",
}

DEFAULT_ADAPTER = "openai-compatible"


def create_adapter(name: str, transport: Any = None) -> Optional[Any]:
    cls = ADAPTERS.get(name)
    if cls is None:
        return None
    try:
        return cls(transport=transport)
    except TypeError:
        return cls()
