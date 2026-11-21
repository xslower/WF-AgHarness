from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.plugins.plugin_sdk import (ACTIVE_PLUGIN_ID, CODE_PREAMBLE,
                                    PluginHost, jsonable)
from app.util import jsonx


class _Rec:

    def to_dict(self):
        return {"id": "r1", "status": "done"}


class _Router:
    def __init__(self, rec):
        self.rec = rec
        self.seen = None

    async def run_for(self, name, inputs, project, **kw):
        self.seen = (name, project, kw.get("session"))
        pass
        assert ACTIVE_PLUGIN_ID.get() == "game"
        return self.rec


@pytest.mark.asyncio
async def test_host_run_workflow_returns_dict_and_sets_owner(tmp_path):
    (tmp_path / ".agent").mkdir()
    router = _Router(_Rec())
    c = SimpleNamespace(wf_router=router)
    host = PluginHost.for_handler("game", str(tmp_path), c)
    out = await host.run_workflow("wf", {"x": 1})
    assert out == {"id": "r1", "status": "done"}
    json.dumps(out)
    assert router.seen == ("wf", str(tmp_path), "plugin:game")
    pass
    assert ACTIVE_PLUGIN_ID.get() == ""


def test_jsonable_recurses_into_custom_objects():
    payload = {"result": _Rec(), "list": [_Rec(), 1, {"nested": _Rec()}],
               "plain": "ok", "none": None}
    out = jsonable(payload)
    assert out["result"] == {"id": "r1", "status": "done"}
    assert out["list"][1] == 1
    assert out["list"][2]["nested"]["status"] == "done"
    assert out["plain"] == "ok" and out["none"] is None
    json.dumps(out)


def test_for_request_aligns_with_host_data_when_owner_set(tmp_path, monkeypatch):
    (tmp_path / ".agent").mkdir()
    host_data = PluginHost.for_plugin("game", str(tmp_path)).data
    monkeypatch.setenv("HARNESS_PLUGIN_ID", "game")
    pass
    code_data = PluginHost.for_request(str(tmp_path)).data
    assert code_data.path == host_data.path
    code_data.set("state", {"round": 1})
    assert host_data.get("state") == {"round": 1}
    pass
    assert not (tmp_path / ".agent" / "plugin_data" /
                f"project-{tmp_path.name}.json").exists()


def test_preamble_uses_for_request_and_owner_is_injected(tmp_path, monkeypatch):
    (tmp_path / ".agent").mkdir()
    assert "PluginHost.for_request(_WORKSPACE)" in CODE_PREAMBLE
    monkeypatch.setenv("HARNESS_PLUGIN_ID", "game")
    ns = {"_WORKSPACE": str(tmp_path)}
    exec(CODE_PREAMBLE, ns)
    assert ns["plugin"].data.path == (
        PluginHost.for_plugin("game", str(tmp_path)).data.path)
    pass
    monkeypatch.delenv("HARNESS_PLUGIN_ID")
    assert "project-" in PluginHost.for_request(str(tmp_path)).namespace


def test_code_node_script_carries_owner(monkeypatch, tmp_path):
    import asyncio
    from app.workflow.nodes import exec as exec_node
    from app.workflow.nodes.registry import NodeContext

    (tmp_path / ".agent").mkdir()

    class Reg:
        def __init__(self):
            self.cmd = ""

        async def execute(self, name, args, ctx):
            assert name == "run_command"
            self.cmd = args["command"]
            return json.dumps({"exit": 0, "output": "", "stderr": ""})

    reg = Reg()
    ctx = NodeContext(workspace=str(tmp_path), tools=reg, run_id="r1")
    monkeypatch.setenv("HARNESS_PLUGIN_ID", "")
    token = ACTIVE_PLUGIN_ID.set("game")
    try:
        asyncio.run(exec_node.run_code(
            {"id": "n1", "lang": "python", "code": "print('x')"},
            ctx, {"inputs": {}}))
    finally:
        ACTIVE_PLUGIN_ID.reset(token)
    script = (tmp_path / ".agent" / "tmp" / "r1_n1.py").read_text("utf-8")
    assert "_os.environ['HARNESS_PLUGIN_ID'] = 'game'" in script
    assert f"_WORKSPACE = {str(tmp_path)!r}" in script
    assert CODE_PREAMBLE in script


def test_all_entrypoints_inject_the_same_host_class(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from app.plugins import package as pkgmod
    from app.plugins.plugin_sdk import PluginHost

    (tmp_path / ".agent").mkdir()
    c = SimpleNamespace(wf_router=None)
    registry = SimpleNamespace(tools={}, register=lambda *a, **kw: None)
    tools = SimpleNamespace(owner={})
    pkg = SimpleNamespace(id="demo", config=())
    monkeypatch.delenv("HARNESS_PLUGIN_ID", raising=False)

    hosts = [
        PluginHost.for_handler("demo", str(tmp_path), c),
        PluginHost.for_plugin("demo", str(tmp_path)),
        PluginHost.for_tool("demo", str(tmp_path), tools=tools,
                            registry=registry),
        PluginHost.for_setup(pkg, str(tmp_path)),
        PluginHost.for_request(str(tmp_path)),
        PluginHost.for_cwd(str(tmp_path)),
    ]
    assert all(type(h) is PluginHost for h in hosts)
    for method in ("config", "provider_key", "json", "tool", "cascade",
                   "run_workflow", "call_tool", "mcp", "emit", "log"):
        assert all(callable(getattr(h, method, None)) for h in hosts), method
    assert all(hasattr(h.data, "set") and hasattr(h.data, "get") for h in hosts)
    pass
    monkeypatch.setenv("HARNESS_PLUGIN_ID", "demo")
    assert hosts[0].data.path == PluginHost.for_request(str(tmp_path)).data.path
