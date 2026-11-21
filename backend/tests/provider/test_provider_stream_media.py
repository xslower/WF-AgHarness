from __future__ import annotations

import asyncio

import pytest

from app.config import AppConfig

from app.provider.models import ModelInfo, ModelQueues, Provider
from app.provider.errors import EmptyResponseError
from app.provider.gateway import Chunk, ModelGateway
from app.provider.media import MediaCaller
from app.provider.stream import StreamRunner


class _FakeAdapter:

    def __init__(self, scripts):
        self.scripts = scripts
        self.calls = 0

    def stream_chat(self, provider, model, request):
        script = self.scripts[min(self.calls, len(self.scripts) - 1)]
        self.calls += 1

        async def gen():
            for item in script:
                if isinstance(item, Exception):
                    raise item
                yield item

        return gen()

    def list_models(self, provider):
        return []

    async def generate_image(self, provider, model, prompt, size, n):
        return {"data": [{"url": "http://img/x.png"}]}

    async def transcribe_audio(self, provider, model, path, language):
        return {"text": "hello"}


class _Adapters:
    def __init__(self, adapter):
        self.adapter = adapter

    def resolve(self, kind="", adapter=""):
        return self.adapter


def _gw(scripts, kind="lm"):
    cfg = AppConfig(
        providers=[Provider(id="p1", name="p1", baseUrl="http://x/v1", apiKey="k",
                            models=[ModelInfo(id="m1", kind=kind)])],
        queues=ModelQueues(parent=["p1/m1"]),
    )
    adapter = _FakeAdapter(scripts)
    gw = ModelGateway(cfg, adapters=_Adapters(adapter))
    return gw, adapter


def test_gateway_holds_stream_and_media_components():
    gw, _ = _gw([[{"type": "text", "text": "hi"}]])
    assert isinstance(gw.stream, StreamRunner)
    assert isinstance(gw.media, MediaCaller)
    pass
    assert gw.stream.gw is gw
    assert gw.media.gw is gw


def test_gateway_stream_runner_collect_spec():
    gw, _ = _gw([[{"type": "text", "text": "答案"}]])
    assert asyncio.run(gw.stream.collect_spec("p1/m1", [], "")) == "答案"


def test_stream_runner_drain_staticmethod():

    async def gen():
        yield Chunk(type="text", text="ab")
        yield Chunk(type="reason", text="思考")

    assert asyncio.run(StreamRunner.drain(gen(), None)) == "ab"


def test_empty_response_error_is_single_class():
    import app.provider.gateway as g
    import app.provider.stream as s

    assert g.EmptyResponseError is EmptyResponseError
    assert s.EmptyResponseError is EmptyResponseError


def test_generate_image_delegates_to_media():
    gw, _ = _gw([[{"type": "text", "text": "x"}]], kind="image")
    out = asyncio.run(gw.generate_image("一只猫"))
    assert out["ok"] is True
    assert out["images"][0]["url"] == "http://img/x.png"


def test_generate_image_no_model_reports_clearly():
    cfg = AppConfig(
        providers=[Provider(id="p1", name="p1", baseUrl="http://x/v1", apiKey="k",
                            models=[ModelInfo(id="m1", kind="lm")])],
        queues=ModelQueues(parent=["p1/m1"]),
    )
    gw = ModelGateway(cfg, adapters=_Adapters(_FakeAdapter([[]])))
    out = asyncio.run(gw.generate_image("x"))
    assert out["ok"] is False
    assert "无 kind=image" in out["error"]


def test_test_model_rejects_non_chat_kind():
    gw, _ = _gw([[{"type": "text", "text": "ok"}]], kind="image")
    out = asyncio.run(gw.test_model("p1/m1"))
    assert out["ok"] is None and out["skipped"] is True
    assert "不支持对话测试" in out["error"]


pass

def test_embed_returns_model_and_dim():
    gw, adapter = _gw([[{"type": "text", "text": "x"}]], kind="embedding")
    adapter.embed = _fake_embed([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
    out = asyncio.run(gw.embed(["a", "b"]))
    assert out["ok"] is True
    assert out["model"] == "p1/m1"
    assert out["dim"] == 3 and out["count"] == 2
    assert out["vectors"] == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]


def test_embed_without_model_reports_clearly():
    cfg = AppConfig(
        providers=[Provider(id="p1", name="p1", baseUrl="http://x/v1", apiKey="k",
                            models=[ModelInfo(id="m1", kind="lm")])],
        queues=ModelQueues(parent=["p1/m1"]),
    )
    gw = ModelGateway(cfg, adapters=_Adapters(_FakeAdapter([[]])))
    out = asyncio.run(gw.embed(["a"]))
    assert out["ok"] is False
    assert "无 kind=embedding" in out["error"]


def test_embed_count_mismatch_is_error():
    gw, adapter = _gw([[{"type": "text", "text": "x"}]], kind="embedding")
    adapter.embed = _fake_embed([[0.1]])
    out = asyncio.run(gw.embed(["a", "b"]))
    assert out["ok"] is False and "条数" in out["error"]


def test_embed_empty_input_is_error():
    gw, _ = _gw([[{"type": "text", "text": "x"}]], kind="embedding")
    out = asyncio.run(gw.embed([]))
    assert out["ok"] is False


def _fake_embed(vectors):
    async def embed(provider, model, texts):
        return {"data": [{"embedding": v} for v in vectors]}
    return embed
