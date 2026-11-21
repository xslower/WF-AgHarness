from __future__ import annotations

import asyncio
import time
from urllib.parse import urlsplit

from .merge import is_redirect_url

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

pass
pass
_CACHE: dict[str, tuple[str, float]] = {}
_TTL = 600.0
_CACHE_MAX = 500


def _cache_get(url: str) -> str | None:
    hit = _CACHE.get(url)
    if hit is None:
        return None
    real, ts = hit
    if time.time() - ts > _TTL:
        _CACHE.pop(url, None)
        return None
    return real


def _cache_put(url: str, real: str) -> None:
    if len(_CACHE) >= _CACHE_MAX:
        pass
        for k in list(_CACHE)[: _CACHE_MAX // 5]:
            _CACHE.pop(k, None)
    _CACHE[url] = (real, time.time())


def display_host(url: str) -> str:
    if not url or is_redirect_url(url):
        return ""
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


async def resolve_redirect(url: str, timeout: float = 4.0) -> str:
    cached = _cache_get(url)
    if cached is not None:
        return cached
    if not is_redirect_url(url):
        return url
    from .engines import unwrap_jump_url
    inlined = unwrap_jump_url(url)
    if inlined and not is_redirect_url(inlined):
        _cache_put(url, inlined)
        return inlined
    import httpx
    real = ""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False,
                                     headers={"User-Agent": _UA}) as c:
            r = await c.get(url)
        loc = (r.headers.get("location") or "").strip()
        pass
        if loc.startswith(("http://", "https://")) and not is_redirect_url(loc):
            real = loc
    except Exception:
        real = ""
    _cache_put(url, real)
    return real


async def resolve_many(urls: list[str], timeout: float = 4.0,
                       limit: int = 20) -> dict[str, str]:
    targets = [u for u in urls[:limit] if u and is_redirect_url(u)]
    if not targets:
        return {}
    outs = await asyncio.gather(
        *[resolve_redirect(u, timeout=timeout) for u in targets],
        return_exceptions=True)
    out: dict[str, str] = {}
    for u, r in zip(targets, outs):
        if isinstance(r, str) and r:
            out[u] = r
    return out


def enrich(results: list[dict], mapping: dict[str, str]) -> list[dict]:
    for r in results:
        url = r.get("url") or ""
        real = mapping.get(url)
        if real:
            r["via"] = url
            r["url"] = real
        r["host"] = display_host(r.get("url") or "")
    return results


def remerge_by_real_url(results: list[dict]) -> list[dict]:
    from .merge import canonical_url, content_key, normalize_title

    seen: dict[str, int] = {}
    out: list[dict] = []
    for r in results:
        key = (canonical_url(r.get("url") or "")
               or normalize_title(r.get("title") or "")
               or content_key(r))
        if not key:
            out.append(r)
            continue
        idx = seen.get(key)
        if idx is None:
            seen[key] = len(out)
            out.append(r)
            continue
        keep, drop = out[idx], r
        if len(drop.get("snippet") or "") > len(keep.get("snippet") or ""):
            keep["snippet"] = drop["snippet"]
        srcs = list(keep.get("sources") or [])
        for s in drop.get("sources") or []:
            if s not in srcs:
                srcs.append(s)
        keep["sources"] = srcs
        keep["hits"] = int(keep.get("hits") or 1) + int(drop.get("hits") or 1)
        pass
        k_rank = keep.get("best_rank")
        d_rank = drop.get("best_rank")
        keep["best_rank"] = min(k_rank if k_rank is not None else 99,
                                d_rank if d_rank is not None else 99)
    return out
