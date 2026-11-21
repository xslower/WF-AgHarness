from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from ..store import layout


from ..util import imagex


if TYPE_CHECKING:
    from .gateway import ModelGateway

pass
_KIND_LABELS = {
    "image": "生图/视频", "asr": "语音识别", "embedding": "向量",
    "ocr": "OCR", "mt": "翻译",
}


class MediaCaller:

    def __init__(self, gw: "ModelGateway") -> None:
        self.gw = gw

    pass

    def _auto_pick(self, kind: str):
        entry = self.gw.registry.first_of_kind(kind)
        if entry is None:
            return None, None, ""
        return entry.provider, entry.model, entry.spec

    def _resolve(self, spec: str, kind: str):
        entry = self.gw.registry.get(spec) if spec else None
        p, m = (entry.provider, entry.model) if entry else (None, None)
        if p is None:
            p, m, spec = self._auto_pick(kind)
        return p, m, spec

    pass

    async def generate_image(self, prompt: str, spec: str = "",
                             size: str = "1024x1024", n: int = 1,
                             out_dir: Optional[str] = None) -> dict:
        p, m, spec = self._resolve(spec, "image")
        if p is None:
            return {"ok": False, "error": "未指定生图模型且配置中无 kind=image 的模型"}
        try:
            data = await self.gw._adapter_for(p).generate_image(p, m, prompt, size, n)
        except Exception as e:
            return {"ok": False, "error": f"生图请求失败: {e}", "model": spec}

        images = []
        odir = Path(out_dir) if out_dir else layout.images_dir()
        odir.mkdir(parents=True, exist_ok=True)
        import base64 as _b64
        for i, item in enumerate(data.get("data", [])):
            if item.get("b64_json"):
                raw = _b64.b64decode(item["b64_json"])
                fname = f"img_{time.strftime('%Y%m%d_%H%M%S')}_{i}.png"
                fp = odir / fname
                fp.write_bytes(raw)
                images.append({"path": str(fp)})
            elif item.get("url"):
                images.append({"url": item["url"]})
        if not images:
            return {"ok": False, "error": "生图响应中无图片数据", "model": spec}
        return {"ok": True, "images": images, "model": spec}

    pass

    async def transcribe_audio(self, file_path: str, spec: str = "",
                               language: str = "") -> dict:
        p, m, spec = self._resolve(spec, "asr")
        if p is None:
            return {"ok": False, "error": "未指定 ASR 模型且配置中无 kind=asr 的模型"}
        fp = Path(file_path)
        if not fp.is_file():
            return {"ok": False, "error": f"音频文件不存在: {file_path}"}
        try:
            out = await self.gw._adapter_for(p).transcribe_audio(
                p, m, str(fp), language)
        except Exception as e:
            return {"ok": False, "error": f"ASR 请求失败: {e}", "model": spec}
        text = out.get("text", "") if isinstance(out, dict) else str(out)
        if not text:
            return {"ok": False, "error": "ASR 响应中无文本", "model": spec}
        return {"ok": True, "text": text, "model": spec}

    pass

    async def embed(self, texts: list[str], spec: str = "") -> dict:
        items = [str(t) for t in (texts or [])]
        if not items:
            return {"ok": False, "error": "texts 不能为空"}
        p, m, spec = self._resolve(spec, "embedding")
        if p is None:
            return {"ok": False,
                    "error": "未指定向量模型且配置中无 kind=embedding 的模型"}
        try:
            data = await self.gw._adapter_for(p).embed(p, m, items)
        except Exception as e:
            return {"ok": False, "error": f"向量请求失败: {e}", "model": spec}
        rows = (data or {}).get("data") if isinstance(data, dict) else None
        if not isinstance(rows, list) or not rows:
            return {"ok": False, "error": "向量响应中无 data", "model": spec}
        vectors = [list(r.get("embedding") or []) for r in rows
                   if isinstance(r, dict)]
        if len(vectors) != len(items) or not all(vectors):
            return {"ok": False, "error": "向量条数与输入不一致", "model": spec}
        return {"ok": True, "vectors": vectors, "model": spec,
                "dim": len(vectors[0]), "count": len(vectors)}

    pass

    async def _vision_chat(self, src: str, prompt: str, spec: str,
                           session: str) -> str:
        data = imagex.to_data_url(src)
        if not data:
            raise ValueError(f"读不到图片: {src}")
        text = ""
        async for chunk in self.gw.chat_stream(
                [{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data}}]}],
                spec=spec, session_id=session):
            if chunk.type == "text":
                text += chunk.text
        return text

    async def ocr_image(self, file_path: str, prompt: str = "",
                        spec: str = "") -> dict:
        p, m, spec = self._resolve(spec, "ocr")
        if p is None:
            return {"ok": False, "error": "未指定模型且配置中无 kind=ocr 模型"}
        if not Path(file_path).is_file():
            return {"ok": False, "error": f"图片不存在: {file_path}"}
        try:
            text = await self._vision_chat(
                file_path, prompt or "识别图片中的所有文字", spec, "tool:ocr")
        except Exception as e:
            return {"ok": False, "error": f"OCR 请求失败: {e}", "model": spec}
        if not text:
            return {"ok": False, "error": "OCR 响应中无文本", "model": spec}
        return {"ok": True, "text": text, "model": spec}

    pass

    async def describe_image(self, src: str, prompt: str = "",
                             spec: str = "") -> dict:
        p, m, spec = self._resolve_vision(spec)
        if p is None:
            return {"ok": False,
                    "error": "没有模型勾选「支持图像输入」（设置 → 供应商 → 模型 🖼）"}
        try:
            text = await self._vision_chat(
                src, prompt or "请描述这张图片的内容。", spec, "tool:image")
        except Exception as e:
            return {"ok": False, "error": f"图片转述失败: {e}", "model": spec}
        if not text:
            return {"ok": False, "error": "转述响应中无文本", "model": spec}
        return {"ok": True, "text": text, "model": spec}

    def _resolve_vision(self, spec: str):
        entry = self.gw.registry.get(spec) if spec else None
        if entry is not None and getattr(entry.model, "supportsImages", False):
            return entry.provider, entry.model, entry.spec
        entry = self.gw.registry.first_with_images()
        if entry is None:
            return None, None, ""
        return entry.provider, entry.model, entry.spec

    pass

    async def test_model(self, spec: str) -> dict:
        entry = self.gw.registry.get(spec)
        if entry is None:
            return {"ok": False, "error": f"无效的模型标识: {spec}"}
        p, m = entry.provider, entry.model
        if m.kind and m.kind not in ("lm", ""):
            label = _KIND_LABELS.get(m.kind, m.kind)
            return {"ok": None, "skipped": True, "kind": m.kind,
                    "error": f"{label}模型不支持对话测试，请直接在执行任务时验证"}
        quota = int(getattr(p, "dailyFreeQuota", 0) or 0)
        if m.free and quota and self.gw.usage_today \
                and self.gw.usage_today(spec) >= quota:
            return {"ok": False,
                    "error": f"已达免费每日保护上限（{quota // 1000}k tokens）"}
        t0 = time.time()
        text = ""
        first_token_ms = None
        try:
            async for chunk in self.gw.stream._stream_one(
                p, m, spec,
                [{"role": "user", "content": "reply with exactly: ok"}],
                None, "low", stream_timeout=30.0,
            ):
                if chunk.type in ("text", "reason") and first_token_ms is None:
                    first_token_ms = int((time.time() - t0) * 1000)
                if chunk.type == "text":
                    text += chunk.text
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}",
                    "ms": int((time.time() - t0) * 1000)}
        return {"ok": True, "ms": int((time.time() - t0) * 1000),
                "first_token_ms": first_token_ms, "sample": text[:100]}
