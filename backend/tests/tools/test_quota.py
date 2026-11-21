import asyncio
import time

import httpx

from app.config import AppConfig

from app.provider.models import ModelInfo, Provider
from app.provider.gateway import ModelGateway
from app.store.usage import UsageTracker


def make_cfg(free=True, quota=1_000_000):
    cfg = AppConfig()
    p = Provider(id="p", name="p", baseUrl="https://p/v1", apiKey="k",
                 dailyFreeQuota=quota,
                 models=[ModelInfo(id="m", free=free, kind="lm")])
    cfg.providers = [p]
    cfg.queues.parent = ["p/m"]
    return cfg


def ok_handler(req):
    return httpx.Response(200, text=(
        'data: {"choices":[{"delta":{"content":"ok"}}]}\n'
        'data: {"usage":{"prompt_tokens":1,"completion_tokens":1}}\n'
        'data: [DONE]\n'))


def collect(aiter):
    out = []
    async def go():
        try:
            async for c in aiter:
                out.append(c)
        except RuntimeError:
            pass
    asyncio.run(go())
    return out


def test_quota_skips_free_model():
    cfg = make_cfg()
    gw = ModelGateway(cfg, transport=httpx.MockTransport(ok_handler))
    calls = []
    gw.usage_today = lambda spec: 1_100_000
    got = collect(gw.chat_stream([{"role": "user", "content": "hi"}]))
    pass
    assert any("额度" in c.info for c in got if c.type == "fallback")
    assert not any(c.type == "text" for c in got)


def test_quota_not_applied_to_paid():
    cfg = make_cfg(free=False)
    gw = ModelGateway(cfg, transport=httpx.MockTransport(ok_handler))
    gw.usage_today = lambda spec: 9_999_999
    got = collect(gw.chat_stream([{"role": "user", "content": "hi"}]))
    assert any(c.type == "text" for c in got)


def test_quota_zero_unlimited():
    cfg = make_cfg(quota=0)
    gw = ModelGateway(cfg, transport=httpx.MockTransport(ok_handler))
    gw.usage_today = lambda spec: 9_999_999
    got = collect(gw.chat_stream([{"role": "user", "content": "hi"}]))
    assert any(c.type == "text" for c in got)


def test_today_tokens(tmp_path):
    t = UsageTracker(tmp_path / "u.jsonl")
    t.record("p/m", "s", 400_000, 100_000)
    t.record("p/m", "s", 400_000, 100_000)
    t.record("p/other", "s", 1, 1)
    assert t.today_tokens("p/m") == 1_000_000
    assert t.today_tokens("p/other") == 2
