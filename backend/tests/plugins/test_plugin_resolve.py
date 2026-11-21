from __future__ import annotations

import pytest

from .helpers import api_package, mk_project


@pytest.fixture()
def api(container, tmp_dirs):
    from app.plugins.install import install
    from app.plugins.api_dispatch import reset_cache
    from app.factory import _install_plugin_api

    from .test_plugin_api import _client

    proj = mk_project(tmp_dirs)
    pkg = api_package(proj, cfg={"api_base": "http://x"})
    _install_plugin_api(container)
    reset_cache()
    install(pkg, str(proj), store=container.installs)
    return _client(container), proj, pkg


@pytest.fixture()
def two_installs(container, tmp_dirs):
    from app.plugins.install import install
    from app.factory import _install_plugin_api

    _install_plugin_api(container)
    a, b = mk_project(tmp_dirs, "a"), mk_project(tmp_dirs, "b")
    install(api_package(a, cfg={"api_base": "A"}), str(a),
            store=container.installs)
    install(api_package(b, cfg={"api_base": "B"}), str(b),
            store=container.installs)
    return container.installs, a, b


def test_unique_id_needs_no_project_name(api, container):
    from app.plugins import resolve as resolver

    _, proj, _ = api
    rec = resolver.resolve(container.installs, "demo")
    assert rec["id"] == "demo"
    assert rec["project"].endswith("/proj")


def test_ambiguous_id_requires_project_name(two_installs):
    from app.plugins import resolve as resolver

    installs, a, b = two_installs
    with pytest.raises(resolver.PluginScopeError) as ei:
        resolver.resolve(installs, "demo")
    assert ei.value.status == 409
    assert "a" in ei.value.detail and "b" in ei.value.detail
    assert str(a) not in ei.value.detail


def test_project_name_picks_the_right_row(two_installs):
    from app.plugins import resolve as resolver

    installs, a, b = two_installs
    ra = resolver.resolve(installs, "demo", "a")
    rb = resolver.resolve(installs, "demo", "b")
    assert ra["project"] == str(a) and rb["project"] == str(b)


def test_path_is_rejected(two_installs):
    from app.plugins import resolve as resolver

    installs, a, _ = two_installs
    with pytest.raises(resolver.PluginScopeError) as ei:
        resolver.resolve(installs, "demo", str(a))
    assert ei.value.status == 400
    assert "名称" in ei.value.detail


def test_unknown_project_name_lists_installed(two_installs):
    from app.plugins import resolve as resolver

    installs, _, _ = two_installs
    with pytest.raises(resolver.PluginScopeError) as ei:
        resolver.resolve(installs, "demo", "nope")
    assert ei.value.status == 404
    assert "已装" in ei.value.detail


def test_unknown_plugin_is_404(container):
    from app.plugins import resolve as resolver

    with pytest.raises(resolver.PluginScopeError) as ei:
        resolver.resolve(container.installs, "no-such-plugin")
    assert ei.value.status == 404


def test_http_detail_endpoint_only_needs_id(api, container):
    from .test_plugin_api import _client

    client, proj, pkg = api
    r = client.get("/api/plugins/demo/detail")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["id"] == "demo"
    assert str(pkg) not in r.text
    assert data["project"] == proj.name


def test_project_arg_accepts_name_and_path(api, container):
    from app.plugins import resolve as resolver

    _client, proj, _pkg = api
    assert resolver.project_arg(proj.name, container.installs) == str(proj)
    assert resolver.project_arg(str(proj) + "/", container.installs) == str(proj)
    assert resolver.project_arg("", container.installs) == ""
    pass
    assert resolver.project_arg("no-such-project", container.installs) \
        == "no-such-project"


def test_config_and_uninstall_accept_project_name(api, container):
    client, proj, _pkg = api

    r = client.get("/api/plugins/config/demo", params={"project": proj.name})
    assert r.status_code == 200, r.text
    assert r.json()["project"] == str(proj)

    rows = client.get("/api/plugins/installed", params={"project": proj.name}).json()
    assert [x["id"] for x in rows["installed"]] == ["demo"]

    r = client.delete("/api/plugins/installed/demo", params={"project": proj.name})
    assert r.status_code == 200, r.text
    assert container.installs.plugins_by_id("demo") == []
