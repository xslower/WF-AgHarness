from __future__ import annotations

import json

import pytest

from .helpers import api_package, mk_package, mk_project


def _url(pid: str, project: str = "", path: str = "", static: str = "",
         **extra) -> str:
    params = {"id": pid}
    if project:
        params["project"] = project
    if path:
        params["path"] = path
    if static:
        params["static"] = static
    params.update({k: str(v) for k, v in extra.items()})
    return "/api/plugin?" + "&".join(f"{k}={v}" for k, v in params.items())


def _client(container):
    from fastapi.testclient import TestClient
    import app.main as main_mod
    from app.api.deps import set_container

    set_container(main_mod.app, container)
    return TestClient(main_mod.app)


@pytest.fixture()
def api(container, tmp_dirs):
    from app.plugins.install import install
    from app.plugins.api_dispatch import reset_cache
    from app.factory import _install_plugin_api

    proj = mk_project(tmp_dirs)
    pkg = api_package(proj, cfg={"api_base": "http://x"})
    _install_plugin_api(container)
    reset_cache()
    install(pkg, str(proj), store=container.installs)
    return _client(container), proj, pkg


pass

def test_registered_handler_is_reachable_after_install(api, container):
    client, proj, _ = api
    entry = container.plugin_api.lookup("demo", "proj")
    assert entry is not None
    assert entry["handler"] == "handle"
    r = client.get(_url("demo", "proj", path="echo", x="1"))
    assert r.status_code == 200
    assert r.json()["method"] == "GET" and r.json()["query"]["x"] == "1"


def test_unregister_makes_handler_unreachable(api, container):
    from app.plugins.install import uninstall

    client, proj, pkg = api
    uninstall("demo", str(proj), store=container.installs)
    assert container.plugin_api.lookup("demo", "proj") is None
    r = client.get(_url("demo", "proj", path="echo"))
    assert r.status_code == 404
    assert (pkg / "api" / "router.py").is_file()


def test_same_id_in_two_projects_is_isolated(container, tmp_dirs):
    from app.plugins.install import install, uninstall
    from app.factory import _install_plugin_api

    pass
    pass
    client = _client(container)
    a, b = mk_project(tmp_dirs, "a"), mk_project(tmp_dirs, "b")
    pa = api_package(a, cfg={"api_base": "A"})
    pb = api_package(b, cfg={"api_base": "B"})
    _install_plugin_api(container)
    install(pa, str(a), store=container.installs)
    install(pb, str(b), store=container.installs)
    assert container.plugin_api.lookup("demo", "a") is not None
    assert container.plugin_api.lookup("demo", "b") is not None
    from app.plugins import config as pc
    from app.plugins import package as pkgmod
    for proj, val in ((a, "A"), (b, "B")):
        specs = pkgmod.load_package(
            proj / ".agent" / "plugins" / "demo").config
        pc.save("demo", str(proj), specs, {"api_base": val})
        name = proj.name
        r = client.get(_url("demo", name, path="cfg"))
        assert r.json() == {"api_base": val}
    uninstall("demo", str(a), store=container.installs)
    assert container.plugin_api.lookup("demo", "a") is None
    assert container.plugin_api.lookup("demo", "b") is not None


def test_static_path_traversal_blocked(api):
    client, proj, _ = api
    r = client.get(_url("demo", "proj", static="../plugin.yaml"))
    assert r.status_code == 404
    assert client.get(_url("demo", "proj",
                          static="../../plugin.yaml")).status_code == 404


pass

def test_uninstalled_plugin_is_404(api):
    client, _, _ = api
    r = client.get(_url("nope", path="echo"))
    assert r.status_code == 404
    assert r.json()["error"]["plugin"] == "nope"
    pass
    assert client.get(_url("nope")).status_code == 404


def test_handler_gets_request_shape(api):
    client, proj, _ = api
    r = client.get(_url("demo", "proj", path="echo", x="1"))
    assert r.status_code == 200
    assert r.json()["query"]["x"] == "1"


def test_handler_receives_json_body(api):
    client, proj, _ = api
    r = client.post(_url("demo", "proj", path="echo"), json={"a": 1})
    assert r.json()["json"] == {"a": 1}


def test_handler_reads_plugin_config(api):
    from app.plugins import config as pc
    from app.plugins import package as pkgmod
    client, proj, pkg = api
    specs = pkgmod.load_package(pkg).config
    pc.save("demo", str(proj), specs, {"api_base": "http://real"})
    assert (pkg / "config.json").is_file()
    r = client.get(_url("demo", "proj", path="cfg"))
    assert r.json() == {"api_base": "http://real"}


def test_handler_status_tuple(api):
    client, proj, _ = api
    r = client.get(_url("demo", "proj", path="status"))
    assert r.status_code == 418 and r.json() == {"teapot": True}


def test_handler_error_is_500_and_isolated(api):
    client, proj, _ = api
    r = client.get(_url("demo", "proj", path="boom"))
    assert r.status_code == 500 and "插件自己炸了" in r.json()["error"]["detail"]
    assert client.get("/api/plugins/installed").status_code == 200


def test_handler_streaming(api):
    client, proj, _ = api
    r = client.get(_url("demo", "proj", path="stream"))
    assert r.status_code == 200
    assert "data: one" in r.text and "data: two" in r.text




def test_specific_routes_not_stolen_by_dispatcher(api):
    client, _, _ = api
    r = client.post("/api/plugins/install", json={"source": "/nonexistent"})
    assert r.status_code == 400


pass

def test_static_files_not_registered(api, container):
    _, proj, _ = api
    rows = container.installs.files_of("demo", str(proj))
    assert [r["kind"] for r in rows] == ["api"]
    assert all(r["rel_path"].endswith(".py") for r in rows)


def test_entry_served_with_template_and_context(api):
    client, proj, _ = api
    r = client.get(_url("demo", "proj"))
    assert r.status_code == 200
    assert "game" not in r.text
    assert "<script>window.plugin=" in r.text
    assert "/api/plugin?id=demo" in r.text
    pass
    assert "\"project\": \"proj\"" in r.text or "\"project\": \"" in r.text
    assert str(proj) not in r.text
    assert "{{base}}" not in r.text and "{{id}}" not in r.text

    assert r.headers["cache-control"] == "no-store"


def test_static_relative_path_and_render(api):
    client, proj, _ = api
    html = client.get(_url("demo", "proj", static="page.html"))
    assert html.status_code == 200 and "page demo" in html.text
    assert "{{id}}" not in html.text
    js = client.get(_url("demo", "proj", static="res/app.js"))
    assert js.status_code == 200 and "window.plugin" in js.text
    binary = client.get(_url("demo", "proj", static="res/pic.bin"))
    assert binary.status_code == 200 and binary.content == b"\x00\x01\x02"


def test_uninstall_makes_static_unreachable(api, container):
    from app.plugins.install import uninstall

    client, proj, pkg = api
    uninstall("demo", str(proj), store=container.installs)
    assert (pkg / "index.html").is_file()
    assert client.get(_url("demo", "proj")).status_code == 404


pass

def test_three_entries_share_one_dataset(api, container, monkeypatch):
    from app.plugins.plugin_sdk import CODE_PREAMBLE, PluginHost
    from app.tools.builtin.data_tool import plugin_data
    from app.tools.registry import ToolContext

    client, proj, _ = api
    pass
    r = client.post(_url("demo", "proj", path="save"), json={"progress": 3})
    assert r.json() == {"saved": True}
    pass
    ctx = ToolContext(str(proj / ".agent" / "plugins" / "demo"))
    assert '"value": 3' in plugin_data(ctx, action="get", key="progress")
    assert "progress" in plugin_data(ctx, action="keys")
    pass
    pass
    pass
    pkg_dir = proj / ".agent" / "plugins" / "demo"
    monkeypatch.chdir(pkg_dir)
    monkeypatch.setenv("HARNESS_PLUGIN_ID", "demo")
    ns = {"_WORKSPACE": str(proj)}
    exec(CODE_PREAMBLE, ns)
    assert ns["plugin"].data.get("progress") == 3
    pass
    assert (PluginHost.for_plugin("demo", str(proj)).data.path
            == ns["plugin"].data.path)
    monkeypatch.delenv("HARNESS_PLUGIN_ID")
    pass
    ns2 = {"_WORKSPACE": str(proj)}
    exec(CODE_PREAMBLE, ns2)
    assert ns2["plugin"].namespace.startswith("project-")


def test_handler_reads_data_written_by_tool(api):
    from app.tools.builtin.data_tool import plugin_data
    from app.tools.registry import ToolContext

    client, proj, _ = api
    ctx = ToolContext(str(proj / ".agent" / "plugins" / "demo"))
    plugin_data(ctx, action="set", key="progress", value=42)
    r = client.get(_url("demo", "proj", path="data"))
    assert r.json() == {"value": 42}


def test_namespaces_are_isolated(api, container, tmp_dirs):
    from app.plugins.plugin_sdk import PluginHost
    from app.plugins.install import install
    from .helpers import mk_project

    _, proj, _ = api
    PluginHost.for_plugin("demo", str(proj)).data.set("k", "plugin")
    PluginHost.for_cwd(proj).data.set("k", "project")
    assert PluginHost.for_plugin("demo", str(proj)).data.get("k") == "plugin"
    assert PluginHost.for_cwd(proj).data.get("k") == "project"
    pass
    b = mk_project(tmp_dirs, "b")
    install(api_package(b), str(b), store=container.installs)
    assert PluginHost.for_plugin("demo", str(b)).data.get("k") is None


def test_route_query_keys_not_leaked_to_handler(api):
    client, proj, _ = api
    r = client.get(_url("demo", "proj", path="echo", x="1"))
    q = r.json()["query"]
    assert q == {"x": "1"}
    assert not ({"id", "project", "path", "static"} & set(q))


def test_host_call_tool_loads_project_tools_before_first_chat(container, tmp_dirs):
    from fastapi.testclient import TestClient
    import app.main as main_mod
    from app.api.deps import set_container
    from app.plugins.api_dispatch import reset_cache
    from app.factory import _install_plugin_api, register_builtin_plugins
    from app.plugins.install import install

    pass
    register_builtin_plugins(container)
    proj = mk_project(tmp_dirs)
    pkg = proj / ".agent" / "plugins" / "probe"
    (pkg / "tools").mkdir(parents=True)
    (pkg / "api").mkdir()
    import yaml
    (pkg / "plugin.yaml").write_text(yaml.safe_dump({
        "id": "probe", "name": "probe", "version": "1.0.0",
        "kinds": ["tool", "api"], "mode": "release",
        "tools": [{"name": "t", "scope": "system"}]}), "utf-8")
    (pkg / "tools" / "t.py").write_text(
        "def register(reg):\n"
        "    async def probe_tool(ctx, x: str = '') -> str:\n"
        "        return 'v:' + x\n"
        "    reg.tool('probe_tool', 'demo', {}, probe_tool, [])\n",
        encoding="utf-8")
    (pkg / "api" / "router.py").write_text(
        "async def handle(req, host):\n"
        "    return {'result': await host.call_tool('probe_tool', {'x': 'ok'})}\n",
        encoding="utf-8")

    _install_plugin_api(container)
    reset_cache()
    install(pkg, str(proj), store=container.installs, gateway=None)
    pass
    assert "probe_tool" not in container.registry.tools

    set_container(main_mod.app, container)
    client = TestClient(main_mod.app)
    r = client.get(f"/api/plugin?id=probe&project={proj.name}&path=/go")
    assert r.status_code == 200, r.text
    assert r.json()["result"] == "v:ok"


pass
pass
pass
pass
pass
pass

import asyncio as _asyncio
import threading as _threading



@pytest.fixture()
def slow_api(container, tmp_dirs):
    from app.plugins.install import install
    from app.plugins.api_dispatch import reset_cache
    from app.factory import _install_plugin_api

    proj = mk_project(tmp_dirs, "slow")
    pkg = mk_package(proj, pid="slow", kinds=("api",), files={
        "api/router.py": (
            "import threading, time\n"
            "def handle(req, host):\n"
            "    time.sleep(0.3)\n"
            "    return {'tid': threading.get_ident()}\n"),
    })
    _install_plugin_api(container)
    reset_cache()
    install(pkg, str(proj), store=container.installs)
    return container, proj


async def test_sync_handler_runs_off_event_loop_thread(slow_api):
    container, proj = slow_api
    entry = container.plugin_api.lookup("slow", proj.name)
    assert entry is not None
    status, payload, _ = await container.plugin_api.invoke(
        "slow", proj.name, {"method": "GET", "path": "/go"}, container)
    assert status == 200
    assert payload["tid"] != _threading.get_ident()


async def test_slow_handler_does_not_stall_the_loop(slow_api):
    container, proj = slow_api
    ticks = 0

    async def ticker():
        nonlocal ticks
        while True:
            await _asyncio.sleep(0.01)
            ticks += 1

    task = _asyncio.create_task(ticker())
    try:
        await container.plugin_api.invoke(
            "slow", proj.name, {"method": "GET", "path": "/go"}, container)
    finally:
        task.cancel()
    pass
    assert ticks >= 15, f"事件循环被阻塞了：只推进了 {ticks} 次"


async def test_coroutine_handler_still_awaited_in_loop(slow_api, monkeypatch):
    container, proj = slow_api
    seen = {}

    async def handler(req, host):
        seen["tid"] = _threading.get_ident()
        return {"ok": True}

    monkeypatch.setattr("app.plugins.api_dispatch._load_handler",
                        lambda e, pid: handler)
    status, payload, _ = await container.plugin_api.invoke(
        "slow", proj.name, {"method": "GET", "path": "/go"}, container)
    assert status == 200 and payload == {"ok": True}
    assert seen["tid"] == _threading.get_ident()


async def test_sync_handler_returning_awaitable_is_awaited(slow_api, monkeypatch):
    container, proj = slow_api

    def handler(req, host):
        async def inner():
            return {"late": True}
        return inner()

    monkeypatch.setattr("app.plugins.api_dispatch._load_handler",
                        lambda e, pid: handler)
    status, payload, _ = await container.plugin_api.invoke(
        "slow", proj.name, {"method": "GET", "path": "/go"}, container)
    assert status == 200 and payload == {"late": True}
