from __future__ import annotations

import html
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .relevance import grade, score_items
from .query import split

pass
pass
_TITLE_TAIL = re.compile(r"\s*[-–—_|｜]\s*[^-–—_|｜]{0,12}$")
pass
_ZW = re.compile(r"[\u200b-\u200f\ufeff]")
_FULLWIDTH_SPACE = re.compile(r"[\u3000\xa0]")
_SPACES = re.compile(r"\s+")

pass
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "spm", "from", "source", "ref", "referer", "share_token", "timestamp",
    "sa", "ved", "usg", "rsv_spt", "rsv_iqid", "issp",
}

pass
_REDIRECT_HOSTS = (
    "baidu.com/link", "baidu.com/baidu.php", "sogou.com/link",
    "so.com/link", "so.com/jump", "bing.com/ck/a",
    "duckduckgo.com/l/", "google.com/url",
)


def normalize_title(title: str) -> str:
    s = html.unescape(title or "")
    s = re.sub(r"<[^>]+>", "", s)
    s = _ZW.sub("", s)
    s = _FULLWIDTH_SPACE.sub(" ", s)
    s = _SPACES.sub(" ", s).strip()
    pass
    pass
    pass
    for _ in range(2):
        cut = _TITLE_TAIL.sub("", s)
        if cut == s or len(cut) < 3:
            break
        s = cut.strip()
    return s.lower()


def is_redirect_url(url: str) -> bool:
    low = (url or "").lower()
    return any(h in low for h in _REDIRECT_HOSTS)


def canonical_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    try:
        p = urlsplit(raw)
    except ValueError:
        return raw.lower()
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if k.lower() not in _TRACKING_PARAMS]
    path = p.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    port = f":{p.port}" if p.port and p.port not in (80, 443) else ""
    return urlunsplit((p.scheme or "https", host + port, path,
                       urlencode(query), ""))


pass
_CONTENT_PREFIX = 80
pass
_MIN_SNIPPET = 20
pass
_PUNCT = re.compile(r"[\s\u3000\xa0,.，。;；:：!！?？\"'“”‘’()（）\[\]【】<>《》/\\|~`\-–—_+=*&^%$#@]+")


def normalize_text(text: str) -> str:
    s = html.unescape(_ZW.sub("", text or ""))
    return _PUNCT.sub("", s).lower()


def content_key(item: dict) -> str:
    sn = normalize_text(item.get("snippet") or "")
    if len(sn) < _MIN_SNIPPET:
        return ""
    return sn[:_CONTENT_PREFIX]


def dedupe_key(item: dict) -> tuple[str, str]:
    url = item.get("url") or ""
    ukey = "" if is_redirect_url(url) else canonical_url(url)
    return ukey, normalize_title(item.get("title") or "")


def _new_row(it: dict, g_idx: int, rank: int) -> dict:
    return {
        "title": (it.get("title") or "").strip(),
        "url": (it.get("url") or "").strip(),
        "snippet": (it.get("snippet") or "").strip(),
        "sources": [g_idx],
        "hits": 1,
        "best_rank": rank,
    }


def _absorb(row: dict, it: dict, g_idx: int, rank: int) -> None:
    if len(it.get("snippet") or "") > len(row["snippet"]):
        row["snippet"] = (it.get("snippet") or "").strip()[:400]
    if not row["url"] and it.get("url"):
        row["url"] = it["url"]
    if not row["title"] and (it.get("title") or "").strip():
        row["title"] = it["title"].strip()
    if g_idx not in row["sources"]:
        row["sources"].append(g_idx)
    row["hits"] += 1
    row["best_rank"] = min(row["best_rank"], rank)


def merge_results(groups: list[list[dict]]) -> list[dict]:
    merged: list[dict] = []
    by_url: dict[str, int] = {}
    by_title: dict[str, int] = {}
    by_content: dict[str, int] = {}
    for g_idx, items in enumerate(groups):
        for rank, it in enumerate(items or []):
            ukey, tkey = dedupe_key(it)
            ckey = content_key(it)
            idx = by_url.get(ukey) if ukey else None
            if idx is None and tkey:
                idx = by_title.get(tkey)
            if idx is None and ckey:
                idx = by_content.get(ckey)
            if idx is None:
                merged.append(_new_row(it, g_idx, rank))
                idx = len(merged) - 1
            else:
                _absorb(merged[idx], it, g_idx, rank)
            if ukey and ukey not in by_url:
                by_url[ukey] = idx
            if tkey and tkey not in by_title:
                by_title[tkey] = idx
            if ckey and ckey not in by_content:
                by_content[ckey] = idx
    return merged


_TRUST_ORDER = {"high": 0, "medium": 1, "low": 2}

pass
_GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "X": 3}

pass
pass
MAX_ROWS = 20


def rank_results(results: list[dict], query: str) -> list[dict]:
    ents, topic = split(query)
    for r, s in zip(results, score_items(query, results)):
        r["_q"] = s
        r["_g"] = grade(r, ents, topic)
    results.sort(key=lambda r: (
        _GRADE_ORDER.get(r.get("_g"), 3),
        -r.get("_q", 0.0),
        -len(r.get("sources") or []),
        _TRUST_ORDER.get(r.get("trust", "medium"), 1),
        r.get("best_rank", 99),
    ))
    for r in results:
        r.pop("_q", None)
    return results


def select_top(results: list[dict], limit: int) -> list[dict]:
    want = max(1, int(limit or 1))
    top = list(results[:want])
    for r in results[want:MAX_ROWS]:
        if r.get("_g") != "A":
            break
        top.append(r)
    return top
