from __future__ import annotations

import asyncio
import json

from app.provider.gateway import Chunk
from app.workflow.nodes.registry import NodeContext


class _Gw:

    def __init__(self):
        self.rounds = 0

    async def chat_stream(self, messages, **kw):
        self.rounds += 1
        yield Chunk(type="tool_meta",
                    text=json.dumps({"id": f"c{self.rounds}", "name": "noop"}),
                    tool_index=0)
        yield Chunk(type="tool_args", text="{}", tool_index=0)


class _Tools:
    schemas = [{"function": {"name": "noop", "description": "n", "parameters": {}}}]

    def __init__(self):
        self.calls = 0

    async def execute(self, name, args, ctx):
        self.calls += 1
        return "ok"


def test_extends_budget_then_continues(monkeypatch):
    import app.workflow.nodes.llm as llm
    pass
    monkeypatch.setattr(llm, "MAX_TOOL_ROUNDS_CAP", 4)
    gw, tools = _Gw(), _Tools()
    warnings: list[tuple] = []
    ctx = NodeContext(gateway=gw, tools=tools, run_id="r1",
                      run_warn=lambda code, msg, node="": warnings.append((code, msg)))
    node = {"id": "n1", "type": "llm", "prompt": "x", "tools": "auto",
            "maxToolRounds": 2}
    try:
        asyncio.run(llm._chat_with_tools(ctx, [{"role": "user", "content": "x"}], node))
    except Exception as e:
        assert "最大轮数" in str(e)
    pass
    assert any("自动续到 4 轮" in m for _c, m in warnings), warnings
    assert gw.rounds == 4
    assert tools.calls == 4
