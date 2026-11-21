from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .... import ToolContext

pass
_STORE: dict[str, dict[str, list[str]]] = {}
MAX_FILES = 5
MAX_VERSIONS = 3


def _all(ctx: "ToolContext") -> dict[str, list[str]]:
    return _STORE.setdefault(getattr(ctx, "session_id", "") or "anon", {})


def _stack(ctx: "ToolContext", p: Path) -> list[str]:
    store = _all(ctx)
    if str(p) not in store and len(store) >= MAX_FILES:
        store.pop(next(iter(store)))
    return store.setdefault(str(p), [])


def _read(ctx: "ToolContext", p: Path) -> list[str]:
    return _all(ctx).get(str(p)) or []


def push(ctx: "ToolContext", p: Path, old_text: str) -> None:
    stack = _stack(ctx, p)
    stack.append(old_text)
    del stack[:-MAX_VERSIONS]


def pop(ctx: "ToolContext", p: Path) -> str | None:
    stack = _read(ctx, p)
    return stack.pop() if stack else None


def peek(ctx: "ToolContext", p: Path) -> str | None:
    stack = _read(ctx, p)
    return stack[-1] if stack else None


def reset(ctx: "ToolContext", p: Path, text: str) -> None:
    _all(ctx)[str(p)] = [text]
