import json
import os
import threading
import time
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


pass

def test_ensure_repo_creates_dir_and_init(tmp_path):
    from app.checkpoints import ensure_repo
    ws = tmp_path / "new_ws"
    ensure_repo(str(ws))
    assert (ws / ".git").exists()
    assert (ws / ".gitignore").exists()


def test_ensure_repo_idempotent(tmp_path):
    from app.checkpoints import ensure_repo
    ws = tmp_path / "ws2"
    ensure_repo(str(ws))
    ensure_repo(str(ws))
    assert (ws / ".git").exists()


def test_snapshot_no_changes(tmp_path):
    from app.checkpoints import ensure_repo, snapshot
    ws = tmp_path / "snap_ws"
    ensure_repo(str(ws))
    pass
    (ws / "init.txt").write_text("init")
    snapshot(str(ws), "agent:init")
    sha = snapshot(str(ws), "agent:nochange")
    assert sha is None


def test_snapshot_with_changes(tmp_path):
    from app.checkpoints import ensure_repo, snapshot
    ws = tmp_path / "snap_ws2"
    ensure_repo(str(ws))
    (ws / "file.txt").write_text("hello")
    sha = snapshot(str(ws), "agent:test commit")
    assert sha is not None
    assert len(sha) > 0


def test_snapshot_git_error_returns_none(tmp_path):
    def test_snapshot_git_error_returns_none(tmp_path):
        pass
    from app.checkpoints import ensure_repo, snapshot
    ensure_repo(str(tmp_path))
    (tmp_path / "a.txt").write_text("v1", encoding="utf-8")
    with patch("app.checkpoints.ensure_repo", side_effect=Exception("fail")):
        sha = snapshot(str(tmp_path), "msg")
        assert sha is None

def test_list_checkpoints_no_git(tmp_path):
    from app.checkpoints import list_checkpoints
    ws = tmp_path / "no_git"
    ws.mkdir()
    result = list_checkpoints(str(ws))
    assert result == []


def test_list_checkpoints_with_commits(tmp_path):
    from app.checkpoints import ensure_repo, snapshot, list_checkpoints
    ws = tmp_path / "gc_ws"
    ensure_repo(str(ws))
    (ws / "f1.txt").write_text("a")
    snapshot(str(ws), "agent:commit1")
    (ws / "f2.txt").write_text("b")
    snapshot(str(ws), "agent:commit2")
    cps = list_checkpoints(str(ws))
    assert len(cps) >= 2
    assert "sha" in cps[0]
    assert "message" in cps[0]


def test_restore_checkpoint(tmp_path):
    from app.checkpoints import ensure_repo, snapshot, restore
    ws = tmp_path / "restore_ws"
    ensure_repo(str(ws))
    (ws / "f.txt").write_text("original")
    sha = snapshot(str(ws), "agent:v1")
    (ws / "f.txt").write_text("modified")
    restore(str(ws), sha)
    assert (ws / "f.txt").read_text() == "original"


pass

def _make_usage_tracker(tmp_path):
    from app.store.usage import UsageTracker
    return UsageTracker(tmp_path / "usage.db")


def test_usage_today_tokens_empty_db(tmp_path):
    ut = _make_usage_tracker(tmp_path)
    assert ut.today_tokens("p1/m1") == 0


def test_usage_today_tokens_with_data(tmp_path):
    ut = _make_usage_tracker(tmp_path)
    ut.record("p1/m1", "s1", prompt_tokens=100, completion_tokens=50)
    assert ut.today_tokens("p1/m1") == 150
    assert ut.today_tokens("p2/m2") == 0


def test_usage_today_tokens_reads_persisted_rows(tmp_path):
    f = tmp_path / "usage.db"
    ut = _make_usage_tracker(tmp_path)
    ut.record("p1/m1", "s1", prompt_tokens=100, completion_tokens=50)
    ut.flush()
    from app.store.usage import UsageTracker
    assert UsageTracker(f).today_tokens("p1/m1") == 150


def test_usage_summary_empty_db(tmp_path):
    result = _make_usage_tracker(tmp_path).summary()
    pass
    assert "by_provider" in result
    assert "by_session" not in result
    assert result["by_provider"] == {}
    assert result["today_cost"] == 0.0


def test_usage_record_updates_memory_only(tmp_path):
    ut = _make_usage_tracker(tmp_path)
    ut.record("p1/m1", "s1", prompt_tokens=100, completion_tokens=50)
    assert ut.db.load_all() == []
    assert ut.today_tokens("p1/m1") == 150
    assert ut.flush() == 1
    rec = ut.db.load_all()[0]
    assert rec["spec"] == "p1/m1" and rec["prompt"] == 100
    assert rec["prompt"] == 100


pass

def _make_memory_store(tmp_path):
    from app.project.manager import ProjectManager
    from app.tools.builtin.memory import MemoryStore
    pm = ProjectManager(str(tmp_path))
    return MemoryStore(pm)


def test_memory_load_no_file(tmp_path):
    ms = _make_memory_store(tmp_path)
    assert ms.load("nonexist") == []


def test_memory_load_bad_json(tmp_path):
    from app.project.manager import ProjectManager, MARKER
    proj = tmp_path / "proj"
    (proj / MARKER).mkdir(parents=True)
    (proj / MARKER / "memory.json").write_text("bad json", "utf-8")
    from app.tools.builtin.memory import MemoryStore
    ms = MemoryStore(ProjectManager(str(tmp_path)))
    assert ms.load(str(proj)) == []


def test_memory_add_and_load(tmp_path):
    from app.project.manager import ProjectManager, MARKER
    proj = tmp_path / "proj1"
    (proj / MARKER).mkdir(parents=True)
    from app.tools.builtin.memory import MemoryStore
    ms = MemoryStore(ProjectManager(str(tmp_path)))
    entry = ms.add(str(proj), "important note")
    assert entry["content"] == "important note"
    entries = ms.load(str(proj))
    assert len(entries) == 1
    assert entries[0]["content"] == "important note"


def test_memory_add_dedup(tmp_path):
    from app.project.manager import ProjectManager, MARKER
    proj = tmp_path / "proj2"
    (proj / MARKER).mkdir(parents=True)
    from app.tools.builtin.memory import MemoryStore
    ms = MemoryStore(ProjectManager(str(tmp_path)))
    ms.add(str(proj), "same note")
    ms.add(str(proj), "same note")
    entries = ms.load(str(proj))
    assert len(entries) == 1


def test_memory_add_empty_raises(tmp_path):
    ms = _make_memory_store(tmp_path)
    with pytest.raises(ValueError):
        ms.add(str(tmp_path / "proj"), "")


def test_memory_delete_not_found(tmp_path):
    ms = _make_memory_store(tmp_path)
    assert ms.delete("nonexist", "nonexistent") is False


def test_memory_delete_success(tmp_path):
    from app.project.manager import ProjectManager, MARKER
    proj = tmp_path / "proj3"
    (proj / MARKER).mkdir(parents=True)
    from app.tools.builtin.memory import MemoryStore
    ms = MemoryStore(ProjectManager(str(tmp_path)))
    entry = ms.add(str(proj), "to delete")
    assert ms.delete(str(proj), entry["id"]) is True
    assert len(ms.load(str(proj))) == 0


def test_memory_docs_files_default(tmp_path):
    ms = _make_memory_store(tmp_path)
    assert ms.docs_files(str(tmp_path / "proj_no_cfg")) == ["README.md"]


def test_memory_docs_files_bad_json(tmp_path):
    from app.project.manager import ProjectManager, MARKER
    proj = tmp_path / "proj4"
    (proj / MARKER).mkdir(parents=True)
    (proj / MARKER / "docs.json").write_text("bad json", "utf-8")
    from app.tools.builtin.memory import MemoryStore
    ms = MemoryStore(ProjectManager(str(tmp_path)))
    assert ms.docs_files(str(proj)) == ["README.md"]


def test_memory_docs_files_custom(tmp_path):
    from app.project.manager import ProjectManager, MARKER
    proj = tmp_path / "proj5"
    (proj / MARKER).mkdir(parents=True)
    (proj / MARKER / "docs.json").write_text(json.dumps(["GUIDE.md"]), "utf-8")
    from app.tools.builtin.memory import MemoryStore
    ms = MemoryStore(ProjectManager(str(tmp_path)))
    assert ms.docs_files(str(proj)) == ["GUIDE.md"]


def test_memory_read_docs(tmp_path):
    proj = tmp_path / "proj6"
    proj.mkdir()
    (proj / "README.md").write_text("# Hello", "utf-8")
    ms = _make_memory_store(tmp_path)
    docs = ms.read_docs(str(proj))
    assert "Hello" in docs


def test_memory_context_for_empty_project(tmp_path):
    ms = _make_memory_store(tmp_path)
    assert ms.context_for("") == ""


def test_memory_context_for_with_memory(tmp_path):
    from app.project.manager import ProjectManager, MARKER
    proj = tmp_path / "proj7"
    (proj / MARKER).mkdir(parents=True)
    from app.tools.builtin.memory import MemoryStore
    ms = MemoryStore(ProjectManager(str(tmp_path)))
    ms.add(str(proj), "key info")
    ctx = ms.context_for(str(proj))
    assert "key info" in ctx


@pytest.mark.asyncio
async def test_gate_memory_model_unavailable():
    from app.tools.builtin.memory import gate_memory
    gw = MagicMock()
    gw.call_utility = AsyncMock(side_effect=Exception("no model"))
    keep, reason = await gate_memory(gw, "some content")
    assert keep is True
    assert reason == ""


@pytest.mark.asyncio
async def test_gate_memory_no_json_match():
    from app.tools.builtin.memory import gate_memory
    gw = MagicMock()
    gw.call_utility = AsyncMock(return_value="not json at all")
    keep, reason = await gate_memory(gw, "some content")
    assert keep is True


@pytest.mark.asyncio
async def test_gate_memory_bad_json():
    from app.tools.builtin.memory import gate_memory
    gw = MagicMock()
    gw.call_utility = AsyncMock(return_value="{bad json}")
    keep, reason = await gate_memory(gw, "some content")
    assert keep is True


@pytest.mark.asyncio
async def test_gate_memory_keep_true():
    from app.tools.builtin.memory import gate_memory
    gw = MagicMock()
    gw.call_utility = AsyncMock(return_value='{"keep": true}')
    keep, reason = await gate_memory(gw, "important architecture decision")
    assert keep is True


@pytest.mark.asyncio
async def test_gate_memory_keep_false():
    from app.tools.builtin.memory import gate_memory
    gw = MagicMock()
    gw.call_utility = AsyncMock(return_value='{"keep": false}')
    keep, reason = await gate_memory(gw, "temporary bug status")
    assert keep is False


pass

def test_sessions_crud(tmp_path, monkeypatch):
    from app import config
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    from app.chat.sessions import SessionStore
    store = SessionStore()
    pass
    proj = str(tmp_path / "proj1")
    s = store.create("My Task", proj)
    sid = s["id"]
    assert s["title"] == "My Task"
    assert s["project"] == proj
    got = store.get(sid)
    assert got["title"] == "My Task"
    items = store.list(proj)
    assert any(i["id"] == sid for i in items)
    s = store.get(sid)
    s["messages"] = [{"role": "user", "content": "hello"}]
    store.save(s)
    got = store.get(sid)
    assert len(got["messages"]) == 1
    store.delete(sid)
    assert store.get(sid) is None


def test_sessions_migrate_bad_json(tmp_path, monkeypatch):
    from app import config
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    sd = tmp_path / "sessions"
    sd.mkdir()
    (sd / "bad.json").write_text("not json", "utf-8")
    from app.chat.sessions import SessionStore
    store = SessionStore()
    assert store.list("") == []


pass

def test_classify_model_ocr():
    from app.provider.meta import classify_model
    assert classify_model("some-ocr-model") == "ocr"


def test_classify_model_mt():
    from app.provider.meta import classify_model
    assert classify_model("hunyuan-mt-7b") == "mt"


def test_classify_model_image():
    from app.provider.meta import classify_model
    assert classify_model("stable-diffusion-xl") == "image"


def test_classify_model_embedding():
    from app.provider.meta import classify_model
    assert classify_model("bge-large-zh") == "embedding"


def test_classify_model_asr():
    from app.provider.meta import classify_model
    assert classify_model("whisper-large") == "asr"


def test_classify_model_lm_default():
    from app.provider.meta import classify_model
    assert classify_model("gpt-4o") == "lm"


def test_import_filter_siliconflow():
    from app.provider.presets import import_filter, SILICONFLOW_FREE_IDS
    if SILICONFLOW_FREE_IDS:
        assert import_filter("siliconflow", list(SILICONFLOW_FREE_IDS)[0]) is True
    assert import_filter("siliconflow", "random-model") is False


def test_import_filter_unknown_provider():
    from app.provider.presets import import_filter
    assert import_filter("unknown_provider", "m1") is True


def test_import_filter_openrouter():
    from app.provider.presets import import_filter
    assert import_filter("openrouter", "model:free") is True
    assert import_filter("openrouter", "model-pro") is False


def test_import_filter_qianfan():
    from app.provider.presets import import_filter
    assert import_filter("qianfan", "ernie-speed-128k") is True
    assert import_filter("qianfan", "ernie-4.5-turbo") is False


def test_is_free_model_unknown_provider():
    from app.provider.presets import is_free_model
    assert is_free_model("unknown", "m1") is False


def test_is_free_model_openrouter():
    from app.provider.presets import is_free_model
    assert is_free_model("openrouter", "m:free") is True
    assert is_free_model("openrouter", "m-pro") is False


def test_guess_context_explicit_k():
    from app.provider.meta import guess_context
    assert guess_context("model-32k") == 32768


def test_guess_context_explicit_m():
    from app.provider.meta import guess_context
    assert guess_context("model-1m") == 1_000_000


def test_guess_context_qwen3_8b():
    from app.provider.meta import guess_context
    assert guess_context("Qwen3-8B") == 262_144


def test_guess_context_small_model():
    from app.provider.meta import guess_context
    assert guess_context("model-7b") == 32768


def test_guess_context_vl():
    from app.provider.meta import guess_context
    assert guess_context("model-vl-8b") == 32768


def test_guess_context_embedding():
    from app.provider.meta import guess_context
    assert guess_context("bge-large") == 8192


def test_guess_context_deepseek():
    from app.provider.meta import guess_context
    assert guess_context("deepseek-v3") == 131_072


def test_guess_context_glm_small():
    from app.provider.meta import guess_context
    pass
    assert guess_context("glm-4-9b") == 32768


def test_guess_context_glm_large():
    from app.provider.meta import guess_context
    assert guess_context("glm-5") == 131_072


def test_guess_context_kimi():
    from app.provider.meta import guess_context
    assert guess_context("moonshot-v1") == 131_072


def test_guess_context_ernie():
    from app.provider.meta import guess_context
    assert guess_context("ernie-4.0") == 131_072


def test_guess_context_qwen():
    from app.provider.meta import guess_context
    assert guess_context("qwen-72b") == 131_072


def test_guess_context_hunyuan():
    from app.provider.meta import guess_context
    assert guess_context("hunyuan-turbo") == 131_072


def test_guess_context_128k():
    from app.provider.meta import guess_context
    assert guess_context("model-128k") == 131_072


def test_guess_context_256k():
    from app.provider.meta import guess_context
    assert guess_context("model-256k") == 262_144


def test_guess_context_unknown():
    from app.provider.meta import guess_context
    assert guess_context("totally-unknown-model") == 65_536


def test_describe_model():
    from app.provider.meta import describe_model
    assert isinstance(describe_model("gpt-4o"), str)
    assert isinstance(describe_model("unknown-xyz"), str)


def test_usage_flushes_on_interval_not_on_timer(tmp_path, monkeypatch):
    from app.store import usage as usage_mod
    from app.store.usage import UsageTracker

    monkeypatch.setattr(usage_mod, "USAGE_FLUSH_INTERVAL", 0.05)
    ut = UsageTracker(tmp_path / "usage.db")

    ut.record("p1/m1", "s1", prompt_tokens=100, completion_tokens=50)
    assert ut.db.load_all() == []

    time.sleep(0.08)
    ut.record("p1/m1", "s1", prompt_tokens=10, completion_tokens=5)
    rows = ut.db.load_all()
    assert rows and rows[0]["calls"] == 2


def test_usage_maybe_flush_is_safe_without_dirty():
    from unittest.mock import MagicMock
    from app.store.usage import UsageTracker

    ut = UsageTracker.__new__(UsageTracker)
    ut._lock = threading.Lock()
    ut._dirty = set()
    ut._cells = {}
    ut._calib = {}
    ut._tokens = {}
    ut._day_cost = {}
    ut._last_flush = 0.0
    ut.db = MagicMock()
    assert ut.maybe_flush() == 0
    ut.db.upsert_many.assert_not_called()


pass

def _cfg(**kw):
    from types import SimpleNamespace
    base = {"trashEnabled": True, "trashRetentionDays": 7, "wfChatRetentionDays": 7}
    base.update(kw)
    return SimpleNamespace(**base)


def test_janitors_run_once_and_touch_both_cleanups(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from app import boot

    monkeypatch.setattr(boot, "JANITOR_START_DELAY", 0)
    calls: list[str] = []
    monkeypatch.setattr(boot, "_purge_trash_once", lambda _c: calls.append("trash"))
    monkeypatch.setattr(boot, "_purge_wfchat_once", lambda _c: calls.append("wfchat"))

    asyncio.run(boot.run_janitors_once(SimpleNamespace()))
    assert calls == ["trash", "wfchat"]


def test_purge_trash_once_swallows_errors(monkeypatch):
    from types import SimpleNamespace
    from app import boot
    from app.tools.builtin.fs import trash

    def boom(_tree, _days):
        raise RuntimeError("扫盘挂了")

    monkeypatch.setattr(trash, "purge_tree", boom)
    c = SimpleNamespace(
        store=SimpleNamespace(config=SimpleNamespace(settings=_cfg())),
        projects=SimpleNamespace(tree=lambda: {}))
    boot._purge_trash_once(c)


def test_purge_trash_once_skips_when_disabled(monkeypatch):
    from types import SimpleNamespace
    from app import boot
    from app.tools.builtin.fs import trash

    calls: list[int] = []
    monkeypatch.setattr(trash, "purge_tree", lambda _t, d: calls.append(d))

    def container(**settings):
        return SimpleNamespace(
            store=SimpleNamespace(config=SimpleNamespace(settings=_cfg(**settings))),
            projects=SimpleNamespace(tree=lambda: {}))

    boot._purge_trash_once(container(trashEnabled=False))
    boot._purge_trash_once(container(trashRetentionDays=0))
    assert calls == []
    boot._purge_trash_once(container())
    assert calls == [7]


def test_purge_wfchat_once_swallows_errors():
    from types import SimpleNamespace
    from app import boot

    def boom(_days):
        raise RuntimeError("库挂了")

    c = SimpleNamespace(
        store=SimpleNamespace(config=SimpleNamespace(settings=_cfg())),
        sessions=SimpleNamespace(purge_old=boom))
    boot._purge_wfchat_once(c)
