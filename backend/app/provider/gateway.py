from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator, Optional

import json

import httpx

from ..config import AppConfig, Provider, ModelInfo
from .adapters.registry import build_adapter_registry
from .availability import REASON_COOLING, REASON_QUOTA, Availability, AvailabilityChecker
from .registry import ModelRegistry
from .spec import (CONNECT_TIMEOUT_SEC, QUEUE_CHILD, QUEUE_PARENT,
                   QUEUE_SUMMARY, STREAM_TIMEOUT_SEC, ModelSpec, queue_of)
from ..util.timeutil import hm_and_weekday
from .errors import EmptyResponseError, RateLimitedError
from .media import MediaCaller
from .stream import StreamRunner, collect_text

logger = logging.getLogger("harness.gateway")


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class Chunk:
    type: str
    text: str = ""
    tool_index: int = 0
    usage: Optional[Usage] = None
    info: str = ""
    pass
    spec: str = ""


class ToolCallAcc:

    def __init__(self) -> None:
        self.parts: dict[int, dict] = {}

    def feed(self, chunk: Chunk) -> bool:
        if chunk.type == "tool_meta":
            meta = json.loads(chunk.text)
            t = self.parts.setdefault(chunk.tool_index, {"arguments": ""})
            t["id"] = t.get("id") or meta.get("id")
            t["name"] = t.get("name") or meta.get("name")
            return True
        if chunk.type == "tool_args":
            t = self.parts.setdefault(
                chunk.tool_index, {"id": "", "name": "", "arguments": ""})
            t["arguments"] += chunk.text
            return True
        return False

    def calls(self) -> list[dict]:
        return [{"id": t.get("id") or f"call_{i}", "type": "function",
                 "function": {"name": t.get("name", ""), "arguments": t["arguments"]}}
                for i, t in sorted(self.parts.items())]

    def __bool__(self) -> bool:
        return bool(self.parts)


@dataclass
class AssistantMsg:
    role: str = "assistant"
    content: Optional[str] = None
    tool_calls: list[dict] = field(default_factory=list)
    model: str = ""


@dataclass
class _Cooldown:
    until: float = 0.0


class ModelGateway:

    COOLDOWN_SEC = 60.0
    pass
    STREAM_TIMEOUT_SEC = STREAM_TIMEOUT_SEC
    CONNECT_TIMEOUT_SEC = CONNECT_TIMEOUT_SEC

    def __init__(self, config: AppConfig, transport: Optional[httpx.BaseTransport] = None,
                 adapters=None) -> None:
        self.config = config
        pass
        pass
        pass
        pass
        self.adapters = adapters if adapters is not None else build_adapter_registry(transport)
        pass
        self.registry = ModelRegistry(config)
        pass
        pass
        self._checker = AvailabilityChecker()
        pass
        pass
        self.stream = StreamRunner(self)
        self.media = MediaCaller(self)
        pass
        self._rate_hits: dict[str, int] = {}
        pass
        pass
        pass
        self._demoted: set[str] = set()
        self.usage_sink = None
        self.last_spec = ""
        self.usage_today = None
        self._checker.usage_today = lambda s: (
            self.usage_today(s) if self.usage_today else 0)

    _QUEUE_LABEL = {QUEUE_PARENT: "父", QUEUE_CHILD: "子", QUEUE_SUMMARY: "总结"}

    def _queue_specs(self, queue: str) -> list[str]:
        q = getattr(self.config.queues, queue, None)
        if not q and queue == QUEUE_SUMMARY:
            q = self.config.queues.child or self.config.queues.parent
        return list(q or self.config.queues.parent)

    @staticmethod
    def _queue_and_pin(spec: str) -> tuple[str, str]:
        s = ModelSpec.parse(spec)
        pin = "" if (s.is_auto or s.is_queue) else s.raw
        return queue_of(spec), pin

    def _ordered_specs(self, queue: str = QUEUE_PARENT,
                       pin: str = "") -> list[str]:
        if pin:
            return [pin]
        q = self._queue_specs(queue)
        if not q:
            raise RuntimeError(
                "未配置模型队列，请先在设置中添加 Provider 并配置父/子模型队列")
        now = self.now()
        fresh: list[str] = []
        demoted: list[str] = []
        soft: list[str] = []
        cooling: list[str] = []
        blocked: list[tuple[str, "Availability"]] = []
        for s in q:
            av = self._availability(s, now)
            if av.usable:
                (demoted if s in self._demoted else fresh).append(s)
            elif av.reason == REASON_COOLING:
                cooling.append(s)
            elif av.reason == REASON_QUOTA:
                soft.append(s)
            else:
                blocked.append((s, av))
        ordered = fresh + soft + demoted + cooling
        if ordered:
            return ordered
        raise RuntimeError(self._explain_queue(queue, q, blocked, cooling))

    pass

    pass
    pass
    now = staticmethod(time.time)

    def _availability(self, spec: str, now: float | None = None) -> "Availability":
        entry = self.registry.get(spec)
        if entry is None:
            return self._checker.check(spec, None, self.now() if now is None else now)
        return self._checker.check(spec, entry.model,
                                   self.now() if now is None else now,
                                   provider=entry.provider)

    def _explain_queue(self, queue: str, q: list[str],
                       blocked: list[tuple[str, "Availability"]],
                       cooling: list[str]) -> str:
        label = self._QUEUE_LABEL.get(queue, queue)
        if not q:
            return f"{label}队列是空的，先在设置里添加模型"
        parts = []
        for spec, av in blocked:
            parts.append(f"{spec}: {av.detail or av.reason}")
        for spec in cooling:
            av = self._availability(spec)
            parts.append(f"{spec}: {av.detail or '冷却中'}")
        return (f"{label}队列内模型均不可用（当前 {hm_and_weekday(self.now())[0]}）："
                + "; ".join(parts))


    def _cooldown_for(self, spec: str, p: Provider, err: Exception) -> float:
        base = float(getattr(p, "cooldownSec", 0) or self.COOLDOWN_SEC)
        n = self._rate_hits.get(spec, 0) + 1
        self._rate_hits[spec] = n
        retry_after = getattr(err, "retry_after", None)
        try:
            if retry_after:
                base = max(base, float(retry_after))
        except (TypeError, ValueError):
            pass
        return min(base * (2 ** (n - 1)), max(base, 1800.0))

    def reset_throttle_state(self) -> None:
        self._demoted.clear()
        self._rate_hits.clear()
        self._checker.cooldowns.clear()

    def _adapter_for(self, p: Provider):
        kind = getattr(p, "kind", "") or "openai_compatible"
        base = self.adapters.resolve(kind=kind, adapter=getattr(p, "adapter", "") or "")
        plugin_id = getattr(p, "pluginId", "") or ""
        if plugin_id:
            from .outbound import OUTBOUND
            from .adapters.switching import SwitchingAdapter
            handler = OUTBOUND.lookup(plugin_id)
            if handler is not None:
                return SwitchingAdapter(base, handler)
        return base

    async def fetch_models(self, p: Provider) -> list[str]:
        return [clean for clean, _ in await self.fetch_models_with_wire(p)]

    async def fetch_models_with_wire(self, p: Provider) -> list[tuple[str, str]]:
        models = await self._adapter_for(p).list_models(p)
        ids = [m.get("id") for m in models if isinstance(m, dict) and m.get("id")]
        from .ids import normalize_pairs
        return normalize_pairs(ids)

    async def chat_stream(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        effort: str = "",
        spec: str = "",
        session_id: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[Chunk]:
        effort = effort or getattr(self.config.settings, "defaultEffort", "medium") \
            or "medium"
        pass
        queue, pin = self._queue_and_pin(spec)
        specs = self._ordered_specs(queue, pin)
        if not specs:
            raise RuntimeError("未配置模型队列，请先在设置中添加 Provider 并配置父/子模型队列")
        last_err: Optional[Exception] = None
        failures: list[str] = []
        for spec in specs:
            entry = self.registry.get(spec)
            if entry is None:
                continue
            p, m = entry.provider, entry.model
            pass
            pass
            av = self._availability(spec)
            if not av.usable:
                pass
                pass
                failures.append(f"{spec}: {av.detail or av.reason}")
                yield Chunk(type="fallback", info=f"{spec} {av.detail or av.reason}，跳过")
                continue
            pass
            pass
            pass
            yield Chunk(type="model", spec=spec, info=entry.label)
            try:
                async for chunk in self.stream._stream_one(
                        p, m, spec, messages, tools, effort,
                        session_id=session_id, temperature=temperature,
                        max_tokens=max_tokens):
                    yield chunk
                self._checker.clear_cooldown(spec)
                self._rate_hits.pop(spec, None)
                pass
                self._demoted.discard(spec)
                return
            except EmptyResponseError as e:
                pass
                pass
                pass
                pass
                last_err = e
                failures.append(f"{spec}: 空响应")
                raise
            except RateLimitedError as e:
                last_err = e
                failures.append(f"{spec}: 限流")
                secs = self._cooldown_for(spec, p, e)
                self._checker.cool_down(spec, time.time() + secs)
                self._demoted.add(spec)
                yield Chunk(type="fallback",
                            info=f"{spec} 限流，冷却 {secs // 60} 分钟并降到队列末尾")
            except (httpx.HTTPError, RuntimeError) as e:
                last_err = e
                failures.append(f"{spec}: {e}")
                pass
                pass
                secs = self._cooldown_for(spec, p, e)
                self._checker.cool_down(spec, time.time() + secs)
                self._demoted.add(spec)
                yield Chunk(type="fallback",
                            info=f"{spec} 调用失败({type(e).__name__})，冷却 {secs // 60} 分钟并降到队列末尾")
        raise RuntimeError(self._explain_failures(queue, failures))

    def _explain_failures(self, queue: str, failures: list[str]) -> str:
        label = self._QUEUE_LABEL.get(queue, queue)
        if not failures:
            return f"{label}队列没有可尝试的模型"
        return f"{label}队列全部失败: " + "; ".join(failures)

    pass
    pass
    pass
    pass
    pass


    async def stream_hedged(self, messages: list[dict], specs: list[str],
                            hedge_ms: int = 2500,
                            session_id: str = "") -> AsyncIterator[Chunk]:
        async for chunk in self.stream.stream_hedged(
                messages, specs, hedge_ms=hedge_ms, session_id=session_id):
            yield chunk

    pass
    pass
    pass

    async def call_utility(self, kind: str, messages: list[dict],
                           session_id: str = "") -> str:
        u = getattr(self.config, "utility", None)
        specs = list(getattr(u, kind, []) or []) if u is not None else []
        if not specs:
            return ""
        text = ""
        ok = False
        failures: list[str] = []
        for spec in specs:
            try:
                text = await self._collect(messages, spec, session_id)
                ok = True
                break
            except Exception as e:
                failures.append(f"{kind}/{spec}: {type(e).__name__}: {e}")
        if not ok:
            for q in (QUEUE_CHILD, QUEUE_PARENT):
                if not self._ordered_specs(q):
                    continue
                try:
                    text = await self._collect_queue(messages, q, session_id)
                    ok = True
                    break
                except Exception as e:
                    failures.append(f"queue/{q}: {type(e).__name__}: {e}")
        if not ok:
            pass
            pass
            pass
            for line in failures:
                logger.warning("功能调用回退失败: %s", line)
            detail = f"（尝试 {len(failures)} 个来源均失败）" if failures else ""
            raise RuntimeError(f"功能调用无可用模型（专用模型与队列均失败）{detail}")
        return text

    async def _collect(self, messages: list[dict], spec: str,
                       session_id: str) -> str:
        pass
        return await collect_text(self.chat_stream(
            messages, spec=spec, session_id=session_id))

    async def _collect_queue(self, messages: list[dict], queue: str,
                             session_id: str) -> str:
        return await collect_text(self.chat_stream(
            messages, spec=queue, session_id=session_id))

    pass
    pass
    pass

    async def generate_image(self, prompt: str, spec: str = "",
                             size: str = "1024x1024", n: int = 1,
                             out_dir: Optional[str] = None) -> dict:
        return await self.media.generate_image(prompt, spec=spec, size=size,
                                               n=n, out_dir=out_dir)

    async def transcribe_audio(self, file_path: str, spec: str = "",
                               language: str = "") -> dict:
        return await self.media.transcribe_audio(file_path, spec=spec,
                                                 language=language)

    async def ocr_image(self, file_path: str, prompt: str = "",
                        spec: str = "") -> dict:
        return await self.media.ocr_image(file_path, prompt=prompt, spec=spec)

    async def describe_image(self, src: str, prompt: str = "",
                             spec: str = "") -> dict:
        return await self.media.describe_image(src, prompt=prompt, spec=spec)

    async def test_model(self, spec: str) -> dict:
        return await self.media.test_model(spec)

    async def embed(self, texts: list[str], spec: str = "") -> dict:
        return await self.media.embed(texts, spec=spec)
