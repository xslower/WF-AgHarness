from __future__ import annotations

import asyncio

from app.provider.gateway import Chunk
from app.tools.builtin import build_tools as build_registry
from app.workflow import WorkflowEngine


class _SessionStub:

    def __init__(self):
        self.rows: dict[str, dict] = {}
        self._n = 0

    def create(self, title="", project="", kind="", origin=""):
        self._n += 1
        sid = f"s{self._n}"
        self.rows[sid] = {"id": sid, "title": title, "project": project,
                          "created_at": float(self._n), "messages": [],
                          "kind": kind, "origin": origin}
        return dict(self.rows[sid])

    def find_active(self, project, kind, origin):
        hits = [r for r in self.rows.values()
                if r["kind"] == kind and r["origin"] == origin]
        return hits[-1] if hits else None

    def get(self, sid):
        row = self.rows.get(sid)
        return dict(row) if row else None

    def save(self, s):
        row = self.rows.setdefault(s["id"], {})
        row.update({k: v for k, v in s.items() if k != "messages"})
        row["messages"] = list(s.get("messages") or [])

    def wf_node_parents(self):
        return {r["origin"] for r in self.rows.values()
                if r.get("kind") == "wf-node" and r.get("origin")}

    def delete(self, sid):
        self.rows.pop(sid, None)


class _Gw:

    def __init__(self, reply="好的"):
        self.reply = reply
        self.seen: list[list[dict]] = []

    async def chat_stream(self, messages, **kw):
        self.seen.append([dict(m) for m in messages])
        yield Chunk(type="text", text=self.reply)


def _engine(tmp_path, gw, sessions):
    return WorkflowEngine(gateway=gw, registry=build_registry(),
                          agent_runner=None, workspace=str(tmp_path),
                          workflows_dir=tmp_path / "wf", sessions=sessions)


def _wf(tmp_path, prompt="任务A"):
    (tmp_path / "wf").mkdir(exist_ok=True)
    return {"name": "s", "nodes": [
        {"id": "n1", "type": "llm", "system": "你是助手", "prompt": prompt}]}


def test_same_session_replays_history_and_keeps_prefix(tmp_path):
    sessions = _SessionStub()
    gw = _Gw("第一轮结论")
    eng = _engine(tmp_path, gw, sessions)
    eng.save(_wf(tmp_path))
    first = asyncio.run(eng.execute_sync("s", {}, session="new"))
    assert first.status == "done", first.error
    assert first.session, "运行记录必须带会话 id，前端据此归类"

    gw2 = _Gw("第二轮结论")
    eng2 = _engine(tmp_path, gw2, sessions)
    eng2.save(_wf(tmp_path))
    second = asyncio.run(eng2.execute_sync("s", {}, session=first.session))

    msgs = gw2.seen[0]
    assert [m["role"] for m in msgs] == ["system", "user", "assistant", "user"]
    pass
    assert msgs[0]["content"] == "你是助手"
    assert msgs[1]["content"] == "任务A"
    assert msgs[2]["content"] == "第一轮结论"
    assert second.session == first.session


def test_new_session_starts_clean(tmp_path):
    sessions = _SessionStub()
    eng = _engine(tmp_path, _Gw(), sessions)
    eng.save(_wf(tmp_path))
    first = asyncio.run(eng.execute_sync("s", {}, session="new"))

    gw2 = _Gw()
    eng2 = _engine(tmp_path, gw2, sessions)
    eng2.save(_wf(tmp_path))
    second = asyncio.run(eng2.execute_sync("s", {}, session="new"))
    assert [m["role"] for m in gw2.seen[0]] == ["system", "user"]
    assert second.session != first.session


def test_run_without_llm_node_recycled_empty_session(tmp_path):
    from app.workflow.nodes.registry import NodeRegistry, NodeSpec

    async def run_echo(node, ctx, vars):
        return "ok", None

    reg = NodeRegistry()
    reg.register(NodeSpec(type="echo", label="echo", run=run_echo))
    sessions = _SessionStub()
    eng = WorkflowEngine(gateway=_Gw(), registry=build_registry(),
                         agent_runner=None, workspace=str(tmp_path),
                         workflows_dir=tmp_path / "wf", sessions=sessions,
                         nodes=reg)
    (tmp_path / "wf").mkdir(exist_ok=True)
    eng.save({"name": "codeonly", "nodes": [
        {"id": "n1", "type": "echo", "text": "ok"}]})
    rec = asyncio.run(eng.execute_sync("codeonly", {}, session="new"))
    assert rec.status == "done", rec.error
    assert rec.session
    assert rec.session not in sessions.rows, "空壳 wf-session 必须被回收"


def test_run_with_llm_node_keeps_session(tmp_path):
    sessions = _SessionStub()
    eng = _engine(tmp_path, _Gw(), sessions)
    eng.save(_wf(tmp_path))
    rec = asyncio.run(eng.execute_sync("s", {}, session="new"))
    assert rec.status == "done", rec.error
    assert rec.session in sessions.rows


def test_no_session_store_keeps_old_behavior(tmp_path):
    gw = _Gw()
    eng = WorkflowEngine(gateway=gw, registry=build_registry(),
                         agent_runner=None, workspace=str(tmp_path),
                         workflows_dir=tmp_path / "wf")
    eng.save(_wf(tmp_path))
    rec = asyncio.run(eng.execute_sync("s", {}))
    assert rec.status == "done" and rec.session == ""
    assert [m["role"] for m in gw.seen[0]] == ["system", "user"]
