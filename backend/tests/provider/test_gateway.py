import asyncio
import json
import time

import httpx
import pytest

from app.config import AppConfig

from app.provider.models import ModelInfo, Provider
from app.provider.errors import EmptyResponseError
from app.provider.gateway import Chunk, ModelGateway


def make_config(specs: list[str]) -> AppConfig:
    cfg = AppConfig()
    for spec in specs:
        pid, mid = spec.split("/")
        p = next((x for x in cfg.providers if x.id == pid), None)
        if not p:
            p = Provider(id=pid, name=pid, baseUrl=f"https://{pid}.test/v1", apiKey="k")
            cfg.providers.append(p)
        p.models.append(ModelInfo(id=mid, supportsThinking=True))
    cfg.queues.parent = specs
    return cfg


def sse_response(chunks: list[dict], usage: dict | None = None, status=200):
    events = [f"data: {json.dumps(c)}" for c in chunks]
    if usage:
        events.append(f"data: {json.dumps({'usage': usage})}")
    events.append("data: [DONE]")
    body = "\n".join(events) + "\n"
    return httpx.Response(status, text=body)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def collect(aiter):
    out = []
    async def go():
        async for c in aiter:
            out.append(c)
    asyncio.run(go())
    return out


pass
def test_generate_image_b64_saved(tmp_path, monkeypatch):
    import base64
    cfg = make_config(["p1/m1"])
    p = cfg.providers[0]
    p.models.append(ModelInfo(id="img1", kind="image"))
    raw = b"PNGDATA"
    b64 = base64.b64encode(raw).decode()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/images/generations")
        body = json.loads(request.content)
        assert body["model"] == "img1"
        assert body["prompt"] == "a cat"
        return httpx.Response(200, json={"data": [{"b64_json": b64}]})

    gw = ModelGateway(cfg, transport=httpx.MockTransport(handler))
    r = asyncio.run(gw.generate_image("a cat", out_dir=str(tmp_path)))
    assert r["ok"] is True
    assert r["model"] == "p1/img1"
    assert r["images"][0]["path"].endswith(".png")
    with open(r["images"][0]["path"], "rb") as f:
        assert f.read() == raw


def test_generate_image_url_passthrough():
    cfg = make_config(["p1/m1"])
    cfg.providers[0].models.append(ModelInfo(id="img1", kind="image"))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"url": "http://img/1.png"}]})

    gw = ModelGateway(cfg, transport=httpx.MockTransport(handler))
    r = asyncio.run(gw.generate_image("a cat", spec="p1/img1"))
    assert r["ok"] is True
    assert r["images"][0]["url"] == "http://img/1.png"


def test_generate_image_no_image_model():
    cfg = make_config(["p1/m1"])
    gw = ModelGateway(cfg, transport=httpx.MockTransport(
        lambda req: httpx.Response(200, json={})))
    r = asyncio.run(gw.generate_image("a cat"))
    assert r["ok"] is False
    assert "image" in r["error"]


def test_generate_image_api_error():
    cfg = make_config(["p1/m1"])
    cfg.providers[0].models.append(ModelInfo(id="img1", kind="image"))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    gw = ModelGateway(cfg, transport=httpx.MockTransport(handler))
    r = asyncio.run(gw.generate_image("a cat", spec="p1/img1"))
    assert r["ok"] is False
    assert "生图请求失败" in r["error"]


pass
def test_transcribe_audio_auto_route(tmp_path):
    cfg = make_config(["p1/m1"])
    cfg.providers[0].models.append(ModelInfo(id="asr1", kind="asr"))
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"WAVDATA")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/audio/transcriptions")
        return httpx.Response(200, json={"text": "你好世界"})

    gw = ModelGateway(cfg, transport=httpx.MockTransport(handler))
    r = asyncio.run(gw.transcribe_audio(str(audio)))
    assert r["ok"] is True
    assert r["text"] == "你好世界"
    assert r["model"] == "p1/asr1"


def test_transcribe_audio_no_asr_model(tmp_path):
    cfg = make_config(["p1/m1"])
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"WAVDATA")
    gw = ModelGateway(cfg, transport=httpx.MockTransport(
        lambda req: httpx.Response(200, json={})))
    r = asyncio.run(gw.transcribe_audio(str(audio)))
    assert r["ok"] is False
    assert "asr" in r["error"]


def test_transcribe_audio_file_missing():
    cfg = make_config(["p1/m1"])
    cfg.providers[0].models.append(ModelInfo(id="asr1", kind="asr"))
    gw = ModelGateway(cfg, transport=httpx.MockTransport(
        lambda req: httpx.Response(200, json={})))
    r = asyncio.run(gw.transcribe_audio("/nonexistent/a.wav"))
    assert r["ok"] is False
    assert "不存在" in r["error"]


def test_stream_text_tools_usage():
    cfg = make_config(["p1/m1"])
    chunks = [
        {"choices": [{"delta": {"content": "你"}}]},
        {"choices": [{"delta": {"content": "好"}}]},
        {"choices": [{"delta": {"tool_calls": [
            {"index": 0, "id": "c1", "function": {"name": "read_file", "arguments": '{"pa'}}]}}]},
        {"choices": [{"delta": {"tool_calls": [
            {"index": 0, "function": {"arguments": 'th":"x"}'}}]}}]},
    ]
    transport = httpx.MockTransport(
        lambda req: sse_response(chunks, usage={"prompt_tokens": 10, "completion_tokens": 5}))
    gw = ModelGateway(cfg, transport=transport)

    got = collect(gw.chat_stream([{"role": "user", "content": "hi"}]))
    texts = "".join(c.text for c in got if c.type == "text")
    metas = [json.loads(c.text) for c in got if c.type == "tool_meta"]
    args = "".join(c.text for c in got if c.type == "tool_args")
    usage = [c.usage for c in got if c.type == "usage"]

    assert texts == "你好"
    assert metas == [{"id": "c1", "name": "read_file"}]
    assert args == '{"path":"x"}'
    assert usage and usage[0].prompt_tokens == 10
    assert gw.last_spec


def test_fallback_on_429():
    cfg = make_config(["p1/m1", "p2/m2"])

    def handler(req: httpx.Request) -> httpx.Response:
        if "p1.test" in str(req.url):
            return httpx.Response(429, text="rate limited")
        return sse_response([{"choices": [{"delta": {"content": "ok"}}]}],
                            usage={"prompt_tokens": 1, "completion_tokens": 1})

    gw = ModelGateway(cfg, transport=httpx.MockTransport(handler))
    got = collect(gw.chat_stream([{"role": "user", "content": "hi"}]))
    assert any(c.type == "fallback" and "p1/m1" in c.info for c in got)
    assert "".join(c.text for c in got if c.type == "text") == "ok"

    pass
    reqs = []
    def handler2(req: httpx.Request) -> httpx.Response:
        reqs.append(str(req.url))
        return sse_response([{"choices": [{"delta": {"content": "ok"}}]}],
                            usage={"prompt_tokens": 1, "completion_tokens": 1})
    gw2 = ModelGateway(cfg, transport=httpx.MockTransport(handler2))
    collect(gw2.chat_stream([{"role": "user", "content": "hi"}]))
    pass
    import time
    gw2._checker.cool_down("p1/m1", time.time() + 60)
    assert gw2._ordered_specs() == ["p2/m2", "p1/m1"]



def test_queue_and_pin_keeps_queue_as_failover_axis():
    gw = ModelGateway(make_config(["p1/m1"]))
    assert gw._queue_and_pin("") == ("parent", "")
    assert gw._queue_and_pin("child") == ("child", "")
    assert gw._queue_and_pin("summary") == ("summary", "")
    assert gw._queue_and_pin("p1/m1") == ("parent", "p1/m1")
    pass
    gw._demoted.add("p1/m1")
    gw._checker.cool_down("p1/m1", time.time() + 3600)
    assert gw._ordered_specs("parent", "p1/m1") == ["p1/m1"]
    pass
    cfg = make_config(["p1/m1", "p2/m2"])
    gw2 = ModelGateway(cfg)
    gw2._demoted.add("p1/m1")
    assert gw2._ordered_specs("parent") == ["p2/m2", "p1/m1"]

def test_child_queue_independent():
    cfg = make_config(["p1/m1", "p2/m2"])
    cfg.queues.child = ["p2/m2"]
    transport = httpx.MockTransport(
        lambda req: sse_response([{"choices": [{"delta": {"content": "ok"}}]}],
                                 usage={"prompt_tokens": 1, "completion_tokens": 1}))
    gw = ModelGateway(cfg, transport=transport)
    collect(gw.chat_stream([{"role": "user", "content": "hi"}], spec="child"))
    pass
    assert gw.last_spec == "p2/m2"


def test_reasoning_content_streamed():
    cfg = make_config(["p1/m1"])
    chunks = [
        {"choices": [{"delta": {"reasoning_content": "想想"}}]},
        {"choices": [{"delta": {"content": "答"}}]},
    ]
    transport = httpx.MockTransport(
        lambda req: sse_response(chunks, usage={"prompt_tokens": 1, "completion_tokens": 1}))
    gw = ModelGateway(cfg, transport=transport)
    got = collect(gw.chat_stream([{"role": "user", "content": "hi"}]))
    reasons = "".join(c.text for c in got if c.type == "reason")
    texts = "".join(c.text for c in got if c.type == "text")
    assert reasons == "想想" and texts == "答"


def test_test_model_ok_and_bad():
    cfg = make_config(["p1/m1"])
    transport = httpx.MockTransport(
        lambda req: sse_response([{"choices": [{"delta": {"content": "ok!"}}]}],
                                 usage={"prompt_tokens": 1, "completion_tokens": 1}))
    gw = ModelGateway(cfg, transport=transport)
    r = asyncio.run(gw.test_model("p1/m1"))
    assert r["ok"] and r["sample"] == "ok!" and r["ms"] >= 0
    r = asyncio.run(gw.test_model("nope/m-x"))
    assert not r["ok"] and "无效" in r["error"]


def _set_model_sched(cfg, spec, scheds):
    from app.provider.models import ModelSchedule
    pid, _, mid = spec.partition("/")
    m = next(m for p in cfg.providers if p.id == pid for m in p.models if m.id == mid)
    m.schedules = scheds
    return m

def _at(hm: str, weekday: int = 0) -> float:
    import time as _t
    base = _t.mktime((2026, 11, 2, 0, 0, 0, 0, 0, -1))
    h, m = str(hm).split(":")
    return base + int(h) * 3600 + int(m) * 60 + weekday * 86400


def test_schedule_filters_models():
    from app.provider.models import ModelSchedule
    cfg = make_config(["p1/m1", "p2/m2"])
    pass
    _set_model_sched(cfg, "p1/m1", [ModelSchedule(start="00:00", end="01:00")])
    gw = ModelGateway(cfg)
    gw.now = lambda: _at("12:00")
    assert gw._ordered_specs() == ["p2/m2"]
    pass
    gw.now = lambda: _at("00:30")
    assert gw._ordered_specs() == ["p1/m1", "p2/m2"]
    pass
    _set_model_sched(cfg, "p1/m1", [ModelSchedule(start="22:00", end="06:00")])
    gw.now = lambda: _at("23:30")
    assert gw._ordered_specs() == ["p1/m1", "p2/m2"]
    gw.now = lambda: _at("12:00")
    assert gw._ordered_specs() == ["p2/m2"]
    pass
    cfg2 = make_config(["p1/m1"])
    _set_model_sched(cfg2, "p1/m1", [ModelSchedule(start="00:00", end="01:00")])
    gw2 = ModelGateway(cfg2)
    gw2.now = lambda: _at("12:00")
    with pytest.raises(RuntimeError, match="不可用"):
        gw2._ordered_specs()

def test_schedule_weekday_filters():
    from app.provider.models import ModelSchedule
    cfg = make_config(["p1/m1", "p2/m2"])
    pass
    _set_model_sched(cfg, "p1/m1", [ModelSchedule(days=[0], start="00:00", end="23:59")])
    gw = ModelGateway(cfg)
    gw.now = lambda: _at("12:00", weekday=0)
    assert gw._ordered_specs() == ["p1/m1", "p2/m2"]
    gw.now = lambda: _at("12:00", weekday=3)
    assert gw._ordered_specs() == ["p2/m2"]


def test_spec_override_skips_queue():
    cfg = make_config(["p1/m1", "p2/m2"])
    transport = httpx.MockTransport(
        lambda req: sse_response([{"choices": [{"delta": {"content": "ok"}}]}],
                                 usage={"prompt_tokens": 1, "completion_tokens": 1}))
    gw = ModelGateway(cfg, transport=transport)
    got = collect(gw.chat_stream([{"role": "user", "content": "hi"}], spec="p2/m2"))
    assert "".join(c.text for c in got if c.type == "text") == "ok"
    assert gw.last_spec == "p2/m2"


def test_all_fail_raises():
    cfg = make_config(["p1/m1", "p2/m2"])
    transport = httpx.MockTransport(lambda req: httpx.Response(500, text="boom"))
    gw = ModelGateway(cfg, transport=transport)
    with pytest.raises(RuntimeError, match="全部失败"):
        collect(gw.chat_stream([{"role": "user", "content": "hi"}]))


def test_empty_queue():
    gw = ModelGateway(AppConfig())
    with pytest.raises(RuntimeError, match="未配置"):
        collect(gw.chat_stream([{"role": "user", "content": "hi"}]))


def test_thinking_effort_passed():
    cfg = make_config(["p1/m1"])
    bodies = []

    def handler(req: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(req.content))
        return sse_response([{"choices": [{"delta": {"content": "ok"}}]}],
                            usage={"prompt_tokens": 1, "completion_tokens": 1})

    gw = ModelGateway(cfg, transport=httpx.MockTransport(handler))
    collect(gw.chat_stream([{"role": "user", "content": "hi"}], effort="high"))
    assert bodies[0]["enable_thinking"] is True
    assert bodies[0]["reasoning_effort"] == "high"
    assert bodies[0]["stream"] is True
    assert bodies[0]["stream_options"] == {"include_usage": True}


def test_default_effort_from_settings():
    cfg = make_config(["p1/m1"])
    bodies = []

    def handler(req: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(req.content))
        return sse_response([{"choices": [{"delta": {"content": "ok"}}]}],
                            usage={"prompt_tokens": 1, "completion_tokens": 1})

    gw = ModelGateway(cfg, transport=httpx.MockTransport(handler))
    cfg.settings.defaultEffort = "high"
    collect(gw.chat_stream([{"role": "user", "content": "hi"}]))
    assert bodies[0]["reasoning_effort"] == "high"
    assert bodies[0]["enable_thinking"] is True

    cfg.settings.defaultEffort = "off"
    bodies.clear()
    collect(gw.chat_stream([{"role": "user", "content": "hi"}]))
    assert "reasoning_effort" not in bodies[0]
    assert "enable_thinking" not in bodies[0]


def test_fetch_models_parses():
    cfg = make_config(["p1/m1"])
    transport = httpx.MockTransport(lambda req: httpx.Response(
        200, json={"data": [{"id": "m1"}, {"id": "m2"}]}))
    gw = ModelGateway(cfg, transport=transport)
    ids = asyncio.run(gw.fetch_models(cfg.providers[0]))
    assert ids == ["m1", "m2"]


pass
pass
pass
pass
pass
pass
def test_empty_response_does_not_switch_model():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return sse_response([])

    cfg = make_config(["p1/m1", "p2/m2"])
    gw = ModelGateway(cfg, transport=httpx.MockTransport(handler))
    with pytest.raises(EmptyResponseError):
        collect(gw.chat_stream([{"role": "user", "content": "hello"}]))
    assert calls["n"] == 1, "不许换模型重发（换模型 = 整段缓存前缀作废）"


def test_empty_response_no_cooldown_no_demote():
    def handler(request: httpx.Request) -> httpx.Response:
        return sse_response([])

    cfg = make_config(["p1/m1", "p2/m2"])
    gw = ModelGateway(cfg, transport=httpx.MockTransport(handler))
    for _ in range(3):
        with pytest.raises(EmptyResponseError):
            collect(gw.chat_stream([{"role": "user", "content": "hello"}]))
    assert not gw._checker.is_cooling("p1/m1")
    assert "p1/m1" not in gw._demoted
    assert gw._ordered_specs("parent")[0] == "p1/m1"


def test_ratelimited_model_demoted_and_retried_after_cooldown():
    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        is_m1 = '"model": "m1"' in body or '"model":"m1"' in body
        if is_m1:
            return httpx.Response(429, text="rate limited")
        return sse_response([{"choices": [{"delta": {"content": "ok"}}]}])

    cfg = make_config(["p1/m1", "p2/m2"])
    gw = ModelGateway(cfg, transport=httpx.MockTransport(handler))

    pass
    out = collect(gw.chat_stream([{"role": "user", "content": "hello"}]))
    assert "".join(c.text for c in out if c.type == "text") == "ok"
    assert "p1/m1" in gw._demoted and gw._checker.is_cooling("p1/m1")

    pass
    assert gw._ordered_specs("parent")[0] == "p2/m2"

    pass
    gw._checker.cooldowns.clear()
    assert gw._ordered_specs("parent") == ["p2/m2", "p1/m1"]


pass
def test_tool_acc_meta_then_args():
    from app.provider.gateway import Chunk, ToolCallAcc
    acc = ToolCallAcc()
    assert acc.feed(Chunk(type="tool_meta", tool_index=0,
                          text=json.dumps({"id": "c1", "name": "read_file"})))
    assert acc.feed(Chunk(type="tool_args", tool_index=0, text='{"path": '))
    assert acc.feed(Chunk(type="tool_args", tool_index=0, text='"a.txt"}'))
    assert acc.calls() == [{"id": "c1", "type": "function",
                            "function": {"name": "read_file",
                                         "arguments": '{"path": "a.txt"}'}}]


def test_tool_acc_args_before_meta():
    from app.provider.gateway import Chunk, ToolCallAcc
    acc = ToolCallAcc()
    acc.feed(Chunk(type="tool_args", tool_index=0, text='{"q":'))
    acc.feed(Chunk(type="tool_args", tool_index=0, text='"x"}'))
    acc.feed(Chunk(type="tool_meta", tool_index=0,
                   text=json.dumps({"id": "c9", "name": "grep"})))
    [call] = acc.calls()
    assert call["id"] == "c9" and call["function"]["name"] == "grep"
    assert call["function"]["arguments"] == '{"q":"x"}'


def test_tool_acc_first_meta_wins_and_order_by_index():
    from app.provider.gateway import Chunk, ToolCallAcc
    acc = ToolCallAcc()
    acc.feed(Chunk(type="tool_meta", tool_index=1, text=json.dumps({"id": "b", "name": "two"})))
    acc.feed(Chunk(type="tool_args", tool_index=1, text="{}"))
    acc.feed(Chunk(type="tool_meta", tool_index=0, text=json.dumps({"id": "a", "name": "one"})))
    acc.feed(Chunk(type="tool_meta", tool_index=0, text=json.dumps({"id": "zz", "name": "other"})))
    assert [c["id"] for c in acc.calls()] == ["a", "b"]
    assert [c["function"]["name"] for c in acc.calls()] == ["one", "two"]


def test_tool_acc_missing_id_gets_stable_placeholder():
    from app.provider.gateway import Chunk, ToolCallAcc
    acc = ToolCallAcc()
    acc.feed(Chunk(type="tool_args", tool_index=3, text="{}"))
    [call] = acc.calls()
    assert call["id"] == "call_3"


def test_tool_acc_ignores_text_chunks():
    from app.provider.gateway import Chunk, ToolCallAcc
    acc = ToolCallAcc()
    assert acc.feed(Chunk(type="text", text="hello")) is False
    assert acc.feed(Chunk(type="reason", text="thinking")) is False
    assert not acc and acc.calls() == []


pass
def _summary_cfg():
    cfg = make_config(["p1/fast", "p2/slow", "p3/backup"])
    cfg.queues.summary = ["p1/fast", "p2/slow", "p3/backup"]
    return cfg


def test_summary_queue_falls_back_to_child_then_parent():
    cfg = make_config(["p/f", "p/child"])
    cfg.queues.summary = []
    cfg.queues.child = ["p/child"]
    gw = ModelGateway(cfg, transport=httpx.MockTransport(lambda r: sse_response(
        [{"choices": [{"delta": {"content": "ok"}}]}])))
    assert gw._ordered_specs("summary") == ["p/child"]


def test_hedged_takes_primary_when_fast():
    cfg = _summary_cfg()
    hits: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        hits.append(body["model"])
        return sse_response([{"choices": [{"delta": {"content": "主"}}]}])

    gw = ModelGateway(cfg, transport=httpx.MockTransport(handler))
    out = collect(gw.stream_hedged([{"role": "user", "content": "hi"}],
                                   ["p1/fast", "p2/slow", "p3/backup"], hedge_ms=3000))
    assert [c.text for c in out if c.type == "text"] == ["主"]
    assert hits == ["fast"]


def test_hedged_backup_wins_when_primary_stalls():
    cfg = _summary_cfg()
    gw = ModelGateway(cfg, transport=httpx.MockTransport(
        lambda r: sse_response([{"choices": [{"delta": {"content": "x"}}]}])))
    delays = {"p2/slow": 0.5, "p3/backup": 0.0}

    async def fake_chat_stream(messages, tools=None, effort="", spec="",
                               session_id=""):
        await asyncio.sleep(delays.get(spec, 0.0))
        yield Chunk(type="text", text="慢" if spec == "p2/slow" else "快")

    gw.chat_stream = fake_chat_stream

    out = collect(gw.stream_hedged([{"role": "user", "content": "hi"}],
                                   ["p2/slow", "p3/backup"], hedge_ms=100))
    texts = [c.text for c in out if c.type == "text"]
    assert texts == ["快"]
    assert any(c.type == "fallback" for c in out)


def test_hedged_all_fail_raises():
    cfg = _summary_cfg()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    gw = ModelGateway(cfg, transport=httpx.MockTransport(handler))
    with pytest.raises(RuntimeError):
        collect(gw.stream_hedged([{"role": "user", "content": "hi"}],
                                 ["p1/fast", "p3/backup"], hedge_ms=100))


pass
def test_cooldown_uses_provider_setting():
    from app.provider.models import ModelInfo, Provider
    cfg = AppConfig()
    cfg.providers = [Provider(id="wb", name="wb", baseUrl="https://wb/v1", apiKey="k",
                              cooldownSec=14400, models=[ModelInfo(id="m")])]
    gw = ModelGateway(cfg)
    p = cfg.providers[0]
    assert gw._cooldown_for("wb/m", p, RuntimeError("429")) == 14400
    pass
    assert gw._cooldown_for("wb/m", p, RuntimeError("429")) == 14400


def test_cooldown_minute_level_provider():
    from app.provider.models import ModelInfo, Provider
    cfg = AppConfig()
    cfg.providers = [Provider(id="p", name="p", baseUrl="https://p/v1", apiKey="k",
                              cooldownSec=60, models=[ModelInfo(id="m")])]
    gw = ModelGateway(cfg)
    p = cfg.providers[0]
    assert gw._cooldown_for("p/m", p, RuntimeError("429")) == 60
    assert gw._cooldown_for("p/m", p, RuntimeError("429")) == 120


def test_rate_limited_model_moves_to_queue_tail():
    import time as _t
    from app.provider.models import ModelInfo, Provider
    cfg = AppConfig()
    cfg.providers = [Provider(id="p", name="p", baseUrl="https://p/v1", apiKey="k",
                              models=[ModelInfo(id="a"), ModelInfo(id="b")])]
    cfg.queues.parent = ["p/a", "p/b"]
    gw = ModelGateway(cfg)
    gw._checker.cool_down("p/a", _t.time() + 600)
    assert gw._ordered_specs("parent") == ["p/b", "p/a"]


def test_queue_order_wins_no_affinity():
    cfg = make_config(["p1/a", "p2/b"])
    cfg.queues.parent = ["p1/a", "p2/b"]
    gw = ModelGateway(cfg)
    assert gw._ordered_specs("parent") == ["p1/a", "p2/b"]
    pass
    assert not hasattr(gw, "_last_ok")


pass
_UTILITY_KINDS = ("completion", "classify", "review", "suggest")


def _utility_gateway():
    cfg = make_config(["p1/m1"])
    cfg.queues.child = ["p1/m1"]
    gw = ModelGateway(cfg)
    calls = []

    async def fake_chat_stream(messages, tools=None, effort="", spec="",
                               session_id=""):
        calls.append(spec)
        yield Chunk(type="text", text="ok")

    gw.chat_stream = fake_chat_stream
    return gw, cfg, calls


@pytest.mark.parametrize("kind", _UTILITY_KINDS)
def test_call_utility_empty_is_disabled(kind):
    gw, _cfg, calls = _utility_gateway()
    out = asyncio.run(gw.call_utility(kind, [{"role": "user", "content": "x"}]))
    assert out == ""
    assert calls == [], f"{kind} 留空却调了模型: {calls}"


def test_call_utility_explicit_spec_enables():
    gw, cfg, calls = _utility_gateway()
    cfg.utility.completion = ["p1/m1"]
    out = asyncio.run(gw.call_utility(
        "completion", [{"role": "user", "content": "x"}]))
    assert out == "ok"
    assert calls == ["p1/m1"]


def test_call_utility_queue_fallback_only_when_configured_but_failed():
    gw, cfg, calls = _utility_gateway()
    cfg.utility.review = ["p1/m1"]

    async def failing(messages, tools=None, effort="", spec="", session_id=""):
        calls.append(spec)
        if spec == "p1/m1":
            raise RuntimeError("专用模型挂了")
        yield Chunk(type="text", text="ok")

    gw.chat_stream = failing
    out = asyncio.run(gw.call_utility(
        "review", [{"role": "user", "content": "x"}]))
    assert out == "ok"
    assert calls == ["p1/m1", "child"], calls
