
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable

from ...store import project_crypto
from ...util import textindex
from ...util.jsonx import dumps
from . import kb_index
from .kb_index import RRF_K, _SCHEMA


pass
MAX_BODY = 100_000
pass
MAX_BATCH = 512


pass
_ENGINES = ("bm25", "vector", "hybrid")


class KBError(ValueError):
    pass


def _norm(text: str) -> str:
    return " ".join(str(text or "").split())


def _check_vectors(coll: str, vecs: list[list[float]], model: str,
                   meta: dict) -> None:
    dim = len(vecs[0])
    if any(len(v) != dim for v in vecs):
        raise KBError("vectors 内各条维度不一致")
    if meta["exists"] and meta["model"] and meta["model"] != model:
        raise KBError(
            f"集合 {coll} 已用模型 {meta['model']} 建库（{meta['dim']} 维），"
            f"不能改用 {model or '未指定模型'} 写入；换模型必须重建集合")
    if meta["exists"] and meta["dim"] and meta["dim"] != dim:
        raise KBError(f"集合 {coll} 的向量维度是 {meta['dim']}，收到 {dim}")


class KnowledgeBase:

    def __init__(self, db_path: Path, project: str = "", embed=None) -> None:
        self.path = Path(db_path)
        self.project = project
        pass
        pass
        self.embed = embed
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db: sqlite3.Connection | None = None
        pass
        self._ix: dict[str, tuple[str, Any]] = {}
        pass
        _ = self.db

    pass
    @property
    def db(self) -> sqlite3.Connection:
        if self._db is None:
            pass
            from ...store.db import open_db
            self._db = open_db(self.path, _SCHEMA)
        return self._db

    def close(self) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None
        self._ix.clear()

    pass
    def collections(self) -> list[dict]:
        rows = self.db.execute(
            "SELECT c.name, c.model, c.dim, c.updated, "
            "(SELECT COUNT(*) FROM kb_docs d WHERE d.coll=c.name) "
            "FROM kb_collections c ORDER BY c.name").fetchall()
        return [{"name": r[0], "model": r[1], "dim": r[2],
                 "updated": r[3], "count": r[4]} for r in rows]

    def info(self, coll: str) -> dict:
        row = self.db.execute(
            "SELECT name, model, dim, updated FROM kb_collections WHERE name=?",
            (coll,)).fetchone()
        if row is None:
            return {"name": coll, "exists": False, "model": "", "dim": 0,
                    "count": 0, "vectors": 0, "missing": 0}
        n, nv = self.db.execute(
            "SELECT (SELECT COUNT(*) FROM kb_docs WHERE coll=?),"
            "       (SELECT COUNT(*) FROM kb_docs d"
            "        JOIN kb_vecs v ON v.doc_id=d.id WHERE d.coll=?)",
            (coll, coll)).fetchone()
        return {"name": row[0], "exists": True, "model": row[1],
                "dim": row[2], "updated": row[3], "count": n,
                "vectors": nv, "missing": int(n) - int(nv),
                "backends": kb_index.available_backends()}

    def drop(self, coll: str) -> int:
        with self._tx() as db:
            ids = [r[0] for r in db.execute(
                "SELECT id FROM kb_docs WHERE coll=?", (coll,))]
            for i in ids:
                db.execute("DELETE FROM kb_vecs WHERE doc_id=?", (i,))
                db.execute("DELETE FROM kb_fts WHERE rowid=?", (i,))
            db.execute("DELETE FROM kb_docs WHERE coll=?", (coll,))
            db.execute("DELETE FROM kb_collections WHERE name=?", (coll,))
        self._ix.pop(coll, None)
        return len(ids)

    def _tx(self):
        kb = self

        class _Ctx:
            def __enter__(self):
                return kb.db

            def __exit__(self, et, ev, tb):
                if et is None:
                    kb.db.commit()
                else:
                    kb.db.rollback()
                return False

        return _Ctx()

    pass
    def add(self, coll: str, docs: Iterable[dict], *, model: str = "",
            vectors: list[list[float]] | None = None) -> dict:
        rows = list(docs or [])
        if not rows:
            raise KBError("add 需要至少一条文档")
        if len(rows) > MAX_BATCH:
            raise KBError(f"一次最多写 {MAX_BATCH} 条，收到 {len(rows)}")
        vecs = list(vectors) if vectors is not None else None
        if vecs is not None and len(vecs) != len(rows):
            raise KBError(f"vectors 条数({len(vecs)})与 docs 条数({len(rows)})不一致")
        model = (model or "").strip()
        meta = self.info(coll)
        if vecs:
            _check_vectors(coll, vecs, model, meta)
        pass
        pass
        pass
        pass
        now = time.time()
        ids: list[int] = []
        with self._tx() as db:
            db.execute(
                "INSERT OR IGNORE INTO kb_collections(name, model, dim, meta, updated)"
                " VALUES (?,?,?,?,?)", (coll, model, (len(vecs[0]) if vecs else 0),
                                        "{}", now))
            db.execute("UPDATE kb_collections SET updated=? WHERE name=?",
                       (now, coll))
            for i, doc in enumerate(rows):
                ids.append(self._put_doc(db, coll, doc))
                if vecs:
                    self._put_vec(db, ids[-1], vecs[i])
        if vecs:
            self._ix.pop(coll, None)
        return {"ok": True, "collection": coll, "count": len(ids),
                "model": model or meta.get("model", ""),
                "dim": (len(vecs[0]) if vecs else 0)}

    def _put_doc(self, db: sqlite3.Connection, coll: str, doc: dict) -> int:
        dkey = _norm(doc.get("key"))
        if not dkey:
            raise KBError("doc.key 不能为空（它是覆盖写入的唯一标识）")
        title = _norm(doc.get("title"))[:500]
        body = str(doc.get("body") or "")
        if len(body) > MAX_BODY:
            raise KBError(f"doc.body 超过 {MAX_BODY} 字符（key={dkey}）")
        meta = dumps(doc.get("meta") or {}) if isinstance(doc.get("meta"), dict) else "{}"
        sealed = project_crypto.seal_in(self.project, body)
        terms = " ".join(textindex.terms(f"{title} {body}"))
        old = db.execute("SELECT id FROM kb_docs WHERE coll=? AND dkey=?",
                         (coll, dkey)).fetchone()
        if old:
            doc_id = old[0]
            db.execute(
                "UPDATE kb_docs SET title=?, body=?, meta=? WHERE id=?",
                (title, sealed, meta, doc_id))
        else:
            cur = db.execute(
                "INSERT INTO kb_docs(coll,dkey,title,body,meta) VALUES (?,?,?,?,?)",
                (coll, dkey, title, sealed, meta))
            doc_id = int(cur.lastrowid)
        pass
        db.execute("DELETE FROM kb_fts WHERE rowid=?", (doc_id,))
        db.execute("INSERT INTO kb_fts(rowid, terms) VALUES (?,?)",
                   (doc_id, terms))
        return doc_id

    def _put_vec(self, db: sqlite3.Connection, doc_id: int,
                 vec: list[float]) -> None:
        db.execute("INSERT OR REPLACE INTO kb_vecs(doc_id, vec) VALUES (?,?)",
                   (doc_id, kb_index._pack([float(x) for x in vec])))

    pass
    def all_texts(self, coll: str) -> list[tuple[int, str]]:
        rows = self.db.execute(
            "SELECT id, title, body FROM kb_docs WHERE coll=? ORDER BY id",
            (coll,)).fetchall()
        return [(int(r[0]), " ".join(
            f"{r[1]} {project_crypto.unseal_in(self.project, r[2])}".split()))
                for r in rows]

    def missing_vectors(self, coll: str) -> list[tuple[int, str]]:
        rows = self.db.execute(
            "SELECT d.id, d.title, d.body FROM kb_docs d "
            "LEFT JOIN kb_vecs v ON v.doc_id=d.id "
            "WHERE d.coll=? AND v.doc_id IS NULL ORDER BY d.id",
            (coll,)).fetchall()
        return [(int(r[0]), " ".join(
            f"{r[1]} {project_crypto.unseal_in(self.project, r[2])}".split()))
                for r in rows]

    def set_vectors(self, coll: str, model: str,
                    pairs: list[tuple[int, list[float]]]) -> dict:
        rows = list(pairs or [])
        if not rows:
            return {"ok": True, "collection": coll, "count": 0}
        model = (model or "").strip()
        if not model:
            raise KBError("set_vectors 需要 model（不知道按哪个模型比对）")
        meta = self.info(coll)
        _check_vectors(coll, [v for _, v in rows], model, meta)
        dim = len(rows[0][1])
        now = time.time()
        with self._tx() as db:
            db.execute(
                "INSERT OR IGNORE INTO kb_collections(name, model, dim, meta, updated)"
                " VALUES (?,?,?,'{}',?)", (coll, model, dim, now))
            db.execute("UPDATE kb_collections SET model=?, dim=?, updated=?"
                       " WHERE name=?", (model, dim, now, coll))
            for doc_id, vec in rows:
                self._put_vec(db, int(doc_id), [float(x) for x in vec])
        self._ix.pop(coll, None)
        return {"ok": True, "collection": coll, "count": len(rows),
                "model": model, "dim": dim}

    def rebuild_lexical(self, coll: str) -> dict:
        rows = self.db.execute(
            "SELECT id, title, body FROM kb_docs WHERE coll=?", (coll,)).fetchall()
        with self._tx() as db:
            for doc_id, title, body in rows:
                text = f"{title} {project_crypto.unseal_in(self.project, body)}"
                db.execute("DELETE FROM kb_fts WHERE rowid=?", (doc_id,))
                db.execute("INSERT INTO kb_fts(rowid, terms) VALUES (?,?)",
                           (doc_id, " ".join(textindex.terms(text))))
        return {"ok": True, "collection": coll, "count": len(rows)}

    async def build(self, coll: str, *, engine: str = "bm25",
                    embed=None, batch: int = 64) -> dict:
        eng = (engine or "bm25").strip().lower()
        if eng not in _ENGINES:
            raise KBError(f"engine 必须是 {'/'.join(_ENGINES)}，收到: {engine}")
        meta = self.info(coll)
        if not meta["exists"] or not meta["count"]:
            raise KBError(f"集合 {coll} 没有文档，先 add 再 build")
        lex = self.rebuild_lexical(coll)
        if eng == "bm25":
            return {"ok": True, "collection": coll, "engine": eng,
                    "documents": meta["count"], "lexical": lex["count"],
                    "embedded": 0, "model": meta["model"],
                    "dim": meta["dim"], "missing": meta["missing"]}
        embed = embed or self.embed
        if embed is None:
            raise KBError(f"engine={eng} 需要向量模型（没有可用的 embedding 网关）")
        todo = (self.missing_vectors(coll) if eng == "vector"
                else self.all_texts(coll))
        got = await _run_embed(embed, [t for _, t in todo], meta["model"], batch)
        if not got["ok"]:
            raise KBError(f"向量化失败: {got.get('error')}")
        saved = self.set_vectors(coll, got["model"],
                                 [(doc_id, v) for (doc_id, _), v
                                  in zip(todo, got["vectors"])])
        after = self.info(coll)
        return {"ok": True, "collection": coll, "engine": eng,
                "documents": after["count"], "lexical": lex["count"],
                "embedded": saved["count"], "model": saved["model"],
                "dim": saved["dim"], "missing": after["missing"]}

    def delete(self, coll: str, keys: list[str]) -> int:
        with self._tx() as db:
            n = 0
            for k in keys or []:
                row = db.execute("SELECT id FROM kb_docs WHERE coll=? AND dkey=?",
                                 (coll, _norm(k))).fetchone()
                if not row:
                    continue
                db.execute("DELETE FROM kb_vecs WHERE doc_id=?", (row[0],))
                db.execute("DELETE FROM kb_fts WHERE rowid=?", (row[0],))
                db.execute("DELETE FROM kb_docs WHERE id=?", (row[0],))
                n += 1
        if n:
            self._ix.pop(coll, None)
        return n

    pass
    def search(self, coll: str, query: str, *, limit: int = 8,
               vector: list[float] | None = None,
               vector_error: str = "") -> dict:
        q = _norm(query)
        if not q:
            raise KBError("query 不能为空")
        limit = max(1, min(int(limit or 8), 50))
        lex = self._lexical(coll, q, limit * 3)
        vec: list[tuple[int, float]] = []
        if vector:
            vec, err = self._semantic(coll, vector, limit * 3)
            if err:
                vector_error = vector_error or err
        fused = self._rrf([[i for i, _ in lex], [i for i, _ in vec]])
        meta = self.info(coll)
        degraded = not vec
        return {
            "ok": True, "collection": coll, "model": meta["model"],
            "dim": meta["dim"], "query": q,
            "degraded": degraded,
            "reason": (vector_error or
                       ("" if vec else
                        "未提供 query 向量（可用 host.embed 生成后再检索）")),
            "missing_vectors": meta["missing"],
            "lexical_hits": len(lex), "vector_hits": len(vec),
            "items": self._items(coll, fused[:limit]),
            "backends": kb_index.available_backends(),
        }

    def _lexical(self, coll: str, query: str, k: int) -> list[tuple[int, float]]:
        terms = textindex.terms(query)
        if not terms:
            return []
        pass
        expr = " OR ".join(f'"{t}"' for t in terms if '"' not in t)
        if not expr:
            return []
        try:
            rows = self.db.execute(
                "SELECT f.rowid, bm25(kb_fts) FROM kb_fts f "
                "JOIN kb_docs d ON d.id=f.rowid "
                "WHERE kb_fts MATCH ? AND d.coll=? "
                "ORDER BY bm25(kb_fts) LIMIT ?", (expr, coll, k)).fetchall()
        except sqlite3.OperationalError as e:
            raise KBError(f"检索表达式无效: {e}") from None
        return [(int(r[0]), -float(r[1])) for r in rows]

    def _semantic(self, coll: str, vec: list[float], k: int):
        meta = self.info(coll)
        if not meta["exists"] or not meta["count"]:
            return [], ""
        if meta["dim"] and len(vec) != meta["dim"]:
            return [], f"query 向量维度 {len(vec)} 与集合 {meta['dim']} 不一致"
        ix = self._index(coll)
        hits = ix.search([float(x) for x in vec], k)
        return hits, ""

    def _index(self, coll: str):
        meta = self.info(coll)
        cached = self._ix.get(coll)
        if cached is not None and cached[0] == f"{meta['model']}:{meta['count']}":
            return cached[1]
        ix = kb_index._make_index(max(int(meta["dim"] or 1), 1))
        rows = self.db.execute(
            "SELECT v.doc_id, v.vec FROM kb_vecs v JOIN kb_docs d ON d.id=v.doc_id "
            "WHERE d.coll=?", (coll,)).fetchall()
        if rows:
            ix.add([int(r[0]) for r in rows],
                   [kb_index._unpack(r[1]) for r in rows])
        self._ix[coll] = (f"{meta['model']}:{meta['count']}", ix)
        return ix

    @staticmethod
    def _rrf(lists: list[list[int]]) -> list[tuple[int, float]]:
        score: dict[int, float] = {}
        for ids in lists:
            for rank, doc_id in enumerate(ids):
                score[doc_id] = score.get(doc_id, 0.0) + 1.0 / (RRF_K + rank + 1)
        return sorted(score.items(), key=lambda kv: -kv[1])

    def _items(self, coll: str, hits: list[tuple[int, float]]) -> list[dict]:
        out: list[dict] = []
        for doc_id, s in hits:
            row = self.db.execute(
                "SELECT dkey, title, body, meta FROM kb_docs WHERE id=?",
                (doc_id,)).fetchone()
            if row is None:
                continue
            out.append({"key": row[0], "title": row[1],
                        "body": project_crypto.unseal_in(self.project, row[2]),
                        "meta": _loads(row[3]), "score": round(s, 6)})
        return out


async def _run_embed(embed, texts: list[str], model: str,
                     batch: int = 64) -> dict:
    if not texts:
        return {"ok": True, "vectors": [], "model": model, "dim": 0}
    out: list[list[float]] = []
    locked = (model or "").strip()
    for i in range(0, len(texts), batch):
        got = await embed(texts[i:i + batch], locked)
        if not got or not got.get("ok"):
            return {"ok": False, "model": locked,
                    "error": (got or {}).get("error", "未知错误")}
        now = str(got.get("model") or "").strip()
        if not now:
            return {"ok": False, "model": locked,
                    "error": "embedding 未回传 model（无法锁定向量空间）"}
        if locked and now != locked:
            return {"ok": False, "model": locked,
                    "error": f"向量模型中途变了（{locked} → {now}），已中止"}
        locked = now
        out.extend(list(got.get("vectors") or []))
    if len(out) != len(texts):
        return {"ok": False, "model": locked,
                "error": f"向量条数 {len(out)} 与文本条数 {len(texts)} 不一致"}
    return {"ok": True, "vectors": out, "model": locked,
            "dim": len(out[0]) if out else 0}


def _loads(raw: str) -> Any:
    try:
        import json
        return json.loads(raw or "{}")
    except ValueError:
        return {}


__all__ = ["KnowledgeBase", "KBError", "MAX_BODY", "MAX_BATCH"]
