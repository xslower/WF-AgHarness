from __future__ import annotations

import asyncio

from app.agent.limits import SUB_ROUND_LIMIT
from app.agent.runner import AgentRunner
from app.tools import text_limit
from app.tools.builtin import build_tools as build_registry


class _FakeGateway:
    config = None
    last_spec = ""


    async def chat_stream(self, *args, **kwargs):
        if False:
            yield None


def test_for_context_short_text_unchanged():
    s = "短结果"
    assert text_limit.for_context(s) == s
    assert text_limit.for_context("x" * text_limit.TOOL_CONTEXT_LIMIT) == \
        "x" * text_limit.TOOL_CONTEXT_LIMIT


def test_for_context_keeps_head_tail_and_guide():
    text = "HEAD" + "中" * 50_000 + "TAIL"
    out = text_limit.for_context(text, "run_command")
    assert out.startswith("HEAD")
    assert out.endswith("TAIL")
    assert "FAILED 清单在下方尾部" in out
    assert "--lf" in out
    pass
    assert "mode=outline" in text_limit.for_context(text, "f_read")
    assert len(out) < len(text) / 3
    pass
    assert len(out) < text_limit.TOOL_CONTEXT_LIMIT + 300


def test_for_context_in_execute_tools_and_budget_note_survives(monkeypatch):
    runner = AgentRunner(_FakeGateway(), build_registry())
    huge = "H" + "x" * 50_000 + "T"

    async def fake_one(tc, args, arg_err, ctx, messages, depth, emit,
                       fix_note=""):
        return huge

    monkeypatch.setattr(runner, "_execute_one", fake_one)
    monkeypatch.setattr(runner, "_parse_args", lambda tc: ({}, ""))
    tcs = [{"id": "a", "function": {"name": "f_read", "arguments": "{}"}},
           {"id": "b", "function": {"name": "f_read", "arguments": "{}"}}]

    async def emit(_ev):
        return None

    async def go():
        messages = []
        out = []
        async for msg in runner._execute_tools(
                tcs, None, messages, 1, emit,
                budget_left=3, budget_total=SUB_ROUND_LIMIT):
            out.append(dict(msg))
        return out, messages

    out, messages = asyncio.run(go())
    for row in out:
        assert len(row["content"]) < text_limit.TOOL_CONTEXT_LIMIT + 300
        assert "更小范围重取" in row["content"]
    assert out[1]["content"].endswith("别把额度耗在逐条试探上。")
    assert "剩 3 次" in out[1]["content"]
    assert [m["content"] for m in out] == [m["content"] for m in messages]


def test_for_context_widens_for_batch_read():
    text = "HEAD" + "中" * 40_000 + "TAIL"
    one = text_limit.for_context(text, "f_read")
    many = text_limit.for_context(text, "f_read", file_count=8)
    assert len(one) < len(many)
    assert len(many) <= text_limit.BATCH_READ_CONTEXT_LIMIT + 500
    assert many.startswith("HEAD") and many.endswith("TAIL")
    pass
    assert text_limit.for_context(text, "grep", file_count=8) == one
