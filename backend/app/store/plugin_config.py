from __future__ import annotations

from pathlib import Path

from ..util import pathx
from . import layout, vault
from .db import SqliteStore


class PluginConfigStore(SqliteStore):

    _schema = """
        CREATE TABLE IF NOT EXISTS plugin_config (
          pid TEXT NOT NULL, project TEXT NOT NULL,
          values_json TEXT NOT NULL, PRIMARY KEY (pid, project));
        CREATE TABLE IF NOT EXISTS plugin_grants (
          pid TEXT NOT NULL, project TEXT NOT NULL,
          names TEXT NOT NULL, PRIMARY KEY (pid, project));
        """

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__(db_path or layout.agent_db())

    @staticmethod
    def _project(project) -> str:
        return pathx.project_path(str(project or ""))

    def get(self, pid: str, project: str = "") -> dict:
        row = self._row(
            "SELECT values_json FROM plugin_config WHERE pid=? AND project=?",
            (pid, self._project(project)))
        if row is None:
            return {}
        try:
            raw = self.load(row[0])
        except (ValueError, TypeError):
            return {}
        if not isinstance(raw, dict):
            return {}
        return {k: vault.unseal(v) for k, v in raw.items()}

    def put(self, pid: str, project: str, values: dict) -> None:
        self._write("INSERT OR REPLACE INTO plugin_config VALUES (?, ?, ?)",
                    (pid, self._project(project), self.dump(dict(values or {}))))

    pass
    def grants(self, pid: str, project: str = "") -> tuple[str, ...]:
        row = self._row(
            "SELECT names FROM plugin_grants WHERE pid=? AND project=?",
            (pid, self._project(project)))
        if row is None:
            return ()
        try:
            names = self.load(row[0])
        except (ValueError, TypeError):
            return ()
        return tuple(str(n) for n in names) if isinstance(names, list) else ()

    def set_grants(self, pid: str, project: str, names) -> None:
        self._write("INSERT OR REPLACE INTO plugin_grants VALUES (?, ?, ?)",
                    (pid, self._project(project),
                     self.dump([str(n) for n in (names or ())])))


    def retarget(self, old: str, new: str) -> int:
        from .retarget import retarget_project_column

        old_key, new_key = self._project(old), self._project(new)
        if not old_key or old_key == new_key:
            return 0
        with self._lock:
            moved = retarget_project_column(self._db, "plugin_config",
                                            old_key, new_key)
            moved += retarget_project_column(self._db, "plugin_grants",
                                             old_key, new_key)
            self._db.commit()
        return moved

__all__ = ["PluginConfigStore"]
