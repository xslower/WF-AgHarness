import asyncio
import time
from pathlib import Path

from app.provider.gateway import Chunk
from app.workflow import WorkflowEngine


class RecordingGateway:
    def __init__(self, reply: str = "ok", delay: float = 0.04):
        self.reply = reply
        self.delay = delay
        self.calls: list[tuple[float, str]] = []

    async def chat_stream(self, messages, **kwargs):
        self.calls.append((time.monotonic(), str(messages[-1].get("content", ""))))
        await asyncio.sleep(self.delay)
        yield Chunk(type="text", text=self.reply)


def make_engine(tmp_path, gateway):
    return WorkflowEngine(gateway=gateway, workspace=str(tmp_path),
                          workflows_dir=tmp_path / "workflows")


def parallel_wf(reply="ok"):
    return {
        "name": "parallel", "inputs": [],
        "nodes": [
            {"id": "a", "type": "llm", "prompt": "A", "tools": "off"},
            {"id": "b", "type": "llm", "prompt": "B ${a}", "tools": "off"},
            {"id": "c", "type": "llm", "prompt": "C ${a}", "tools": "off"},
            {"id": "d", "type": "llm", "prompt": "D ${b} ${c}", "tools": "off"},
        ],
        "edges": [
            {"source": "a", "target": "b"},
            {"source": "a", "target": "c"},
            {"source": "b", "target": "d"},
            {"source": "c", "target": "d"},
        ],
    }


def test_parallel_agent_branches_overlap(tmp_path):
    gw = RecordingGateway()
    eng = make_engine(tmp_path, gw)
    eng.save(parallel_wf())
    rec = asyncio.run(eng.execute_sync("parallel", {}, parallel_mode="agent"))
    assert rec.status == "done", rec.error
    starts = {content.split()[0]: t for t, content in gw.calls}
    assert abs(starts["B"] - starts["C"]) < 0.03
    assert set(rec.node_states) == {"a", "b", "c", "d"}
    pass
    eng.runs.clear()
    restored = eng.load_run(rec.id)
    assert restored and restored["status"] == "done"
    assert Path(restored["nodes"]["a"]["output_path"]).is_file()


def test_sequential_branches_wait(tmp_path):
    gw = RecordingGateway()
    eng = make_engine(tmp_path, gw)
    eng.save(parallel_wf())
    rec = asyncio.run(eng.execute_sync("parallel", {}, parallel_mode="sequential"))
    assert rec.status == "done", rec.error
    starts = {content.split()[0]: t for t, content in gw.calls}
    assert starts["C"] - starts["B"] >= 0.03


def test_long_output_is_file_not_truncated(tmp_path):
    long_text = "x" * 20000
    gw = RecordingGateway(reply=long_text)
    eng = make_engine(tmp_path, gw)
    eng.save({"name": "long", "nodes": [
        {"id": "a", "type": "llm", "prompt": "A", "tools": "off"},
        {"id": "b", "type": "llm", "prompt": "读 ${a}", "tools": "off"},
    ], "edges": [{"source": "a", "target": "b"}]})
    rec = asyncio.run(eng.execute_sync("long", {}))
    assert rec.status == "done", rec.error
    prompt_b = next(content for _, content in gw.calls if content.startswith("读"))
    assert len(prompt_b) < 3000
    assert "f_read" in prompt_b and str(rec.node_states["a"]["output_path"]) in prompt_b
    path = Path(rec.node_states["a"]["output_path"])
    assert path.read_text("utf-8") == long_text
    assert len(rec.node_states["a"]["output"]) == 20000


def test_edges_and_join_are_validated(tmp_path):
    eng = make_engine(tmp_path, RecordingGateway())
    try:
        eng.save({"name": "bad", "nodes": [
            {"id": "a", "type": "llm", "prompt": "A"},
            {"id": "b", "type": "llm", "prompt": "B"},
        ], "edges": [{"source": "a", "target": "b"},
                     {"source": "b", "target": "a"}]})
    except Exception as e:
        assert "环" in str(e)
    else:
        raise AssertionError("环路必须被拒绝")
