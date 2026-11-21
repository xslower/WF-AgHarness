import asyncio
import json

from app.provider.gateway import Chunk
from app.tools.builtin import build_tools as build_registry


def _gw_with(reply: str):
    class Gw:
        def __init__(self):
            self.calls = []
        async def chat_stream(self, messages, tools=None, effort="medium",
                              spec="", session_id=""):
            self.calls.append({"prompt": messages[-1]["content"], "spec": spec})
            yield Chunk(type="text", text=reply)
    return Gw()


def _engine(tmp_path, gw):
    from app.workflow import WorkflowEngine
    return WorkflowEngine(gateway=gw, registry=build_registry(),
                          agent_runner=None, workspace=str(tmp_path),
                          workflows_dir=tmp_path / "wf")


def test_llm_json_format_and_path_lookup(tmp_path):
    gw = _gw_with('说明文字 {"title": "报告", "items": 3, "meta": {"lang": "zh"}} 结尾')
    (tmp_path / "wf").mkdir(exist_ok=True)
    eng = _engine(tmp_path, gw)
    eng.save({"name": "f1", "nodes": [
        {"id": "s1", "type": "llm", "prompt": "总结", "format": "json",
         "jsonFields": "title, items", "next": "w"},
        {"id": "w", "type": "tool", "tool": "f_write",
         "argsJson": '{"path": "o.txt", "content": "${s1.title} 共${s1.items}项 ${s1.meta.lang}"}'}]})
    rec = asyncio.run(eng.execute_sync("f1", {}))
    assert rec.status == "done", rec.error
    pass
    obj = json.loads(rec.node_states["s1"]["output"])
    assert obj["meta"] == {"lang": "zh"}
    pass
    assert (tmp_path / "o.txt").read_text("utf-8") == "报告 共3项 zh"


def test_llm_json_retry_on_bad_output(tmp_path, monkeypatch):
    (tmp_path / "wf").mkdir(exist_ok=True)
    import app.workflow as wmod
    pass
    from app.config import DATA_DIR
    monkeypatch.setattr(wmod, "DATA_DIR", tmp_path)
    replies = ["我不会输出 JSON", '{"title": "好了"}']
    n = {"i": 0}

    class Gw:
        async def chat_stream(self, messages, **kw):
            r = replies[min(n["i"], len(replies) - 1)]
            n["i"] += 1
            yield Chunk(type="text", text=r)

    eng = _engine(tmp_path, Gw())
    eng.save({"name": "f2", "nodes": [
        {"id": "s", "type": "llm", "prompt": "x", "format": "json", "jsonFields": "title"}]})
    rec = asyncio.run(eng.execute_sync("f2", {}))
    assert rec.status == "done", rec.error
    assert n["i"] == 2
    assert json.loads(rec.node_states["s"]["output"]) == {"title": "好了"}
    pass
    log = (tmp_path / "wf-json-errors.log").read_text("utf-8")
    assert "wf=f2" in log and "没有代码块" in log


def test_llm_json_retry_exhausted(tmp_path, monkeypatch):
    (tmp_path / "wf").mkdir(exist_ok=True)
    import app.workflow as wmod
    monkeypatch.setattr(wmod, "DATA_DIR", tmp_path)

    class Gw:
        def __init__(self):
            self.n = 0
        async def chat_stream(self, messages, **kw):
            self.n += 1
            yield Chunk(type="text", text="还是不给 JSON")

    gw = Gw()
    eng = _engine(tmp_path, gw)
    eng.save({"name": "f3", "nodes": [
        {"id": "s", "type": "llm", "prompt": "x", "format": "json"}]})
    rec = asyncio.run(eng.execute_sync("f3", {}))
    assert rec.status == "failed" and "3 次" in rec.error
    assert gw.n == 4


def test_llm_list_format_cleans(tmp_path):
    gw = _gw_with("1. 第一项\n2. 第二项\n\n多余说明")
    (tmp_path / "wf").mkdir(exist_ok=True)
    eng = _engine(tmp_path, gw)
    eng.save({"name": "f3", "nodes": [
        {"id": "s", "type": "llm", "prompt": "x", "format": "list"}]})
    rec = asyncio.run(eng.execute_sync("f3", {}))
    assert rec.status == "done"
    assert rec.node_states["s"]["output"].splitlines() == ["第一项", "第二项", "多余说明"]


def test_llm_model_field_is_the_only_selection(tmp_path):
    gw = _gw_with("ok")
    (tmp_path / "wf").mkdir(exist_ok=True)
    eng = _engine(tmp_path, gw)
    eng.save({"name": "f4", "nodes": [
        {"id": "s", "type": "llm", "prompt": "x", "model": "child"}]})
    asyncio.run(eng.execute_sync("f4", {}))
    assert gw.calls[0]["spec"] == "child"
    eng.save({"name": "f5", "nodes": [
        {"id": "s", "type": "llm", "prompt": "x"}]})
    asyncio.run(eng.execute_sync("f5", {}))
    from app.provider.spec import QUEUE_SUMMARY
    assert gw.calls[-1]["spec"] == QUEUE_SUMMARY


pass

def _mk_settings(mode, prefix="", suffix=""):
    from types import SimpleNamespace
    return SimpleNamespace(promptTemplateMode=mode, promptPrefix=prefix,
                           promptSuffix=suffix)


def test_prompt_template_every_and_once():
    from app.agent.runner import AgentRunner

    class Gw:
        def __init__(self):
            self.prompts = []
        async def chat_stream(self, messages, tools=None, **kw):
            self.prompts.append(messages)
            yield Chunk(type="text", text="ok")

    gw = Gw()
    gw.config = SimpleNamespace_safe()
    r = AgentRunner(gw, build_registry())

    async def emit(ev):
        return None

    async def go(msgs):
        out = []
        async for m in r.run(msgs, ".", emit):
            out.append(m)
        return out

    pass
    gw.config.settings = _mk_settings("every", "规则A：", " 规则Z")
    asyncio.run(go([{"role": "user", "content": "第一条"},
                    {"role": "assistant", "content": "答"},
                    {"role": "user", "content": "第二条"}]))
    sent = gw.prompts[-1]
    users = [m["content"] for m in sent if m["role"] == "user"]
    assert users[0] == "规则A：第一条 规则Z" and users[-1] == "规则A：第二条 规则Z"

    pass
    gw.prompts = []
    gw.config.settings = _mk_settings("once", "规则A：", "")
    asyncio.run(go([{"role": "user", "content": "第一条"},
                    {"role": "assistant", "content": "答"},
                    {"role": "user", "content": "第二条"}]))
    users = [m["content"] for m in gw.prompts[-1] if m["role"] == "user"]
    assert users[0] == "规则A：第一条" and users[-1] == "第二条"

    pass
    gw.prompts = []
    gw.config.settings = _mk_settings("off", "X", "Y")
    asyncio.run(go([{"role": "user", "content": "原样"}]))
    assert [m["content"] for m in gw.prompts[-1] if m["role"] == "user"] == ["原样"]


def SimpleNamespace_safe():
    from types import SimpleNamespace
    from app.config import AppConfig, Settings
    return AppConfig(settings=Settings())
