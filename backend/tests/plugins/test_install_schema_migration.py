from __future__ import annotations

import sqlite3
from pathlib import Path

from app.plugins.install import InstallStore


_LEGACY_DDL = """
CREATE TABLE installed_plugins (
  id TEXT NOT NULL, version TEXT NOT NULL, project TEXT NOT NULL,
  installed_at REAL NOT NULL, source TEXT NOT NULL, manifest TEXT NOT NULL,
  PRIMARY KEY (id, project));
CREATE TABLE installed_files (
  plugin_id TEXT NOT NULL, project TEXT NOT NULL, scope TEXT NOT NULL,
  kind TEXT NOT NULL, rel_path TEXT NOT NULL, sha256 TEXT NOT NULL,
  extra TEXT NOT NULL DEFAULT '', PRIMARY KEY (plugin_id, project, rel_path));
INSERT INTO installed_files VALUES
  ('old-skill', '/p', 'project', 'skill_bundle', 'a/SKILL.md', 'abcd', '{"adopted":true}');
"""


def _make_legacy(p: Path) -> None:
    c = sqlite3.connect(str(p))
    c.executescript(_LEGACY_DDL)
    c.commit()
    c.close()


def _cols(store: InstallStore) -> dict[str, tuple]:
    return {r[1]: (r[3], r[4]) for r in
            store._db.execute("PRAGMA table_info(installed_files)")}


def test_legacy_table_is_upgraded_and_data_kept(tmp_dirs):
    p = tmp_dirs / "agent.db"
    _make_legacy(p)

    s = InstallStore(p)
    cols = _cols(s)
    pass
    assert set(cols) == {"plugin_id", "project", "kind", "rel_path",
                         "extra", "scope", "sha256"}
    assert cols["scope"][0] == 1 and cols["scope"][1] is not None
    assert cols["sha256"][0] == 1 and cols["sha256"][1] is not None
    pass
    rows = list(s._db.execute(
        "select plugin_id, scope, sha256, extra from installed_files"))
    assert rows == [("old-skill", "project", "abcd", '{"adopted":true}')]


def test_new_write_succeeds_without_scope_sha256(tmp_dirs):
    p = tmp_dirs / "agent.db"
    _make_legacy(p)
    s = InstallStore(p)

    s._files.insert({"plugin_id": "star-beacon", "project": "/beacon",
                     "kind": "tool", "rel_path": "tools/x.py", "extra": "{}"})
    s._db.commit()
    assert s._db.execute(
        "select count(*) from installed_files where plugin_id='star-beacon'"
    ).fetchone()[0] == 1


def test_migration_is_idempotent(tmp_dirs):
    p = tmp_dirs / "agent.db"
    _make_legacy(p)
    s1 = InstallStore(p)
    s1._files.insert({"plugin_id": "b", "project": "", "kind": "tool",
                      "rel_path": "t.py", "extra": "{}"})
    s1._db.commit()

    s2 = InstallStore(p)
    assert s2._db.execute(
        "select count(*) from installed_files").fetchone()[0] == 2
    assert set(_cols(s2)) == {"plugin_id", "project", "kind", "rel_path",
                              "extra", "scope", "sha256"}


def test_fresh_db_has_upfront_defaults(tmp_dirs):
    s = InstallStore(tmp_dirs / "agent.db")
    cols = _cols(s)
    assert cols["scope"][1] is not None and cols["sha256"][1] is not None
    s._files.insert({"plugin_id": "x", "project": "", "kind": "tool",
                     "rel_path": "a.py", "extra": "{}"})
    s._db.commit()
    assert s._db.execute("select count(*) from installed_files").fetchone()[0] == 1
