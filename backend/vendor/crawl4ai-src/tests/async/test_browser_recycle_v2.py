
import asyncio
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

import pytest

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


pass
pass
pass

PAGES = {}
for i in range(100):
    PAGES[f"/page{i}"] = (
        f"<!DOCTYPE html><html><head><title>Page {i}</title></head>"
        f"<body><h1>Page {i}</h1><p>Content for page {i}.</p></body></html>"
    ).encode()


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        body = PAGES.get(self.path, PAGES["/page0"])
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(body)


class _Server(HTTPServer):
    allow_reuse_address = True


@pytest.fixture(scope="module")
def srv():
    s = _Server(("127.0.0.1", 0), Handler)
    port = s.server_address[1]
    t = threading.Thread(target=s.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}"
    s.shutdown()


def _u(base, i):
    return f"{base}/page{i}"


def _bm(c):
    return c.crawler_strategy.browser_manager


pass
pass
pass

@pytest.mark.asyncio
async def test_version_bump_on_threshold(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        max_pages_before_recycle=3,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        assert bm._browser_version == 1

        pass
        for i in range(2):
            r = await c.arun(url=_u(srv, i), config=run)
            assert r.success

        assert bm._browser_version == 1, "Version should still be 1 after 2 pages"
        assert bm._pages_served == 2

        pass
        r = await c.arun(url=_u(srv, 2), config=run)
        assert r.success
        assert bm._browser_version == 2, "Version should bump after 3rd page"
        assert bm._pages_served == 0, "Counter resets after bump"

        pass
        r = await c.arun(url=_u(srv, 3), config=run)
        assert r.success
        assert bm._pages_served == 1


@pytest.mark.asyncio
async def test_signature_changes_after_version_bump(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        max_pages_before_recycle=2,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        pass
        sig_v1 = bm._make_config_signature(run)

        pass
        for i in range(2):
            await c.arun(url=_u(srv, i), config=run)

        pass
        await c.arun(url=_u(srv, 2), config=run)

        pass
        sig_v2 = bm._make_config_signature(run)
        assert sig_v1 != sig_v2, "Signature should change after version bump"


@pytest.mark.asyncio
async def test_no_version_bump_when_disabled(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        max_pages_before_recycle=0,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        for i in range(20):
            r = await c.arun(url=_u(srv, i), config=run)
            assert r.success

        assert bm._browser_version == 1, "Version should not bump when disabled"
        assert bm._pages_served == 20


pass
pass
pass

@pytest.mark.asyncio
async def test_old_signature_goes_to_pending_cleanup(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        max_pages_before_recycle=2,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        pass
        for i in range(2):
            await c.arun(url=_u(srv, i), config=run)

        pass
        assert bm._browser_version == 2

        pass
        pass
        pass
        assert len(bm._pending_cleanup) == 0


@pytest.mark.asyncio
async def test_cleanup_happens_when_refcount_hits_zero(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        max_pages_before_recycle=3,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        pass
        pass
        for i in range(10):
            r = await c.arun(url=_u(srv, i), config=run)
            assert r.success

        pass
        pass
        assert len(bm._pending_cleanup) == 0, "All old contexts should be cleaned up"


pass
pass
pass

@pytest.mark.asyncio
async def test_concurrent_crawls_dont_block_on_recycle(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        max_pages_before_recycle=5,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        pass
        tasks = [c.arun(url=_u(srv, i), config=run) for i in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        pass
        excs = [r for r in results if isinstance(r, Exception)]
        assert len(excs) == 0, f"Exceptions: {excs[:3]}"

        successes = [r for r in results if not isinstance(r, Exception) and r.success]
        assert len(successes) == 20, f"Only {len(successes)} succeeded"

        pass
        assert bm._browser_version >= 2, "Should have recycled at least once"


@pytest.mark.asyncio
async def test_high_concurrency_with_small_threshold(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        max_pages_before_recycle=3,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        pass
        tasks = [c.arun(url=_u(srv, i % 100), config=run) for i in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        excs = [r for r in results if isinstance(r, Exception)]
        assert len(excs) == 0, f"Exceptions: {excs[:3]}"

        successes = [r for r in results if not isinstance(r, Exception) and r.success]
        assert len(successes) == 50


pass
pass
pass

@pytest.mark.asyncio
async def test_safety_cap_limits_pending_browsers(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        max_pages_before_recycle=2,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)
        bm._max_pending_browsers = 2

        pass
        for i in range(15):
            r = await c.arun(url=_u(srv, i), config=run)
            assert r.success

        pass
        pass
        pass
        assert len(bm._pending_cleanup) <= bm._max_pending_browsers


pass
pass
pass

@pytest.mark.asyncio
async def test_managed_browser_recycle(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
        max_pages_before_recycle=3,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        for i in range(10):
            r = await c.arun(url=_u(srv, i), config=run)
            assert r.success, f"Page {i} failed"

        pass
        assert bm._browser_version >= 2


@pytest.mark.asyncio
async def test_managed_browser_isolated_context_recycle(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
        create_isolated_context=True,
        max_pages_before_recycle=3,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        for i in range(10):
            r = await c.arun(url=_u(srv, i), config=run)
            assert r.success, f"Page {i} failed"

        assert bm._browser_version >= 2


pass
pass
pass

@pytest.mark.asyncio
async def test_threshold_of_one(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        max_pages_before_recycle=1,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        for i in range(5):
            r = await c.arun(url=_u(srv, i), config=run)
            assert r.success

        pass
        pass
        pass
        pass
        pass
        assert bm._browser_version == 6


@pytest.mark.asyncio
async def test_different_configs_get_separate_cleanup_tracking(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        max_pages_before_recycle=2,
    )

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        run_a = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)
        run_b = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, verbose=False,
            override_navigator=True,
        )

        pass
        for i in range(6):
            cfg_to_use = run_a if i % 2 == 0 else run_b
            r = await c.arun(url=_u(srv, i), config=cfg_to_use)
            assert r.success

        pass
        assert bm._browser_version >= 2
