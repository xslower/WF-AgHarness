from __future__ import annotations

from typing import Any

from ...util.jsonx import valid_tool_args


def sanitize_tool_calls(calls: Any) -> list | None:
    if calls is None:
        return None
    out = []
    for tc in calls or []:
        call = dict(tc) if isinstance(tc, dict) else {}
        fn = dict(call.get("function") or {}) if isinstance(call.get("function"), dict) else {}
        if not isinstance(fn.get("name"), str) or not fn["name"]:
            fn["name"] = "unknown"
        if not valid_tool_args(fn.get("arguments")):
            fn["arguments"] = "{}"
        call["id"] = call.get("id") or "call_invalid"
        call["type"] = "function"
        call["function"] = fn
        out.append(call)
    return out


def wire_messages(messages: list) -> list:
    out: list[Any] = []
    for msg in messages or []:
        if not isinstance(msg, dict):
            out.append(msg)
            continue
        m = {k: v for k, v in msg.items() if not str(k).startswith("_")}
        if "tool_calls" in m:
            m["tool_calls"] = sanitize_tool_calls(m["tool_calls"])
        out.append(m)
    return out
