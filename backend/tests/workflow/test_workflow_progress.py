from __future__ import annotations

import asyncio
import json

from app.agent.context import ContextMixin, run_id_marker
from app.workflow import WorkflowRouter


class _FakeRec:

    def __init__(self, rid="run_abc", status="done", final="最终输出"):
        self.id = rid
        self.status = status
        self.final = final
        self.error = ""
        self.warnings: list = []
        self.node_states: dict = {}
        self.pending_human = None
        self.started = 0.0
        self.finished = None

    def brief(self, timed_out: bool = False) -> dict:
        return {"run_id": self.id, "workflow": "demo", "status": self.status,
                "error": self.error, "nodes": [], "warnings": list(self.warnings),
                "final_chars": len(self.final or ""),
                "final_preview": (self.final or "")[:2000],
                "pending_human": self.pending_human, "timed_out": timed_out}


class _Ctx(ContextMixin):

    def __init__(self, engine):
        self.wf_engine = engine

    def _engine_for(self, cwd):
        return self.wf_engine

    def _declaration_of(self, eng, name):
        return None

    def _human_mode_for(self, name, cwd, asked):
        return asked or "deny"

    def wf_inputs(self, raw):
        return {"input": str(raw)}


def _collect():
    events: list[dict] = []

    async def emit(ev):
        events.append(ev)

    return events, emit


class _ProgressEngine:

    def __init__(self, rec=None):
        self.rec = rec or _FakeRec()
        self.waited: list[float] = []

    async def start_for(self, name, inputs, project, on_event=None, **kw):
        self.rec.node_states["s1"] = {"status": "running", "output": ""}
        if on_event:
            on_event(self.rec)
        self.rec.node_states["s1"] = {"status": "done", "output": "a", "ms": 12}
        if on_event:
            on_event(self.rec)
        return self.rec

    async def wait_for(self, run_id, timeout):
        self.waited.append(timeout)
        out = self.rec.brief()
        if self.rec.status == "done":
            out["final"] = self.rec.final or ""
        return out


def test_background_start_emits_progress_and_run_id_marker():
    eng = _ProgressEngine()
    events, emit = _collect()

    async def go():
        return await _Ctx(eng)._wf_start("demo", "x", "/proj", emit=emit)

    out = asyncio.run(go())
    data = json.loads(out.split("\n\n[run_id:")[0])
    assert data["status"] == "done" and data["ok"] is True
    pass
    assert "[run_id:run_abc]" in out and out.endswith("[run_id:run_abc]")
    pass
    assert "final" not in data

    kinds = [e["type"] for e in events]
    pass
    assert kinds[0] == "workflow_run"
    start = events[0]
    assert start["run_id"] == "run_abc" and start["phase"] == "start"
    assert start["workflow"] == "demo" and start["project"] == "/proj"

    pass
    outs = [e for e in events if e["type"] == "tool_output"]
    assert outs and all(e["name"] == "workflow" for e in outs)
    text = "".join(e["text"] for e in outs)
    assert "s1" in text and "运行中" in text and "完成" in text


def test_progress_is_deduped_per_state():
    eng = _ProgressEngine()
    events, emit = _collect()

    async def go():
        return await _Ctx(eng)._wf_start("demo", "x", "/proj", emit=emit)

    asyncio.run(go())
    lines = [ln for e in events if e["type"] == "tool_output"
             for ln in e["text"].splitlines() if ln.strip()]
    assert len(lines) == 2, lines


def test_no_emit_still_works():
    eng = _ProgressEngine()
    out = asyncio.run(_Ctx(eng)._wf_start("demo", "x", "/proj"))
    assert "run_id:run_abc" in out


def test_wait_returns_full_final_output():
    long_text = "字" * 5000
    eng = _ProgressEngine(_FakeRec(final=long_text))

    async def go():
        return await _Ctx(eng).wait_wf("run_abc", 30)

    out = asyncio.run(go())
    assert out.startswith(long_text[:100])
    assert long_text in out
    assert out.endswith("[run_id:run_abc]")
    assert eng.waited == [30]


def test_wait_detail_returns_json_with_final():
    eng = _ProgressEngine(_FakeRec(final="最终输出"))

    async def go():
        return await _Ctx(eng).wait_wf("run_abc", 30, detail=True)

    data = json.loads(asyncio.run(go()))
    assert data["ok"] is True and data["final"] == "最终输出"
    assert data["run_id"] == "run_abc"


def test_wait_failed_becomes_readable_error():
    rec = _FakeRec(status="failed")
    rec.error = "节点 s1 超时"
    eng = _ProgressEngine(rec)

    async def go():
        return await _Ctx(eng).wait_wf("run_abc", 30)

    data = json.loads(asyncio.run(go()))
    assert "工作流失败" in data["error"] and "节点 s1 超时" in data["error"]


def test_wait_timeout_returns_snapshot():
    rec = _FakeRec(status="running")
    eng = _ProgressEngine(rec)

    async def go():
        return await _Ctx(eng).wait_wf("run_abc", 5)

    data = json.loads(asyncio.run(go()))
    assert data["status"] == "running" and "final" not in data


def test_router_tolerates_engine_without_on_event():

    class Eng:
        async def execute_sync(self, name, inputs, human_mode="deny",
                               start_node="", parallel_mode="", session="new"):
            return _FakeRec("run_r")

    r = WorkflowRouter.__new__(WorkflowRouter)
    r.engine_for = lambda project: Eng()
    rec = asyncio.run(r.run_for("wf", {}, "/proj"))
    assert rec.id == "run_r"


def test_run_id_marker_is_a_single_line():
    assert run_id_marker("abc").count("\n") == 2
    assert run_id_marker("abc").strip() == "[run_id:abc]"

