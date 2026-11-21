from __future__ import annotations

import logging

from ....store import layout
from .engines import parse_wiki_json
from .merge import merge_results

logger = logging.getLogger("harness.tools.web_channels")

pass
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def _ensure_crawl4ai():
    import sys
    from pathlib import Path
    p = layout.BACKEND_ROOT / "vendor" / "crawl4ai-src"
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
    return p


def _parse(url: str, html: str, engine) -> list[dict]:
    from .tool import _parse_serp
    return _parse_serp(html, engine.sel, engine.link_sel, base=url,
                       title_sel=engine.title_sel)


async def _fetch_html(url: str, timeout: float = 8.0) -> tuple[int, str]:
    import httpx
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True,
                                 headers={"User-Agent": _UA,
                                          "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}) as c:
        r = await c.get(url)
    return r.status_code, r.text


async def fetch_doc(url: str, timeout: float = 20.0) -> dict:
    import httpx
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as c:
        r = await c.get(url, headers={"User-Agent": _UA})
    return {"status": r.status_code,
            "content_type": r.headers.get("content-type", ""),
            "text": r.text,
            "final_url": str(r.url)}


def detect_antibot(html: str, status: int) -> str:
    body = html or ""
    if status in (403, 429):
        return f"被限流（HTTP {status}）"
    pass
    if "请输入验证码" in body or "网络不给力" in body:
        return "触发了反爬验证（请稍后重试）"
    if "验证码" in body and len(body) < 4000:
        return "触发了反爬验证（请稍后重试）"
    pass
    if len(body) < 2000:
        return f"返回内容过短（{len(body)} 字节，疑似拦截页）"
    return ""


async def _search_via_browser(url: str, sel: str, link_sel: str,
                              title_sel: str = "",
                              crawler=None) -> list[dict]:
    _ensure_crawl4ai()
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

    cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=1)

    def _rows(html: str) -> list[dict]:
        from .tool import _parse_serp
        return _parse_serp(html, sel, link_sel, base=url, title_sel=title_sel)

    pass
    pass
    own = crawler is None
    handle = LazyBrowser(True) if own else crawler
    try:
        inst = await handle.acquire()
        if inst is None:
            return []
        r = await inst.arun(url=url, config=cfg)
        return _rows(r.html) if (r.success and r.html) else []
    finally:
        if own:
            await handle.close()


async def browser_session():
    _ensure_crawl4ai()
    from crawl4ai import AsyncWebCrawler, BrowserConfig
    return AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False))


class LazyBrowser:

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._inst = None

    async def acquire(self):
        if not self.enabled:
            return None
        if self._inst is None:
            inst = await browser_session()
            await inst.__aenter__()
            self._inst = inst
        return self._inst

    async def close(self) -> None:
        if self._inst is None:
            return
        try:
            await self._inst.__aexit__(None, None, None)
        except Exception:
            logger.debug("crawler.__aexit__ 失败", exc_info=True)
        self._inst = None


async def _fetch_variant(engine, query: str, page: int,
                          timeout: float) -> tuple[list[dict], str]:
    url = engine.page_url(query, page)
    try:
        status, html = await _fetch_html(url, timeout=timeout)
    except Exception:
        return [], ""
    items = _parse(url, html, engine) if status == 200 else []
    return items, "" if items else detect_antibot(html, status)


async def search_one_page(engine, query: str, page: int,
                          use_browser: bool,
                          timeout: float = 8.0,
                          crawler=None) -> list[dict]:
    if engine.kind == "wiki":
        url = engine.page_url(query, page)
        try:
            status, raw = await _fetch_html(url, timeout=timeout)
        except Exception as e:
            raise RuntimeError(f"维基不可达: {type(e).__name__}") from e
        if status != 200:
            raise RuntimeError(f"维基 HTTP {status}")
        return parse_wiki_json(raw)
    blocked = ""
    for variant in (engine, *getattr(engine, "alts", ())):
        items, why = await _fetch_variant(variant, query, page, timeout)
        if items:
            return items
        blocked = blocked or why
    pass
    pass
    if use_browser and getattr(engine, "browser_ok", True):
        url = engine.page_url(query, page)
        try:
            got = await _search_via_browser(url, engine.sel, engine.link_sel,
                                            engine.title_sel, crawler=crawler)
            if got:
                return got
        except Exception:
            logger.debug("浏览器通道搜索失败: %s", url, exc_info=True)
    if blocked:
        pass
        raise RuntimeError(blocked)
    return []


async def search_one_engine(engine, query: str, pages: int,
                            use_browser: bool,
                            timeout: float = 8.0,
                            crawler=None,
                            first_page: int = 1) -> tuple[list[dict], str]:
    pass
    pass
    from . import pacing
    decision = await pacing.gate(engine)
    if decision == "skip":
        logger.debug("频控跳过 %s（%s）", engine.id, decision)
        return [], ""
    pass
    if getattr(engine, "pace", False):
        pacing.mark(engine.id)
    items: list[dict] = []
    pass
    pass
    err_msg = ""
    start = max(1, int(first_page or 1))
    for p in range(start, start + max(1, pages)):
        try:
            items.extend(await search_one_page(engine, query, p, use_browser,
                                               timeout, crawler=crawler))
        except Exception as e:
            err_msg = err_msg or f"{type(e).__name__}: {e}"
    return merge_results([items]), err_msg
