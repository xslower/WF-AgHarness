from __future__ import annotations

from typing import Any, Optional


def last_content(messages: list, role: str, *, skip_interrupted: bool = False,
                 raw: bool = False) -> str:
    for m in reversed(messages or []):
        if not isinstance(m, dict) or m.get("role") != role:
            continue
        if skip_interrupted and m.get("interrupted"):
            continue
        content = m.get("content")
        if raw:
            return content
        if isinstance(content, str):
            return content
    return ""


def last_user_text(messages: list) -> str:
    return last_content(messages, "user")


def last_assistant_text(messages: list) -> str:
    return last_content(messages, "assistant", skip_interrupted=True)


def last_message_content(messages: list) -> Optional[Any]:
    for m in reversed(messages or []):
        if isinstance(m, dict) and m.get("content") is not None:
            return m.get("content")
    return None


def last_assistant_with_usage(messages: list) -> Optional[dict]:
    for m in reversed(messages or []):
        if isinstance(m, dict) and m.get("role") == "assistant" and m.get("usage"):
            return m
    return None
