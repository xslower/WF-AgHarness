from __future__ import annotations

import json
import sqlite3
import threading

import pytest

from app.util import dumps, err, ok
from app.util.fsx import ensure_dir, ensure_parent
from app.tools.schema_fmt import DESC_LIMIT, param_brief, popular_row
from app.store.db import SqliteStore, open_db


class TestJsonx:
    def test_dumps_keeps_chinese(self):
        out = dumps({"error": "文件不存在"})
        assert "文件不存在" in out
        assert "\\u" not in out

    def test_err_shape(self):
        assert json.loads(err("坏了")) == {"error": "坏了"}

    def test_err_keeps_extra_fields_in_order(self):
        payload = json.loads(err("坏了", subagent_id="sa1", risks=["x"]))
        assert list(payload) == ["error", "subagent_id", "risks"]
        assert payload["subagent_id"] == "sa1"

    def test_err_does_not_stringify_structured_error(self):
        assert json.loads(err({"code": 1}))["error"] == {"code": 1}

    def test_ok_shape(self):
        assert json.loads(ok(note="done")) == {"ok": True, "note": "done"}

    def test_dumps_nested(self):
        assert json.loads(dumps({"a": ["中", 1]})) == {"a": ["中", 1]}


class TestSchemaBrief:
    def _schema(self, props, desc="工具说明"):
        return {"type": "function",
                "function": {"name": "t", "description": desc,
                             "parameters": {"properties": props}}}

    def test_param_brief(self):
        s = self._schema({"path": {"type": "string"}, "n": {"type": "integer"}})
        assert param_brief(s) == "path:string, n:integer"

    def test_param_brief_without_type(self):
        assert param_brief(self._schema({"x": {}})) == "x:?"

    def test_param_brief_empty(self):
        assert param_brief({"function": {"parameters": {}}}) == ""
        assert param_brief({}) == ""

    def test_popular_row_truncates_description(self):
        row = popular_row("t", 3, self._schema({}, desc="长" * (DESC_LIMIT + 50)))
        assert len(row["description"]) == DESC_LIMIT
        assert row["call_count"] == 3

    def test_popular_row_survives_missing_fields(self):
        row = popular_row("t", 1, {"function": {}})
        assert row["params"] == ""
        assert row["description"] == ""



pass

def test_ensure_dir_accepts_str_and_is_idempotent(tmp_path):
    target = tmp_path / "a" / "b" / "c"
    assert ensure_dir(str(target)).is_dir()
    assert ensure_dir(target).is_dir()
    assert ensure_dir(target) == target


def test_ensure_parent_creates_parent_not_file_path(tmp_path):
    f = tmp_path / "deep" / "dir" / "file.txt"
    assert ensure_parent(f) == f
    assert f.parent.is_dir()
    assert not f.exists()


def test_ensure_parent_concurrent_safe(tmp_path):
    target = tmp_path / "race" / "file.txt"
    errors = []

    def worker():
        try:
            ensure_parent(target)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []


pass

class _Demo(SqliteStore):
    _schema = "CREATE TABLE IF NOT EXISTS demo (id TEXT PRIMARY KEY, data TEXT NOT NULL)"

    def put(self, key: str, value) -> None:
        self._write("INSERT OR REPLACE INTO demo VALUES (?,?)", (key, self.dump(value)))

    def get(self, key, default=None):
        row = self._row("SELECT data FROM demo WHERE id=?", (key,))
        return default if row is None else self.load(row[0])

    def drop(self, key: str) -> bool:
        return self._write("DELETE FROM demo WHERE id=?", (key,)) > 0


def test_store_roundtrip_keeps_chinese_readable(tmp_path):
    s = _Demo(tmp_path / "db" / "agent.db")
    s.put("k", {"名称": "中文"})
    assert s.get("k") == {"名称": "中文"}
    pass
    raw = sqlite3.connect(tmp_path / "db" / "agent.db").execute(
        "SELECT data FROM demo").fetchone()[0]
    assert "中文" in raw


def test_store_delete_reports_rowcount(tmp_path):
    s = _Demo(tmp_path / "agent.db")
    s.put("a", 1)
    assert s.drop("a") is True
    assert s.drop("a") is False


def test_store_enables_wal(tmp_path):
    s = _Demo(tmp_path / "agent.db")
    mode = s._db.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"


def test_store_usable_across_threads(tmp_path):
    s = _Demo(tmp_path / "agent.db")
    err = []

    def worker():
        try:
            s.put("t", {"x": 1})
            assert s.get("t") == {"x": 1}
        except Exception as e:
            err.append(e)

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    assert err == []


def test_open_db_reuses_existing_table(tmp_path):
    p = tmp_path / "agent.db"
    conn = open_db(p, "CREATE TABLE IF NOT EXISTS t (k TEXT PRIMARY KEY)")
    conn.execute("INSERT INTO t VALUES ('x')")
    conn.commit()
    conn.close()
    conn2 = open_db(p, "CREATE TABLE IF NOT EXISTS t (k TEXT PRIMARY KEY)")
    assert conn2.execute("SELECT k FROM t").fetchall() == [("x",)]
    conn2.close()


def test_subclasses_share_one_agent_db_file(tmp_path):
    from app.store.kv import KVStore, PresetStore, RegistryStore
    from app.provider.store import ProviderStore

    db = tmp_path / "agent.db"
    KVStore(db).set_json("k", 1)
    PresetStore(db).upsert({"id": "p1"})
    RegistryStore(db).add("/tmp/proj")
    ProviderStore(db).upsert("openai", {"id": "openai"})

    tables = {r[0] for r in sqlite3.connect(db).execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"kv", "prompt_presets", "registered_projects", "providers"} <= tables
    pass
    assert KVStore(db).get_json("k") == 1
    assert [p["id"] for p in PresetStore(db).list()] == ["p1"]
    assert RegistryStore(db).list_paths() == ["/tmp/proj"]
    assert ProviderStore(db).list_all() == [{"id": "openai"}]
