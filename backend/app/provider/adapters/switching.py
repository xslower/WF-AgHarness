from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Optional

from ..outbound import OUTBOUND, OutboundHandler, OutboundRequest, OutboundResponse

logger = logging.getLogger("harness.switching")


class SwitchingAdapter:

    def __init__(self, base: Any, handler: OutboundHandler) -> None:
        self._base = base
        self._handler = handler

    async def _call(self, req: OutboundRequest, what: str):
        try:
            result = self._handler(req)
            if asyncio.iscoroutine(result):
                result = await result
            if isinstance(result, OutboundResponse):
                return result
            logger.warning("outbound switch %s handler returned non-response: %r",
                           what, type(result))
        except Exception as e:
            logger.warning("outbound switch %s handler failed: %s, fallback to default",
                           what, e)
        return None

    pass

    async def list_models(self, provider: Any) -> list[dict[str, Any]]:
        req = OutboundRequest(
            kind="models",
            provider=provider,
            model=None,
            method="GET",
            url=self._base.endpoint(provider, "models") if hasattr(self._base, "endpoint") else "",
            headers=self._base.headers(provider) if hasattr(self._base, "headers") else {},
            transport=getattr(self._base, "_transport", None),
        )
        resp = await self._call(req, "models")
        if resp is not None and resp.data is not None:
            return resp.data
        return await self._base.list_models(provider)

    pass

    async def stream_chat(self, provider: Any, model: Any,
                          request: dict[str, Any]) -> AsyncIterator[dict]:
        req = OutboundRequest(
            kind="chat",
            provider=provider,
            model=model,
            method="POST",
            url=self._base.endpoint(provider, "chat/completions") if hasattr(self._base, "endpoint") else "",
            headers=self._base.headers(provider) if hasattr(self._base, "headers") else {},
            body=self._base._request_body(model, request) if hasattr(self._base, "_request_body") else {},
            request=request,
            timeout=getattr(self._base, "STREAM_TIMEOUT_SEC", 120.0),
            transport=getattr(self._base, "_transport", None),
        )
        resp = await self._call(req, "chat")
        if resp is not None and resp.stream is not None:
            async for chunk in resp.stream:
                yield chunk
            return
        async for chunk in self._base.stream_chat(provider, model, request):
            yield chunk

    pass

    async def generate_image(self, provider: Any, model: Any, prompt: str,
                             size: str = "", n: int = 1) -> dict:
        req = OutboundRequest(
            kind="image",
            provider=provider,
            model=model,
            method="POST",
            url=self._base.endpoint(provider, "images/generations") if hasattr(self._base, "endpoint") else "",
            headers=self._base.headers(provider) if hasattr(self._base, "headers") else {},
            body={"prompt": prompt, "size": size, "n": n},
            transport=getattr(self._base, "_transport", None),
        )
        resp = await self._call(req, "image")
        if resp is not None and resp.data is not None:
            return resp.data
        return await self._base.generate_image(provider, model, prompt, size, n)

    pass

    async def transcribe_audio(self, provider: Any, model: Any,
                               file_path: str, language: str = "") -> dict:
        req = OutboundRequest(
            kind="audio",
            provider=provider,
            model=model,
            file_path=file_path,
            transport=getattr(self._base, "_transport", None),
        )
        resp = await self._call(req, "audio")
        if resp is not None and resp.data is not None:
            return resp.data
        return await self._base.transcribe_audio(provider, model, file_path, language)

    pass

    async def embed(self, provider: Any, model: Any, texts: list[str]) -> dict:
        req = OutboundRequest(
            kind="embed",
            provider=provider,
            model=model,
            method="POST",
            url=self._base.endpoint(provider, "embeddings") if hasattr(self._base, "endpoint") else "",
            headers=self._base.headers(provider) if hasattr(self._base, "headers") else {},
            body={"model": getattr(model, "wireId", "") or getattr(model, "id", ""),
                  "input": list(texts)},
            transport=getattr(self._base, "_transport", None),
        )
        resp = await self._call(req, "embed")
        if resp is not None and resp.data is not None:
            return resp.data
        return await self._base.embed(provider, model, texts)
