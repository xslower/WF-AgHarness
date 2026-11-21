from __future__ import annotations

import time

from .db import Cmp, Table
from .session_db import SessionDb


class CompactionRepo:

    _json_columns = frozenset({"items"})

    def __init__(self, db: SessionDb) -> None:
        self.db = db

    def _table(self, project: str, sid: str) -> Table:
        t = Table(self.db._db_for(project, sid), "compactions")
        t._json_columns = self._json_columns
        return t

    def _tx(self, project: str, sid: str):
        return self.db.session_tx(project, sid, "compactions", self._json_columns)

    def get(self, project: str, sid: str) -> list[dict]:
        with self.db._db_lock(project, sid):
            rows = self._table(project, sid).select(order="upto_seq")
        return [{"upto_seq": r["upto_seq"], "items": r["items"]} for r in rows]

    def add(self, project: str, sid: str, upto_seq: int,
            items: list[dict]) -> None:
        if upto_seq <= 0 or not items:
            return
        with self._tx(project, sid) as t:
            t.insert({
                "upto_seq": upto_seq,
                "items": items,
                "created": time.time(),
            })

    def set_items(self, project: str, sid: str, upto_seq: int,
                  items: list[dict]) -> None:
        with self._tx(project, sid) as t:
            t.update({"items": items}, {"upto_seq": int(upto_seq)})

    def delete_before(self, project: str, sid: str, upto_seq: int) -> int:
        with self._tx(project, sid) as t:
            return t.delete({"upto_seq": Cmp("<", int(upto_seq))})

    def truncate_at(self, project: str, sid: str, keep_from_seq: int) -> int:
        with self._tx(project, sid) as t:
            return t.delete({"upto_seq": Cmp(">", int(keep_from_seq))})

    def clear(self, project: str, sid: str) -> None:
        with self._tx(project, sid) as t:
            t.clear()
