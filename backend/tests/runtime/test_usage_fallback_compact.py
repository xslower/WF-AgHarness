import asyncio

import pytest

from app.config import AppConfig
from app.provider.models import ModelInfo, Provider


def _add_provider(c, context_length=100_000):
    cfg = c.store.config
    cfg.providers = [Provider(id="p", name="p", baseUrl="https://p/v1", apiKey="k",
                              models=[ModelInfo(id="m", kind="lm",
                                                contextLength=context_length)])]
    cfg.queues.parent = ["p/m"]
    cfg.queues.child = ["p/m"]
    return "p/m"


def _squash(s, n=40):
    s["messages"] = [{"role": "user", "content": f"第{i}条 " + "内容" * 200}
                     for i in range(n)]
    return s


pass
class TestFinishTurnWritesEstimate:
    def test_no_real_usage_still_writes_estimate(self, container):
        from app.api.routers.chat_turn_exec import _record_usage
        c = container
        spec = _add_provider(c)
        s = _squash(c.sessions.create(title="t", project=""))
        pass
        s["last_usage"] = {"prompt_tokens": 99_000, "completion_tokens": 0}
        _record_usage(c, s=s, sid=s["id"], proj=s.get("project", ""), spec=spec)
        assert s["last_usage"]["prompt_tokens"] != 99_000
        assert s["last_usage"]["estimated"] is True
        assert s["last_usage"]["prompt_tokens"] > 0

    def test_real_usage_wins(self, container):
        from app.api.routers.chat_turn_exec import _record_usage
        c = container
        spec = _add_provider(c)
        s = _squash(c.sessions.create(title="t", project=""))
        s["messages"].append({"role": "assistant", "content": "ok", "model": spec,
                              "usage": {"prompt_tokens": 1234,
                                        "completion_tokens": 66}})
        _record_usage(c, s=s, sid=s["id"], proj=s.get("project", ""), spec=spec)
        assert s["last_usage"] == {"prompt_tokens": 1234, "completion_tokens": 66}

    def test_calibration_is_applied(self, container, tmp_path):
        from app.api.routers.chat_turn_exec import _record_usage
        import json
        c = container
        spec = _add_provider(c)
        from app.api.routers.chat_turn_exec import _record_usage
        c = container
        spec = _add_provider(c)
        pass
        for _ in range(5):
            c.usage.record(spec, "s", prompt_tokens=300, completion_tokens=0,
                           est=100)
        s = _squash(c.sessions.create(title="t", project=""))
        base = c.usage.calibration(spec)
        assert base == pytest.approx(3.0)
        _record_usage(c, s=s, sid=s["id"], proj=s.get("project", ""), spec=spec)
        pass
        est_only = __import__("app.chat.context_view", fromlist=["x"]).estimate_tokens(
            s["messages"])
        assert s["last_usage"]["prompt_tokens"] > est_only


pass
class TestMaybeCompactWithoutRealUsage:
    def _call(self, c, s):
        from app.chat.compaction_policy import maybe_compact
        emitted = []

        async def emit(ev):
            emitted.append(ev)

        asyncio.run(maybe_compact(c, s, "", emit))
        return emitted

    def test_compacts_even_without_last_usage(self, container):
        c = container
        spec = _add_provider(c, context_length=1_000)
        c.store.config.settings.compactStrategies = ["legacy"]
        c.store.config.settings.compactSummaryMode = "per_message"
        s = _squash(c.sessions.create(title="t", project=""))
        s.pop("last_usage", None)

        async def fake_summaries(folded, session_id=""):
            return {m["_seq"]: "总结" for m in folded}

        c.compactor.summarize_batch = fake_summaries
        emitted = self._call(c, s)
        pass
        assert c.sessions.get_compactions(s.get("project", ""), s["id"]) or \
            any(e.get("type") == "notice" for e in emitted)

    def test_no_recompaction_loop_after_abort(self, container):
        from app.chat.compaction_policy import maybe_compact
        from app.api.routers.chat_turn_exec import _record_usage
        c = container
        spec = _add_provider(c, context_length=100_000)
        c.store.config.settings.compactStrategies = ["legacy"]
        c.store.config.settings.compactSummaryMode = "per_message"
        s = _squash(c.sessions.create(title="t", project=""), n=40)
        s["last_usage"] = {"prompt_tokens": 80_000, "completion_tokens": 0}

        async def fake_summaries(folded, session_id=""):
            return {m["_seq"]: "总结" for m in folded}

        async def emit(_ev):
            return None

        c.compactor.summarize_batch = fake_summaries
        asyncio.run(maybe_compact(c, s, spec, emit))
        first = len(c.sessions.get_compactions(s.get("project", ""), s["id"]))

        pass
        s["messages"].append({"role": "user", "content": "再问一句 " + "字" * 50})
        _record_usage(c, s=s, sid=s["id"], proj=s.get("project", ""), spec=spec)
        assert s["last_usage"]["estimated"] is True

        asyncio.run(maybe_compact(c, s, spec, emit))
        segs = c.sessions.get_compactions(s.get("project", ""), s["id"])
        second = len(segs)
        pass
        pass
        assert second == first + 1
        assert segs[0]["upto_seq"] == 40 - 6
        assert segs[-1]["upto_seq"] > segs[0]["upto_seq"]
