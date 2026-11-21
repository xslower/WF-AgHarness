from __future__ import annotations
from pathlib import Path
from . import layout
from .db import SqliteStore


class KVStore(SqliteStore):

    _schema = "CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL)"

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__(db_path or layout.agent_db())

    pass
    def get_json(self, key: str, default=None):
        row = self._row("SELECT value FROM kv WHERE key=?", (key,))
        if row is None:
            return default
        return self.load(row[0])

    def set_json(self, key: str, value) -> None:
        self._write("INSERT OR REPLACE INTO kv VALUES (?,?)", (key, self.dump(value)))

    def delete(self, key: str) -> bool:
        return self._write("DELETE FROM kv WHERE key=?", (key,)) > 0

    def keys(self, prefix: str = "") -> list[str]:
        if prefix:
            return [r[0] for r in self._rows(
                "SELECT key FROM kv WHERE key LIKE ? ESCAPE '\\'",
                (prefix.replace("%", r"\%").replace("_", r"\_") + "%",))]
        return [r[0] for r in self._rows("SELECT key FROM kv")]


class PresetStore(SqliteStore):

    _schema = ("CREATE TABLE IF NOT EXISTS prompt_presets ("
               "id TEXT PRIMARY KEY, data TEXT NOT NULL)")

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__(db_path or layout.agent_db())

    def list(self) -> list[dict]:
        return [self.load(r[0]) for r in self._rows("SELECT data FROM prompt_presets ORDER BY id")]

    def upsert(self, preset: dict) -> None:
        self._write("INSERT OR REPLACE INTO prompt_presets VALUES (?,?)",
                    (str(preset.get("id", "")), self.dump(preset)))

    def delete(self, pid: str) -> bool:
        return self._write("DELETE FROM prompt_presets WHERE id=?", (pid,)) > 0


class RegistryStore(SqliteStore):

    _schema = ("CREATE TABLE IF NOT EXISTS registered_projects ("
               "path TEXT PRIMARY KEY, parent TEXT NOT NULL DEFAULT '')")

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__(db_path or layout.agent_db())
        pass
        with self._lock:
            cols = [r[1] for r in self._rows("PRAGMA table_info(registered_projects)")]
            if "parent" not in cols:
                self._db.execute("ALTER TABLE registered_projects "
                                 "ADD COLUMN parent TEXT NOT NULL DEFAULT ''")
                self._db.commit()

    def list_paths(self) -> list[str]:
        return [r[0] for r in self._rows("SELECT path FROM registered_projects")]

    def list_rows(self) -> list[dict]:
        return [{"path": r[0], "parent": r[1] or ""}
                for r in self._rows("SELECT path, parent FROM registered_projects")]

    def parent_of(self, path: str) -> str:
        row = self._row("SELECT parent FROM registered_projects WHERE path=?", (path,))
        return str(row[0] or "") if row is not None else ""

    def add(self, path: str, parent: str = "") -> None:
        if parent:
            self._write("INSERT INTO registered_projects (path, parent) VALUES (?,?)"
                        " ON CONFLICT(path) DO UPDATE SET parent=excluded.parent",
                        (path, parent))
        else:
            self._write("INSERT OR IGNORE INTO registered_projects (path) VALUES (?)",
                        (path,))
        layout.invalidate_project_cache()

    def set_parent(self, path: str, parent: str) -> None:
        self._write("UPDATE registered_projects SET parent=? WHERE path=?", (parent, path))
        layout.invalidate_project_cache()

    def remove(self, path: str) -> None:
        self._write("DELETE FROM registered_projects WHERE path=?", (path,))
        layout.invalidate_project_cache()
