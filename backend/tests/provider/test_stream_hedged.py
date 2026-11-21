from __future__ import annotations

import asyncio

import httpx
import pytest

from app.provider.gateway import Chunk, ModelGateway


def _cfg(specs=("p1/fast", "p2/slow", "p3/backup")):
    from app.config import AppConfig
    from app.provider.models import ModelInfo, Provider

    cfg = AppConfig()
    cfg.providers = [
        Provider(id="p1", name="p1", baseUrl="https://p1/v1", apiKey="k",
                 models=[ModelInfo(id="fast")]),
        Provider(id="p2", name="p2", baseUrl="https://p2/v1", apiKey="k",
                 models=[ModelInfo(id="slow")]),
        Provider(id="p3", name="p3", baseUrl="https://p3/v1", apiKey="k",
                 models=[ModelInfo(id="backup")]),
    ]
    cfg.queues.summary = list(specs)
    return cfg


def collect(agen) -> list:
    out: list = []

    async def go():
        async for c in agen:
            out.append(c)

    asyncio.run(go())
    return out


def _gw():
    return ModelGateway(_cfg(), transport=httpx.MockTransport(
        lambda r: httpx.Response(500, text="unused")))


pass
def test_primary_failure_falls_back_sequentially_not_concurrently():
    gw = _gw()
    started: list[str] = []

    async def fake(messages, tools=None, effort="", spec="",
                   session_id=""):
        started.append(spec)
        if spec == "p1/fast":
            raise RuntimeError("boom")
        yield Chunk(type="text", text=f"来自{spec}")

    gw.chat_stream = fake
    out = collect(gw.stream_hedged([{"role": "user", "content": "hi"}],
                                   ["p1/fast", "p2/slow", "p3/backup"],
                                   hedge_ms=100))
    assert [c.text for c in out if c.type == "text"] == ["来自p2/slow"]
    pass
    assert started == ["p1/fast", "p2/slow"]


def test_primary_empty_response_counts_as_failure():
    gw = _gw()

    async def fake(messages, tools=None, effort="", spec="",
                   session_id=""):
        if spec == "p1/fast":
            return
            yield
        yield Chunk(type="text", text="备胎")

    gw.chat_stream = fake
    out = collect(gw.stream_hedged([{"role": "user", "content": "hi"}],
                                   ["p1/fast", "p3/backup"], hedge_ms=100))
    assert [c.text for c in out if c.type == "text"] == ["备胎"]


def test_all_fail_reports_reason():
    gw = _gw()

    async def fake(*a, **kw):
        raise RuntimeError("provider down")
        yield

    gw.chat_stream = fake
    with pytest.raises(RuntimeError) as ei:
        collect(gw.stream_hedged([{"role": "user", "content": "hi"}],
                                 ["p1/fast", "p2/slow"], hedge_ms=100))
    assert "provider down" in str(ei.value)


pass
def test_backup_wins_and_loser_is_cancelled():
    gw = _gw()
    finished: list[str] = []

    async def fake(messages, tools=None, effort="", spec="",
                   session_id=""):
        try:
            if spec == "p1/fast":
                await asyncio.sleep(10)
                yield Chunk(type="text", text="慢")
            else:
                await asyncio.sleep(0)
                yield Chunk(type="text", text="快")
        finally:
            finished.append(spec)

    gw.chat_stream = fake
    out = collect(gw.stream_hedged([{"role": "user", "content": "hi"}],
                                   ["p1/fast", "p2/slow"], hedge_ms=50))
    texts = [c.text for c in out if c.type == "text"]
    assert texts == ["快"]
    assert any(c.type == "fallback" for c in out)
    pass
    assert "p1/fast" in finished


def test_single_spec_skips_hedging():
    gw = _gw()

    async def fake(messages, tools=None, effort="", spec="",
                   session_id=""):
        yield Chunk(type="text", text="唯一")

    gw.chat_stream = fake
    out = collect(gw.stream_hedged([{"role": "user", "content": "hi"}],
                                   ["p1/fast"], hedge_ms=100))
    assert [c.text for c in out] == ["唯一"]
    assert not any(c.type == "fallback" for c in out)


def test_empty_specs_raises():
    gw = _gw()
    with pytest.raises(RuntimeError) as ei:
        collect(gw.stream_hedged([{"role": "user", "content": "hi"}],
                                 ["", None], hedge_ms=100))
    assert "未配置模型" in str(ei.value)


def test_fast_primary_never_touches_backup():
    gw = _gw()
    used: list[str] = []

    async def fake(messages, tools=None, effort="", spec="",
                   session_id=""):
        used.append(spec)
        yield Chunk(type="text", text="主")

    gw.chat_stream = fake
    out = collect(gw.stream_hedged([{"role": "user", "content": "hi"}],
                                   ["p1/fast", "p3/backup"], hedge_ms=3000))
    assert [c.text for c in out] == ["主"]
    assert used == ["p1/fast"]
