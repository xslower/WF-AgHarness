from __future__ import annotations

import pytest

from app.chat.context_view import estimate_event, estimate_tokens, measure


def _msgs(n: int = 6) -> list[dict]:
    return [{"role": "user" if i % 2 == 0 else "assistant",
             "content": f"第 {i} 条内容，中文占多数"} for i in range(n)]


def test_estimate_event_is_same_source_as_measure():
    msgs = _msgs()
    ev = estimate_event(None, msgs, [], spec="p/m")
    assert ev["type"] == "ctx_estimate"
    assert ev["estimated"] is True
    assert ev["model"] == "p/m"
    assert ev["used"] == measure(None, msgs, [], real=None, spec="p/m")["used"]
    assert ev["used"] > 0


def test_estimate_event_survives_unknown_usage_tracker():
    class Boom:
        def calibration(self, spec):
            raise RuntimeError("no stats")

    assert estimate_event(Boom(), _msgs(), [], spec="p/m")["used"] > 0


def test_ctx_estimate_event_shape():
    ev = estimate_event(None, _msgs(), [], spec="p/m")
    assert ev["type"] == "ctx_estimate"
    assert ev["used"] > 0 and ev["model"] == "p/m"
    assert ev["estimated"] is True


def test_estimate_grows_with_history():
    small = estimate_event(None, _msgs(4), [], spec="p/m")["used"]
    big = estimate_event(None, _msgs(40), [], spec="p/m")["used"]
    assert big > small
    assert estimate_tokens(_msgs(40)) > 0


@pytest.mark.parametrize("real", [
    {"prompt_tokens": 0, "completion_tokens": 0},
    {"prompt_tokens": 0, "completion_tokens": 0, "estimated": True},
])
def test_zero_usage_is_never_real(real):
    m = measure(None, _msgs(), [], real=real, spec="p/m")
    assert m["estimated"] is True
    assert m["used"] > 0


def test_real_usage_wins():
    m = measure(None, _msgs(), [], real={"prompt_tokens": 900,
                                         "completion_tokens": 100}, spec="p/m")
    assert m["used"] == 1000 and m["estimated"] is False


def test_record_usage_ignores_zero_shell(container):
    from app.api.routers.chat_turn_exec import _record_usage

    s = container.sessions.create(title="t", project="")
    s["messages"] = _msgs(20)
    s["messages"].append({"role": "assistant", "content": "ok", "model": "p/m",
                          "usage": {"prompt_tokens": 0, "completion_tokens": 0}})
    _record_usage(container, s=s, sid=s["id"], proj="", spec="p/m")
    assert s["last_usage"]["estimated"] is True
    assert s["last_usage"]["prompt_tokens"] > 0


@pytest.mark.asyncio
async def test_execute_turn_emits_estimate_after_each_tool(container, monkeypatch):
    from app.api.routers.chat_turn_exec import execute_turn
    from app.chat.session_runtime import SessionRuntime

    s = container.sessions.create(title="t", project="")
    s["messages"] = [{"role": "user", "content": "帮我查点东西"}]
    rt = SessionRuntime(sid=s["id"])
    events: list[dict] = []

    async def emit(ev):
        events.append(ev)

    async def fake_run(messages, cwd, emit_, **kw):
        yield {"role": "assistant", "content": None,
               "tool_calls": [{"id": "t1", "function": {"name": "x", "arguments": "{}"}}]}
        yield {"role": "tool", "tool_call_id": "t1", "content": "第一个工具结果"}
        yield {"role": "tool", "tool_call_id": "t2",
               "content": "第二个工具结果，长得多。" * 40}
        yield {"role": "assistant", "content": "完成", "model": "p/m",
               "usage": {"prompt_tokens": 0, "completion_tokens": 0}}

    monkeypatch.setattr(container.runner, "run", fake_run)
    await execute_turn(c=container, s=s, sid=s["id"], cwd="", emit=emit, rt=rt,
                       spec="p/m", plan_mode="", project_context="")

    est = [e for e in events if e.get("type") == "ctx_estimate"]
    assert len(est) == 2, "每个落地的工具结果都要推一次占用估算"
    assert all(e["estimated"] is True and e["used"] > 0 for e in est)
    assert est[1]["used"] > est[0]["used"], "账本变长后数值必须真的涨"
    pass
    assert s["last_usage"]["estimated"] is True
    assert s["last_usage"]["prompt_tokens"] > 0

