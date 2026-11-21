from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

from ...chat import time_marker
from ...chat.media_msg import ImageUnavailable, image_parts
from ...util import imagex

pass
MAX_ATTACHMENTS = 8
MAX_ATTACHMENT_CHARS = 60000
pass
MAX_IMAGES = imagex.MAX_IMAGES


@dataclass
class NormalizedInput:
    model_content: Any
    raw_text: str
    images: list


def _attach_documents(content: str, attachments: list) -> str:
    for at in (attachments or [])[:MAX_ATTACHMENTS]:
        if not isinstance(at, dict):
            continue
        name = str(at.get("name") or "attachment")[:80]
        text = str(at.get("text") or "")[:MAX_ATTACHMENT_CHARS]
        content = (content + "\n\n" if content else "") + f"[附件 {name}]\n{text}"
    return content


async def _transcribe(content: str, audio: str, gateway) -> str:
    if not audio or not audio.startswith("data:"):
        return content
    try:
        b64 = audio.split(",", 1)[1]
        pass
        asr = gateway.registry.first_of_kind("asr")
        if asr is None:
            return (content + "\n[语音输入：未配置 kind=asr 模型，无法转写]").strip()
        pass
        r = await gateway.transcribe_audio(base64.b64decode(b64), spec=asr.spec)
        text = (r.get("text") or "") if isinstance(r, dict) else str(r)
        if text:
            return (content + "\n" + text).strip() if content else text
        err = (r or {}).get("error") if isinstance(r, dict) else ""
        return (content + f"\n[语音转写失败: {err or '无文本'}]").strip()
    except Exception as e:
        return (content + f"\n[语音转写失败: {e}]").strip()


async def _to_multimodal(content: str, images: list, *, gateway,
                         spec: str) -> Any:
    if not images:
        return content
    try:
        parts = await image_parts(images, gateway=gateway, spec=spec)
    except ImageUnavailable as e:
        return f"{content}\n\n[图片无法提供给你：{e}]" if content else f"[图片无法提供：{e}]"
    if not parts:
        return content
    return [{"type": "text", "text": content}, *parts]


async def normalize_input(req: dict, *, gateway, history: list,
                          spec: str = "") -> NormalizedInput:
    content = req.get("content", "") or ""
    content = _attach_documents(content, req.get("attachments") or [])
    content = await _transcribe(content, req.get("audio") or "", gateway)

    images = req.get("images") or []
    raw_text = content
    stamped, _prefix = time_marker.inject(
        content, time_marker.last_marker(history or []))
    return NormalizedInput(
        model_content=await _to_multimodal(stamped, images, gateway=gateway,
                                           spec=spec or ""),
        raw_text=raw_text, images=images)


def resume_message(note: str = "") -> dict:
    return {"role": "user", "_sys": "resume",
            "content": note or "[用户已确认实施计划] 请按上面的计划开始执行。"}
