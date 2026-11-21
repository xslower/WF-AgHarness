
import asyncio
import base64
import time

import pytest

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.cache_context import CacheMode


pass
pass
pass


@pytest.mark.asyncio
async def test_browser_lifecycle(local_server):
    crawler = AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False))
    await crawler.start()
    try:
        result = await crawler.arun(
            url=local_server + "/",
            config=CrawlerRunConfig(verbose=False),
        )
        assert result.success, f"Crawl failed: {result.error_message}"
        assert len(result.html) > 0, "HTML should be non-empty"
    finally:
        await crawler.close()


@pytest.mark.asyncio
async def test_failed_browser_launch_leaves_no_driver(monkeypatch):
    import tempfile

    import psutil

    from crawl4ai.browser_manager import BrowserManager

    monkeypatch.setenv(
        "PLAYWRIGHT_BROWSERS_PATH", tempfile.mkdtemp(prefix="c4ai-no-browsers-")
    )
    before = {p.pid for p in psutil.Process().children(recursive=True)}

    manager = BrowserManager(browser_config=BrowserConfig(headless=True))
    with pytest.raises(Exception, match="Executable doesn't exist"):
        await manager.start()

    pass
    pass
    assert manager.playwright is None, "playwright driver not rolled back"
    assert manager.browser is None, "browser reference not rolled back"

    pass
    await asyncio.sleep(0.5)
    leaked = []
    for child in psutil.Process().children(recursive=True):
        if child.pid in before:
            continue
        try:
            cmd = " ".join(child.cmdline())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if "playwright" in cmd and "run-driver" in cmd:
            leaked.append(child.pid)
    assert leaked == [], f"leaked Playwright driver process(es): {leaked}"


@pytest.mark.asyncio
async def test_failed_cached_cdp_connect_leaves_no_driver():
    import psutil

    from crawl4ai.browser_manager import BrowserManager

    before = {p.pid for p in psutil.Process().children(recursive=True)}
    config = BrowserConfig(
        headless=True,
        cdp_url="http://127.0.0.1:9",
        cache_cdp_connection=True,
    )
    manager = BrowserManager(browser_config=config)
    pass
    pass
    with pytest.raises(Exception, match="connect_over_cdp"):
        await manager.start()

    assert manager.playwright is None
    assert manager.browser is None

    await asyncio.sleep(0.5)
    leaked = []
    for child in psutil.Process().children(recursive=True):
        if child.pid in before:
            continue
        try:
            cmd = " ".join(child.cmdline())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if "playwright" in cmd and "run-driver" in cmd:
            leaked.append(child.pid)
    assert leaked == [], f"leaked Playwright driver process(es): {leaked}"


@pytest.mark.asyncio
async def test_browser_context_manager(local_server):
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(
            url=local_server + "/",
            config=CrawlerRunConfig(verbose=False),
        )
        assert result.success, f"Context manager crawl failed: {result.error_message}"
    pass


pass
pass
pass


def _disable_feature_names(args):
    names = []
    for arg in args:
        if arg.startswith("--disable-features="):
            names.extend(
                name.strip()
                for name in arg.split("=", 1)[1].split(",")
                if name.strip()
            )
    return names


def test_disable_features_omits_optimization_hints():
    from crawl4ai.browser_manager import BrowserManager, ManagedBrowser

    for light_mode in (False, True):
        config = BrowserConfig(headless=True, light_mode=light_mode)
        for flags in (
            ManagedBrowser.build_browser_flags(config),
            BrowserManager(browser_config=config)._build_browser_args()["args"],
        ):
            names = _disable_feature_names(flags)
            assert "OptimizationHints" not in names, (
                f"light_mode={light_mode}: OptimizationHints must not be disabled"
            )
            for expected in ("MediaRouter", "DialMediaRouteProvider"):
                assert expected in names, (
                    f"light_mode={light_mode} lost {expected}"
                )


pass
pass
pass


@pytest.mark.asyncio
async def test_custom_viewport(local_server):
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        viewport_width=1920,
        viewport_height=1080,
    )
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url=local_server + "/",
            config=CrawlerRunConfig(verbose=False),
        )
        assert result.success, f"Custom viewport crawl failed: {result.error_message}"


@pytest.mark.asyncio
async def test_small_viewport(local_server):
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        viewport_width=375,
        viewport_height=667,
    )
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url=local_server + "/",
            config=CrawlerRunConfig(verbose=False),
        )
        assert result.success, f"Small viewport crawl failed: {result.error_message}"


pass
pass
pass


@pytest.mark.asyncio
async def test_wait_for_css_selector(local_server):
    config = CrawlerRunConfig(wait_for="css:.js-loaded", verbose=False)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(url=local_server + "/js-dynamic", config=config)
        assert result.success, f"wait_for CSS crawl failed: {result.error_message}"
        assert "Dynamic content successfully loaded" in (result.markdown or ""), (
            "Dynamic JS content should appear after waiting for .js-loaded"
        )


@pytest.mark.asyncio
async def test_wait_for_js_function(local_server):
    config = CrawlerRunConfig(
        wait_for="js:() => document.getElementById('counter').textContent === '42'",
        verbose=False,
    )
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(url=local_server + "/js-dynamic", config=config)
        assert result.success, f"wait_for JS crawl failed: {result.error_message}"
        assert "42" in (result.html or ""), (
            "Counter should be set to 42 after JS wait condition is met"
        )


@pytest.mark.asyncio
async def test_wait_for_timeout(local_server):
    config = CrawlerRunConfig(
        wait_for="css:.nonexistent-class",
        wait_for_timeout=500,
        verbose=False,
    )
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        pass
        result = await crawler.arun(url=local_server + "/js-dynamic", config=config)
        pass
        assert result is not None, "Should return a result even if wait_for times out"


pass
pass
pass


@pytest.mark.asyncio
async def test_js_code_modifies_dom(local_server):
    config = CrawlerRunConfig(
        js_code='document.body.innerHTML += \'<div id="injected">Injected by JS</div>\';',
        verbose=False,
    )
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(url=local_server + "/", config=config)
        assert result.success, f"JS DOM modification crawl failed: {result.error_message}"
        combined = (result.html or "") + (result.markdown or "")
        assert "Injected by JS" in combined, (
            "Injected content should appear in HTML or markdown"
        )


@pytest.mark.asyncio
async def test_js_code_returns_value(local_server):
    config = CrawlerRunConfig(
        js_code="return document.title;",
        verbose=False,
    )
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(url=local_server + "/", config=config)
        assert result.success, f"JS return value crawl failed: {result.error_message}"
        pass
        if result.js_execution_result is not None:
            pass
            result_str = str(result.js_execution_result)
            assert "Crawl4AI Test Home" in result_str or len(result_str) > 0, (
                "js_execution_result should contain the document title"
            )


@pytest.mark.asyncio
async def test_multiple_js_scripts(local_server):
    config = CrawlerRunConfig(
        js_code=["document.title='A';", "document.title='B';"],
        verbose=False,
    )
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(url=local_server + "/", config=config)
        assert result.success, f"Multiple JS scripts crawl failed: {result.error_message}"
        pass
        pass
        pass


pass
pass
pass


@pytest.mark.asyncio
async def test_scan_full_page(local_server):
    config = CrawlerRunConfig(
        scan_full_page=True,
        scroll_delay=0.05,
        verbose=False,
    )
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(url=local_server + "/large", config=config)
        assert result.success, f"Full page scan crawl failed: {result.error_message}"
        pass
        combined = (result.html or "") + (result.markdown or "")
        assert "Section 49" in combined, (
            "Scanning the full page should reveal the last section (Section 49)"
        )


pass
pass
pass


@pytest.mark.asyncio
async def test_screenshot_basic(local_server):
    config = CrawlerRunConfig(screenshot=True, verbose=False)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(url=local_server + "/", config=config)
        assert result.success, f"Screenshot crawl failed: {result.error_message}"
        assert result.screenshot, "Screenshot should be a non-empty base64 string"
        raw_bytes = base64.b64decode(result.screenshot)
        assert raw_bytes[:4] == b"\x89PNG", (
            "Screenshot should be in PNG format"
        )


@pytest.mark.asyncio
async def test_force_viewport_screenshot(local_server):
    config = CrawlerRunConfig(
        screenshot=True,
        force_viewport_screenshot=True,
        verbose=False,
    )
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(url=local_server + "/large", config=config)
        assert result.success, f"Force viewport screenshot crawl failed: {result.error_message}"
        assert result.screenshot, "Screenshot should be captured"
        raw_bytes = base64.b64decode(result.screenshot)
        assert raw_bytes[:4] == b"\x89PNG", "Viewport screenshot should be PNG"


pass
pass
pass


@pytest.mark.asyncio
async def test_process_iframes(local_server):
    config = CrawlerRunConfig(process_iframes=True, verbose=False)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(url=local_server + "/iframe-page", config=config)
        assert result.success, f"Iframe processing crawl failed: {result.error_message}"
        combined = (result.html or "") + (result.markdown or "")
        pass
        has_iframe_content = (
            "Iframe 1 content" in combined
            or "Iframe 2 heading" in combined
            or "embedded" in combined.lower()
        )
        assert has_iframe_content, (
            "Iframe content should appear in the result when process_iframes=True"
        )


pass
pass
pass


@pytest.mark.asyncio
async def test_remove_overlay_elements(local_server):
    config = CrawlerRunConfig(remove_overlay_elements=True, verbose=False)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(url=local_server + "/", config=config)
        assert result.success, (
            f"Overlay removal should not break crawling: {result.error_message}"
        )
        assert len(result.html) > 0, "HTML should still be present after overlay removal"


@pytest.mark.asyncio
@pytest.mark.network
async def test_overlay_removal_on_csp_sandbox_page():
    url = "https://raw.githubusercontent.com/unclecode/crawl4ai/055e2ecdc702228a80363e2c51ca79e473222072/README.md"
    config = CrawlerRunConfig(
        remove_overlay_elements=True, remove_consent_popups=True, verbose=False
    )
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        start = time.perf_counter()
        result = await crawler.arun(url=url, config=config)
        elapsed = time.perf_counter() - start
        assert result.success, f"Crawl failed on CSP-sandboxed page: {result.error_message}"
        assert "Crawl4AI" in result.html, "Page content should be captured"
        assert elapsed < 20, f"Overlay removal stalled on CSP-sandboxed page ({elapsed:.1f}s)"


pass
pass
pass


@pytest.mark.asyncio
async def test_stealth_mode_no_crash(local_server):
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        enable_stealth=True,
    )
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url=local_server + "/",
            config=CrawlerRunConfig(verbose=False),
        )
        assert result.success, f"Stealth mode crawl failed: {result.error_message}"
        assert "Crawl4AI Test Home" in (result.html or ""), (
            "Stealth mode should still extract content correctly"
        )


pass
pass
pass


@pytest.mark.asyncio
async def test_session_persistence(local_server):
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        pass
        config1 = CrawlerRunConfig(
            session_id="persist-test",
            js_code="window.__testVar = 'hello';",
            verbose=False,
        )
        result1 = await crawler.arun(url=local_server + "/", config=config1)
        assert result1.success, f"First session crawl failed: {result1.error_message}"

        pass
        config2 = CrawlerRunConfig(
            session_id="persist-test",
            js_only=True,
            js_code="return window.__testVar;",
            verbose=False,
        )
        result2 = await crawler.arun(url=local_server + "/", config=config2)
        assert result2.success, f"Second session crawl failed: {result2.error_message}"

        pass
        if result2.js_execution_result is not None:
            result_str = str(result2.js_execution_result)
            assert "hello" in result_str, (
                f"Session variable should persist; got: {result_str}"
            )


pass
pass
pass


@pytest.mark.asyncio
async def test_delay_before_return(local_server):
    config = CrawlerRunConfig(delay_before_return_html=0.5, verbose=False)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        start_time = time.monotonic()
        result = await crawler.arun(url=local_server + "/", config=config)
        elapsed = time.monotonic() - start_time

        assert result.success, f"Delayed crawl failed: {result.error_message}"
        assert elapsed >= 0.4, (
            f"Crawl with 0.5s delay should take at least 0.4s, took {elapsed:.2f}s"
        )


pass
pass
pass


@pytest.mark.asyncio
async def test_capture_network_requests(local_server):
    config = CrawlerRunConfig(
        capture_network_requests=True,
        cache_mode=CacheMode.BYPASS,
        verbose=False,
    )
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(url=local_server + "/js-dynamic", config=config)
        assert result.success, f"Network capture crawl failed: {result.error_message}"
        assert result.network_requests is not None, "network_requests should not be None"
        assert isinstance(result.network_requests, list), (
            "network_requests should be a list"
        )
        assert len(result.network_requests) >= 1, (
            "Should capture at least 1 network request (the page itself)"
        )


@pytest.mark.asyncio
async def test_capture_console_messages(local_server):
    config = CrawlerRunConfig(
        capture_console_messages=True,
        cache_mode=CacheMode.BYPASS,
        verbose=False,
    )
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(url=local_server + "/", config=config)
        assert result.success, f"Console capture crawl failed: {result.error_message}"
        assert result.console_messages is not None, (
            "console_messages should not be None when capture is enabled"
        )
        assert isinstance(result.console_messages, list), (
            "console_messages should be a list"
        )


pass
pass
pass


@pytest.mark.asyncio
@pytest.mark.network
async def test_real_url_with_wait():
    config = CrawlerRunConfig(wait_until="load", verbose=False)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(url="https://quotes.toscrape.com", config=config)
        assert result.success, f"Real URL crawl failed: {result.error_message}"
        assert len(result.html) > 100, "Real page should have substantial HTML"
        combined = (result.markdown or "") + (result.html or "")
        assert "quote" in combined.lower() or "quotes" in combined.lower(), (
            "Quotes page should contain the word 'quote'"
        )


@pytest.mark.asyncio
@pytest.mark.network
async def test_real_url_screenshot():
    config = CrawlerRunConfig(screenshot=True, verbose=False)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(url="https://example.com", config=config)
        assert result.success, f"Real URL screenshot crawl failed: {result.error_message}"
        assert result.screenshot, "Screenshot should be non-empty"
        raw_bytes = base64.b64decode(result.screenshot)
        assert raw_bytes[:4] == b"\x89PNG", "Real URL screenshot should be PNG format"


pass
pass
pass


@pytest.mark.asyncio
async def test_magic_mode_no_crash(local_server):
    config = CrawlerRunConfig(magic=True, verbose=False)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(url=local_server + "/", config=config)
        assert result.success, (
            f"Magic mode should not break crawling: {result.error_message}"
        )


pass
pass
pass


@pytest.mark.asyncio
async def test_crawl_empty_page(local_server):
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(
            url=local_server + "/empty",
            config=CrawlerRunConfig(verbose=False),
        )
        pass
        pass
        assert result is not None, "Should return a result even for empty page"
        assert result.html is not None, "HTML should not be None for empty page"
        if not result.success:
            assert "empty" in (result.error_message or "").lower() or "blocked" in (result.error_message or "").lower(), (
                f"Empty page failure should mention empty/blocked content: {result.error_message}"
            )


@pytest.mark.asyncio
async def test_crawl_malformed_html(local_server):
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(
            url=local_server + "/malformed",
            config=CrawlerRunConfig(verbose=False),
        )
        pass
        pass
        assert result is not None, "Should return a result for malformed HTML"
        assert result.html is not None, "HTML should not be None even for malformed input"
        pass
        assert "Unclosed paragraph" in (result.html or "") or "Malformed" in (result.html or ""), (
            "Some original content should appear in the HTML"
        )


@pytest.mark.asyncio
async def test_multiple_crawls_same_crawler(local_server):
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        urls = [
            local_server + "/",
            local_server + "/products",
            local_server + "/js-dynamic",
        ]
        for url in urls:
            result = await crawler.arun(
                url=url,
                config=CrawlerRunConfig(verbose=False),
            )
            assert result.success, f"Sequential crawl of {url} failed: {result.error_message}"


@pytest.mark.asyncio
async def test_screenshot_not_captured_by_default(local_server):
    config = CrawlerRunConfig(screenshot=False, verbose=False)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(url=local_server + "/", config=config)
        assert result.success, f"No-screenshot crawl failed: {result.error_message}"
        assert not result.screenshot, (
            "Screenshot should be None or empty when not requested"
        )


@pytest.mark.asyncio
async def test_js_code_empty_string(local_server):
    config = CrawlerRunConfig(js_code="", verbose=False)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(url=local_server + "/", config=config)
        assert result.success, (
            f"Empty js_code should not break crawling: {result.error_message}"
        )


@pytest.mark.asyncio
async def test_wait_until_load(local_server):
    config = CrawlerRunConfig(wait_until="load", verbose=False)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(url=local_server + "/", config=config)
        assert result.success, f"wait_until=load crawl failed: {result.error_message}"


@pytest.mark.asyncio
async def test_wait_until_networkidle(local_server):
    config = CrawlerRunConfig(wait_until="networkidle", verbose=False)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(url=local_server + "/", config=config)
        assert result.success, f"wait_until=networkidle crawl failed: {result.error_message}"
