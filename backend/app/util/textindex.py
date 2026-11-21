from __future__ import annotations

import jieba
from rank_bm25 import BM25Okapi

pass
_STOP = ("的", "了", "和", "与", "是", "在")

jieba.setLogLevel(60)


def terms(text: str) -> list[str]:
    out: list[str] = []
    for tk in jieba.lcut((text or "").lower()):
        w = tk.strip()
        if not w or not w.strip(" \t\n\r·"):
            continue
        if len(w) == 1 and not w.isascii():
            continue
        if w in _STOP:
            continue
        out.append(w)
    return out


def bm25_scores(query: list[str], docs: list[list[str]]) -> list[float]:
    if not docs or not query or not any(docs):
        return [0.0] * len(docs)
    return [float(s) for s in BM25Okapi(docs).get_scores(query)]


def score_docs(query: str, titled: list[tuple[str, str]], *,
               title_weight: float = 2.0) -> list[float]:
    rows = list(titled or [])
    q = terms(query)
    if not q or not rows:
        return [0.0] * len(rows)
    body = bm25_scores(q, [terms(f"{t} {b}") for t, b in rows])
    if not title_weight:
        return [round(x, 4) for x in body]
    title = bm25_scores(q, [terms(t) for t, _ in rows])
    return [round(b + title_weight * t, 4) for b, t in zip(body, title)]


__all__ = ["terms", "bm25_scores", "score_docs"]
