import asyncio
import json

import httpx
import pytest

from app.provider.models import ModelInfo, Provider
from app.provider.errors import RateLimitedError
from app.provider.adapters.openai_compatible import OpenAICompatibleAdapter
from app.provider.adapters.registry import build_adapter_registry


def _provider() -> Provider:
    return Provider(id="p1", name="p1", baseUrl="https://p1.test/v1", apiKey="k")


def _request() -> dict:
    return {"messages": [{"role": "user", "content": "hi"}], "tools": None,
            "spec": "p1/m1", "stream_timeout": 5}


def sse(chunks: list[dict], usage: dict | None = None, status: int = 200):
    events = [f"data: {json.dumps(c)}" for c in chunks]
    if usage:
        events.append(f"data: {json.dumps({'usage': usage})}")
    events.append("data: [DONE]")
    return httpx.Response(status, text="\n".join(events) + "\n")


def collect(agen):
    out = []

    async def go():
        async for item in agen:
            out.append(item)

    asyncio.run(go())
    return out


def test_stream_parses_text_reason_and_tool_calls():
    chunks = [
        {"choices": [{"delta": {"reasoning_content": "想想"}}]},
        {"choices": [{"delta": {"content": "你好"}}]},
        {"choices": [{"delta": {"tool_calls": [
            {"index": 0, "id": "c1",
             "function": {"name": "read_file", "arguments": '{"pa'}}]}}]},
        {"choices": [{"delta": {"tool_calls": [
            {"index": 0, "function": {"arguments": 'th":"x"}'}}]}}]},
    ]
    adapter = OpenAICompatibleAdapter(transport=httpx.MockTransport(
        lambda req: sse(chunks, usage={"prompt_tokens": 10, "completion_tokens": 5})))
    events = collect(adapter.stream_chat(_provider(), ModelInfo(id="m1", supportsThinking=True),
                                         _request()))

    assert "".join(e["text"] for e in events if e["type"] == "reason") == "想想"
    assert "".join(e["text"] for e in events if e["type"] == "text") == "你好"
    meta = [json.loads(e["text"]) for e in events if e["type"] == "tool_meta"]
    assert meta == [{"id": "c1", "name": "read_file"}]
    args = "".join(e["text"] for e in events if e["type"] == "tool_args")
    assert args == '{"path":"x"}'
    usage = next(e["usage"] for e in events if e["type"] == "usage")
    assert usage == {"prompt_tokens": 10, "completion_tokens": 5}


def test_stream_429_raises_rate_limited():
    adapter = OpenAICompatibleAdapter(transport=httpx.MockTransport(
        lambda req: httpx.Response(429, text="rate limited")))
    with pytest.raises(RateLimitedError):
        collect(adapter.stream_chat(_provider(), ModelInfo(id="m1"), _request()))


def test_stream_http_error_has_status_detail():
    adapter = OpenAICompatibleAdapter(transport=httpx.MockTransport(
        lambda req: httpx.Response(400, text="bad request")))
    with pytest.raises(RuntimeError, match="HTTP 400"):
        collect(adapter.stream_chat(_provider(), ModelInfo(id="m1"), _request()))


def test_list_models_returns_model_dicts():
    adapter = OpenAICompatibleAdapter(transport=httpx.MockTransport(
        lambda req: httpx.Response(200, json={"data": [{"id": "a"}, {"id": "b"}, {}]})))
    models = asyncio.run(adapter.list_models(_provider()))
    assert models == [{"id": "a"}, {"id": "b"}]


def test_registry_resolves_by_kind_and_adapter_name():
    reg = build_adapter_registry()
    assert reg.resolve(kind="openai_compatible").kind == "openai_compatible"
    assert reg.resolve(kind="env_preset").kind == "openai_compatible"
    assert reg.resolve(adapter="openai-compatible").kind == "openai_compatible"
    assert reg.resolve(kind="unknown-kind").kind == "openai_compatible"


def test_schema_and_config_smoke(client):
    assert client.get("/api/config").status_code == 200
    r = client.get("/api/providers/schema")
    assert r.status_code == 200, r.text
    body = r.json()
    assert {k["kind"] for k in body["kinds"]} == {"openai_compatible", "env_preset"}
    assert any(p["id"] == "siliconflow" for p in body["presets"])



pass

def test_adapter_embed_posts_input_and_returns_json():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["url"] = str(req.url)
        seen["body"] = json.loads(req.content.decode())
        return httpx.Response(200, json={
            "data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}],
            "usage": {"prompt_tokens": 4, "total_tokens": 4}})

    adapter = OpenAICompatibleAdapter(transport=httpx.MockTransport(handler))
    out = asyncio.run(adapter.embed(_provider(),
                                    ModelInfo(id="m1", wireId="wire-e"),
                                    ["甲", "乙"]))
    assert seen["url"] == "https://p1.test/v1/embeddings"
    assert seen["body"] == {"model": "wire-e", "input": ["甲", "乙"]}
    assert [r["embedding"] for r in out["data"]] == [[0.1, 0.2], [0.3, 0.4]]
