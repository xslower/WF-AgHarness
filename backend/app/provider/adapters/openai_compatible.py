from __future__ import annotations

import json
from pathlib import Path
from typing import Any, AsyncIterator, Optional

import httpx

from ..errors import RateLimitedError
from .openai_sse import error_from_status, parse_sse
from .protocol_wire import wire_messages
from ..spec import CONNECT_TIMEOUT_SEC, STREAM_TIMEOUT_SEC


def wire_id(model: Any) -> str:
    w = getattr(model, "wireId", "") or ""
    return w or getattr(model, "id", "")


class OpenAICompatibleAdapter:

    kind = "openai_compatible"

    def __init__(self, transport: Optional[httpx.BaseTransport] = None) -> None:
        self._transport = transport

    @staticmethod
    def endpoint(provider: Any, path: str) -> str:
        return provider.baseUrl.rstrip("/") + "/" + path.lstrip("/")

    @staticmethod
    def headers(provider: Any) -> dict:
        return {"Authorization": f"Bearer {provider.apiKey}",
                "Content-Type": "application/json"}

    pass
    pass

    async def list_models(self, provider: Any) -> list[dict[str, Any]]:
        url = self.endpoint(provider, "models")
        async with httpx.AsyncClient(timeout=15, transport=self._transport) as client:
            r = await client.get(url, headers=self.headers(provider))
            r.raise_for_status()
            return [m for m in r.json().get("data", []) if m.get("id")]

    def stream_chat(self, provider: Any, model: Any,
                    request: dict[str, Any]) -> AsyncIterator[Any]:
        return self._stream(provider, model, request)

    async def _stream(self, provider: Any, model: Any,
                      request: dict[str, Any]) -> AsyncIterator[dict]:
        body = self._request_body(model, request)
        timeout = httpx.Timeout(
            request.get("stream_timeout") or STREAM_TIMEOUT_SEC,
            connect=CONNECT_TIMEOUT_SEC)
        url = self.endpoint(provider, "chat/completions")
        headers = self.headers(provider)
        try:
            async with httpx.AsyncClient(timeout=timeout, transport=self._transport) as client:
                async with client.stream(
                        "POST", url, headers=headers, json=body) as resp:
                    detail = ""
                    if resp.status_code >= 400:
                        detail = (await resp.aread()).decode("utf-8", "replace")
                    err = error_from_status(resp.status_code, detail,
                                            str(request.get("spec", model.id)))
                    if err is not None:
                        pass
                        pass
                        if isinstance(err, RateLimitedError):
                            try:
                                ra = resp.headers.get("retry-after", "")
                                if ra:
                                    err.retry_after = float(ra)
                            except (TypeError, ValueError):
                                pass
                        raise err
                    async for ev in parse_sse(resp.aiter_lines()):
                        yield ev
        except httpx.TimeoutException as e:
            raise RuntimeError(f"timeout: {e}") from e

    @staticmethod
    def _wire_messages(messages: list) -> list:
        return wire_messages(messages)

    @staticmethod
    def _request_body(model: Any, request: dict[str, Any]) -> dict:
        body: dict = {
            "model": wire_id(model),
            "messages": OpenAICompatibleAdapter._wire_messages(request.get("messages") or []),
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        tools = request.get("tools")
        if tools:
            body["tools"] = tools
        pass
        for key in ("temperature", "max_tokens"):
            val = request.get(key)
            if val is not None:
                body[key] = val
            body["tools"] = tools
        pass
        pass
        pass
        pass
        pass
        if getattr(model, "supportsThinking", False):
            effort = (request.get("effort") or "medium").strip() or "medium"
            if effort != "off":
                body["reasoning_effort"] = effort
                body["enable_thinking"] = True
        return body

    async def generate_image(self, provider: Any, model: Any, prompt: str,
                             size: str = "1024x1024", n: int = 1) -> dict:
        url = self.endpoint(provider, "images/generations")
        body = {"model": wire_id(model), "prompt": prompt, "n": n, "size": size,
                "response_format": "b64_json"}
        async with httpx.AsyncClient(timeout=300, transport=self._transport) as client:
            r = await client.post(url, headers=self.headers(provider), json=body)
            r.raise_for_status()
            return r.json()

    async def transcribe_audio(self, provider: Any, model: Any, file_path: str,
                               language: str = "") -> dict:
        url = self.endpoint(provider, "audio/transcriptions")
        data = {"model": wire_id(model)}
        if language:
            data["language"] = language
        async with httpx.AsyncClient(timeout=600, transport=self._transport) as client:
            with open(file_path, "rb") as f:
                r = await client.post(url, headers=self.headers(provider),
                                      data=data,
                                      files={"file": (Path(file_path).name, f)})
            r.raise_for_status()
            return r.json()


    async def embed(self, provider: Any, model: Any, texts: list[str]) -> dict:
        url = self.endpoint(provider, "embeddings")
        body = {"model": wire_id(model), "input": list(texts)}
        async with httpx.AsyncClient(timeout=120, transport=self._transport) as client:
            r = await client.post(url, headers=self.headers(provider), json=body)
            r.raise_for_status()
            return r.json()
