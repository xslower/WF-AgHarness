from __future__ import annotations

import json
import time

import pytest
from fastapi import HTTPException

from app.api.routers.chat_mode import _validate_spec
from app.provider.models import ModelInfo, Provider


class _FakeConfig:

    def __init__(self, providers):
        self.providers = providers


class _FakeC:
    def __init__(self, providers):
        self.store = type("S", (), {"config": _FakeConfig(providers)})()


@pytest.fixture
def fake_c():
    pass
    prov = Provider(id="p1", name="p1", baseUrl="http://x/v1", apiKey="k",
                    models=[ModelInfo(id="m1"), ModelInfo(id="m2", disabled=True)])
    return _FakeC([prov])


def test_valid_spec_is_used_as_is(fake_c):
    assert _validate_spec(fake_c, "p1/m1") == "p1/m1"


def test_empty_spec_means_auto(fake_c):
    assert _validate_spec(fake_c, "") == ""


def test_unknown_provider_raises(fake_c):
    with pytest.raises(HTTPException) as ei:
        _validate_spec(fake_c, "no-such-provider/no-such-model")
    assert "不存在" in str(ei.value.detail)


def test_unknown_model_raises(fake_c):
    with pytest.raises(HTTPException) as ei:
        _validate_spec(fake_c, "p1/no-such-model")
    assert "不存在" in str(ei.value.detail)


def test_disabled_model_raises(fake_c):
    with pytest.raises(HTTPException) as ei:
        _validate_spec(fake_c, "p1/m2")
    assert "禁用" in str(ei.value.detail)


def _turn(ws, payload: dict, delay: float = 0.2) -> list[dict]:
    ws.send_json(payload)
    time.sleep(delay)
    return _settle(ws)


def _settle(ws, tries: int = 20, per_try: int = 20) -> list[dict]:
    collected: list[dict] = []
    for _ in range(tries):
        ws.send_json({"type": "stop"})
        for _ in range(per_try):
            try:
                ev = ws.receive_json()
            except Exception:
                return collected
            collected.append(ev)
            if ev.get("type") == "notice":
                if ev.get("text") == "当前没有正在进行的回复":
                    return collected
                break
        time.sleep(0.05)
    return collected


def _fake_cfg(c):
    c.store.config.providers = [Provider(
        id="p1", name="p1", baseUrl="http://x/v1", apiKey="k",
        models=[ModelInfo(id="m1")])]
    return c


def _patch_runner(c, seen: dict):
    orig = c.runner.run

    async def fake_run(view, cwd, emit, **kw):
        seen["spec"] = kw.get("spec")
        seen["called"] = True
        return
        yield {}

    c.runner.run = fake_run
    return orig


def _send_and_wait_turn_saved(ws, payload: dict) -> None:
    ws.send_text(json.dumps(payload))
    for _ in range(80):
        try:
            ev = ws.receive_json()
        except Exception:
            break
        if ev.get("type") == "turn_saved":
            break
    _settle(ws)


def test_ws_payload_model_is_the_only_source(client, container):
    c = _fake_cfg(container)
    sid = client.post("/api/sessions", params={"title": "payload 真源"}).json()["id"]
    seen: dict = {}
    orig = _patch_runner(c, seen)
    try:
        with client.websocket_connect(f"/ws/{sid}") as ws:
            _send_and_wait_turn_saved(ws, {"type": "chat", "content": "hi",
                                           "model": "p1/m1"})
    finally:
        c.runner.run = orig
    assert seen.get("spec") == "p1/m1"


def test_ws_payload_queue_name(client, container):
    c = _fake_cfg(container)
    c.store.config.queues.child = ["p1/m1"]
    sid = client.post("/api/sessions", params={"title": "子队列"}).json()["id"]
    seen: dict = {}
    orig = _patch_runner(c, seen)
    try:
        with client.websocket_connect(f"/ws/{sid}") as ws:
            _send_and_wait_turn_saved(ws, {"type": "chat", "content": "hi",
                                           "model": "child"})
    finally:
        c.runner.run = orig
    assert seen.get("spec") == "child"


def test_ws_no_model_field_defaults_to_parent(client, container):
    c = _fake_cfg(container)
    sid = client.post("/api/sessions", params={"title": "默认"}).json()["id"]
    seen: dict = {}
    orig = _patch_runner(c, seen)
    try:
        with client.websocket_connect(f"/ws/{sid}") as ws:
            _send_and_wait_turn_saved(ws, {"type": "chat", "content": "hi"})
    finally:
        c.runner.run = orig
    assert seen.get("spec") == ""


def test_ws_invalid_model_reports_error(client, container):
    c = _fake_cfg(container)
    sid = client.post("/api/sessions", params={"title": "失效模型"}).json()["id"]
    seen: dict = {}
    orig = _patch_runner(c, seen)
    try:
        with client.websocket_connect(f"/ws/{sid}") as ws:
            evs = _turn(ws, {"type": "chat", "content": "hi",
                             "model": "gone/model"})
    finally:
        c.runner.run = orig
    errors = [e.get("text", "") for e in evs if e.get("type") == "error"]
    assert any("模型不可用" in t for t in errors), f"未收到报错，实收: {evs}"
    pass
    assert not seen.get("called")
