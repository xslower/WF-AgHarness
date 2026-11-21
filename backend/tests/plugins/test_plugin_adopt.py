from __future__ import annotations

import json

import pytest
import yaml

from app.plugins import adopt, package as pkgmod
from app.plugins.install import InstallStore
from .helpers import TOOL_SRC, mk_package, mk_project, tool_package


@pytest.fixture()
def store(tmp_dirs):
    return InstallStore(tmp_dirs / "agent.db")


@pytest.fixture()
def proj(tmp_dirs):
    return mk_project(tmp_dirs)


pass

def test_scan_finds_pending_plugin_skill_and_tool(proj, store):
    mk_package(proj, kinds=("workflow",), files={
        "workflows/a.json": '{"name":"a","nodes":[]}'})
    skill = proj / ".agent" / "skills" / "myskill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# myskill\n", "utf-8")
    tools = proj / ".agent" / "tools"
    tools.mkdir(parents=True)
    (tools / "mytool.py").write_text(TOOL_SRC, "utf-8")
    got = adopt.scan_local(str(proj), store)
    pass
    pass
    assert got["plugins"] == []
    assert [s["name"] for s in got["skills"]] == ["myskill"]
    assert [t["name"] for t in got["tools"]] == ["mytool"]
    assert len(got["dev"]) == 1 and got["dev"][0]["id"] == "demo"
    assert got["dev"][0]["registered"] is False


def test_scan_skips_registered(proj, store):
    pkg = mk_package(proj)
    adopt.adopt_plugin(str(proj), "demo", installs=store)
    got = adopt.scan_local(str(proj), store)
    assert got["plugins"] == []
    assert got["dev"][0]["registered"] is True
    assert (pkg / "plugin.yaml").is_file()


def test_scan_not_a_project_is_empty(tmp_dirs, store):
    got = adopt.scan_local(str(tmp_dirs / "nope"), store)
    assert got == {"plugins": [], "skills": [], "tools": [], "dev": []}


def test_scan_one_level_of_grouping(proj, store):
    for name in ("甲", "乙"):
        d = proj / ".agent" / "skills" / "分组" / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("# x\n", "utf-8")
    got = adopt.scan_local(str(proj), store)
    assert [s["name"] for s in got["skills"]] == ["分组/乙", "分组/甲"]


def test_registered_skill_dirs_resolve_real_path(proj, store):
    d = proj / ".agent" / "skills" / "分组" / "甲"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("# x\n", "utf-8")
    adopt.adopt_skill(str(proj), "分组/甲", installs=store)
    assert adopt.registered_skill_dirs(store, str(proj)) == [d.resolve()]


pass

def test_adopt_skill_registers_without_copying(proj, store):
    d = proj / ".agent" / "skills" / "myskill"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("# x\n", "utf-8")
    before = sorted(str(f) for f in d.rglob("*"))
    r = adopt.adopt_skill(str(proj), "myskill", installs=store)
    assert r["kind"] == "skill_bundle"
    assert sorted(str(f) for f in d.rglob("*")) == before
    assert store.files_by_kind("skill_bundle", str(proj))


def test_adopt_skill_missing_raises(proj, store):
    with pytest.raises(ValueError):
        adopt.adopt_skill(str(proj), "nope", installs=store)


def test_adopt_tool_registers_without_copying(proj, store):
    tools = proj / ".agent" / "tools"
    tools.mkdir(parents=True)
    p = tools / "mytool.py"
    p.write_text(TOOL_SRC, "utf-8")
    r = adopt.adopt_tool(str(proj), "mytool", installs=store)
    assert r["kind"] == "tool"
    assert p.is_file()
    rows = store.files_by_kind("tool", str(proj))
    assert rows[0]["rel_path"] == ".agent/tools/mytool.py"


def test_adopt_tool_without_register_is_refused_but_dev_visible(proj, store):
    tools = proj / ".agent" / "tools"
    tools.mkdir(parents=True)
    (tools / "bad.py").write_text("x = 1\n", "utf-8")
    with pytest.raises(ValueError, match="register"):
        adopt.adopt_tool(str(proj), "bad", installs=store)
    pass
    assert store.files_by_kind("tool", str(proj)) == []


def test_adopt_plugin_registers_in_place(proj, store):
    pkg = mk_package(proj, kinds=("tool",), files={"tools/my_tool.py": TOOL_SRC})
    def snapshot():
        return sorted(str(f.relative_to(pkg)) for f in pkg.rglob("*")
                      if f.is_file() and f.suffix != ".pyc")
    before = snapshot()
    r = adopt.adopt_plugin(str(proj), "demo", installs=store)
    assert r["id"] == "demo"
    assert snapshot() == before
    assert not (proj / ".agent" / "tools").exists()


def test_adopt_plugin_missing_yaml_raises(proj, store):
    d = proj / ".agent" / "plugins" / "x"
    d.mkdir(parents=True)
    with pytest.raises(ValueError, match="plugin.yaml"):
        adopt.adopt_plugin(str(proj), "x", installs=store)


def test_diagnose_reports_bad_tool(proj):
    pkg = tool_package(proj, src="x = 1\n")
    errors = adopt.diagnose(str(proj), pkg)
    assert any("register" in e for e in errors)
    got = adopt.scan_local(str(proj), InstallStore())["dev"]
    assert got[0]["errors"] and got[0]["registered"] is False


pass

DIR_TOOL_YAML = """\
name: 目录工具
version: 2.1.0
desc: 一个目录里放多个文件
entry: main.py
scope: local
tools:
  - name: dir_alpha
  - name: dir_beta
    desc: 来自 tool.yaml 的描述
cascade:
  mode: system_first
  target: web
"""

DIR_MAIN = """\
from helper import answer

def register(reg):
    reg.tool("dir_alpha", "演示工具", {"x": {"type": "string"}}, run)
    reg.tool("dir_beta", "", {"x": {"type": "string"}}, run)

def run(x: str = "", ctx=None):
    return answer(x)
"""


def _mk_dir_tool(proj, name="dirt", yaml_text=DIR_TOOL_YAML, main=DIR_MAIN,
                 helper="def answer(x):\n    return 'dir:' + x\n"):
    d = proj / ".agent" / "tools" / name
    d.mkdir(parents=True)
    (d / "tool.yaml").write_text(yaml_text, "utf-8")
    (d / "main.py").write_text(main, "utf-8")
    (d / "helper.py").write_text(helper, "utf-8")
    (d / "notes.txt").write_text("不是工具", "utf-8")
    return d


def test_scan_finds_dir_tool_without_listing_siblings(proj, store):
    d = _mk_dir_tool(proj)
    got = adopt.scan_local(str(proj), store)["tools"]
    assert len(got) == 1
    assert got[0]["name"] == "dirt" and got[0]["unit"] == "dir"
    assert got[0]["display"] == "目录工具"
    assert got[0]["path"] == str(d)
    assert got[0]["desc"] == "一个目录里放多个文件"


def test_scan_reports_bad_tool_yaml_without_breaking_page(proj, store):
    _mk_dir_tool(proj, name="bad", yaml_text="name: x\n")
    got = adopt.scan_local(str(proj), store)["tools"]
    assert len(got) == 1 and "entry" in got[0]["error"]


def test_adopt_dir_tool_registers_only_entry(proj, store):
    d = _mk_dir_tool(proj)
    r = adopt.adopt_tool(str(proj), "dirt", installs=store)
    assert r["kind"] == "tool"
    rows = store.files_by_kind("tool", str(proj))
    assert len(rows) == 1
    assert rows[0]["rel_path"] == ".agent/tools/dirt/main.py"
    extra = json.loads(rows[0]["extra"])
    assert extra["unit"] == "dir" and extra["scope"] == "local"
    pass
    pass
    assert set(extra) == {"unit", "scope", "cascade", "descs", "schemas"}
    assert extra["cascade"] == {"mode": "system_first", "target": "web"}
    assert extra["descs"] == {"dir_beta": "来自 tool.yaml 的描述"}
    pass
    assert (d / "helper.py").is_file() and (d / "notes.txt").is_file()
    pass
    assert adopt.scan_local(str(proj), store)["tools"] == []


def test_dir_tool_desc_falls_back_to_docstring_like_single_file(proj, store):
    _mk_dir_tool(proj, name="nod", yaml_text="entry: main.py\n")
    adopt.adopt_tool(str(proj), "nod", installs=store)
    extra = json.loads(store.files_by_kind("tool", str(proj))[0]["extra"])
    schemas = extra["schemas"]
    pass
    assert schemas["dir_alpha"]["desc"] == "演示工具"
    assert schemas["dir_beta"]["desc"] == "dir_beta"


def test_dir_tool_with_yaml_desc_fills_missing_description(proj, store):
    _mk_dir_tool(proj)
    adopt.adopt_tool(str(proj), "dirt", installs=store)
    extra = json.loads(store.files_by_kind("tool", str(proj))[0]["extra"])
    assert extra["schemas"]["dir_beta"]["desc"] == "来自 tool.yaml 的描述"


def test_dir_tool_rejects_global_for_independent_tool(proj, store):
    _mk_dir_tool(proj, name="glb", yaml_text="entry: main.py\nscope: global\n")
    with pytest.raises(ValueError, match="独立工具只能是 local"):
        adopt.adopt_tool(str(proj), "glb", installs=store)
    assert store.files_by_kind("tool", str(proj)) == []


@pytest.mark.parametrize("bad, msg", [
    ("entry: ../escape.py\n", "entry"),
    ("entry: main.txt\n", ".py"),
    ("name: x\n", "entry"),
    ("entry: main.py\nscope: everywhere\n", "scope"),
    ("entry: main.py\ncascade: {mode: nope}\n", "cascade.mode"),
    ("entry: main.py\ncascade: {mode: system_first}\n", "target"),
    ("entry: main.py\ntools: [{desc: 没名字}]\n", "name"),
])
def test_bad_tool_yaml_is_refused(proj, store, bad, msg):
    _mk_dir_tool(proj, name="bad", yaml_text=bad)
    with pytest.raises(ValueError, match=msg):
        adopt.adopt_tool(str(proj), "bad", installs=store)
    assert store.files_by_kind("tool", str(proj)) == []


def test_dir_tool_entry_escape_is_blocked(proj, store):
    d = _mk_dir_tool(proj, name="esc")
    (proj / "outside.py").write_text(DIR_MAIN, "utf-8")
    (d / "tool.yaml").write_text("entry: ../outside.py\n", "utf-8")
    with pytest.raises(ValueError, match="entry"):
        adopt.adopt_tool(str(proj), "esc", installs=store)


def test_single_file_tool_still_works(proj, store):
    tools = proj / ".agent" / "tools"
    tools.mkdir(parents=True)
    (tools / "legacy.py").write_text(TOOL_SRC, "utf-8")
    r = adopt.adopt_tool(str(proj), "legacy", installs=store)
    assert r["kind"] == "tool"
    rows = store.files_by_kind("tool", str(proj))
    assert rows[0]["rel_path"] == ".agent/tools/legacy.py"
    assert "unit" not in json.loads(rows[0]["extra"])


pass


@pytest.mark.parametrize("raw, want", [
    ("local", "local"), ("project", "local"), ("LOCAL", "local"),
    ("Project", "local"),
])
def test_scope_alias_project_is_local(proj, store, raw, want):
    _mk_dir_tool(proj, name="alias", yaml_text=f"entry: main.py\nscope: {raw}\n")
    adopt.adopt_tool(str(proj), "alias", installs=store)
    extra = json.loads(store.files_by_kind("tool", str(proj))[0]["extra"])
    assert extra["scope"] == want


def test_scope_alias_system_means_local(proj, store):
    _mk_dir_tool(proj, name="alias", yaml_text="entry: main.py\nscope: System\n")
    adopt.adopt_tool(str(proj), "alias", installs=store)
    extra = json.loads(store.files_by_kind("tool", str(proj))[0]["extra"])
    assert extra["scope"] == "local"


def test_scan_dir_tool_with_project_scope_has_no_error(proj, store):
    _mk_dir_tool(proj, name="alias", yaml_text="entry: main.py\nscope: project\n")
    got = adopt.scan_local(str(proj), store)["tools"]
    assert len(got) == 1 and not got[0].get("error")
    assert got[0]["scope"] == "local"
    r = adopt.adopt_tool(str(proj), "alias", installs=store)
    assert r["kind"] == "tool"
    rows = store.files_by_kind("tool", str(proj))
    assert rows[0]["rel_path"] == ".agent/tools/alias/main.py"
    assert json.loads(rows[0]["extra"])["scope"] == "local"


def test_bad_scope_error_lists_all_valid_values(proj, store):
    _mk_dir_tool(proj, name="bad", yaml_text="entry: main.py\nscope: everywhere\n")
    with pytest.raises(ValueError) as ei:
        adopt.adopt_tool(str(proj), "bad", installs=store)
    msg = str(ei.value)
    for word in ("local", "project", "global", "system"):
        assert word in msg



pass

@pytest.mark.parametrize("raw, want", [
    ("project", "system"), ("local", "system"),
    ("Project", "system"), ("LOCAL", "system"),
    ("internal", "internal"), ("global", "global"),
])
def test_plugin_yaml_scope_accepts_tool_yaml_words(proj, store, raw, want):
    pkg = mk_package(proj, kinds=("tool",), files={"tools/my_tool.py": TOOL_SRC},
                     tool_scope=raw)
    assert pkgmod.load_package(pkg).tools[0]["scope"] == want
    pkg = mk_package(proj, kinds=("tool",), files={"tools/my_tool.py": TOOL_SRC},
                     tool_scope=raw)
    assert pkgmod.load_package(pkg).tools[0]["scope"] == want
    if want == "global":
        return
    adopt.adopt_plugin(str(proj), "demo", installs=store)

def test_plugin_yaml_scope_still_rejects_unknown(proj):
    pkg = mk_package(proj, kinds=("tool",), files={"tools/my_tool.py": TOOL_SRC},
                     tool_scope="everywhere")
    with pytest.raises(ValueError) as ei:
        pkgmod.load_package(pkg)
    msg = str(ei.value)
    for word in ("internal", "system", "global", "project"):
        assert word in msg
