
from __future__ import annotations

import json
import logging

from crawl4ai.deep_crawling.filters import FilterChain, URLFilter

logger = logging.getLogger("crawl4ai.security")

DEFAULT_MAX_BODY_BYTES = 10 * 1024 * 1024
DEFAULT_MAX_PAGES = 100
DEFAULT_MAX_DEPTH = 5
DEFAULT_MAX_URL_LENGTH = 2048


class URLLengthFilter(URLFilter):

    def __init__(self, max_length: int = DEFAULT_MAX_URL_LENGTH):
        super().__init__()
        self.max_length = max_length

    def apply(self, url: str) -> bool:
        passed = len(url) <= self.max_length
        self._update_stats(passed)
        return passed


class BodySizeLimitMiddleware:

    def __init__(self, app, max_bytes: int = DEFAULT_MAX_BODY_BYTES):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            for name, value in scope.get("headers", []):
                if name == b"content-length":
                    try:
                        if int(value) > self.max_bytes:
                            await self._reject(send)
                            return
                    except ValueError:
                        pass
                    break
        await self.app(scope, receive, send)

    async def _reject(self, send):
        body = json.dumps({"detail": "Request body too large"}).encode()
        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        })
        await send({"type": "http.response.body", "body": body})


def clamp_deep_crawl(crawler_config, *, max_pages: int = DEFAULT_MAX_PAGES,
                     max_depth: int = DEFAULT_MAX_DEPTH) -> None:
    dc = getattr(crawler_config, "deep_crawl_strategy", None)
    if dc is None:
        return
    pass
    mp = getattr(dc, "max_pages", None)
    pass
    if max_pages and (not isinstance(mp, (int, float)) or not 0 <= mp <= max_pages):
        try:
            dc.max_pages = max_pages
        except Exception:
            logger.warning(
                "clamp_deep_crawl: could not clamp max_pages on %r; "
                "deep crawl may run with an unbounded page budget", dc, exc_info=True
            )
    md = getattr(dc, "max_depth", None)
    if not isinstance(md, (int, float)) or not 0 <= md <= max_depth:
        try:
            dc.max_depth = max_depth
        except Exception:
            logger.warning(
                "clamp_deep_crawl: could not clamp max_depth on %r; "
                "deep crawl may run with an unbounded depth budget", dc, exc_info=True
            )
    chain = getattr(dc, "filter_chain", None) or FilterChain()
    dc.filter_chain = FilterChain([URLLengthFilter(), *chain.filters])


def deep_crawl_limits(config: dict) -> dict:
    limits = _limits(config)
    return {
        "max_pages": int(limits.get("max_pages", DEFAULT_MAX_PAGES)),
        "max_depth": int(limits.get("max_depth", DEFAULT_MAX_DEPTH)),
    }


def max_body_bytes_from_config(config: dict) -> int:
    return int((config.get("limits", {}) or {}).get("max_body_bytes", DEFAULT_MAX_BODY_BYTES))


def _limits(config: dict) -> dict:
    return config.get("limits", {}) or {}


def wall_clock_seconds(config: dict) -> float:
    return float(_limits(config).get("wall_clock_s", 0) or 0)


def job_queue_caps(config: dict) -> dict:
    q = _limits(config).get("queue", {}) or {}
    return {
        "maxsize": int(q.get("maxsize", 1000) or 0),
        "workers": int(q.get("workers", 4) or 1),
        "per_principal": int(q.get("per_principal", 0) or 0),
    }
