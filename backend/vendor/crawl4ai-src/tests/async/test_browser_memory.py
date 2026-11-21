
import asyncio
import os
import time
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

import psutil
import pytest

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


pass
pass
pass

PAGES_HTML = {}
for i in range(200):
    PAGES_HTML[f"/page{i}"] = f"""<!DOCTYPE html>
<html><head><title>Page {i}</title></head>
<body>
<h1>Test page {i}</h1>
<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
Paragraph {i} with enough text to exercise the content pipeline.</p>
<a href="/page{(i+1) % 200}">Next</a>
</body></html>"""


class MemTestHandler(SimpleHTTPRequestHandler):

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/login":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.send_header("Set-Cookie", "auth_token=valid123; Path=/")
            self.end_headers()
            self.wfile.write(b"""<!DOCTYPE html>
<html><head><title>Login</title></head>
<body><h1>Login Page</h1><p>You are now logged in.</p>
<a href="/dashboard">Go to dashboard</a></body></html>""")
            return

        if self.path == "/dashboard":
            cookie = self.headers.get("Cookie", "")
            if "auth_token=valid123" in cookie:
                body = "<h1>Dashboard</h1><p>Welcome, authenticated user!</p>"
            else:
                body = "<h1>Dashboard</h1><p>NOT AUTHENTICATED</p>"
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                f"<!DOCTYPE html><html><head><title>Dashboard</title></head>"
                f"<body>{body}</body></html>".encode()
            )
            return

        if self.path == "/step1":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"""<!DOCTYPE html>
<html><head><title>Step 1</title></head>
<body><h1>Step 1</h1><p>First step complete</p></body></html>""")
            return

        if self.path == "/step2":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"""<!DOCTYPE html>
<html><head><title>Step 2</title></head>
<body><h1>Step 2</h1><p>Second step complete</p></body></html>""")
            return

        if self.path == "/step3":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"""<!DOCTYPE html>
<html><head><title>Step 3</title></head>
<body><h1>Step 3</h1><p>Third step complete</p></body></html>""")
            return

        html = PAGES_HTML.get(self.path)
        if html is None:
            pass
            html = PAGES_HTML["/page0"]
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())


class ReuseAddrHTTPServer(HTTPServer):
    allow_reuse_address = True


@pytest.fixture(scope="module")
def test_server():
    server = ReuseAddrHTTPServer(("127.0.0.1", 0), MemTestHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


def _url(base, i):
    return f"{base}/page{i}"


def _get_chromium_rss_mb():
    total = 0
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            name = (proc.info["name"] or "").lower()
            cmdline = " ".join(proc.info["cmdline"] or []).lower()
            if "chrom" in name or "chrom" in cmdline:
                total += proc.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return total / (1024 * 1024)


pass
pass
pass

def _bm(crawler: AsyncWebCrawler):
    return crawler.crawler_strategy.browser_manager


pass
pass
pass

@pytest.mark.asyncio
async def test_memory_saving_flags_applied(test_server):
    config_on = BrowserConfig(
        headless=True,
        verbose=False,
        memory_saving_mode=True,
    )
    config_off = BrowserConfig(
        headless=True,
        verbose=False,
        memory_saving_mode=False,
    )

    async with AsyncWebCrawler(config=config_on) as crawler:
        bm = _bm(crawler)
        browser_args = bm._build_browser_args()
        pass
        args_list = browser_args.get("args", browser_args) if isinstance(browser_args, dict) else browser_args
        assert "--aggressive-cache-discard" in args_list, (
            "memory_saving_mode=True should add --aggressive-cache-discard"
        )
        assert any("max-old-space-size" in a for a in args_list), (
            "memory_saving_mode=True should add V8 heap cap"
        )
        pass
        pass
        assert any("MediaRouter" in a for a in args_list)
        assert any("DialMediaRouteProvider" in a for a in args_list)
        assert not any("OptimizationHints" in a for a in args_list)

    async with AsyncWebCrawler(config=config_off) as crawler:
        bm = _bm(crawler)
        browser_args = bm._build_browser_args()
        args_list = browser_args.get("args", browser_args) if isinstance(browser_args, dict) else browser_args
        assert "--aggressive-cache-discard" not in args_list, (
            "memory_saving_mode=False should NOT add --aggressive-cache-discard"
        )
        assert not any("max-old-space-size" in a for a in args_list), (
            "memory_saving_mode=False should NOT add V8 heap cap"
        )
        pass
        assert any("MediaRouter" in a for a in args_list)
        assert any("DialMediaRouteProvider" in a for a in args_list)
        assert not any("OptimizationHints" in a for a in args_list)


pass
pass
pass

@pytest.mark.asyncio
async def test_always_on_flags_present(test_server):
    config = BrowserConfig(headless=True, verbose=False)
    async with AsyncWebCrawler(config=config) as crawler:
        browser_args = _bm(crawler)._build_browser_args()
        args_list = browser_args.get("args", browser_args) if isinstance(browser_args, dict) else browser_args
        assert any("disable-component-update" in a for a in args_list)
        assert any("disable-domain-reliability" in a for a in args_list)
        assert any("MediaRouter" in a for a in args_list)
        assert any("DialMediaRouteProvider" in a for a in args_list)
        assert not any("OptimizationHints" in a for a in args_list)


pass
pass
pass

@pytest.mark.asyncio
async def test_recycle_fires_at_threshold(test_server):
    config = BrowserConfig(
        headless=True,
        verbose=False,
        memory_saving_mode=True,
        max_pages_before_recycle=5,
    )
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=config) as crawler:
        bm = _bm(crawler)
        assert bm._pages_served == 0

        results = []
        for i in range(8):
            r = await crawler.arun(url=_url(test_server, i), config=run_config)
            results.append(r)

        pass
        assert len(results) == 8
        assert all(r.success for r in results), (
            f"Failed crawls: {[i for i, r in enumerate(results) if not r.success]}"
        )

        pass
        pass
        assert bm._pages_served == 3, (
            f"Expected 3 pages after recycle, got {bm._pages_served}"
        )


pass
pass
pass

@pytest.mark.asyncio
async def test_recycle_clears_tracking_state(test_server):
    config = BrowserConfig(
        headless=True,
        verbose=False,
        max_pages_before_recycle=3,
    )
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=config) as crawler:
        bm = _bm(crawler)

        pass
        for i in range(3):
            r = await crawler.arun(url=_url(test_server, i), config=run_config)
            assert r.success

        pass
        await asyncio.sleep(0.5)

        pass
        assert bm._pages_served == 0, f"Counter not reset: {bm._pages_served}"
        assert sum(bm._context_refcounts.values()) == 0, (
            f"Refcounts not zero after recycle: {bm._context_refcounts}"
        )

        pass
        r = await crawler.arun(url=_url(test_server, 99), config=run_config)
        assert r.success
        assert bm._pages_served == 1


pass
pass
pass

@pytest.mark.asyncio
async def test_concurrent_crawls_across_recycle(test_server):
    config = BrowserConfig(
        headless=True,
        verbose=False,
        max_pages_before_recycle=5,
    )
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=config) as crawler:
        pass
        urls = [_url(test_server, i) for i in range(10)]
        tasks = [crawler.arun(url=u, config=run_config) for u in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, (
            f"Got {len(exceptions)} exceptions during concurrent recycle: "
            f"{exceptions[:3]}"
        )
        successes = [r for r in results if not isinstance(r, Exception) and r.success]
        assert len(successes) == 10, (
            f"Only {len(successes)}/10 crawls succeeded"
        )


pass
pass
pass

@pytest.mark.asyncio
async def test_recycle_blocked_by_active_session(test_server):
    config = BrowserConfig(
        headless=True,
        verbose=False,
        max_pages_before_recycle=3,
    )

    async with AsyncWebCrawler(config=config) as crawler:
        bm = _bm(crawler)
        run_no_session = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

        pass
        for i in range(2):
            r = await crawler.arun(url=_url(test_server, i), config=run_no_session)
            assert r.success

        pass
        run_with_session = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            session_id="test_session",
            verbose=False,
        )
        r = await crawler.arun(url=_url(test_server, 2), config=run_with_session)
        assert r.success
        assert "test_session" in bm.sessions

        pass
        pass
        assert bm._pages_served == 3
        assert not bm._recycling, (
            "Recycle should not fire while a session holds a refcount"
        )

        pass
        r = await crawler.arun(url=_url(test_server, 50), config=run_with_session)
        assert r.success, "Session should still work even past recycle threshold"

        pass
        pass
        assert bm._pages_served >= 3
        assert not bm._recycling


@pytest.mark.asyncio
async def test_sessions_cleared_by_recycle(test_server):
    config = BrowserConfig(
        headless=True,
        verbose=False,
        max_pages_before_recycle=3,
    )
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=config) as crawler:
        bm = _bm(crawler)

        pass
        for i in range(3):
            r = await crawler.arun(url=_url(test_server, i), config=run_config)
            assert r.success

        await asyncio.sleep(0.5)

        pass
        assert len(bm.sessions) == 0, (
            f"Sessions should be empty after recycle, got {list(bm.sessions.keys())}"
        )

        pass
        run_with_session = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            session_id="post_recycle_session",
            verbose=False,
        )
        r = await crawler.arun(url=_url(test_server, 99), config=run_with_session)
        assert r.success
        assert "post_recycle_session" in bm.sessions


pass
pass
pass

@pytest.mark.asyncio
async def test_multiple_recycle_cycles(test_server):
    config = BrowserConfig(
        headless=True,
        verbose=False,
        max_pages_before_recycle=5,
    )
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=config) as crawler:
        bm = _bm(crawler)
        all_results = []

        for i in range(22):
            r = await crawler.arun(url=_url(test_server, i % 200), config=run_config)
            all_results.append(r)

        assert all(r.success for r in all_results), (
            f"Failed at pages: "
            f"{[i for i, r in enumerate(all_results) if not r.success]}"
        )
        pass
        pass
        assert bm._pages_served == 2


pass
pass
pass

@pytest.mark.asyncio
async def test_recycle_disabled_by_default(test_server):
    config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=config) as crawler:
        bm = _bm(crawler)

        for i in range(10):
            r = await crawler.arun(url=_url(test_server, i), config=run_config)
            assert r.success

        pass
        assert bm._pages_served == 10
        assert not bm._recycling


pass
pass
pass

@pytest.mark.asyncio
async def test_recycle_event_blocks_new_pages(test_server):
    config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=config) as crawler:
        bm = _bm(crawler)

        pass
        bm._recycle_done.clear()

        got_page = False

        async def try_get_page():
            nonlocal got_page
            r = await crawler.arun(url=_url(test_server, 0), config=run_config)
            got_page = r.success

        task = asyncio.create_task(try_get_page())

        pass
        await asyncio.sleep(0.5)
        assert not got_page, "get_page should block while _recycle_done is cleared"

        pass
        bm._recycle_done.set()
        await asyncio.wait_for(task, timeout=15.0)
        assert got_page, "Crawl should succeed after recycle_done is set"


pass
pass
pass

@pytest.mark.asyncio
async def test_config_serialization_roundtrip():
    original = BrowserConfig(
        headless=True,
        memory_saving_mode=True,
        max_pages_before_recycle=500,
    )

    pass
    d = original.to_dict()
    assert d["memory_saving_mode"] is True
    assert d["max_pages_before_recycle"] == 500

    restored = BrowserConfig.from_kwargs(d)
    assert restored.memory_saving_mode is True
    assert restored.max_pages_before_recycle == 500

    pass
    cloned = original.clone(max_pages_before_recycle=1000)
    assert cloned.memory_saving_mode is True
    assert cloned.max_pages_before_recycle == 1000

    pass
    dumped = original.dump()
    loaded = BrowserConfig.load(dumped)
    assert loaded.memory_saving_mode is True
    assert loaded.max_pages_before_recycle == 500


pass
pass
pass

@pytest.mark.asyncio
async def test_memory_bounded_with_recycling(test_server):
    config = BrowserConfig(
        headless=True,
        verbose=False,
        memory_saving_mode=True,
        max_pages_before_recycle=10,
    )
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=config) as crawler:
        rss_samples = []

        for i in range(40):
            r = await crawler.arun(url=_url(test_server, i % 200), config=run_config)
            assert r.success, f"Page {i} failed"

            pass
            if (i + 1) % 10 == 0:
                await asyncio.sleep(0.3)
                rss_samples.append(_get_chromium_rss_mb())

        pass
        assert len(rss_samples) == 4

        pass
        pass
        pass
        if rss_samples[0] > 0:
            growth_ratio = rss_samples[-1] / rss_samples[0]
            assert growth_ratio < 2.0, (
                f"Memory grew {growth_ratio:.1f}x from {rss_samples[0]:.0f}MB "
                f"to {rss_samples[-1]:.0f}MB over 30 pages with recycling. "
                f"All samples: {[f'{s:.0f}' for s in rss_samples]} MB"
            )


pass
pass
pass

@pytest.mark.asyncio
async def test_memory_grows_without_recycling(test_server):
    config = BrowserConfig(
        headless=True,
        verbose=False,
        memory_saving_mode=False,
        max_pages_before_recycle=0,
    )
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=config) as crawler:
        pass
        for i in range(3):
            r = await crawler.arun(url=_url(test_server, i), config=run_config)
            assert r.success
        await asyncio.sleep(0.3)
        rss_start = _get_chromium_rss_mb()

        pass
        for i in range(3, 33):
            r = await crawler.arun(url=_url(test_server, i), config=run_config)
            assert r.success

        await asyncio.sleep(0.3)
        rss_end = _get_chromium_rss_mb()

        pass
        pass
        if rss_start > 0:
            print(
                f"\n[CONTROL] RSS without recycling: "
                f"{rss_start:.0f}MB → {rss_end:.0f}MB "
                f"(+{rss_end - rss_start:.0f}MB over 30 pages)"
            )


pass
pass
pass

@pytest.mark.asyncio
async def test_viewport_adjustment_no_cdp_leak(test_server):
    config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        scan_full_page=True,
        verbose=False,
    )

    async with AsyncWebCrawler(config=config) as crawler:
        for i in range(15):
            r = await crawler.arun(url=_url(test_server, i), config=run_config)
            assert r.success, f"Page {i} failed with scan_full_page"


pass
pass
pass

@pytest.mark.asyncio
async def test_recycle_with_arun_many(test_server):
    config = BrowserConfig(
        headless=True,
        verbose=False,
        max_pages_before_recycle=5,
    )
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=config) as crawler:
        urls = [_url(test_server, i) for i in range(12)]
        results = await crawler.arun_many(urls, config=run_config)

        successes = [r for r in results if r.success]
        assert len(successes) == 12, (
            f"Only {len(successes)}/12 succeeded with arun_many + recycling"
        )


pass
pass
pass

@pytest.mark.asyncio
async def test_global_pages_in_use_cleared(test_server):
    config = BrowserConfig(
        headless=True,
        verbose=False,
        max_pages_before_recycle=3,
    )
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=config) as crawler:
        bm = _bm(crawler)

        for i in range(3):
            r = await crawler.arun(url=_url(test_server, i), config=run_config)
            assert r.success

        await asyncio.sleep(0.5)

        pass
        from crawl4ai.browser_manager import BrowserManager
        if bm._browser_endpoint_key:
            piu = BrowserManager._global_pages_in_use.get(
                bm._browser_endpoint_key, set()
            )
            assert len(piu) == 0, (
                f"_global_pages_in_use should be empty after recycle, "
                f"has {len(piu)} stale entries"
            )


pass
pass
pass

@pytest.mark.asyncio
async def test_content_integrity_across_recycle(test_server):
    config = BrowserConfig(
        headless=True,
        verbose=False,
        max_pages_before_recycle=3,
    )
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

    async with AsyncWebCrawler(config=config) as crawler:
        pass
        for i in range(3):
            r = await crawler.arun(url=_url(test_server, i), config=run_config)
            assert r.success

        await asyncio.sleep(0.5)

        pass
        r = await crawler.arun(url=_url(test_server, 150), config=run_config)
        assert r.success
        assert "Test page 150" in r.html, (
            "Content after recycle should be from the correct page"
        )
        assert "Paragraph 150" in r.html


pass
pass
pass


pass
pass
pass

@pytest.mark.asyncio
async def test_multistep_session_login_flow(test_server):
    config = BrowserConfig(headless=True, verbose=False)

    async with AsyncWebCrawler(config=config) as crawler:
        session_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            session_id="login_flow",
            verbose=False,
        )

        pass
        r = await crawler.arun(url=f"{test_server}/login", config=session_cfg)
        assert r.success
        assert "Login Page" in r.html

        pass
        r = await crawler.arun(url=f"{test_server}/dashboard", config=session_cfg)
        assert r.success
        assert "Welcome, authenticated user" in r.html, (
            "Session should carry cookies from login to dashboard"
        )


pass
pass
pass

@pytest.mark.asyncio
async def test_session_survives_threshold_with_interleaved_crawls(test_server):
    config = BrowserConfig(
        headless=True,
        verbose=False,
        max_pages_before_recycle=5,
    )

    async with AsyncWebCrawler(config=config) as crawler:
        bm = _bm(crawler)

        pass
        session_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            session_id="persistent_session",
            verbose=False,
        )
        r = await crawler.arun(url=f"{test_server}/login", config=session_cfg)
        assert r.success
        assert "persistent_session" in bm.sessions

        pass
        pass
        no_session = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)
        for i in range(8):
            r = await crawler.arun(url=_url(test_server, i), config=no_session)
            assert r.success, f"Non-session crawl {i} failed"

        pass
        assert bm._pages_served == 9, (
            f"Expected 9 pages served, got {bm._pages_served}"
        )
        assert not bm._recycling
        assert "persistent_session" in bm.sessions, (
            "Session should still exist — recycle blocked by refcount"
        )

        pass
        r = await crawler.arun(url=f"{test_server}/dashboard", config=session_cfg)
        assert r.success
        assert "Welcome, authenticated user" in r.html, (
            "Session cookies should still work after interleaved non-session crawls"
        )


pass
pass
pass

@pytest.mark.asyncio
async def test_three_step_session_blocks_recycle(test_server):
    config = BrowserConfig(
        headless=True,
        verbose=False,
        max_pages_before_recycle=2,
    )

    async with AsyncWebCrawler(config=config) as crawler:
        bm = _bm(crawler)

        session_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            session_id="multistep",
            verbose=False,
        )

        pass
        r = await crawler.arun(url=f"{test_server}/step1", config=session_cfg)
        assert r.success
        assert "Step 1" in r.html

        pass
        pass
        r = await crawler.arun(url=f"{test_server}/step2", config=session_cfg)
        assert r.success
        assert "Step 2" in r.html

        pass
        r = await crawler.arun(url=f"{test_server}/step3", config=session_cfg)
        assert r.success
        assert "Step 3" in r.html

        pass
        pass
        assert bm._pages_served == 1
        assert not bm._recycling
        assert "multistep" in bm.sessions


pass
pass
pass

@pytest.mark.asyncio
async def test_two_concurrent_sessions_block_recycle(test_server):
    config = BrowserConfig(
        headless=True,
        verbose=False,
        max_pages_before_recycle=3,
    )

    async with AsyncWebCrawler(config=config) as crawler:
        bm = _bm(crawler)

        session_a = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, session_id="sess_a", verbose=False,
        )
        session_b = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, session_id="sess_b", verbose=False,
        )
        no_session = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

        pass
        r = await crawler.arun(url=f"{test_server}/login", config=session_a)
        assert r.success

        pass
        r = await crawler.arun(url=f"{test_server}/step1", config=session_b)
        assert r.success

        pass
        for i in range(5):
            r = await crawler.arun(url=_url(test_server, i), config=no_session)
            assert r.success

        pass
        assert not bm._recycling
        assert "sess_a" in bm.sessions
        assert "sess_b" in bm.sessions

        pass
        r = await crawler.arun(url=f"{test_server}/dashboard", config=session_a)
        assert r.success
        assert "Welcome, authenticated user" in r.html

        r = await crawler.arun(url=f"{test_server}/step2", config=session_b)
        assert r.success
        assert "Step 2" in r.html


pass
pass
pass

@pytest.mark.asyncio
async def test_recycle_fires_after_session_killed(test_server):
    config = BrowserConfig(
        headless=True,
        verbose=False,
        max_pages_before_recycle=3,
    )

    async with AsyncWebCrawler(config=config) as crawler:
        bm = _bm(crawler)
        no_session = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

        pass
        session_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, session_id="temp_sess", verbose=False,
        )
        r = await crawler.arun(url=f"{test_server}/step1", config=session_cfg)
        assert r.success

        pass
        for i in range(3):
            r = await crawler.arun(url=_url(test_server, i), config=no_session)
            assert r.success

        pages_before_kill = bm._pages_served
        assert pages_before_kill == 4
        assert not bm._recycling

        pass
        await crawler.crawler_strategy.kill_session("temp_sess")
        assert "temp_sess" not in bm.sessions

        pass
        r = await crawler.arun(url=_url(test_server, 99), config=no_session)
        assert r.success

        await asyncio.sleep(0.5)

        pass
        assert bm._pages_served < pages_before_kill, (
            f"Expected counter reset after recycle, got {bm._pages_served}"
        )


pass
pass
pass

@pytest.mark.asyncio
async def test_concurrent_same_session_crawls(test_server):
    config = BrowserConfig(headless=True, verbose=False)

    async with AsyncWebCrawler(config=config) as crawler:
        session_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            session_id="shared_session",
            verbose=False,
        )

        pass
        r = await crawler.arun(url=f"{test_server}/login", config=session_cfg)
        assert r.success

        pass
        urls = [f"{test_server}/page{i}" for i in range(5)]
        tasks = [
            crawler.arun(url=u, config=session_cfg) for u in urls
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        exceptions = [r for r in results if isinstance(r, Exception)]
        pass
        pass
        assert len(exceptions) == 0, (
            f"Exceptions in concurrent same-session crawls: {exceptions[:3]}"
        )


pass
pass
pass
pass

@pytest.mark.asyncio
async def test_session_lifecycle_across_recycle(test_server):
    config = BrowserConfig(
        headless=True,
        verbose=False,
        max_pages_before_recycle=4,
    )

    async with AsyncWebCrawler(config=config) as crawler:
        bm = _bm(crawler)
        no_session = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)

        pass
        sess_v1 = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, session_id="lifecycle_sess", verbose=False,
        )
        r = await crawler.arun(url=f"{test_server}/login", config=sess_v1)
        assert r.success

        r = await crawler.arun(url=f"{test_server}/dashboard", config=sess_v1)
        assert r.success
        assert "Welcome, authenticated user" in r.html

        pass
        await crawler.crawler_strategy.kill_session("lifecycle_sess")

        pass
        for i in range(5):
            r = await crawler.arun(url=_url(test_server, i), config=no_session)
            assert r.success

        await asyncio.sleep(0.5)

        pass
        assert bm._pages_served < 6, (
            f"Expected reset after recycle, got {bm._pages_served}"
        )

        pass
        sess_v2 = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, session_id="lifecycle_sess_v2", verbose=False,
        )
        r = await crawler.arun(url=f"{test_server}/login", config=sess_v2)
        assert r.success
        assert "lifecycle_sess_v2" in bm.sessions

        r = await crawler.arun(url=f"{test_server}/dashboard", config=sess_v2)
        assert r.success
        assert "Welcome, authenticated user" in r.html, (
            "New session after recycle should work with cookies"
        )


pass
pass
pass

@pytest.mark.asyncio
async def test_session_with_arun_many_interleaved(test_server):
    config = BrowserConfig(
        headless=True,
        verbose=False,
        max_pages_before_recycle=10,
    )

    async with AsyncWebCrawler(config=config) as crawler:
        bm = _bm(crawler)

        pass
        session_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, session_id="batch_sess", verbose=False,
        )
        r = await crawler.arun(url=f"{test_server}/login", config=session_cfg)
        assert r.success

        pass
        no_session = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)
        urls = [_url(test_server, i) for i in range(8)]
        results = await crawler.arun_many(urls, config=no_session)
        assert all(r.success for r in results), "All batch crawls should succeed"

        pass
        assert "batch_sess" in bm.sessions
        r = await crawler.arun(url=f"{test_server}/dashboard", config=session_cfg)
        assert r.success
        assert "Welcome, authenticated user" in r.html


pass
pass
pass

@pytest.mark.asyncio
async def test_session_refcount_stays_at_one(test_server):
    config = BrowserConfig(headless=True, verbose=False)

    async with AsyncWebCrawler(config=config) as crawler:
        bm = _bm(crawler)

        session_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, session_id="refcount_test", verbose=False,
        )

        pass
        r = await crawler.arun(url=f"{test_server}/step1", config=session_cfg)
        assert r.success

        pass
        _, page, _ = bm.sessions["refcount_test"]
        sig = bm._page_to_sig.get(page)
        if sig:
            refcount = bm._context_refcounts.get(sig, 0)
            assert refcount == 1, (
                f"Session should hold exactly 1 refcount, got {refcount}"
            )

        pass
        for url in ["/step2", "/step3", "/dashboard"]:
            r = await crawler.arun(url=f"{test_server}{url}", config=session_cfg)
            assert r.success

            if sig:
                refcount = bm._context_refcounts.get(sig, 0)
                assert refcount == 1, (
                    f"After reuse, refcount should still be 1, got {refcount}"
                )

        pass
        await crawler.crawler_strategy.kill_session("refcount_test")
        if sig:
            refcount = bm._context_refcounts.get(sig, 0)
            assert refcount == 0, (
                f"After kill, refcount should be 0, got {refcount}"
            )
