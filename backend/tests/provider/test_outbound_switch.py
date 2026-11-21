from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.provider.adapters.openai_compatible import OpenAICompatibleAdapter
from app.provider.adapters.switching import SwitchingAdapter
from app.provider.models import ModelInfo, Provider
from app.provider.outbound import OUTBOUND, OutboundResponse


def _provider(name: str = "p1", plugin_id: str = "") -> Provider:
    kw = {"id": name, "name": name,
          "baseUrl": "https://p1.test/v1", "apiKey": "k"}
    if plugin_id:
        kw["pluginId"] = plugin_id
    return Provider(**kw)


def _sse() -> httpx.Response:
    return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"ok"}}]}\n'
                                     'data: [DONE]\n')


@pytest.fixture(autouse=True)
def _clean():
    OUTBOUND.clear()
    yield
    OUTBOUND.clear()


def _chat(adapter, provider=None, request=None):
    async def go():
        return [c async for c in adapter.stream_chat(
            provider or _provider(), ModelInfo(id="m1"),
            request or {"messages": [{"role": "user", "content": "hi"}],
                        "spec": "p1/m1", "stream_timeout": 5})]
    return asyncio.run(go())


def test_no_handler_request_is_byte_identical():
    seen: list[httpx.Request] = []
    base = OpenAICompatibleAdapter(transport=httpx.MockTransport(
        lambda req: (seen.append(req), _sse())[1]))
    _chat(SwitchingAdapter(base, lambda req: None))
    assert len(seen) == 1
    assert seen[0].headers["Authorization"] == "Bearer k"
    assert seen[0].headers["Content-Type"] == "application/json"
    body = json.loads(seen[0].content)
    assert body["model"] == "m1" and body["stream"] is True
    assert body["messages"] == [{"role": "user", "content": "hi"}]


def test_handler_takes_over_chat_stream():
    seen: list[httpx.Request] = []
    base = OpenAICompatibleAdapter(transport=httpx.MockTransport(
        lambda req: (seen.append(req), _sse())[1]))

    async def stream():
        yield {"choices": [{"delta": {"content": "switched"}}]}

    def handle(req):
        assert req.kind == "chat" and req.provider.pluginId == "mine"
        assert req.body["model"] == "m1"
        return OutboundResponse(stream=stream())

    adapter = SwitchingAdapter(base, handle)
    got = _chat(adapter, _provider(plugin_id="mine"))
    assert got == [{"choices": [{"delta": {"content": "switched"}}]}]
    assert seen == []


def test_handler_returning_none_falls_back_to_default():
    seen: list[httpx.Request] = []
    base = OpenAICompatibleAdapter(transport=httpx.MockTransport(
        lambda req: (seen.append(req), _sse())[1]))
    _chat(SwitchingAdapter(base, lambda req: None), _provider(plugin_id="mine"))
    assert len(seen) == 1


def test_bad_handler_does_not_break_request():
    seen: list[httpx.Request] = []
    base = OpenAICompatibleAdapter(transport=httpx.MockTransport(
        lambda req: (seen.append(req), _sse())[1]))

    def boom(req):
        raise RuntimeError("bad plugin")

    _chat(SwitchingAdapter(base, boom), _provider(plugin_id="mine"))
    assert len(seen) == 1


def test_lookup_is_by_plugin_id_and_last_register_wins():
    def a(req):
        return None

    def b(req):
        return None

    OUTBOUND.register("mine", a)
    assert OUTBOUND.lookup("mine") is a
    assert OUTBOUND.lookup("other") is None
    OUTBOUND.register("mine", b)
    assert OUTBOUND.lookup("mine") is b
    assert OUTBOUND.active == {"mine": b}
    OUTBOUND.unregister("mine")
    assert OUTBOUND.lookup("mine") is None


def test_models_handler_can_override_list():
    base = OpenAICompatibleAdapter(transport=httpx.MockTransport(
        lambda req: httpx.Response(200, json={"data": [{"id": "default"}]})))

    def handle(req):
        assert req.kind == "models" and req.method == "GET"
        return OutboundResponse(data=[{"id": "switched"}])

    got = asyncio.run(SwitchingAdapter(base, handle).list_models(
        _provider(plugin_id="mine")))
    assert got == [{"id": "switched"}]
