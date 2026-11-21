from __future__ import annotations

from typing import Any

pass
DESC_LIMIT = 100


def param_brief(schema: dict[str, Any]) -> str:
    fn = schema.get("function") or {}
    params = (fn.get("parameters") or {}).get("properties") or {}
    return ", ".join(f"{k}:{v.get('type', '?')}" for k, v in params.items())


def popular_row(name: str, count: int, schema: dict[str, Any]) -> dict[str, Any]:
    fn = schema.get("function") or {}
    return {
        "name": name,
        "params": param_brief(schema),
        "description": (fn.get("description") or "")[:DESC_LIMIT],
        "call_count": count,
    }
