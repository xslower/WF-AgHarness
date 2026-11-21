from __future__ import annotations

import logging
import time

from ....util.jsonx import append_jsonl
from .paths import logs_dir
from .relevance import judge

logger = logging.getLogger("harness.tools.web_health")

_LOG_NAME = "web_engine_health.jsonl"


def _log_path():
    d = logs_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / _LOG_NAME


def observe(groups: list[list[dict]], picked: list, query: str,
            errors: dict[str, str]) -> list[dict]:
    out: list[dict] = []
    for e, items in zip(picked, groups):
        r = judge(query, items)
        row = {"ts": time.time(), "engine": e.id, "query": query[:80],
               "total": r["total"], "relevant": r["relevant"],
               "ratio": round(r["ratio"], 3),
               "blocked": bool(errors.get(e.id)) and not items,
               "entities": r["entities"], "topics": r["topics"][:8]}
        out.append(row)
        append_jsonl(_log_path(), row)
        if row["blocked"]:
            logger.info("web 引擎被拦: %s (%s)", e.id, errors.get(e.id))
    return out


def log_usage(query: str, is_page: bool, steps, debug, limit) -> None:
    acts = [s["act"] for s in (steps or [])[:20]
            if isinstance(s, dict) and isinstance(s.get("act"), str)]
    d = logs_dir()
    d.mkdir(parents=True, exist_ok=True)
    append_jsonl(d / "web_usage.jsonl", {
        "ts": time.time(), "page": is_page, "q": query[:80],
        "steps": len(steps or []), "acts": acts, "debug": bool(debug),
        "debug_type": type(debug).__name__, "limit": limit})


def log_sources(query: str, rows: list[dict]) -> None:
    if not rows:
        return
    d = logs_dir()
    d.mkdir(parents=True, exist_ok=True)
    append_jsonl(d / "web_sources.jsonl", {
        "ts": time.time(), "q": query[:80],
        "rows": [{"t": (r.get("title") or "")[:60],
                  "s": list(r.get("sources") or []),
                  "g": r.get("_g")} for r in rows[:20]],
    })
