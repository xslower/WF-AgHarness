from __future__ import annotations

import asyncio

from ..util import imagex

__all__ = ["ImageUnavailable", "DESCRIBE_PROMPT", "supports_images",
           "vision_spec", "image_parts"]

pass
pass
DESCRIBE_PROMPT = (
    "把这张图片转述给一个看不见图的同事：先说它是什么（界面截图/照片/"
    "图表/文档扫描），再逐项列出可见的文字、按钮控件、数据与布局关系，"
    "最后指出明显的异常或报错。只描述事实，不要评价。"
)


class ImageUnavailable(RuntimeError):
    pass


def supports_images(gateway, spec: str) -> bool:
    if gateway is None or not spec:
        return False
    m = gateway.registry.model_of(spec)
    return bool(m is not None and getattr(m, "supportsImages", False))


def vision_spec(gateway, spec: str = "") -> str:
    if supports_images(gateway, spec):
        return spec
    entry = gateway.registry.first_with_images() if gateway is not None else None
    return entry.spec if entry is not None else ""


async def image_parts(urls, *, gateway, spec: str) -> list[dict]:
    items = [str(u) for u in (urls or []) if u][:imagex.MAX_IMAGES]
    if not items:
        return []
    if supports_images(gateway, spec):
        return [{"type": "image_url",
                 "image_url": {"url": imagex.to_data_url(u) or u}}
                for u in items]
    v = vision_spec(gateway, spec)
    if not v:
        raise ImageUnavailable(
            "没有任何模型勾选「支持图像输入」：到 设置 → 供应商 → 模型 里"
            "给一个视觉模型打开 🖼，或换一个支持图像的模型")
    texts = await asyncio.gather(*[_describe(gateway, u, v) for u in items])
    return [{"type": "text", "text": t} for t in texts]


async def _describe(gateway, src: str, spec: str) -> str:
    r = await gateway.describe_image(src, prompt=DESCRIBE_PROMPT, spec=spec)
    if isinstance(r, dict) and r.get("ok"):
        return f"[图片转述]\n{r.get('text') or ''}"
    err_text = (r or {}).get("error") if isinstance(r, dict) else str(r)
    return f"[图片转述失败：{err_text or '未知原因'}]"
