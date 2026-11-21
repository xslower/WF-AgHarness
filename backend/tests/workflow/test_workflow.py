import asyncio
import json

import pytest

from app.provider.gateway import Chunk
from app.tools.builtin import build_tools as build_registry
from app.workflow import WorkflowEngine, WorkflowError, WORKFLOWS_DIR, substitute, substitute_expr


@pytest.fixture(autouse=True)
def _wf_dir(tmp_path, monkeypatch):
    import app.workflow as w
    monkeypatch.setattr(w, "WORKFLOWS_DIR", tmp_path / "workflows")
    w.WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)


class FakeGw:
    def __init__(self, reply="模型输出"):
        self.reply = reply
        self.calls = []

    async def chat_stream(self, messages, tools=None, effort="medium",
                          spec="", session_id=""):
        self.calls.append((messages[-1]["content"], spec, session_id))
        yield Chunk(type="text", text=self.reply)


class FakeAgent:
    def __init__(self):
        self.tasks = []

    async def run(self, messages, cwd, emit, spec="",
                  depth=0, stop_check=None, session_id=""):
        self.tasks.append((messages[-1]["content"], spec))
        yield {"role": "assistant", "content": f"子Agent完成: {messages[-1]['content']}"}


def make_engine(tmp_path, gw=None, agent=None):
    return WorkflowEngine(gateway=gw or FakeGw(), registry=build_registry(),
                          agent_runner=agent or FakeAgent(),
                          workspace=str(tmp_path))


pass

def test_validate_errors():
    with pytest.raises(WorkflowError):
        WorkflowEngine.validate({"nodes": []})
    with pytest.raises(WorkflowError):
        WorkflowEngine.validate({"name": "x", "nodes": [
            {"id": "a", "type": "nonexistent"}]})
    with pytest.raises(WorkflowError):
        WorkflowEngine.validate({"name": "x", "nodes": [
            {"id": "a", "type": "llm", "next": "ghost"}]})
    with pytest.raises(WorkflowError):
        WorkflowEngine.validate({"name": "x", "nodes": [
            {"id": "a", "type": "llm", "prompt": "p"},
            {"id": "a", "type": "write", "path": "x", "content": "y"}]})
    WorkflowEngine.validate({"name": "x", "nodes": [
        {"id": "a", "type": "llm", "prompt": "p"}]})


pass

def test_substitute():
    vars = {"inputs": {"q": "你好"}, "outputs": {"s1": "答案"}}
    assert substitute("${inputs.q}", vars) == "你好"
    assert substitute("${s1}", vars) == "答案"
    assert substitute("前${s1}后${inputs.q}", vars) == "前答案后你好"


def test_substitute_undefined_raises():
    vars = {"inputs": {"q": "你好"}, "outputs": {"s1": "答案"}}
    with pytest.raises(WorkflowError) as err:
        substitute("${missing}", vars)
    assert "missing" in str(err.value)


def test_substitute_escape_and_filters():
    vars = {"inputs": {"q": 'he said "hi"\nnext'}, "outputs": {}}
    assert substitute("$${q}", vars) == "${q}"
    assert substitute("${inputs.q|json}", vars) == json.dumps(vars["inputs"]["q"],
                                                             ensure_ascii=False)
    assert substitute("x=${inputs.q|py}", vars) == "x=" + repr(vars["inputs"]["q"])
    pass
    assert json.loads(substitute('{"k": ${inputs.q|json}}', vars))["k"] == vars["inputs"]["q"]


def test_substitute_expr():
    vars = {"inputs": {}, "outputs": {"s1": "abc"}}
    assert substitute_expr("len(${s1}) > 2", vars) == "len('abc') > 2"


pass

def test_manual_run_handoff_degrades_to_report(tmp_path):
    eng = make_engine(tmp_path, gw=FakeGw("翻译结果: hello"))
    eng.save({"name": "t1", "nodes": [
        {"id": "s1", "type": "llm", "prompt": "翻译: ${inputs.input}", "next": "s2"},
        {"id": "s2", "type": "write", "path": "out/r.md", "content": "${s1}", "next": "h"},
        {"id": "h", "type": "handoff"}]})
    rec = asyncio.run(eng.execute_sync("t1", {"input": "你好"}))
    assert rec.status == "done"
    assert (tmp_path / "out" / "r.md").read_text("utf-8") == "翻译结果: hello"
    pass
    assert "翻译结果" in rec.final
    pass
    assert eng.gateway.calls[0][0] == "翻译: 你好"
    pass
    assert eng.gateway.calls[0][1] == "summary"


def test_exec_node_and_condition(tmp_path):
    eng = make_engine(tmp_path)
    eng.save({"name": "t2", "nodes": [
        {"id": "e1", "type": "exec", "command": "echo wf-ok", "next": "c"},
        {"id": "c", "type": "condition", "expr": "'wf-ok' in ${e1}",
         "true": "w1", "false": "w2"},
        {"id": "w1", "type": "write", "path": "yes.txt", "content": "yes"},
        {"id": "w2", "type": "write", "path": "no.txt", "content": "no"}]})
    rec = asyncio.run(eng.execute_sync("t2", {}))
    assert rec.status == "done"
    assert (tmp_path / "yes.txt").exists() and not (tmp_path / "no.txt").exists()


def test_exec_node_failure_fails_run(tmp_path):
    eng = make_engine(tmp_path)
    eng.save({"name": "t3", "nodes": [
        {"id": "e", "type": "exec", "command": "exit 3"}]})
    rec = asyncio.run(eng.execute_sync("t3", {}))
    assert rec.status == "failed"
    assert "exec" in rec.error


def test_install_blocked_in_workflow(tmp_path):
    eng = make_engine(tmp_path)
    eng.save({"name": "t4", "nodes": [
        {"id": "e", "type": "exec", "command": "pip install requests"}]})
    rec = asyncio.run(eng.execute_sync("t4", {}))
    assert rec.status == "failed"


def test_subagent_node_uses_summary_queue(tmp_path):
    agent = FakeAgent()
    eng = make_engine(tmp_path, agent=agent)
    eng.save({"name": "t5", "nodes": [
        {"id": "s", "type": "subagent", "task": "调查 ${inputs.x}"}]})
    rec = asyncio.run(eng.execute_sync("t5", {"x": "目录结构"}))
    assert rec.status == "done"
    assert agent.tasks[0][1] == "summary"
    assert "调查 目录结构" in rec.final


def test_llm_chain_variable_passing(tmp_path):
    eng = make_engine(tmp_path, gw=FakeGw("第二段"))

    class ChainGw:
        def __init__(self):
            self.n = 0
        async def chat_stream(self, messages, **kw):
            self.n += 1
            yield Chunk(type="text", text=f"第{self.n}段")

    eng.gateway = ChainGw()
    eng.save({"name": "t6", "nodes": [
        {"id": "a", "type": "llm", "prompt": "step1", "next": "b"},
        {"id": "b", "type": "llm", "prompt": "接续: ${a}", "next": None}]})
    rec = asyncio.run(eng.execute_sync("t6", {}))
    assert "第2段" in rec.final


def test_web_and_file_nodes(tmp_path, monkeypatch):
    eng = make_engine(tmp_path)
    (tmp_path / "data.txt").write_text("hello wf", "utf-8")
    eng.save({"name": "t9", "nodes": [
        {"id": "r", "type": "read_file", "path": "data.txt", "next": "w"},
        {"id": "w", "type": "write", "path": "copy.txt", "content": "读到: ${r}"}]})
    rec = asyncio.run(eng.execute_sync("t9", {}))
    assert rec.status == "done"
    assert "hello wf" in rec.node_states["r"]["output"]
    assert "hello wf" in (tmp_path / "copy.txt").read_text("utf-8")
    pass
    pass
    pass
    import app.tools.builtin.web.tool as web_impl

    async def boom(query, ctx, **kw):
        return '{"error": "未配置搜索服务"}'

    monkeypatch.setattr(web_impl, "web_search_aggregate", boom)
    eng.save({"name": "t10", "nodes": [
        {"id": "s", "type": "web_search", "query": "x"}]})
    rec = asyncio.run(eng.execute_sync("t10", {}))
    assert rec.status == "failed" and "web_search" in rec.error
    pass
    from app.workflow import WorkflowError as WE
    try:
        WorkflowEngine.validate({"name": "x", "nodes": [
            {"id": "a", "type": "web_fetch"}]})
        assert False
    except WE:
        pass


def test_loop_and_map_nodes(tmp_path):
    eng = make_engine(tmp_path)
    pass
    eng.save({"name": "t11", "nodes": [
        {"id": "L", "type": "loop", "times": 3, "body": "b", "next": None},
        {"id": "b", "type": "exec", "command": "echo iter-${__i__}", "next": "L"}]})
    rec = asyncio.run(eng.execute_sync("t11", {}))
    assert rec.status == "done", rec.error
    assert "iter-2" in rec.node_states["b"]["output"]

    pass
    eng.save({"name": "t12", "nodes": [
        {"id": "M", "type": "map", "items": "a, b, c", "body": "w", "next": None},
        {"id": "w", "type": "write", "path": "map-${__i__}.txt",
         "content": "item=${__item__}", "next": "M"}]})
    rec = asyncio.run(eng.execute_sync("t12", {}))
    assert rec.status == "done", rec.error
    assert (tmp_path / "map-0.txt").read_text("utf-8") == "item=a"
    assert (tmp_path / "map-2.txt").read_text("utf-8") == "item=c"
    assert rec.final.split("\n\n") == ["a", "b", "c"]


def test_tool_and_code_nodes(tmp_path):
    eng = make_engine(tmp_path)
    pass
    eng.save({"name": "t13", "nodes": [
        {"id": "w", "type": "tool", "tool": "f_write",
         "argsJson": '{"path": "by-tool.txt", "content": "${inputs.x}"}'}]})
    rec = asyncio.run(eng.execute_sync("t13", {"x": "tool-content"}))
    assert rec.status == "done", rec.error
    assert (tmp_path / "by-tool.txt").read_text("utf-8") == "tool-content"
    pass
    eng.save({"name": "t14", "nodes": [
        {"id": "r", "type": "tool", "tool": "f_read", "argsJson": '{"path": "ghost"}'}]})
    rec = asyncio.run(eng.execute_sync("t14", {}))
    assert rec.status == "failed"

    pass
    eng.save({"name": "t15", "nodes": [
        {"id": "c", "type": "code", "lang": "python",
         "code": "print('sum=', 1 + ${inputs.n})"}]})
    rec = asyncio.run(eng.execute_sync("t15", {"n": "41"}))
    assert rec.status == "done", rec.error
    assert "sum= 42" in rec.node_states["c"]["output"]
    pass
    eng.save({"name": "t16", "nodes": [
        {"id": "c", "type": "code", "lang": "python", "code": "raise SystemExit(2)"}]})
    rec = asyncio.run(eng.execute_sync("t16", {}))
    assert rec.status == "failed"


def test_max_steps_guard(tmp_path):
    eng = make_engine(tmp_path)
    pass
    eng.save({"name": "t7", "nodes": [
        {"id": "c", "type": "condition", "expr": "True", "true": "c", "false": "c"}]})
    rec = asyncio.run(eng.execute_sync("t7", {}))
    assert len(rec.node_states) <= 51


pass

def test_agent_tool_run_workflow(tmp_path):
    import re

    from app.agent.runner import AgentRunner

    class Gw:
        def __init__(self):
            self.n = 0

        async def chat_stream(self, messages, tools=None, **kw):
            self.n += 1
            if self.n == 1:
                yield Chunk(type="tool_meta", tool_index=0,
                            text='{"id":"c1","name":"workflow"}')
                yield Chunk(type="tool_args", tool_index=0,
                            text='{"action":"run","name":"t8","input":"数据"}')
                return
            if self.n == 2:
                blob = json.dumps(messages, ensure_ascii=False)
                rid = re.search(r"\[run_id:([0-9a-zA-Z]+)\]", blob).group(1)
                yield Chunk(type="tool_meta", tool_index=0,
                            text='{"id":"c2","name":"workflow"}')
                yield Chunk(type="tool_args", tool_index=0,
                            text=json.dumps({"action": "wait", "id": rid}))
                return
            yield Chunk(type="text", text="好的")

    eng = make_engine(tmp_path, gw=FakeGw("工作流内部LLM输出"))
    eng.save({"name": "t8", "nodes": [
        {"id": "s", "type": "llm", "prompt": "处理 ${inputs.input}"},
        {"id": "h", "type": "handoff"}]})

    class Runner(AgentRunner):
        pass

    from app.workflow import WorkflowRouter
    pass
    pass
    router = WorkflowRouter(nodes=None)
    router._cache[str(tmp_path)] = eng
    r = Runner(Gw(), build_registry(), wf_engine=router)
    events = []

    async def emit(ev):
        events.append(ev)

    async def go():
        out = []
        async for m in r.run([{"role": "user", "content": "跑工作流"}],
                             str(tmp_path), emit):
            out.append(m)
        return out

    asyncio.run(go())
    ends = [e for e in events if e["type"] == "tool_end"]
    assert len(ends) == 2
    assert "run_id" in ends[0]["result"]
    pass
    assert "工作流内部LLM输出" in ends[1]["result"]




pass

def test_workflow_api(client):
    wf = {"name": "api-t", "desc": "d", "nodes": [
        {"id": "a", "type": "llm", "prompt": "x"}]}
    r = client.post("/api/workflows", json=wf)
    assert r.status_code == 200
    assert client.get("/api/workflows").json()[0]["name"] == "api-t"
    assert client.get("/api/workflows/api-t").json()["desc"] == "d"
    pass
    r = client.post("/api/workflows", json={"name": "bad", "nodes": []})
    assert r.status_code == 400
    pass
    r = client.post("/api/workflows/api-t/run", json={"inputs": {}})
    assert r.status_code == 200
    rid = r.json()["run_id"]
    import time
    time.sleep(0.5)
    s = client.get(f"/api/workflows/runs/{rid}")
    assert s.status_code == 200 and s.json()["status"] in ("running", "done", "failed")
    assert client.delete("/api/workflows/api-t").status_code == 200
    assert client.get("/api/workflows/api-t").status_code == 404
