from __future__ import annotations

import json

from ..tools.text_limit import trunc_marker_mcp

pass
MAX_RESULT = 60_000


def shape_content(content_blocks) -> str:
    parts: list[str] = []
    for cp in (content_blocks or []):
        ct = getattr(cp, "type", "")
        if ct == "text":
            parts.append(getattr(cp, "text", ""))
        elif ct == "image":
            data = getattr(cp, "data", "") or ""
            mime = (getattr(cp, "mime_type", None)
                    or getattr(cp, "mimeType", None) or "image/png")
            parts.append(f"[image:{mime}:{len(data)} bytes]")
        elif ct == "resource":
            parts.append(f"[resource:{getattr(cp, 'uri', '')}]")
    return "\n".join(parts)

def truncate(text: str, limit: int = MAX_RESULT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + trunc_marker_mcp(len(text))


def finalize(result) -> str:
    text = shape_content(getattr(result, "content", None))
    is_error = bool(getattr(result, "is_error", False)
                    or getattr(result, "isError", False))
    if is_error and not text:
        text = json.dumps({"error": "MCP 工具调用失败（服务器未返回正文）"},
                          ensure_ascii=False)
    return truncate(text)
