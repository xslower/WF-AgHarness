from __future__ import annotations

import json

import pytest
import yaml

from app.agent.profile import (AgentProfile, SystemOverride, with_system)
from app.plugins import bot_prompt
from app.plugins import install as inst
from app.plugins.plugin_sdk import PluginHost


def _mk(tmp, *, bot=None, prompt_file=None):
    proj = tmp / "proj"
    (proj / ".agent").mkdir(parents=True, exist_ok=True)
    pkg = proj / ".agent" / "plugins" / "qa"
    pkg.mkdir(parents=True, exist_ok=True)
    data = {"id": "qa", "name": "问答", "version": "1",
            "kinds": ["bot"], "mode": "release",
            "bot": bot if bot is not None else {"title": "制度问答"}}
    (pkg / "plugin.yaml").write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), "utf-8")
    if prompt_file is not None:
        text = (prompt_file if isinstance(prompt_file, str)
                else json.dumps(prompt_file, ensure_ascii=False))
        (pkg / "system_prompt.json").write_text(text, "utf-8")
    store = inst.InstallStore(tmp / "agent.db")
    inst.install(pkg, str(proj), store=store)
    return proj, pkg, store


PROMPTS = {
    "default": {"mode": "append", "text": "只回答制度范围内的问题，引用条款号。"},
    "strict": {"mode": "replace", "text": "你只做条文检索，不回答其它问题。"},
}


pass

PROFILE = AgentProfile(id="default", system_prompt="原始提示词。")


def test_with_system_append_keeps_original():
    got = with_system(PROFILE, SystemOverride(mode="append", text="补充约束"))
    assert got.system_prompt == "原始提示词。\n\n补充约束"
    assert got.id == PROFILE.id and got.allowed_tools == PROFILE.allowed_tools


def test_with_system_replace_drops_original():
    got = with_system(PROFILE, SystemOverride(mode="replace", text="整段接管"))
    assert got.system_prompt == "整段接管"
    assert got.max_rounds == PROFILE.max_rounds


@pytest.mark.parametrize("ov", [None, SystemOverride(mode="append", text="  ")])
def test_with_system_empty_override_is_identity(ov):
    assert with_system(PROFILE, ov) is PROFILE


def test_with_system_unknown_mode_falls_back_to_append():
    got = with_system(PROFILE, SystemOverride(mode="apend", text="X"))
    assert got.system_prompt.endswith("X") and got.system_prompt.startswith("原始提示词")


pass

def test_missing_file_means_not_configured(tmp_dirs):
    proj, _pkg, store = _mk(tmp_dirs)
    assert bot_prompt.profiles(store, "qa", str(proj)) == {}
    assert bot_prompt.current(store, "qa", str(proj)) is None


def test_profiles_read_multiple_named_entries(tmp_dirs):
    proj, _pkg, store = _mk(tmp_dirs, prompt_file=PROMPTS)
    got = bot_prompt.profiles(store, "qa", str(proj))
    assert set(got) == {"default", "strict"}
    assert got["strict"]["mode"] == "replace"


def test_single_profile_shorthand(tmp_dirs):
    proj, _pkg, store = _mk(tmp_dirs, prompt_file={"mode": "append", "text": "独一份"})
    assert bot_prompt.profiles(store, "qa", str(proj)) == {
        "default": {"mode": "append", "text": "独一份"}}


def test_broken_file_means_not_configured(tmp_dirs):
    proj, _pkg, store = _mk(tmp_dirs, prompt_file="{坏 JSON")
    assert bot_prompt.profiles(store, "qa", str(proj)) == {}


def test_current_defaults_to_default_profile(tmp_dirs):
    proj, _pkg, store = _mk(tmp_dirs, prompt_file=PROMPTS)
    got = bot_prompt.current(store, "qa", str(proj))
    assert got == {"name": "default", "mode": "append",
                   "text": PROMPTS["default"]["text"]}


def test_pick_selects_profile_for_later_turns(tmp_dirs):
    proj, _pkg, store = _mk(tmp_dirs, prompt_file=PROMPTS)
    bot_prompt.pick(store, "qa", str(proj), "strict")
    assert bot_prompt.selected(store, "qa", str(proj)) == "strict"
    assert bot_prompt.current(store, "qa", str(proj))["mode"] == "replace"


def test_pick_unknown_name_names_options(tmp_dirs):
    proj, _pkg, store = _mk(tmp_dirs, prompt_file=PROMPTS)
    with pytest.raises(ValueError, match="可选"):
        bot_prompt.pick(store, "qa", str(proj), "不存在")


def test_pick_empty_name_clears_selection(tmp_dirs):
    proj, _pkg, store = _mk(tmp_dirs, prompt_file=PROMPTS)
    bot_prompt.pick(store, "qa", str(proj), "strict")
    bot_prompt.pick(store, "qa", str(proj), "")
    assert bot_prompt.selected(store, "qa", str(proj)) == "default"


def test_selected_profile_without_text_is_unset(tmp_dirs):
    proj, _pkg, store = _mk(tmp_dirs, prompt_file={"default": {"text": "  "}})
    assert bot_prompt.current(store, "qa", str(proj)) is None


pass

def test_host_bot_prompt_selects_and_reads(tmp_dirs):
    proj, _pkg, store = _mk(tmp_dirs, prompt_file=PROMPTS)
    host = PluginHost.for_plugin("qa", str(proj))
    chosen = host.bot_prompt("strict")
    assert chosen["name"] == "strict" and chosen["mode"] == "replace"
    assert bot_prompt.current(store, "qa", str(proj))["text"] == \
        PROMPTS["strict"]["text"]
    assert host.bot_prompt()["name"] == "strict"


def test_host_bot_prompt_without_file_is_empty(tmp_dirs):
    proj, _pkg, _store = _mk(tmp_dirs)
    host = PluginHost.for_plugin("qa", str(proj))
    assert host.bot_prompt()["text"] == ""
