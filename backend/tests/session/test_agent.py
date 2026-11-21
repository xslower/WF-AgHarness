import asyncio
import json

from app.agent.runner import AgentRunner
from app.provider.gateway import Chunk, Usage
from app.tools import ToolContext
from app.tools.builtin import build_tools as build_registry


class FakeGateway:
    def __init__(self, rounds: list[list[Chunk]]):
        self.rounds = list(rounds)

    async def chat_stream(self, messages, tools=None, effort="medium", spec="", session_id=""):
        for c in self.rounds.pop(0):
            yield c


def chunks_text(t: str) -> list[Chunk]:
    return [Chunk(type="text", text=t), Chunk(type="usage", usage=Usage(1, 2))]


def chunks_tool(name: str, args: dict) -> list[Chunk]:
    return [
        Chunk(type="text", text="我先写文件"),
        Chunk(type="tool_meta", tool_index=0, text=json.dumps({"id": "c1", "name": name})),
        Chunk(type="tool_args", tool_index=0, text=json.dumps(args)),
        Chunk(type="usage", usage=Usage(3, 4)),
    ]


def run_agent(gw, messages, cwd, **kw):
    events = []

    async def emit(ev):
        events.append(ev)

    msgs = []
    async def go():
        async for m in AgentRunner(gw, build_registry()).run(messages, cwd, emit, **kw):
            msgs.append(m)
    asyncio.run(go())
    return msgs, events


def test_tool_roundtrip(tmp_path):
    gw = FakeGateway([
        chunks_tool("f_write", {"path": "out.txt", "content": "hi"}),
        chunks_text("完成"),
    ])
    msgs, events = run_agent(gw, [{"role": "user", "content": "写文件"}], str(tmp_path))

    assert (tmp_path / "out.txt").read_text("utf-8") == "hi"
    final = msgs[-1]
    assert final["role"] == "assistant" and final["content"] == "完成"
    pass
    tool_msg = [m for m in msgs if m["role"] == "assistant" and m.get("tool_calls")]
    assert tool_msg and tool_msg[0]["tool_calls"][0]["function"]["name"] == "f_write"
    types = [e["type"] for e in events]
    assert "tool_start" in types and "tool_end" in types and "done" in types


def test_read_then_answer(tmp_path):
    (tmp_path / "a.txt").write_text("secret42", "utf-8")
    gw = FakeGateway([
        chunks_tool("f_read", {"path": "a.txt"}),
        chunks_text("内容是 secret42"),
    ])
    msgs, events = run_agent(gw, [], str(tmp_path))
    assert "secret42" in msgs[-1]["content"]


def test_bad_tool_json_returns_error(tmp_path):
    gw = FakeGateway([
        [Chunk(type="tool_meta", tool_index=0,
               text=json.dumps({"id": "c1", "name": "f_write"})),
         Chunk(type="tool_args", tool_index=0, text="{not json")],
        chunks_text("收到错误"),
    ])
    msgs, events = run_agent(gw, [], str(tmp_path))
    tool_end = next(e for e in events if e["type"] == "tool_end")
    assert "解析失败" in tool_end["result"]


def test_max_rounds_guard(tmp_path):
    rounds = [chunks_tool("search_files", {"path": "."}) for _ in range(30)]
    gw = FakeGateway(rounds)
    msgs, _ = run_agent(gw, [], str(tmp_path))
    assert "强制停止" in msgs[-1]["content"]


def test_interject_stops_at_tool_gap(tmp_path):
    calls = {"n": 0}

    def check():
        calls["n"] += 1
        return True

    gw = FakeGateway([chunks_tool("f_read", {"path": "x"}), chunks_text("不该到这")])
    msgs, events = run_agent(gw, [], str(tmp_path), interject_check=check)

    assert msgs[-1].get("interrupted") is True
    assert "插队" in msgs[-1]["content"]
    assert calls["n"] == 1
    assert gw.rounds
    assert any(e.get("interrupted") for e in events if e["type"] == "done")


def test_interject_false_runs_to_completion(tmp_path):
    gw = FakeGateway([chunks_tool("f_read", {"path": "x"}), chunks_text("完成")])
    msgs, _ = run_agent(gw, [], str(tmp_path), interject_check=lambda: False)
    assert msgs[-1]["content"] == "完成"
    assert not msgs[-1].get("interrupted")


def test_hard_stop_wins_and_does_not_wait_for_gap(tmp_path):
    calls = {"n": 0}

    def interject():
        calls["n"] += 1
        return True

    gw = FakeGateway([chunks_tool("f_read", {"path": "x"})])
    msgs, _ = run_agent(gw, [], str(tmp_path),
                        stop_check=lambda: True, interject_check=interject)
    assert "已中止当前回复" in msgs[-1]["content"]
    assert calls["n"] == 0
