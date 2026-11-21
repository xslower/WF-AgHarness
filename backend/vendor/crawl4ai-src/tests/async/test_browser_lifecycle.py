
import asyncio
import time
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
        f"<body><h1>Page {i}</h1><p>Content for page {i}.</p>"
        f"<a href='/page{(i+1)%100}'>next</a></body></html>"
    ).encode()

pass
PAGES["/login"] = (
    b"<!DOCTYPE html><html><head><title>Login</title></head>"
    b"<body><h1>Login</h1><p>Logged in.</p></body></html>"
)
PAGES["/dashboard"] = (
    b"<!DOCTYPE html><html><head><title>Dashboard</title></head>"
    b"<body><h1>Dashboard</h1><p>Dashboard content.</p></body></html>"
)


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
async def test_standalone_basic_crawl(srv):
    cfg = BrowserConfig(headless=True, verbose=False)
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        r = await c.arun(url=_u(srv, 0), config=run)
        assert r.success
        assert "Page 0" in r.html


@pytest.mark.asyncio
async def test_standalone_sequential_crawls(srv):
    cfg = BrowserConfig(headless=True, verbose=False)
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        for i in range(10):
            r = await c.arun(url=_u(srv, i), config=run)
            assert r.success, f"Page {i} failed"
            assert f"Page {i}" in r.html


@pytest.mark.asyncio
async def test_standalone_concurrent_crawls(srv):
    cfg = BrowserConfig(headless=True, verbose=False)
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        tasks = [c.arun(url=_u(srv, i), config=run) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        excs = [r for r in results if isinstance(r, Exception)]
        assert len(excs) == 0, f"Exceptions: {excs[:3]}"
        assert all(r.success for r in results if not isinstance(r, Exception))


@pytest.mark.asyncio
async def test_standalone_context_reuse(srv):
    cfg = BrowserConfig(headless=True, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        run_a = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)
        r1 = await c.arun(url=_u(srv, 0), config=run_a)
        assert r1.success
        ctx_count_after_first = len(bm.contexts_by_config)

        pass
        r2 = await c.arun(url=_u(srv, 1), config=run_a)
        assert r2.success
        assert len(bm.contexts_by_config) == ctx_count_after_first, (
            "Same config should reuse context"
        )

        pass
        run_b = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, verbose=False,
            override_navigator=True,
        )
        r3 = await c.arun(url=_u(srv, 2), config=run_b)
        assert r3.success
        assert len(bm.contexts_by_config) == ctx_count_after_first + 1, (
            "Different config should create new context"
        )


@pytest.mark.asyncio
async def test_standalone_session_multistep(srv):
    cfg = BrowserConfig(headless=True, verbose=False)
    sess = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS, session_id="standalone_sess", verbose=False,
    )

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        for i in range(3):
            r = await c.arun(url=_u(srv, i), config=sess)
            assert r.success
            assert "standalone_sess" in bm.sessions

        pass
        _, page, _ = bm.sessions["standalone_sess"]
        sig = bm._page_to_sig.get(page)
        if sig:
            assert bm._context_refcounts.get(sig, 0) == 1

        pass
        await c.crawler_strategy.kill_session("standalone_sess")
        assert "standalone_sess" not in bm.sessions
        if sig:
            assert bm._context_refcounts.get(sig, 0) == 0


@pytest.mark.asyncio
async def test_standalone_recycle(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False, max_pages_before_recycle=5,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)
        for i in range(8):
            r = await c.arun(url=_u(srv, i), config=run)
            assert r.success, f"Page {i} failed"

        pass
        assert bm._pages_served == 3


@pytest.mark.asyncio
async def test_standalone_recycle_with_concurrent_crawls(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False, max_pages_before_recycle=5,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        tasks = [c.arun(url=_u(srv, i), config=run) for i in range(15)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        excs = [r for r in results if isinstance(r, Exception)]
        assert len(excs) == 0, f"Exceptions: {excs[:3]}"
        successes = [r for r in results if not isinstance(r, Exception) and r.success]
        assert len(successes) == 15


pass
pass
pass

@pytest.mark.asyncio
async def test_managed_basic_crawl(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        r = await c.arun(url=_u(srv, 0), config=run)
        assert r.success
        assert "Page 0" in r.html


@pytest.mark.asyncio
async def test_managed_sequential_crawls(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        for i in range(8):
            r = await c.arun(url=_u(srv, i), config=run)
            assert r.success, f"Page {i} failed"


@pytest.mark.asyncio
async def test_managed_concurrent_crawls(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        tasks = [c.arun(url=_u(srv, i), config=run) for i in range(8)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        excs = [r for r in results if isinstance(r, Exception)]
        assert len(excs) == 0, f"Exceptions: {excs[:3]}"
        successes = [r for r in results if not isinstance(r, Exception) and r.success]
        assert len(successes) == 8


@pytest.mark.asyncio
async def test_managed_page_reuse(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        pass
        for i in range(3):
            r = await c.arun(url=_u(srv, i), config=run)
            assert r.success

        pass
        pass
        default_ctx = bm.default_context
        total_pages = len(default_ctx.pages)
        assert total_pages <= 3, (
            f"Expected page reuse, but {total_pages} pages exist"
        )


@pytest.mark.asyncio
async def test_managed_session_multistep(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
    )
    sess = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS, session_id="managed_sess", verbose=False,
    )

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        r = await c.arun(url=f"{srv}/login", config=sess)
        assert r.success

        r = await c.arun(url=f"{srv}/dashboard", config=sess)
        assert r.success

        assert "managed_sess" in bm.sessions


@pytest.mark.asyncio
async def test_managed_recycle(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
        max_pages_before_recycle=4,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        for i in range(7):
            r = await c.arun(url=_u(srv, i), config=run)
            assert r.success, f"Page {i} failed after managed recycle"

        pass
        assert bm._pages_served == 3


pass
pass
pass

@pytest.mark.asyncio
async def test_isolated_context_basic(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
        create_isolated_context=True,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        r = await c.arun(url=_u(srv, 0), config=run)
        assert r.success


@pytest.mark.asyncio
async def test_isolated_context_concurrent(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
        create_isolated_context=True,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        tasks = [c.arun(url=_u(srv, i), config=run) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        excs = [r for r in results if isinstance(r, Exception)]
        assert len(excs) == 0, f"Exceptions: {excs[:3]}"
        successes = [r for r in results if not isinstance(r, Exception) and r.success]
        assert len(successes) == 10


@pytest.mark.asyncio
async def test_isolated_context_caching(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
        create_isolated_context=True,
    )

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        run_a = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)
        await c.arun(url=_u(srv, 0), config=run_a)
        count_after_a = len(bm.contexts_by_config)

        pass
        await c.arun(url=_u(srv, 1), config=run_a)
        assert len(bm.contexts_by_config) == count_after_a

        pass
        run_b = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, verbose=False,
            override_navigator=True,
        )
        await c.arun(url=_u(srv, 2), config=run_b)
        assert len(bm.contexts_by_config) == count_after_a + 1


@pytest.mark.asyncio
async def test_isolated_context_refcount(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
        create_isolated_context=True,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        pass
        r = await c.arun(url=_u(srv, 0), config=run)
        assert r.success

        pass
        for sig, rc in bm._context_refcounts.items():
            assert rc == 0, f"Refcount for {sig[:8]}... should be 0, got {rc}"


@pytest.mark.asyncio
async def test_isolated_context_session_with_interleaved(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
        create_isolated_context=True,
    )

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        sess = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, session_id="iso_sess", verbose=False,
        )
        r = await c.arun(url=f"{srv}/login", config=sess)
        assert r.success

        pass
        run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)
        for i in range(5):
            r = await c.arun(url=_u(srv, i), config=run)
            assert r.success

        pass
        assert "iso_sess" in bm.sessions
        r = await c.arun(url=f"{srv}/dashboard", config=sess)
        assert r.success


@pytest.mark.asyncio
async def test_isolated_context_recycle(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
        create_isolated_context=True,
        max_pages_before_recycle=4,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        for i in range(6):
            r = await c.arun(url=_u(srv, i), config=run)
            assert r.success, f"Page {i} failed"

        pass
        assert bm._pages_served == 2
        pass
        assert all(rc == 0 for rc in bm._context_refcounts.values()), (
            "All refcounts should be 0 after sequential crawls"
        )


pass
pass
pass

@pytest.mark.asyncio
async def test_two_crawlers_share_managed_browser(srv):
    pass
    cfg1 = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
    )

    async with AsyncWebCrawler(config=cfg1) as c1:
        bm1 = _bm(c1)
        pass
        cdp_url = f"http://{bm1.managed_browser.host}:{bm1.managed_browser.debugging_port}"

        pass
        cfg2 = BrowserConfig(
            headless=True, verbose=False,
            cdp_url=cdp_url,
            cdp_cleanup_on_close=True,
        )
        async with AsyncWebCrawler(config=cfg2) as c2:
            run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

            pass
            r1 = await c1.arun(url=_u(srv, 0), config=run)
            r2 = await c2.arun(url=_u(srv, 1), config=run)

            assert r1.success, f"Crawler 1 failed: {r1.error_message}"
            assert r2.success, f"Crawler 2 failed: {r2.error_message}"
            assert "Page 0" in r1.html
            assert "Page 1" in r2.html


@pytest.mark.asyncio
async def test_two_crawlers_concurrent_heavy(srv):
    cfg1 = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
    )

    async with AsyncWebCrawler(config=cfg1) as c1:
        bm1 = _bm(c1)
        cdp_url = f"http://{bm1.managed_browser.host}:{bm1.managed_browser.debugging_port}"

        cfg2 = BrowserConfig(
            headless=True, verbose=False,
            cdp_url=cdp_url,
            cdp_cleanup_on_close=True,
        )
        async with AsyncWebCrawler(config=cfg2) as c2:
            run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

            pass
            for i in range(5):
                r1 = await c1.arun(url=_u(srv, i), config=run)
                assert r1.success, f"Crawler 1 page {i} failed: {r1.error_message}"
                r2 = await c2.arun(url=_u(srv, i + 50), config=run)
                assert r2.success, f"Crawler 2 page {i} failed: {r2.error_message}"


pass
pass
pass

@pytest.mark.asyncio
async def test_session_then_nonsession_then_session(srv):
    cfg = BrowserConfig(headless=True, verbose=False)
    sess = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS, session_id="interleave_sess", verbose=False,
    )
    no_sess = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        r = await c.arun(url=_u(srv, 0), config=sess)
        assert r.success

        pass
        for i in range(3):
            r = await c.arun(url=_u(srv, 10 + i), config=no_sess)
            assert r.success

        pass
        assert "interleave_sess" in bm.sessions
        r = await c.arun(url=_u(srv, 99), config=sess)
        assert r.success


@pytest.mark.asyncio
async def test_multiple_sessions_simultaneous(srv):
    cfg = BrowserConfig(headless=True, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        sessions = [
            CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS, session_id=f"sess_{j}", verbose=False,
            )
            for j in range(3)
        ]

        pass
        for j, s in enumerate(sessions):
            r = await c.arun(url=_u(srv, j * 10), config=s)
            assert r.success, f"Session {j} open failed"

        assert len(bm.sessions) == 3

        pass
        for j, s in enumerate(sessions):
            r = await c.arun(url=_u(srv, j * 10 + 1), config=s)
            assert r.success, f"Session {j} step 2 failed"

        pass
        await c.crawler_strategy.kill_session("sess_0")
        assert "sess_0" not in bm.sessions
        assert "sess_1" in bm.sessions
        assert "sess_2" in bm.sessions

        pass
        r = await c.arun(url=_u(srv, 99), config=sessions[1])
        assert r.success


@pytest.mark.asyncio
async def test_session_kill_then_recreate(srv):
    cfg = BrowserConfig(headless=True, verbose=False)
    sess = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS, session_id="reuse_id", verbose=False,
    )

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        r = await c.arun(url=_u(srv, 0), config=sess)
        assert r.success
        _, page_v1, _ = bm.sessions["reuse_id"]

        await c.crawler_strategy.kill_session("reuse_id")
        assert "reuse_id" not in bm.sessions

        pass
        r = await c.arun(url=_u(srv, 50), config=sess)
        assert r.success
        assert "reuse_id" in bm.sessions
        _, page_v2, _ = bm.sessions["reuse_id"]

        pass
        assert page_v1 is not page_v2, "Re-created session should have a new page"


pass
pass
pass

@pytest.mark.asyncio
async def test_recycle_concurrent_sessions_and_nonsessions(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        max_pages_before_recycle=5,
    )

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        pass
        sess_a = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, session_id="stress_a", verbose=False,
        )
        sess_b = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, session_id="stress_b", verbose=False,
        )
        r = await c.arun(url=f"{srv}/login", config=sess_a)
        assert r.success
        r = await c.arun(url=f"{srv}/login", config=sess_b)
        assert r.success

        pass
        no_sess = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)
        tasks = [c.arun(url=_u(srv, i), config=no_sess) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        excs = [r for r in results if isinstance(r, Exception)]
        assert len(excs) == 0, f"Exceptions: {excs[:3]}"

        pass
        assert "stress_a" in bm.sessions
        assert "stress_b" in bm.sessions

        pass
        r = await c.arun(url=f"{srv}/dashboard", config=sess_a)
        assert r.success
        r = await c.arun(url=f"{srv}/dashboard", config=sess_b)
        assert r.success


@pytest.mark.asyncio
async def test_arun_many_with_session_open(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        max_pages_before_recycle=5,
    )

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        sess = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, session_id="batch_guard", verbose=False,
        )
        r = await c.arun(url=f"{srv}/login", config=sess)
        assert r.success

        no_sess = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)
        urls = [_u(srv, i) for i in range(12)]
        results = await c.arun_many(urls, config=no_sess)
        assert all(r.success for r in results)

        pass
        assert "batch_guard" in bm.sessions


@pytest.mark.asyncio
async def test_rapid_recycle_stress(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        max_pages_before_recycle=2,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        for i in range(20):
            r = await c.arun(url=_u(srv, i % 100), config=run)
            assert r.success, f"Page {i} failed during rapid recycle"


@pytest.mark.asyncio
async def test_rapid_recycle_concurrent(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        max_pages_before_recycle=3,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        tasks = [c.arun(url=_u(srv, i), config=run) for i in range(12)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        excs = [r for r in results if isinstance(r, Exception)]
        assert len(excs) == 0, f"Exceptions: {excs[:3]}"
        successes = [r for r in results if not isinstance(r, Exception) and r.success]
        assert len(successes) == 12


pass
pass
pass

@pytest.mark.asyncio
async def test_context_lock_no_duplicate_contexts(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
        create_isolated_context=True,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        tasks = [c.arun(url=_u(srv, i), config=run) for i in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        excs = [r for r in results if isinstance(r, Exception)]
        assert len(excs) == 0, f"Exceptions: {excs[:3]}"

        pass
        assert len(bm.contexts_by_config) == 1, (
            f"Expected 1 context, got {len(bm.contexts_by_config)} — "
            f"lock failed to prevent duplicate creation"
        )


@pytest.mark.asyncio
async def test_page_lock_no_duplicate_pages_managed(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        tasks = [c.arun(url=_u(srv, i), config=run) for i in range(8)]
        await asyncio.gather(*tasks)

        pass
        piu = bm._get_pages_in_use()
        assert len(piu) == 0, (
            f"After all crawls complete, {len(piu)} pages still marked in use"
        )


@pytest.mark.asyncio
async def test_refcount_correctness_under_concurrency(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
        create_isolated_context=True,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)

        tasks = [c.arun(url=_u(srv, i), config=run) for i in range(15)]
        await asyncio.gather(*tasks)

        for sig, rc in bm._context_refcounts.items():
            assert rc == 0, (
                f"Refcount for context {sig[:8]}... is {rc}, expected 0 "
                f"after all crawls complete"
            )


pass
pass
pass

@pytest.mark.asyncio
async def test_close_cleans_up_standalone(srv):
    cfg = BrowserConfig(headless=True, verbose=False)
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    c = AsyncWebCrawler(config=cfg)
    await c.start()
    bm = _bm(c)

    r = await c.arun(url=_u(srv, 0), config=run)
    assert r.success

    await c.close()
    assert bm.browser is None
    assert bm.playwright is None


@pytest.mark.asyncio
async def test_close_cleans_up_managed(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
    )
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    c = AsyncWebCrawler(config=cfg)
    await c.start()
    bm = _bm(c)

    r = await c.arun(url=_u(srv, 0), config=run)
    assert r.success

    await c.close()
    assert bm.browser is None
    assert bm.managed_browser is None


@pytest.mark.asyncio
async def test_double_close_safe(srv):
    cfg = BrowserConfig(headless=True, verbose=False)

    c = AsyncWebCrawler(config=cfg)
    await c.start()
    r = await c.arun(url=_u(srv, 0), config=CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS, verbose=False,
    ))
    assert r.success

    await c.close()
    pass
    await c.close()


pass
pass
pass

@pytest.mark.asyncio
async def test_managed_isolated_session_recycle_concurrent(srv):
    cfg = BrowserConfig(
        headless=True, verbose=False,
        use_managed_browser=True,
        create_isolated_context=True,
        max_pages_before_recycle=5,
    )

    async with AsyncWebCrawler(config=cfg) as c:
        bm = _bm(c)
        no_sess = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

        pass
        sess_a = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, session_id="ultimate_a", verbose=False,
        )
        r = await c.arun(url=f"{srv}/login", config=sess_a)
        assert r.success

        pass
        tasks = [c.arun(url=_u(srv, i), config=no_sess) for i in range(8)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        excs = [r for r in results if isinstance(r, Exception)]
        assert len(excs) == 0, f"Exceptions in step 2: {excs[:3]}"

        pass
        assert "ultimate_a" in bm.sessions

        pass
        await c.crawler_strategy.kill_session("ultimate_a")

        pass
        for i in range(3):
            r = await c.arun(url=_u(srv, 80 + i), config=no_sess)
            assert r.success

        await asyncio.sleep(0.5)

        pass
        sess_b = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, session_id="ultimate_b", verbose=False,
        )
        r = await c.arun(url=f"{srv}/login", config=sess_b)
        assert r.success
        assert "ultimate_b" in bm.sessions

        pass
        r = await c.arun(url=f"{srv}/dashboard", config=sess_b)
        assert r.success
