from __future__ import annotations

import pytest
import yaml

from app.plugins import bot as botmod
from app.plugins import install as inst
from app.plugins import package as pkgmod


def _mk(tmp, *, bot=None, kinds=("bot",), extra=None):
    proj = tmp / "proj"
    (proj / ".agent").mkdir(parents=True, exist_ok=True)
    pkg = proj / ".agent" / "plugins" / "qa"
    pkg.mkdir(parents=True, exist_ok=True)
    data = {"id": "qa", "name": "问答", "version": "1",
            "kinds": list(kinds), "mode": "release"}
    if bot is not None:
        data["bot"] = bot
    data.update(extra or {})
    (pkg / "plugin.yaml").write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), "utf-8")
    return proj, pkg


SPEC = {
    "title": "制度问答",
    "greeting": "可以问我公司制度",
    "prompt": "请只回答制度范围内的问题",
    "workflow": "qa",
    "inputs": {"topic": {"label": "主题", "type": "select",
                         "options": ["请假", "报销"]},
               "question": {"label": "问题", "type": "text", "required": True}},
}


def test_bot_section_parsed_into_inputs(tmp_dirs):
    _, pkg = _mk(tmp_dirs, bot=SPEC)
    b = pkgmod.load_package(pkg).bot
    assert b["title"] == "制度问答" and b["workflow"] == "qa"
    assert [f["key"] for f in b["inputs"]] == ["topic", "question"]


def test_bot_kind_without_section_is_named_error(tmp_dirs):
    _, pkg = _mk(tmp_dirs, bot=None)
    with pytest.raises(ValueError, match="bot 段"):
        pkgmod.load_package(pkg)


def test_non_bot_plugin_without_section_is_fine(tmp_dirs):
    _, pkg = _mk(tmp_dirs, bot=None, kinds=("workflow",))
    assert pkgmod.load_package(pkg).bot == {}


def test_compose_puts_prompt_first_and_labels_values(tmp_dirs):
    proj, pkg = _mk(tmp_dirs, bot=SPEC)
    store = inst.InstallStore(tmp_dirs / "agent.db")
    inst.install(pkg, str(proj), store=store)
    out = botmod.compose_question(store, "qa", str(proj),
                                  {"topic": "请假", "question": "年假能跨年吗"})
    assert out["text"].startswith("请只回答制度范围内的问题")
    assert "主题：请假" in out["text"] and "问题：年假能跨年吗" in out["text"]
    assert out["workflow"] == "qa"


def test_compose_names_missing_required_fields(tmp_dirs):
    proj, pkg = _mk(tmp_dirs, bot=SPEC)
    store = inst.InstallStore(tmp_dirs / "agent.db")
    inst.install(pkg, str(proj), store=store)
    with pytest.raises(ValueError, match="请先填写：问题"):
        botmod.compose_question(store, "qa", str(proj), {"topic": "请假"})


def test_compose_drops_undeclared_keys(tmp_dirs):
    proj, pkg = _mk(tmp_dirs, bot=SPEC)
    store = inst.InstallStore(tmp_dirs / "agent.db")
    inst.install(pkg, str(proj), store=store)
    out = botmod.compose_question(store, "qa", str(proj),
                                  {"question": "Q", "evil": "注入"})
    assert "注入" not in out["text"]


def test_compose_without_bot_section_refuses(tmp_dirs):
    proj, pkg = _mk(tmp_dirs, bot=None, kinds=("workflow",))
    store = inst.InstallStore(tmp_dirs / "agent.db")
    inst.install(pkg, str(proj), store=store)
    with pytest.raises(ValueError, match="没有声明 bot"):
        botmod.compose_question(store, "qa", str(proj), {"a": 1})


def test_compose_unregistered_named_error(tmp_dirs):
    store = inst.InstallStore(tmp_dirs / "agent.db")
    with pytest.raises(LookupError, match="未登记"):
        botmod.compose_question(store, "ghost", "", {})


pass

def test_system_prompt_file_defaults_to_declared_name(tmp_dirs):
    from app.plugins.bot_manifest import DEFAULT_SYSTEM_PROMPT_FILE
    _, pkg = _mk(tmp_dirs, bot=SPEC)
    assert pkgmod.load_package(pkg).bot["system_prompt_file"] == \
        DEFAULT_SYSTEM_PROMPT_FILE


def test_system_prompt_file_rejects_escape(tmp_dirs):
    for bad in ("/etc/passwd", "../outside.json"):
        proj, _pkg = _mk(tmp_dirs, bot={**SPEC, "system_prompt_file": bad})
        pkg2 = proj / ".agent" / "plugins" / "qa"
        with pytest.raises(ValueError, match="包内相对路径"):
            pkgmod.load_package(pkg2)
