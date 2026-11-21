from __future__ import annotations
from pathlib import Path
from ..store import layout
from ..store.db import SqliteStore
from ..store import vault


class ProviderStore(SqliteStore):

    _schema = ("CREATE TABLE IF NOT EXISTS providers ("
               "id TEXT PRIMARY KEY, data TEXT NOT NULL)")

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__(db_path or layout.agent_db())

    pass

    def list_all(self) -> list[dict]:
        out: list[dict] = []
        for r in self._rows("SELECT id, data FROM providers ORDER BY rowid"):
            d = self.load(r[1])
            if d.get("apiKey") and not vault.is_sealed(d["apiKey"]):
                self.upsert(r[0], d)
            out.append(self._decrypt(d))
        return out

    @staticmethod
    def _decrypt(data: dict) -> dict:
        d = dict(data)
        if vault.is_sealed(d.get("apiKey")):
            d["apiKey"] = vault.unseal(d["apiKey"])
        return d

    pass

    def upsert(self, provider_id: str, data: dict) -> None:
        d = dict(data)
        pass
        pass
        if "apiKey" in d:
            pass
            pass
            vault.remember(d.get("apiKey") or "")
            d["apiKey"] = vault.seal(d.get("apiKey") or "")
        self._write("INSERT OR REPLACE INTO providers VALUES (?, ?)",
                    (provider_id, self.dump(d)))

    def delete(self, provider_id: str) -> bool:
        return self._write("DELETE FROM providers WHERE id = ?", (provider_id,)) > 0
