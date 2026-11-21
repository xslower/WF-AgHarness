from __future__ import annotations

import json
import sqlite3
import time
from typing import Optional

from ..store import event_log
from ..store.project_names import project_of
from ..store.session_db import (PURGEABLE_KINDS, WF_SESSION_KIND,
                                SessionDb)
from ..store.compactions import CompactionRepo
from ..store.db import Table



class SessionStore(SessionDb):
    def __init__(self) -> None:
        super().__init__()
        pass
        self.compactions = CompactionRepo(self)

    pass
    def create(self, title: str = "新任务", project: str = "",
               kind: str = "", origin: str = "") -> dict:
        now = time.time()
        s = {
            "id": "",
            "title": title,
            # 落库前归一：项目标识只允许 `~/share/<rel>` 一种写法（换盘不改库）；
            # 收**名称**或路径都行 —— 名称查注册表换成登记路径（与插件 API
            # 同一个 `project_of`），否则 `motion` 会被编成 `motion/`
            # 而不是 `content/motion/`（静默落错 runtimeDir 分区）。
            "project": project_of(project),

            "created_at": now,
            "updated_at": now,
            "messages": [],
            "kind": kind or "",
            "origin": origin or "",
        }
        self.insert_session(s)
        return s

    pass
    def get(self, sid: str) -> Optional[dict]:
        full = self.get_window(sid, tail_pairs=0)
        return full

    def get_window_before(self, sid: str, before_seq: int,
                          limit: int = 150) -> Optional[dict]:
        return self._window(sid, tail_pairs=0, before_seq=before_seq, limit=limit)

    def get_window(self, sid: str, tail_pairs: int = 2) -> Optional[dict]:
        return self._window(sid, tail_pairs=tail_pairs)

    def _window(self, sid: str, tail_pairs: int, before_seq: int | None = None,
                limit: int = 0) -> Optional[dict]:
        row = self.session_head(sid)
        if row is None:
            return None
        project = row[2]
        total = 0
        start = 0
        if tail_pairs > 0:
            total = self.msg_count(project, sid)
            upper = total if before_seq is None else min(total, before_seq)
            start = self.window_start(project, sid, upper, tail_pairs)
            msgs = self.msgs_since(project, sid, start,
                                   upper if before_seq is not None else None)
        elif limit > 0:
            total = self.msg_count(project, sid)
            upper = total if before_seq is None else min(total, before_seq)
            rows = self.msgs_last(project, sid, upper, limit)
            start = int(rows[0][0]) if rows else 0
            msgs = [(r[1],) for r in rows]
        else:
            msgs = self.msgs_all(project, sid)
            total = len(msgs)

        pass
        out = [json.loads(m[0]) for m in msgs]
        return {
            "id": row[0], "title": row[1], "project": row[2],
            "created_at": row[3], "kind": row[4] or "", "origin": row[5] or "",
            "messages": out,
            "total": total or len(out),
            "offset": start,
            "has_more": start > 0,
        }

    def list(self, project: str | None = None, kind: str | None = None,
             origin: str | None = None) -> list[dict]:
        where: list[str] = []
        params: list = []
        if project is not None:
            where.append("project=?")
            params.append(project)
        if kind is not None:
            where.append("kind=?")
            params.append(kind)
        if origin is not None:
            where.append("origin=?")
            params.append(origin)
        rows = self.list_rows(" AND ".join(where), params)
        return [self._row_dict(r) for r in rows]

    @staticmethod
    def _row_dict(r) -> dict:
        return {"id": r[0], "title": r[1] or "未命名", "project": r[2],
                "created_at": r[3], "message_count": r[4],
                "kind": r[5] or "", "origin": r[6] or "",
                "updated_at": (r[7] or r[3])}

    def find_active(self, project: str | None, kind: str,
                    origin: str) -> Optional[dict]:
        where = ["kind=?", "origin=?"]
        params: list = [kind, origin]
        if project is not None:
            where.append("project=?")
            params.append(project)
        row = self.active_row(" AND ".join(where), params)
        return self._row_dict(row) if row else None

    pass
    def save(self, s: dict) -> None:
        project = s.get("project", "")
        sid = s["id"]
        pass
        pass
        self.ensure_index(s)

        msgs = s.get("messages", [])
        n = len(msgs)
        pass
        pass
        with self._lock:
            done = self._persisted.get(sid, -1)
            if 0 <= done <= n:
                slice_ = msgs[done:] if n > done else []
            else:
                slice_ = msgs
            full_rewrite = not (0 <= done <= n)
        rows = [(i, json.dumps(m, ensure_ascii=False))
                for i, m in enumerate(slice_, start=0 if full_rewrite else done)]
        pass
        pass
        with self.session_tx(project, sid, "messages") as mt:
            if full_rewrite:
                pass
                mt.clear()
                mt.insert_many(
                    [{"seq": r[0], "msg": r[1]} for r in rows])
            elif rows:
                pass
                mt.insert_many(
                    [{"seq": r[0], "msg": r[1]} for r in rows],
                    or_replace=True)
        with self._lock:
            self._persisted[sid] = n
            if len(self._persisted) > 2000:
                self._persisted.clear()
        pass
        pass
        pass
        pass
        with self.sys_tx() as st:
            st.update({
                "title": s.get("title") or "未命名",
                "project": project,
                "created_at": s.get("created_at") or 0,
                "message_count": len(msgs),
                "updated_at": time.time(),
            }, where={"id": sid})

    async def save_async(self, s: dict) -> None:
        pass
        import asyncio
        await asyncio.to_thread(self.save, s)

    pass
    def append_message(self, project: str, sid: str, index: int, msg: dict) -> None:
        payload = json.dumps(msg, ensure_ascii=False)
        with self.session_tx(project, sid, "messages") as mt:
            mt.insert({"seq": int(index), "msg": payload}, or_replace=True)
        with self._lock:
            cur = self._persisted.get(sid, -1)
            if cur >= 0:
                self._persisted[sid] = max(cur, int(index) + 1)

    async def append_message_async(self, project: str, sid: str, index: int,
                                   msg: dict) -> None:
        import asyncio
        await asyncio.to_thread(self.append_message, project, sid, index, msg)


    pass
    def get_compactions(self, project: str, sid: str) -> list[dict]:
        return self.compactions.get(project, sid)

    def add_compaction(self, project: str, sid: str, upto_seq: int,
                       items: list[dict]) -> None:
        self.compactions.add(project, sid, upto_seq, items)

    def clear_compactions(self, project: str, sid: str) -> None:
        self.compactions.clear(project, sid)

    def set_compaction_items(self, project: str, sid: str, upto_seq: int,
                             items: list[dict]) -> None:
        self.compactions.set_items(project, sid, upto_seq, items)

    def delete_compactions_before(self, project: str, sid: str,
                                  upto_seq: int) -> int:
        return self.compactions.delete_before(project, sid, upto_seq)

    def truncate_compactions(self, project: str, sid: str,
                             keep_from_seq: int) -> int:
        return self.compactions.truncate_at(project, sid, keep_from_seq)

    pass
    def rename(self, sid: str, title: str) -> None:
        with self.sys_tx() as st:
            st.update({"title": title}, where={"id": sid})

    def purge_old(self, days: int,
                  kinds: tuple[str, ...] = PURGEABLE_KINDS) -> int:
        if days <= 0:
            return 0
        cutoff = time.time() - days * 86400
        rows = self.stale_rows(kinds, cutoff)
        for sid, _project in rows:
            self.delete(sid)
        return len(rows)

    def purge_empty_wf_sessions(self, keep: set[str] | None = None,
                                kind: str = WF_SESSION_KIND) -> int:
        skip = keep or set()
        parents = self.wf_node_parents()
        empty = [str(r["id"]) for r in self.list(kind=kind)
                 if str(r["id"]) not in parents and str(r["id"]) not in skip]
        for sid in empty:
            self.delete(sid)
        return len(empty)

    def delete(self, sid: str) -> None:
        project = self.session_project(sid)
        pass
        pass
        pass
        with self.session_tx(project, sid, "messages") as mt:
            mt.clear()
        for name in ("compactions", "events"):
            try:
                with self.session_tx(project, sid, name) as t:
                    t.clear()
            except sqlite3.OperationalError:
                pass
        with self.sys_tx() as st:
            st.delete(where={"id": sid})
        pass
        pass
        self._close_session(sid)
        event_log.forget_seq(sid)
        pass
        pass
        try:
            import shutil
            from ..store import layout
            d = layout.session_tool_output_dir(project, sid)
            if d.is_dir():
                shutil.rmtree(d, ignore_errors=True)
        except Exception:
            import logging
            logging.getLogger("harness.sessions").debug(
                "清理会话输出目录失败 sid=%s", sid, exc_info=True)
