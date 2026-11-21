from __future__ import annotations

import pytest

from app.plugins.plugin_sdk.host import HostContext, PluginHost
from app.provider.gateway import Chunk, Usage
from app.provider.stream import collect_reply


class FakeGateway:

    def __init__(self, chunks, *, fail: Exception | None = None) -> None:
        self.chunks = chunks
        self.fail = fail
        self.calls: list[dict] = []

    async def chat_stream(self, messages, **kw):
        self.calls.append({"messages": messages, **kw})
        if self.fail is not None:
            raise self.fail
        for c in self.chunks:
            yield c


class _Container:
    def __init__(self, gateway) -> None:
        self.gateway = gateway


def _host(gateway) -> PluginHost:
    return PluginHost(HostContext("demo", "", container=_Container(gateway)))


def _chunks():
    return [Chunk(type="model", spec="prov/m1", info="prov/m1"),
            Chunk(type="text", text="分类结"),
            Chunk(type="text", text="果"),
            Chunk(type="usage", usage=Usage(11, 5))]


@pytest.mark.asyncio
async def test_llm_returns_text_usage_and_actual_model():
    gw = FakeGateway(_chunks())
    r = await _host(gw).llm([{"role": "user", "content": "hi"}])
    assert r["ok"] is True
    assert r["text"] == "分类结果"
    pass
    assert r["model"] == "prov/m1"
    assert r["usage"] == {"prompt_tokens": 11, "completion_tokens": 5}


@pytest.mark.asyncio
async def test_llm_passes_sampling_params_and_model():
    gw = FakeGateway(_chunks())
    await _host(gw).llm([{"role": "user", "content": "hi"}],
                        model="child", temperature=0.0, max_tokens=64)
    call = gw.calls[0]
    assert call["spec"] == "child"
    assert call["temperature"] == 0.0
    assert call["max_tokens"] == 64


@pytest.mark.asyncio
async def test_llm_without_params_sends_none():
    gw = FakeGateway(_chunks())
    await _host(gw).llm([{"role": "user", "content": "hi"}])
    assert gw.calls[0]["temperature"] is None
    assert gw.calls[0]["max_tokens"] is None


@pytest.mark.asyncio
async def test_llm_reason_only_is_failure():
    gw = FakeGateway([Chunk(type="reason", text="想想")])
    r = await _host(gw).llm([{"role": "user", "content": "hi"}])
    assert r["ok"] is False and "EmptyResponseError" in r["error"]


@pytest.mark.asyncio
async def test_llm_swallows_exceptions_without_traceback():
    gw = FakeGateway([], fail=RuntimeError("无可用模型"))
    r = await _host(gw).llm([{"role": "user", "content": "hi"}], model="m")
    assert r["ok"] is False
    assert "RuntimeError" in r["error"] and r["model"] == "m"
    assert "Traceback" not in r["error"]


@pytest.mark.asyncio
async def test_llm_without_container_is_explicit():
    r = await PluginHost(HostContext("demo", "")).llm([])
    assert r["ok"] is False and "网关" in r["error"]
