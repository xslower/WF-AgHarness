from __future__ import annotations

from .pagekind import is_noise
from .query import has_term, split

pass
pass
from ....util.textindex import bm25_scores, score_docs, terms

pass
MIN_ITEMS = 5
pass
MIN_RATIO = 0.80


def score_items(query: str, items: list[dict], *,
                title_weight: float = 2.0) -> list[float]:
    rows = [x for x in (items or []) if isinstance(x, dict)]
    return score_docs(query,
                      [(str(r.get("title") or ""), str(r.get("snippet") or ""))
                       for r in rows],
                      title_weight=title_weight)


def grade(item: dict, ents: list[str], topic: list[str]) -> str:
    if not isinstance(item, dict):
        return "X"
    title = item.get("title") or ""
    url = item.get("url") or ""
    if is_noise(url, title):
        return "X"
    text = f"{title} {item.get('snippet') or ''} {url}".lower()
    eh = sum(1 for e in ents if has_term(text, e))
    th = sum(1 for t in topic if has_term(text, t))
    if eh >= 1 and th >= 1:
        return "A"
    if eh >= 1:
        return "B"
    if th >= 2:
        return "C"
    return "X"


def judge(query: str, items: list[dict], *, min_items: int = MIN_ITEMS,
          min_ratio: float = MIN_RATIO) -> dict:
    rows = [x for x in (items or []) if isinstance(x, dict)]
    ents, topic = split(query)
    grades = [grade(r, ents, topic) for r in rows]
    relevant = sum(1 for g in grades if g == "A")
    total = len(rows)
    ratio = (relevant / total) if total else 0.0
    return {
        "total": total,
        "relevant": relevant,
        "ratio": ratio,
        "ok": total >= min_items and ratio >= min_ratio,
        "grades": grades,
        "entities": ents,
        "topics": topic,
    }


__all__ = ["MIN_ITEMS", "MIN_RATIO", "terms", "bm25_scores",
           "score_items", "score_docs", "grade", "judge"]
