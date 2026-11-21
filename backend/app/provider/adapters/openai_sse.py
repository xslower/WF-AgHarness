from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from ..errors import RateLimitedError, StreamFrameError
from ...util.jsonx import loads_lenient

logger = logging.getLogger("harness.provider.sse")

ERROR_DETAIL_LIMIT = 2000

pass
pass
pass
TOOL_FRAME_HINTS = ('"tool_calls"', '"function"', '"arguments"', '"tool_call"')


def _usage_event(u: dict) -> dict:
    return {"type": "usage", "usage": {
        "prompt_tokens": u.get("prompt_tokens", 0) or 0,
        "completion_tokens": u.get("completion_tokens", 0) or 0}}


def _reason_text(delta: dict) -> str:
    return (delta.get("reasoning_content")
            or delta.get("reasoning")
            or delta.get("thinking") or "")


def _tool_events(tc: dict) -> list[dict]:
    out: list[dict] = []
    idx = tc.get("index", 0)
    fn = tc.get("function") or {}
    if tc.get("id") or fn.get("name"):
        out.append({"type": "tool_meta", "tool_index": idx,
                    "text": json.dumps({"id": tc.get("id", ""),
                                        "name": fn.get("name", "")})})
    piece = fn.get("arguments") or ""
    if piece:
        out.append({"type": "tool_args", "text": piece, "tool_index": idx})
    return out


def delta_events(delta: dict) -> list[dict]:
    out: list[dict] = []
    rc = _reason_text(delta)
    if rc:
        out.append({"type": "reason", "text": rc})
    if delta.get("content"):
        out.append({"type": "text", "text": delta["content"]})
    for tc in delta.get("tool_calls") or []:
        out.extend(_tool_events(tc))
    return out


def chunk_events(obj: dict) -> list[dict]:
    err = obj.get("error")
    if err:
        detail = err.get("message") if isinstance(err, dict) else err
        raise RuntimeError(f"上游流错误: {str(detail)[:ERROR_DETAIL_LIMIT]}")
    out: list[dict] = []
    u = obj.get("usage")
    if u:
        out.append(_usage_event(u))
    for choice in obj.get("choices") or []:
        out.extend(delta_events(choice.get("delta") or {}))
        finish = choice.get("finish_reason")
        if finish:
            out.append({"type": "end", "text": str(finish)})
    return out


def _looks_like_tool_frame(data: str) -> bool:
    return any(h in data for h in TOOL_FRAME_HINTS)


def _repair_frame(data: str) -> tuple[dict | None, str]:
    pass
    v, detail, note = loads_lenient(data, scene="raw")
    if detail or not isinstance(v, dict):
        return None, ""
    return v, note


async def parse_sse(lines: AsyncIterator[str]) -> AsyncIterator[dict]:
    saw_end = False
    repaired = 0
    skipped = 0
    async for line in lines:
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            if saw_end:
                break
            pass
            continue
        try:
            obj = json.loads(data)
        except (ValueError, RecursionError):
            obj, note = _repair_frame(data)
            if obj is None:
                if _looks_like_tool_frame(data):
                    raise StreamFrameError(
                        "上游返回的工具调用帧损坏且无法补全（通常是参数被输出长度"
                        "或代理缓冲切断）",
                        raw=data[:600], frame_bytes=len(data))
                skipped += 1
                logger.warning("SSE 帧无法解析且非工具帧，已跳过（第 %d 帧，%d 字节）：%r",
                               skipped, len(data), data[:200])
                continue
            repaired += 1
            logger.warning("SSE 帧已自动补全（%s，%d 字节）", note or "宽松解析",
                           len(data))
        for ev in chunk_events(obj):
            if ev.get("type") == "end":
                saw_end = True
            yield ev
    if repaired or skipped:
        logger.info("SSE 解析统计：补全 %d 帧 / 跳过 %d 帧", repaired, skipped)


def error_from_status(status: int, detail: str, spec: str) -> Exception | None:
    if status == 429 or status in (502, 503, 529):
        return RateLimitedError(f"{status} from {spec}")
    if status >= 400:
        return RuntimeError(f"HTTP {status}: {detail[:ERROR_DETAIL_LIMIT]}")
    return None
