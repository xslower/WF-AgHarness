from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.provider.ids import normalize_model_id, normalize_model_ids, normalize_pairs


pass
pass
pass
@pytest.mark.parametrize("raw,expect", [
    # 中转前缀
    ("trae-cn/Doubao-Seed-2.1-Turbo", "Doubao-Seed-2.1-Turbo"),
    ("trae-cn/gpt-4o", "gpt-4o"),
    ("TRAE-CN/gpt-4o", "gpt-4o"),
    ("trae/gpt-4o", "gpt-4o"),
    # 组织前缀：一律剥掉（这是本次改动的重点）
    ("nvidia/nemotron-3-super-120b-a12b:free", "nemotron-3-super-120b-a12b:free"),
    ("meta-llama/Llama-3-70B", "Llama-3-70B"),
    ("Qwen/Qwen3-32B", "Qwen3-32B"),
    ("deepseek-ai/DeepSeek-V3", "DeepSeek-V3"),
    ("openai/gpt-4o", "gpt-4o"),
    ("moonshotai/Kimi-K2", "Kimi-K2"),
    ("01-ai/Yi-34B", "Yi-34B"),
    # 多级前缀：剥到只剩模型名
    ("org/sub/model", "model"),
    # 无前缀
    ("gpt-4o-mini", "gpt-4o-mini"),
    # 剥完为空（id 就叫 trae-cn）→ 保留原值，不能变成空 id
    ("trae-cn", "trae-cn"),
    ("", ""),
])
def test_normalize_model_id(raw, expect):
    assert normalize_model_id(raw) == expect


def test_normalize_ids_dedup_keeps_order():
    assert normalize_model_ids(["trae-cn/b", "a", "b", "a"]) == ["b", "a"]


def test_normalize_pairs_keeps_wire_only_when_changed():
    pairs = normalize_pairs(["trae-cn/gpt-4o", "gpt-4o-mini",
                             "meta-llama/Llama-3-70B"])
    assert pairs == [
        ("gpt-4o", "trae-cn/gpt-4o"),
        ("gpt-4o-mini", ""),
        ("Llama-3-70B", "meta-llama/Llama-3-70B"),
    ]


pass
def _gw(handler):
    from app.config import AppConfig
    from app.provider.models import ModelInfo, Provider
    cfg = AppConfig()
    cfg.providers.append(Provider(id="tr", name="tr", baseUrl="https://tr.test/v1",
                                  apiKey="k", models=[]))
    return cfg, __import__("app.provider.gateway", fromlist=["ModelGateway"]).ModelGateway(
        cfg, transport=httpx.MockTransport(handler))


def test_fetch_models_strips_and_exposes_wire():
    cfg, gw = _gw(lambda req: httpx.Response(200, json={"data": [
        {"id": "trae-cn/gpt-4o"}, {"id": "meta-llama/Llama-3-70B"}]}))
    p = cfg.providers[0]
    pass
    assert asyncio.run(gw.fetch_models(p)) == ["gpt-4o", "Llama-3-70B"]
    assert asyncio.run(gw.fetch_models_with_wire(p)) == [
        ("gpt-4o", "trae-cn/gpt-4o"),
        ("Llama-3-70B", "meta-llama/Llama-3-70B"),
    ]


def test_chat_sends_wire_id_not_clean_id():
    bodies = []

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "trae-cn/gpt-4o"}]})
        bodies.append(req.read().decode())
        ev = json.dumps({"choices": [{"delta": {"content": "hi"}}]})
        return httpx.Response(200, text=f"data: {ev}\n\ndata: [DONE]\n\n")

    cfg, gw = _gw(handler)
    p = cfg.providers[0]
    asyncio.run(gw.fetch_models_with_wire(p))
    p.models.append(__import__("app.config", fromlist=["ModelInfo"]).ModelInfo(
        id="gpt-4o", wireId="trae-cn/gpt-4o"))
    cfg.queues.parent = ["tr/gpt-4o"]

    async def go():
        async for _ in gw.chat_stream([{"role": "user", "content": "hi"}]):
            pass
    asyncio.run(go())
    body = json.loads(bodies[0])
    assert body["model"] == "trae-cn/gpt-4o"
    assert body["model"] != "gpt-4o"


pass
def test_fetch_models_persists_wire_id(client, monkeypatch):
    pid = client.post("/api/providers", json={
        "name": "trae", "baseUrl": "https://tr.test/v1", "apiKey": "k",
        "models": []}).json()["id"]

    async def fake(p):
        return [("gpt-4o", "trae-cn/gpt-4o"), ("Doubao-Turbo", "trae-cn/Doubao-Turbo")]

    import app.main as main_mod
    monkeypatch.setattr(main_mod.app.state.container.gateway,
                        "fetch_models_with_wire", fake)
    r = client.post(f"/api/providers/{pid}/fetch_models")
    assert r.status_code == 200
    models = {m["id"]: m for m in r.json()["models"]}
    assert set(models) == {"gpt-4o", "Doubao-Turbo"}
    assert models["gpt-4o"]["wireId"] == "trae-cn/gpt-4o"

    pass
    assert client.delete(f"/api/providers/{pid}/models/gpt-4o").status_code == 200


def test_fetch_models_backfills_wire_id_for_old_rows(client, monkeypatch):
    pid = client.post("/api/providers", json={
        "name": "trae", "baseUrl": "https://tr.test/v1", "apiKey": "k",
        "models": [{"id": "gpt-4o"}]}).json()["id"]

    async def fake(p):
        return [("gpt-4o", "trae-cn/gpt-4o")]

    import app.main as main_mod
    monkeypatch.setattr(main_mod.app.state.container.gateway,
                        "fetch_models_with_wire", fake)
    r = client.post(f"/api/providers/{pid}/fetch_models")
    assert r.status_code == 200
    m = next(x for x in r.json()["models"] if x["id"] == "gpt-4o")
    assert m["wireId"] == "trae-cn/gpt-4o"
