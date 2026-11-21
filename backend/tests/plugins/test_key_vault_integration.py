from __future__ import annotations

import json
import sqlite3

import pytest
import yaml

from app.store import layout, vault


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    monkeypatch.delenv(vault.MASTER_KEY_ENV, raising=False)
    vault._plaintexts.clear()
    yield
    vault._plaintexts.clear()


def _disk_row(pid: str) -> dict:
    con = sqlite3.connect(str(layout.agent_db()))
    try:
        row = con.execute("SELECT data FROM providers WHERE id=?", (pid,)).fetchone()
    finally:
        con.close()
    assert row, f"provider {pid} 未落库"
    return json.loads(row[0])


pass
def test_provider_key_is_encrypted_on_disk(client):
    r = client.post("/api/providers", json={
        "name": "vault-p", "baseUrl": "https://x/v1",
        "apiKey": "sk-disk-secret", "models": []})
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    raw = _disk_row(pid)
    assert raw["apiKey"].startswith(vault.PREFIX)
    assert "sk-disk-secret" not in json.dumps(raw, ensure_ascii=False)
    assert "sk-disk-secret" not in (layout.agent_db().read_bytes()).decode(
        "utf-8", "replace")


def test_provider_key_never_in_http_response(client):
    r = client.post("/api/providers", json={
        "name": "vault-p", "baseUrl": "https://x/v1",
        "apiKey": "sk-http-secret", "models": []})
    pid = r.json()["id"]
    assert r.json()["apiKey"] == vault.MASKED
    assert "sk-http-secret" not in r.text
    conf = client.get("/api/config")
    assert "sk-http-secret" not in conf.text
    assert conf.json()["providers"][0]["apiKey"] == vault.MASKED


def test_provider_key_readable_in_memory_for_adapter(client):
    pid = client.post("/api/providers", json={
        "name": "vault-p", "baseUrl": "https://x/v1",
        "apiKey": "sk-memory-secret", "models": []}).json()["id"]
    from app.config import ConfigStore
    cfg = ConfigStore().config
    p = next(p for p in cfg.providers if p.id == pid)
    assert p.apiKey == "sk-memory-secret"
    from app.provider.adapters.openai_compatible import OpenAICompatibleAdapter
    assert OpenAICompatibleAdapter.headers(p)["Authorization"] == \
        "Bearer sk-memory-secret"


def test_legacy_plaintext_provider_converges_on_load(client):
    from app.provider.store import ProviderStore
    s = ProviderStore()
    s._write("INSERT OR REPLACE INTO providers VALUES (?, ?)",
             ("legacy", s.dump({"id": "legacy", "name": "old",
                                "baseUrl": "https://x/v1",
                                "apiKey": "sk-legacy-plain", "models": []})))
    got = s.list_all()
    assert next(x for x in got if x["id"] == "legacy")["apiKey"] == "sk-legacy-plain"
    assert _disk_row("legacy")["apiKey"].startswith(vault.PREFIX)


def test_masked_value_on_update_keeps_original_key(client):
    pid = client.post("/api/providers", json={
        "name": "vault-p", "baseUrl": "https://x/v1",
        "apiKey": "sk-keep-me", "models": []}).json()["id"]
    r = client.put(f"/api/providers/{pid}", json={
        "name": "renamed", "baseUrl": "https://x/v1",
        "apiKey": vault.MASKED, "models": []})
    assert r.status_code == 200
    from app.config import ConfigStore
    p = next(p for p in ConfigStore().config.providers if p.id == pid)
    assert p.apiKey == "sk-keep-me" and p.name == "renamed"


pass
def _mk_pkg(root, pid, config):
    from app.plugins import package as pkgmod
    d = root / pid
    d.mkdir(parents=True)
    (d / "plugin.yaml").write_text(yaml.safe_dump(
        {"id": pid, "name": pid, "version": "1", "kinds": ["workflow"],
         "mode": "release", "config": config}, allow_unicode=True), "utf-8")
    return d, pkgmod.load_package(d)


def _cfg_row(pid):
    con = sqlite3.connect(str(layout.agent_db()))
    try:
        row = con.execute(
            "SELECT values_json FROM plugin_config WHERE pid=? AND project=?",
            (pid, "")).fetchone()
    finally:
        con.close()
    assert row, f"plugin_config 里没有 {pid}"
    return row[0]


def test_config_key_type_encrypted_on_disk(tmp_dirs):
    from app.plugins import config as pc
    d, view = _mk_pkg(tmp_dirs, "k1", {"my_key": {"type": "key"}})
    pc.save(view.id, "", view.config, {"my_key": "sk-plugin-secret"})
    disk = _cfg_row(view.id)
    assert "sk-plugin-secret" not in disk
    assert json.loads(disk)["my_key"].startswith(vault.PREFIX)
    assert not (d / "config.json").exists()
    assert pc.load(view.id, "", view.config)["my_key"] == "sk-plugin-secret"
    assert pc.masked(view.id, "", view.config)["values"]["my_key"] == vault.MASKED


def test_secret_upgraded_to_encrypted(tmp_dirs):
    from app.plugins import config as pc
    _, view = _mk_pkg(tmp_dirs, "k2", {"token": {"type": "secret"}})
    pc.save(view.id, "", view.config, {"token": "sk-secret-upgraded"})
    assert "sk-secret-upgraded" not in _cfg_row(view.id)
    assert pc.load(view.id, "", view.config)["token"] == "sk-secret-upgraded"


def test_legacy_plaintext_config_stays_unreadable(tmp_dirs):
    from app.plugins import config as pc
    from app.store.plugin_config import PluginConfigStore
    _, view = _mk_pkg(tmp_dirs, "k3", {"token": {"type": "secret"}})
    PluginConfigStore().put(view.id, "", {"token": "sk-old-plain"})
    assert pc.load(view.id, "")["token"] == "sk-old-plain"
    pc.save(view.id, "", view.config, {"token": "sk-old-plain"})
    assert "sk-old-plain" not in _cfg_row(view.id)


def test_config_mask_roundtrip_keeps_value(tmp_dirs):
    from app.plugins import config as pc
    _, view = _mk_pkg(tmp_dirs, "k4", {"key": {"type": "key"},
                                      "token": {"type": "secret"}})
    pc.save(view.id, "", view.config, {"key": "sk-a", "token": "sk-b"})
    pc.save(view.id, "", view.config,
            pc.masked(view.id, "", view.config)["values"])
    got = pc.load(view.id, "", view.config)
    assert got["key"] == "sk-a" and got["token"] == "sk-b"


pass
def _pkg_yaml(root, pid, keys, *, in_project=True):
    base = root / "proj" / ".agent" / "plugins" if in_project else root
    base.mkdir(parents=True, exist_ok=True)
    d = base / pid
    d.mkdir(parents=True, exist_ok=True)
    (d / "plugin.yaml").write_text(yaml.safe_dump(
        {"id": pid, "name": pid, "version": "1", "kinds": ["workflow"],
         "mode": "release", "requested_provider_keys": keys},
        allow_unicode=True), "utf-8")
    (d / "workflows").mkdir(exist_ok=True)
    (d / "workflows" / "a.json").write_text("{}", "utf-8")
    return d


def test_manifest_parses_requested_keys(tmp_dirs):
    from app.plugins import package as pkgmod
    d = _pkg_yaml(tmp_dirs, "k5", ["moss", "siliconflow", "moss"])
    pkg = pkgmod.load_package(d)
    assert pkg.requested_provider_keys == ("moss", "siliconflow")
    from app.plugins.package import load_package_from_text
    again = load_package_from_text((d / "plugin.yaml").read_text("utf-8"), "k5")
    assert again.requested_provider_keys == ("moss", "siliconflow")


def test_install_rejects_missing_or_extra_grants(tmp_dirs):
    from app.plugins import install as inst
    from app.plugins import package as pkgmod
    project = str(tmp_dirs / "proj")
    (tmp_dirs / "proj" / ".agent").mkdir(parents=True)
    d = _pkg_yaml(tmp_dirs, "k6", ["moss", "siliconflow"])
    pkg = pkgmod.load_package(d)
    with pytest.raises(ValueError, match="未获用户许可"):
        inst.register_package(pkg, project, granted_provider_keys=["moss"])
    with pytest.raises(ValueError, match="未在清单声明"):
        inst.register_package(pkg, project,
                              granted_provider_keys=["moss", "siliconflow", "extra"])
    ok = inst.register_package(pkg, project,
                               granted_provider_keys=["moss", "siliconflow"])
    assert ok["id"] == "k6"


def test_undeclared_plugin_installs_without_grants(tmp_dirs):
    from app.plugins import install as inst
    (tmp_dirs / "proj" / ".agent").mkdir(parents=True)
    d = _pkg_yaml(tmp_dirs, "k7", [])
    assert inst.install(d, project=str(tmp_dirs / "proj"))["id"] == "k7"


def test_pregrant_future_provider_name(client, tmp_dirs, container):
    from app.plugins.plugin_sdk import PluginHost
    from app.store.plugin_config import PluginConfigStore
    (tmp_dirs / "proj" / ".agent").mkdir(parents=True)
    d = _pkg_yaml(tmp_dirs, "kfuture", ["future-moss"])
    pass
    assert all(p.name != "future-moss" for p in container.store.config.providers)
    r = client.post("/api/plugins/install", json={
        "source": str(d), "project": str(tmp_dirs / "proj"),
        "grantedProviderKeys": ["future-moss"]})
    assert r.status_code == 200, r.text
    pass
    allowed = PluginConfigStore().grants("kfuture", str(tmp_dirs / "proj"))
    assert allowed == ("future-moss",)
    pass
    client.post("/api/providers", json={
        "name": "future-moss", "baseUrl": "https://x/v1",
        "apiKey": "sk-added-later", "models": []})
    h = PluginHost.for_plugin("kfuture", str(tmp_dirs / "proj"))
    assert h.provider_key("future-moss") == ["sk-added-later"]
    pass
    client.post("/api/providers", json={
        "name": "future-moss-2", "baseUrl": "https://x/v1",
        "apiKey": "sk-added-later-2", "models": []})
    assert h.provider_key("future-moss") == ["sk-added-later",
                                             "sk-added-later-2"]
    with pytest.raises(PermissionError):
        h.provider_key("other")


def test_overview_returns_current_manifest_key_declaration(client, tmp_dirs, container):
    from app.store.kv import RegistryStore
    (tmp_dirs / "proj" / ".agent").mkdir(parents=True)
    proj = str(tmp_dirs / "proj")
    RegistryStore().add(proj)
    d = _pkg_yaml(tmp_dirs, "kov", ["moss"])
    r = client.post("/api/plugins/install", json={
        "source": str(d), "project": proj,
        "grantedProviderKeys": ["moss"]})
    assert r.status_code == 200, r.text
    ov = client.get("/api/projects/overview", params={"path": proj}).json()
    row = next(p for p in ov["plugins"] if p["id"] == "kov")
    assert row["requestedProviderKeys"] == ["moss"]
    pass
    f = d / "plugin.yaml"
    data = yaml.safe_load(f.read_text("utf-8"))
    data["requested_provider_keys"] = ["moss", "siliconflow"]
    f.write_text(yaml.safe_dump(data, allow_unicode=True), "utf-8")
    row2 = next(p for p in client.get(
        "/api/projects/overview", params={"path": proj}).json()["plugins"]
        if p["id"] == "kov")
    assert row2["requestedProviderKeys"] == ["moss", "siliconflow"]


pass
def test_host_provider_key_declared_and_undeclared(tmp_dirs):
    from app.plugins.plugin_sdk import PluginHost
    from app.provider.store import ProviderStore
    from app.store.plugin_config import PluginConfigStore
    ProviderStore().upsert("m", {"id": "m", "name": "moss",
                                 "baseUrl": "https://x/v1",
                                 "apiKey": "sk-moss", "models": []})
    PluginConfigStore().set_grants("x", "", ["moss"])
    h = PluginHost.for_plugin("x", "")
    assert h.provider_key("moss") == ["sk-moss"]
    with pytest.raises(PermissionError, match="未声明或未获许可"):
        h.provider_key("siliconflow")
    PluginConfigStore().set_grants("x", "", ["ghost"])
    pass
    assert PluginHost.for_plugin("x", "").provider_key("ghost") == []


def test_host_config_returns_plaintext(tmp_dirs):
    from app.plugins import config as pc
    from app.plugins.plugin_sdk import PluginHost
    specs = pc.normalize_config({"MOSS_KEY_1": {"type": "key"}})
    pc.save("x", "", specs, {"MOSS_KEY_1": "sk-conf"})
    h = PluginHost.for_plugin("x", "")
    assert h.config("MOSS_KEY_1") == "sk-conf"


def test_http_error_detail_is_redacted(client):
    from app.api import errors
    from fastapi import HTTPException
    vault.remember("sk-in-error")
    exc = errors.bad_request("上游返回 401: Bearer sk-in-error")
    assert isinstance(exc, HTTPException)
    assert "sk-in-error" not in str(exc.detail)
    assert "***" in str(exc.detail)


def test_plugin_api_response_is_redacted(client, container, monkeypatch):
    import asyncio

    from app.plugins import api_dispatch as api_mod
    from app.plugins.api_dispatch import PluginApiRouter
    from app.provider.store import ProviderStore
    from app.store.plugin_config import PluginConfigStore

    ProviderStore().upsert("m", {"id": "m", "name": "moss",
                                 "baseUrl": "https://x/v1",
                                 "apiKey": "sk-moss", "models": []})
    PluginConfigStore().set_grants("k8", "", ["moss"])
    monkeypatch.setattr(api_mod, "_load_handler", lambda e, pid: (
        lambda req, host: {"leak": host.provider_key("moss")}))

    entry = {"project": "", "rel_path": "api/h.py", "module": "h",
             "prefix": "/api/plugins/k8", "handler": "handle", "timeout": 5}
    router = PluginApiRouter(container.installs)
    monkeypatch.setattr(router, "lookup", lambda pid, project="": entry)

    resp = asyncio.run(router.invoke("k8", "",
                                     {"method": "POST", "path": "/do"}, container))
    status, payload, is_stream = resp
    assert status == 200 and is_stream is False
    pass
    assert payload == {"leak": ["***"]}
    assert "sk-moss" not in json.dumps(payload)


pass
def test_provider_key_prefix_match_all_accounts_in_fixed_order(tmp_dirs):
    from app.plugins.plugin_sdk import PluginHost
    from app.provider.store import ProviderStore
    from app.store.plugin_config import PluginConfigStore

    store = ProviderStore()
    pass
    for pid, name, key in [
        ("c", "moss173", "sk-moss173"),
        ("a", "moss-185", "sk-moss185"),
        ("b", "moss-185", "sk-moss185-dup"),
        ("d", "moss-173", "sk-moss173-other"),
        ("e", "mossy", "sk-mossy"),
        ("f", "xmoss", "sk-xmoss"),
    ]:
        store.upsert(pid, {"id": pid, "name": name, "baseUrl": "https://x/v1",
                           "apiKey": key, "models": []})
    PluginConfigStore().set_grants("pref", "", ["moss", "moss-177"])
    h = PluginHost.for_plugin("pref", "")

    pass
    pass
    assert h.provider_key("moss") == ["sk-moss173-other", "sk-moss185",
                                      "sk-moss185-dup", "sk-moss173",
                                      "sk-mossy"]
    pass
    assert h.provider_key("moss-177") == []
    pass
    with pytest.raises(PermissionError):
        h.provider_key("moss-")
    pass
    PluginConfigStore().set_grants("pref", "", ["", "moss"])
    with pytest.raises(PermissionError):
        h.provider_key("")
