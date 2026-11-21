from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

import pytest

import app.agent.stream as agent_stream
from app.agent.budget_wrapup import budget_wrapup
from app.agent.runner import AgentRunner
from app.agent.stream import StreamOutcome, normalize_outcome
from app.chat.session_runtime import SessionRuntimeRegistry
from app.provider.adapters.openai_sse import parse_sse
from app.provider.errors import EmptyResponseError, StreamFrameError
from app.tools import ToolContext, ToolRegistry


pass

async def _lines(*chunks: str) -> AsyncIterator[str]:
    for c in chunks:
        yield c


async def _collect_sse(*chunks: str) -> list[dict]:
    return [ev async for ev in parse_sse(_lines(*chunks))]


def _frame(obj: dict) -> str:
    return "data: " + json.dumps(obj, ensure_ascii=False)


class _Chunk:

    def __init__(self, type: str, text: str = "", **kw):
        self.type = type
        self.text = text
        self.tool_index = kw.get("tool_index", 0)
        self.usage = kw.get("usage")
        self.spec = kw.get("spec", "")
        self.info = kw.get("info", "")


class _Gateway:

    def __init__(self, script):
        self.script = script

    async def chat_stream(self, *a, **kw) -> AsyncIterator[_Chunk]:
        for item in self.script:
            if isinstance(item, Exception):
                raise item
            yield item


class _Runner:

    def __init__(self, gateway):
        self.gateway = gateway


async def _consume(gateway, abort_event=None, stop=None) -> StreamOutcome:
    async def _emit(_ev):
        return None

    return await asyncio.wait_for(
        agent_stream.consume_stream(
            _Runner(gateway), [], [], "child", "sid", _emit,
            stop_check=stop, abort_event=abort_event),
        timeout=3.0)


pass

def test_坏帧只差收尾大括号_补全后照常产出工具参数():
    good = {
        "choices": [{"delta": {"tool_calls": [
            {"index": 0, "id": "c1",
             "function": {"name": "f_read", "arguments": "{\"path\":\"a.py\"}"}}]},
            "finish_reason": None}],
    }
    broken = _frame(good)[:-2]
    async def main():
        evs = await _collect_sse(broken, "data: [DONE]")
        types = [e["type"] for e in evs]
        assert "tool_meta" in types and "tool_args" in types
    asyncio.run(main())


def test_工具帧补不全_抛帧损坏而不是静默丢弃():
    broken = ('data: {"choices":[{"delta":{"tool_calls":[{"index":0,'
              '"id":"c1","function":{"name":"f_write","arguments":"{\\"path\\":')
    async def main():
        with pytest.raises(StreamFrameError) as ei:
            await _collect_sse(broken)
        assert "工具调用帧" in str(ei.value)
        assert ei.value.frame_bytes > 0
    asyncio.run(main())


def test_非工具坏帧仍跳过_不炸整轮():
    good = _frame({"choices": [{"delta": {"content": "你好"}}]})
    async def main():
        evs = await _collect_sse("data: {坏帧", good, "data: [DONE]")
        assert [e["text"] for e in evs if e["type"] == "text"] == ["你好"]
    asyncio.run(main())


pass

def test_帧损坏_保留已收到的内容并标_corrupt():
    async def main():
        gw = _Gateway([_Chunk("reason", "我想读文件："),
                       StreamFrameError("帧坏", raw="…", frame_bytes=120)])
        res = await _consume(gw)
        assert res.status == "corrupt"
        assert res.reason == "我想读文件："
        assert res.calls == []
        assert "120" in res.error
    asyncio.run(main())


def test_空响应_标_empty_而不是_ok():
    async def main():
        res = await _consume(_Gateway([EmptyResponseError("x 返回空响应")]))
        assert res.status == "empty"
        assert "空响应" in res.error
    asyncio.run(main())


def test_一个分片都没有_也标_empty():
    async def main():
        assert (await _consume(_Gateway([]))).status == "empty"
    asyncio.run(main())


def test_有内容但没_finish_reason_标_truncated():
    async def main():
        res = await _consume(_Gateway([_Chunk("text", "半句话")]))
        assert res.status == "truncated" and res.text == "半句话"
    asyncio.run(main())


def test_见到_finish_reason_才算_ok():
    async def main():
        res = await _consume(_Gateway([_Chunk("text", "答完了"),
                                       _Chunk("end", "stop")]))
        assert res.status == "ok"
    asyncio.run(main())


def test_中止优先于一切_标_aborted():
    async def main():
        abort = asyncio.Event()
        abort.set()
        res = await _consume(_Gateway([_Chunk("text", "写了半句")]),
                             abort_event=abort)
        assert res.status == "aborted"
    asyncio.run(main())


pass

def _runner_with(gateway, script_outcomes) -> tuple[AgentRunner, list]:
    runner = AgentRunner(gateway, ToolRegistry(),
                         session_rt=SessionRuntimeRegistry())
    events: list[dict] = []
    seq = list(script_outcomes)

    async def fake_prepare(messages, cwd, emit, depth, session_id, profile,
                           project_context, plan_mode, allowed_tools,
                           stop_check=None, **kw):
        return (ToolContext(cwd), list(messages), [])

    async def fake_consume(messages, tools, spec, session_id, emit,
                           stop_check=None, abort_event=None):
        return seq.pop(0)

    async def noop(*a, **k):
        return None

    async def no_list(*a, **k):
        return []

    runner._prepare_turn = fake_prepare
    runner._consume_stream = fake_consume
    runner._emit_request_debug = noop
    runner._drain_control = noop
    runner._drain_bg_jobs = no_list
    runner._emit_done = noop
    runner._finish_plan_round = lambda *a, **k: _false()
    runner._cost_of = lambda *a: 0.0
    runner._last_model_spec = lambda: "m"
    runner._turn_meta = lambda *a: {}
    runner._round_gap_note = lambda *a: None

    async def emit(ev):
        events.append(ev)

    return runner, events


async def _false():
    return False


def _drain(runner: AgentRunner, events: list[dict]) -> list[dict]:
    async def emit(ev):
        events.append(ev)

    async def go():
        out = []
        async for m in runner.run([{"role": "user", "content": "干活"}],
                                  "/tmp", emit, spec="m"):
            out.append(m)
        return out

    return asyncio.run(go())


def test_空产出_报_error_且不写空回复():
    runner, events = _runner_with(None, [StreamOutcome("", "", [], None, "empty",
                                                       "上游返回空响应")])
    out = _drain(runner, events)
    assert [e["type"] for e in events if e["type"] == "error"], "必须有一条 error 事件"
    assert any(e["type"] == "notice" for e in events) is False
    body = out[-1]["content"]
    assert "没有产出" in body
    assert "(空回复)" not in body
    assert out[-1].get("interrupted") is True


def test_帧损坏_把原因回喂同一模型_不切换模型():
    runner, events = _runner_with(None, [
        StreamOutcome("", "", [], None, "corrupt", "工具调用帧损坏"),
        StreamOutcome("这次我改用短参数重发。", "", [], None, "ok"),
    ])
    out = _drain(runner, events)
    fed = [m for m in out if m.get("_sys") == "tool_frame_corrupt"]
    assert len(fed) == 1, "必须有一条回喂消息，否则模型永远不知道发生了什么"
    assert "没有执行" in fed[0]["content"] and "短" in fed[0]["content"]
    assert out[-1]["content"].startswith("这次我改用短参数")
    pass
    assert not [e for e in events if e["type"] == "error"]


def test_帧连续损坏两次_停止并报错():
    runner, events = _runner_with(None, [
        StreamOutcome("", "", [], None, "corrupt", "帧损坏 1"),
        StreamOutcome("", "", [], None, "corrupt", "帧损坏 2"),
    ])
    out = _drain(runner, events)
    errs = [e for e in events if e["type"] == "error"]
    assert errs and "连续两次" in errs[-1]["text"]
    assert "连续两次" in out[-1]["content"]


pass

class _BoomRegistry(ToolRegistry):

    def __init__(self):
        super().__init__()
        self.calls: list[str] = []

    async def execute(self, name, args, ctx):
        self.calls.append(name)
        if name == "boom":
            raise RuntimeError("工具内部炸了")
        return "ok"


def test_单个工具抛异常_转成_tool_结果回喂并继续():
    reg = _BoomRegistry()
    runner = AgentRunner(_Gateway([]), reg,
                         session_rt=SessionRuntimeRegistry())
    ctx = ToolContext("/tmp")
    messages: list[dict] = []
    calls = [
        {"id": "c1", "type": "function",
         "function": {"name": "boom", "arguments": "{}"}},
        {"id": "c2", "type": "function",
         "function": {"name": "fine", "arguments": "{}"}},
    ]
    events: list[dict] = []

    async def emit(ev):
        events.append(ev)

    async def go():
        return [m async for m in agent_stream.execute_tools(
            runner, calls, ctx, messages, 0, emit)]

    out = asyncio.run(go())
    pass
    assert [m["tool_call_id"] for m in out] == ["c1", "c2"]
    assert json.loads(out[0]["content"])["error"].startswith("工具 boom 执行异常")
    assert out[1]["content"] == "ok"
    assert reg.calls == ["boom", "fine"], "第一个炸了不能挡住第二个"
    assert len([e for e in events if e["type"] == "tool_end"]) == 2


pass

def test_旧四元组仍可用_空产出按_empty_处理():
    assert normalize_outcome(("t", "", [], None)).status == "ok"
    empty = normalize_outcome(("", "", [], None))
    assert empty.status == "empty", "旧形状的‘什么都没产出’也必须判失败"


def test_收尾请求也认新形状():
    class _R:
        async def _consume_stream(self, messages, tools, spec, session_id, emit,
                                  stop_check=None, abort_event=None):
            return StreamOutcome("阶段总结正文", "", [], None, "ok")

        def _cost_of(self, *a):
            return 0.0

        def _last_model_spec(self):
            return "m"

        def _turn_meta(self, *a):
            return {}

        async def _emit_done(self, *a, **k):
            return None

    async def main():
        async def emit(_ev):
            return None
        msg, _usage = await budget_wrapup(_R(), [], "m", "sid", emit)
        assert msg["content"] == "阶段总结正文"

    asyncio.run(main())

