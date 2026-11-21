from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.util import pathx
import app.security.project_mode as pp
from app.project import manager as pm

SHARE = pathx.SHARE_ROOT
LEGACY = [
    "/media/swf/MyDisk/share/share/harness",
    "/media/swf/MyDisk/MyDisk1/share/share/harness",
    "/media/swf/MyDisk1/share/share/harness",
    "/home/swf/share/harness",
    "~/share/harness",
]


@pytest.mark.parametrize("raw", LEGACY)
def test_legacy_mounts_normalize_to_symlink(raw):
    assert pathx.project_path(raw) == SHARE + "/harness"


def test_sub_paths_and_early_single_share_form():
    assert pathx.project_path("/media/swf/MyDisk/share/share/content/paid") == SHARE + "/content/paid"
    assert pathx.project_path("/media/swf/MyDisk/share/harness") == SHARE + "/harness"
    assert pathx.project_path(SHARE + "/harness/") == SHARE + "/harness"


def test_foreign_paths_untouched():
    for raw in ["/home/swf/usb1/buddy", "/tmp/tmp_7m2cf0y/proj",
                "/some/project", "", "/home/swf/miniconda3/envs/313/bin/python3"]:
        assert pathx.project_path(raw) == raw


def test_policy_key_stable_across_mounts():
    assert {pp._key(x) for x in LEGACY} == {"project_policy:" + SHARE + "/harness"}
    assert pathx.normalize_key("project_policy:", LEGACY[0]) == pp._key(SHARE + "/harness")


def test_policy_roundtrip_any_mount(tmp_path, monkeypatch):
    from app.store.kv import KVStore
    monkeypatch.setattr(pp, "_kv", lambda: KVStore(tmp_path / "agent.db"))
    monkeypatch.setattr(pp, "_top", lambda project: project)
    pp.set_mode(LEGACY[0], "review")
    for raw in LEGACY[1:]:
        assert pp.get_mode(raw) == "review"
    assert pp.mode_for_cwd(LEGACY[1]) == "review"


def test_migrated_db_key_matches_code():
    db = Path(__file__).resolve().parents[3] / "data" / "agent.db"
    if not db.is_file():
        pytest.skip("agent.db 不存在（CI 环境）")
    con = sqlite3.connect("file:" + str(db) + "?mode=ro", uri=True)
    keys = [r[0] for r in con.execute("SELECT key FROM kv WHERE key LIKE 'project_policy:%'")]
    left = con.execute("SELECT COUNT(*) FROM kv WHERE key LIKE '%/media/swf%'").fetchone()[0]
    con.close()
    assert left == 0
    assert keys, "迁移后应至少保留一条 project_policy 记录"
    assert all("/media/" not in k for k in keys), "kv key 里不能残留真实挂载路径"
    pass
    pass
    pass
    assert any(pathx.normalize_key("project_policy:",
                                  k[len("project_policy:"):]) == k for k in keys), (
        "kv key 必须是当前代码归一后不变的形式", keys)


class FakeRegistry:

    def __init__(self, paths=None):
        self.paths = list(paths or [])
        self.parents: dict[str, str] = {}

    def list_paths(self):
        return list(self.paths)

    def list_rows(self):
        return [{"path": p, "parent": self.parents.get(p, "")} for p in self.paths]

    def parent_of(self, p):
        return self.parents.get(p, "")

    def add(self, p, parent=""):
        if p not in self.paths:
            self.paths.append(p)
        if parent:
            self.parents[p] = parent

    def set_parent(self, p, parent):
        self.parents[p] = parent

    def remove(self, p):
        self.paths = [x for x in self.paths if x != p]
        self.parents.pop(p, None)

def test_registry_dedup_across_mounts(monkeypatch):
    fake = FakeRegistry()
    monkeypatch.setattr(pm, "RegistryStore", lambda: fake)
    m = pm.ProjectManager(root="/tmp/unused")
    m._register_path(Path(LEGACY[0]))
    m._register_path(Path(SHARE + "/harness"))
    assert fake.paths == [SHARE + "/harness"]


def test_unregister_matches_legacy_row(monkeypatch):
    fake = FakeRegistry([LEGACY[0]])
    monkeypatch.setattr(pm, "RegistryStore", lambda: fake)
    monkeypatch.setattr(pm.Path, "is_dir", lambda self: False)
    m = pm.ProjectManager(root="/tmp/unused")
    assert m.unregister(SHARE + "/harness") is True
    assert fake.paths == []


def test_retarget_rewrites_descendants(monkeypatch):
    fake = FakeRegistry([LEGACY[0].replace("harness", "content"),
                         LEGACY[0].replace("harness", "content/paid")])
    monkeypatch.setattr(pm, "RegistryStore", lambda: fake)
    m = pm.ProjectManager(root="/tmp/unused")
    assert m.retarget("/media/swf/MyDisk/share/share/content",
                      "/home/swf/share/content2") == 2
    assert set(fake.paths) == {SHARE + "/content2", SHARE + "/content2/paid"}
