from __future__ import annotations

import os

import pytest

from app.util import pathx

SHARE = pathx.SHARE_ROOT


pass
@pytest.mark.parametrize("raw", [
    "/mnt/mydisk/share/agent/content/motion",
    SHARE + "/agent/content/motion",
    "/home/swf/agent/content/motion",
    "~/agent/content/motion",
])
def test_all_spellings_collapse(raw):
    assert pathx.project_path(raw) == SHARE + "/agent/content/motion"


def test_alias_of_share_subtree_is_detected():
    assert pathx.project_path("/home/swf/agent/x") == SHARE + "/agent/x"
    assert pathx.project_path("/home/swf/media/x") == SHARE + "/media/x"


def test_share_root_itself():
    assert pathx.project_path(SHARE + "/") == SHARE
    assert pathx.project_path(SHARE) == SHARE


def test_foreign_paths_untouched():
    for raw in ["/home/swf/usb1/buddy", "/home/swf/code/harness",
                "/tmp/tmp_x/proj", "/some/project", "",
                "/home/swf/agency/x"]:
        assert pathx.project_path(raw) == raw


def test_legacy_mount_prefixes_still_recognized():
    assert pathx.project_path("/media/swf/MyDisk/share/share/harness") == SHARE + "/harness"
    assert pathx.project_path("/media/swf/MyDisk1/share/harness") == SHARE + "/harness"


def test_normalization_is_idempotent():
    for raw in ["/mnt/mydisk/share/agent/x", "/home/swf/agent/x",
                SHARE + "/agent/x", "/tmp/a", "/home/swf/usb1/buddy"]:
        once = pathx.project_path(raw)
        assert pathx.project_path(once) == once


def test_syntax_path_does_not_touch_disk():
    assert pathx.syntax_path("~/share/x") == SHARE + "/x"
    assert pathx.syntax_path("/mnt/mydisk/share/x") == "/mnt/mydisk/share/x"


pass
def test_physical_penetrates_symlinks():
    if not os.path.exists("/home/swf/agent"):
        pytest.skip("本机没有 ~/agent 软链")
    assert pathx.same_path("/home/swf/agent/content",
                           "/mnt/mydisk/share/agent/content")
    assert pathx.physical("/home/swf/share/x") == "/mnt/mydisk/share/x"


def test_rel_inside_same_and_outside(tmp_path):
    root = tmp_path / "p"
    (root / "a").mkdir(parents=True)
    assert pathx.rel_inside(root / "a", root) == "a"
    assert pathx.rel_inside(root, root) == ""
    assert pathx.rel_inside(tmp_path / "other", root) is None
    assert pathx.is_within(root / "a", root) is True
    assert pathx.is_within(tmp_path / "other", root) is False


def test_rel_inside_across_spellings():
    rel = pathx.rel_inside("/mnt/mydisk/share/agent/content/a.txt",
                           "/home/swf/agent/content")
    assert rel == "a.txt"


def test_boundary_compare_key_forwards():
    from app.security.audit import boundary

    assert boundary.compare_key(SHARE + "/agent/x") == pathx.physical(SHARE + "/agent/x")


def test_fsx_relative_helpers_forward(tmp_path):
    from app.util import fsx

    root = tmp_path / "r"
    (root / "d").mkdir(parents=True)
    assert fsx.rel_to(root / "d", root) == __import__("pathlib").Path("d")
    assert fsx.is_inside(root / "d", root) is True
    assert fsx.rel_to(tmp_path, root) is None


pass
def test_real_db_has_no_alias_spelling():
    import sqlite3
    from pathlib import Path

    db = Path(__file__).resolve().parents[3] / "data" / "agent.db"
    if not db.is_file():
        pytest.skip("agent.db 不存在（CI 环境）")
    con = sqlite3.connect("file:" + str(db) + "?mode=ro", uri=True)
    checks = [("registered_projects", "path"), ("registered_projects", "parent"),
              ("sessions", "project"), ("installed_plugins", "project"),
              ("installed_files", "project"), ("plugin_grants", "project"),
              ("project_keys", "project")]
    left = []
    for table, col in checks:
        for (val,) in con.execute(f'SELECT DISTINCT "{col}" FROM "{table}"'):
            val = val or ""
            if val != pathx.project_path(val):
                left.append(f"{table}.{col}={val}")
    for (key,) in con.execute("SELECT key FROM kv WHERE key LIKE 'project_policy:%'"):
        p = key.split(":", 1)[1]
        if p != pathx.project_path(p):
            left.append(f"kv.key={key}")
    con.close()
    assert not left, "库里还有未归一的项目写法：" + "; ".join(left)
