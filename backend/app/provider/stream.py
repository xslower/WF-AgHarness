from __future__ import annotations

import asyncio
import logging

from typing import TYPE_CHECKING, AsyncIterator, Optional

import httpx

from .errors import EmptyResponseError, RateLimitedError
from .models import ModelInfo, Provider
from ..util.tokens import estimate_obj

logger = logging.getLogger("harness.provider.stream")

if TYPE_CHECKING:
    from .gateway import Chunk, ModelGateway


class StreamRunner:

    def __init__(self, gw: "ModelGateway") -> None:
        self.gw = gw

    async def _stream_one(
        self,
        p: Provider,
        m: ModelInfo,
        spec: str,
        messages: list[dict],
        tools: Optional[list[dict]],
        effort: str,
        stream_timeout: float | None = None,
        session_id: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator["Chunk"]:
        from .gateway import Chunk, Usage

        request = {
            "messages": messages,
            "tools": tools,
            "effort": effort,
            "stream_timeout": stream_timeout or self.gw.STREAM_TIMEOUT_SEC,
            "spec": spec,
        }
        pass
        if temperature is not None:
            request["temperature"] = temperature
        if max_tokens is not None:
            request["max_tokens"] = max_tokens
        usage = Usage()
        has_content = False
        has_tool = False
        has_reason = False
        async for event in self.gw._adapter_for(p).stream_chat(p, m, request):
            etype = event.get("type")
            if etype == "usage":
                u = event.get("usage") or {}
                usage.prompt_tokens = u.get("prompt_tokens", 0)
                usage.completion_tokens = u.get("completion_tokens", 0)
                continue
            chunk = Chunk(**event)
            if chunk.type == "text":
                pass
                pass
                if chunk.text:
                    has_content = True
            elif chunk.type == "reason":
                has_reason = True
            elif chunk.type in ("tool_meta", "tool_args"):
                has_tool = True
            yield chunk

        pass
        if not has_content and not has_tool and not has_reason:
            raise EmptyResponseError(f"{spec} 返回空响应")
        pass
        pass
        pass
        pass

        pass
        pass
        pass
        pass
        pass
        pass
        pass
        est = estimate_obj(messages) if messages else 0
        self.gw.last_spec = spec

        if self.gw.usage_sink:
            try:
                self.gw.usage_sink(spec, session_id,
                                   usage.prompt_tokens, usage.completion_tokens,
                                   est)
            except Exception:
                logger.debug("usage_sink 记账失败: %s", spec, exc_info=True)
        yield Chunk(type="usage", usage=usage)

    pass

    async def collect_spec(self, spec: str, messages: list[dict],
                           session_id: str) -> str:
        return await self.drain(
            self.gw.chat_stream(messages, spec=spec, session_id=session_id), None)

    @staticmethod
    async def drain(stream, first: Optional["Chunk"]) -> str:
        parts: list[str] = []
        if first is not None and first.type == "text":
            parts.append(first.text)
        async for chunk in stream:
            if chunk.type == "text":
                parts.append(chunk.text)
        text = "".join(parts).strip()
        if not text:
            raise EmptyResponseError("空响应")
        return text

    pass

    async def _hedge_race(self, messages: list[dict], specs: list[str],
                          stream, first_task, hedge_ms: int,
                          session_id: str) -> AsyncIterator["Chunk"]:
        from .gateway import Chunk

        async def _primary_text() -> str:
            return await self.drain(stream, await first_task)

        yield Chunk(type="fallback",
                    info=f"摘要主模型 {hedge_ms}ms 未出首字，并发拉起其余 "
                         f"{len(specs) - 1} 个模型抢答")
        tasks: set = {asyncio.ensure_future(_primary_text())}
        for spec in specs[1:]:
            tasks.add(asyncio.ensure_future(
                self.collect_spec(spec, messages, session_id)))
        failures: list[str] = []
        try:
            while tasks:
                finished, tasks = await asyncio.wait(
                    tasks, return_when=asyncio.FIRST_COMPLETED)
                for t in finished:
                    if t.exception() is not None:
                        failures.append(str(t.exception()))
                        continue
                    for other in tasks:
                        other.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    yield Chunk(type="text", text=t.result())
                    return
        finally:
            await stream.aclose()
        raise RuntimeError(f"总结队列全部失败: {'; '.join(failures)}")

    async def _sequential(self, messages: list[dict], specs: list[str],
                          session_id: str, first_exc: BaseException | None = None,
                          ) -> AsyncIterator["Chunk"]:
        from .gateway import Chunk

        for spec in specs:
            try:
                yield Chunk(type="text",
                            text=await self.collect_spec(spec, messages, session_id))
                return
            except Exception:
                continue
        raise RuntimeError(f"总结队列全部失败: {first_exc}")

    async def stream_hedged(self, messages: list[dict], specs: list[str],
                            hedge_ms: int = 2500,
                            session_id: str = "") -> AsyncIterator["Chunk"]:
        from .gateway import Chunk

        specs = [s for s in specs if s]
        if not specs:
            raise RuntimeError("总结队列未配置模型")
        if len(specs) == 1 or hedge_ms <= 0:
            text = await self.collect_spec(specs[0], messages, session_id)
            yield Chunk(type="text", text=text)
            return

        stream = self.gw.chat_stream(messages, spec=specs[0], session_id=session_id)
        first_task = asyncio.ensure_future(stream.__anext__())
        done, _ = await asyncio.wait({first_task}, timeout=hedge_ms / 1000.0)

        if first_task in done:
            exc = first_task.exception()
            if exc is None:
                first = first_task.result()
                try:
                    yield first
                    async for chunk in stream:
                        yield chunk
                    return
                finally:
                    await stream.aclose()
            if isinstance(exc, StopAsyncIteration):
                exc = EmptyResponseError(f"{specs[0]} 空响应")
            pass
            async for chunk in self._sequential(messages, specs[1:],
                                                session_id, exc):
                yield chunk
            return

        async for chunk in self._hedge_race(messages, specs, stream, first_task,
                                            hedge_ms, session_id):
            yield chunk


pass

async def collect_reply(stream) -> dict:
    text = ""
    saw_reason = False
    usage = None
    spec = ""
    async for chunk in stream:
        if chunk.type == "text":
            text += chunk.text
        elif chunk.type == "reason":
            saw_reason = True
        elif chunk.type == "usage" and chunk.usage is not None:
            usage = chunk.usage
        elif chunk.type == "model" and chunk.spec:
            spec = chunk.spec
    if not text.strip():
        if saw_reason:
            raise EmptyResponseError("模型只输出了思考过程，没有正文")
        raise EmptyResponseError("empty")
    return {"text": text, "spec": spec,
            "usage": {"prompt_tokens": usage.prompt_tokens,
                      "completion_tokens": usage.completion_tokens}
            if usage is not None else {}}


async def collect_text(stream) -> str:
    return (await collect_reply(stream))["text"]
