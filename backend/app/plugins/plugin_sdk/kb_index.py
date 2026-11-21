from __future__ import annotations

import struct

pass
RRF_K = 60

_SCHEMA = """
CREATE TABLE IF NOT EXISTS kb_collections (
  name TEXT PRIMARY KEY, model TEXT NOT NULL DEFAULT '',
  dim INTEGER NOT NULL DEFAULT 0, meta TEXT NOT NULL DEFAULT '{}',
  updated REAL NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS kb_docs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  coll TEXT NOT NULL, dkey TEXT NOT NULL,
  title TEXT NOT NULL DEFAULT '', body TEXT NOT NULL DEFAULT '',
  meta TEXT NOT NULL DEFAULT '{}');
CREATE UNIQUE INDEX IF NOT EXISTS kb_docs_key ON kb_docs(coll, dkey);
CREATE TABLE IF NOT EXISTS kb_vecs (
  doc_id INTEGER PRIMARY KEY, vec BLOB NOT NULL);
CREATE VIRTUAL TABLE IF NOT EXISTS kb_fts USING fts5(
  terms, content='', contentless_delete=1);
"""


pass
def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _unpack(blob: bytes) -> list[float]:
    return list(struct.unpack(f"{len(blob) // 4}f", blob))


class _NumpyIndex:

    name = "numpy_flat"

    def __init__(self, dim: int) -> None:
        import numpy as np
        self.np = np
        self.dim = dim
        self._ids: list[int] = []
        self._mat = np.zeros((0, dim), dtype="float32")

    def add(self, ids: list[int], vecs: list[list[float]]) -> None:
        if not ids:
            return
        np = self.np
        m = np.asarray(vecs, dtype="float32")
        m /= np.clip(np.linalg.norm(m, axis=1, keepdims=True), 1e-12, None)
        self._mat = np.vstack([self._mat, m]) if len(self._ids) else m
        self._ids.extend(ids)

    def search(self, vec: list[float], k: int) -> list[tuple[int, float]]:
        if not self._ids:
            return []
        np = self.np
        q = np.asarray(vec, dtype="float32")
        q /= max(float(np.linalg.norm(q)), 1e-12)
        scores = self._mat @ q
        idx = np.argsort(-scores)[:k]
        return [(self._ids[i], float(scores[i])) for i in idx]

    def __len__(self) -> int:
        return len(self._ids)


class _FaissIndex:

    name = "faiss"

    def __init__(self, dim: int) -> None:
        import faiss
        self.faiss = faiss
        self.dim = dim
        self._ids: list[int] = []
        self._ix = faiss.IndexFlatIP(dim)

    def add(self, ids: list[int], vecs: list[list[float]]) -> None:
        if not ids:
            return
        import numpy as np
        m = np.asarray(vecs, dtype="float32")
        m /= np.clip(np.linalg.norm(m, axis=1, keepdims=True), 1e-12, None)
        self._ix.add(m)
        self._ids.extend(ids)

    def search(self, vec: list[float], k: int) -> list[tuple[int, float]]:
        if not len(self._ids):
            return []
        import numpy as np
        q = np.asarray([vec], dtype="float32")
        q /= np.clip(np.linalg.norm(q, axis=1, keepdims=True), 1e-12, None)
        sim, idx = self._ix.search(q, min(k, len(self._ids)))
        return [(self._ids[i], float(s)) for i, s in zip(idx[0], sim[0]) if i >= 0]

    def __len__(self) -> int:
        return len(self._ids)


class _UsearchIndex:

    name = "usearch"

    def __init__(self, dim: int) -> None:
        from usearch.index import Index
        self.dim = dim
        self._ids: list[int] = []
        self._ix = Index(ndim=dim, metric="cos", connectivity=16)

    def add(self, ids: list[int], vecs: list[list[float]]) -> None:
        if not ids:
            return
        import numpy as np
        m = np.asarray(vecs, dtype="float32")
        m /= np.clip(np.linalg.norm(m, axis=1, keepdims=True), 1e-12, None)
        keys = np.arange(len(self._ids), len(self._ids) + len(ids), dtype="uint64")
        self._ix.add(keys, m)
        self._ids.extend(ids)

    def search(self, vec: list[float], k: int) -> list[tuple[int, float]]:
        if not len(self._ids):
            return []
        import numpy as np
        q = np.asarray(vec, dtype="float32")
        q /= max(float(np.linalg.norm(q)), 1e-12)
        matches = self._ix.search(q, min(k, len(self._ids)))
        return [(self._ids[int(m.key)], 1.0 - float(m.distance))
                for m in matches]

    def __len__(self) -> int:
        return len(self._ids)

pass
pass
_BACKENDS = (("usearch", _UsearchIndex), ("faiss", _FaissIndex),
             ("numpy_flat", _NumpyIndex))

def available_backends() -> list[str]:
    import importlib.util as iu
    return [name for mod, name in (("usearch", "usearch"), ("faiss", "faiss"),
                                   (None, "numpy_flat"))
            if mod is None or iu.find_spec(mod) is not None]


def _make_index(dim: int):
    for mod_name, cls in _BACKENDS:
        try:
            return cls(dim)
        except Exception:
            continue
    return _NumpyIndex(dim)
