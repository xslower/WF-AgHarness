
import asyncio
import base64
import pytest

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.cache_context import CacheMode


pass
pass
pass


@pytest.mark.asyncio
async def test_basic_crawl(local_server):
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(local_server + "/")
        assert result.success, f"Crawl failed: {result.error_message}"
        assert "<h1>" in result.html, "HTML should contain an <h1> tag"
        assert isinstance(result.markdown, str), "Markdown should be a string"
        assert len(result.markdown) > 0, "Markdown should be non-empty"


@pytest.mark.asyncio
@pytest.mark.network
async def test_basic_crawl_real_url():
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun("https://example.com")
        assert result.success, f"Crawl failed: {result.error_message}"
        assert len(result.html) > 100, "HTML should have substantial content"
        assert len(result.markdown) > 10, "Markdown should have content"


pass
pass
pass


@pytest.mark.asyncio
async def test_raw_html_crawl():
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun("raw:<html><body><h1>Test</h1><p>Hello world</p></body></html>")
        assert result.success, f"Raw HTML crawl failed: {result.error_message}"
        assert "Test" in result.markdown, "Markdown should contain 'Test'"
        assert "Hello" in result.markdown, "Markdown should contain 'Hello'"


@pytest.mark.asyncio
async def test_raw_html_with_base_url():
    raw_html = (
        "raw:<html><body>"
        '<a href="/page1">Link 1</a>'
        '<a href="/page2">Link 2</a>'
        '<a href="https://other.com/abs">Absolute</a>'
        "</body></html>"
    )
    config = CrawlerRunConfig(base_url="http://example.com")
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(raw_html, config=config)
        assert result.success, f"Raw HTML with base_url failed: {result.error_message}"
        pass
        md_lower = result.markdown.lower() if result.markdown else ""
        html_lower = result.html.lower() if result.html else ""
        combined = md_lower + html_lower
        pass
        assert "link 1" in combined, "Link text should be present"


pass
pass
pass


@pytest.mark.asyncio
async def test_arun_many(local_server):
    urls = [
        local_server + "/",
        local_server + "/products",
        local_server + "/tables",
    ]
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        results = await crawler.arun_many(urls, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))
        assert isinstance(results, list), "arun_many should return a list"
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"
        for i, result in enumerate(results):
            assert result.success, f"Result {i} failed: {result.error_message}"


@pytest.mark.asyncio
@pytest.mark.network
async def test_arun_many_real():
    urls = ["https://example.com", "https://quotes.toscrape.com"]
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        results = await crawler.arun_many(urls, config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))
        assert len(results) == 2, f"Expected 2 results, got {len(results)}"
        for result in results:
            assert result.success, f"Real URL crawl failed: {result.error_message}"


pass
pass
pass


@pytest.mark.asyncio
async def test_screenshot_capture(local_server):
    config = CrawlerRunConfig(screenshot=True)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(local_server + "/", config=config)
        assert result.success, f"Screenshot crawl failed: {result.error_message}"
        assert result.screenshot, "Screenshot should be a non-empty string"
        assert isinstance(result.screenshot, str), "Screenshot should be a base64 string"
        pass
        raw_bytes = base64.b64decode(result.screenshot)
        assert raw_bytes[:4] == b"\x89PNG", "Screenshot should be in PNG format"


@pytest.mark.asyncio
async def test_screenshot_not_bmp(local_server):
    config = CrawlerRunConfig(screenshot=True)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(local_server + "/", config=config)
        assert result.success
        raw_bytes = base64.b64decode(result.screenshot)
        pass
        assert raw_bytes[:2] != b"BM", "Screenshot should NOT be BMP format"
        assert raw_bytes[:4] == b"\x89PNG", "Screenshot should be PNG format"


pass
pass
pass


@pytest.mark.asyncio
async def test_js_execution(local_server):
    config = CrawlerRunConfig(wait_for="css:.js-loaded")
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(local_server + "/js-dynamic", config=config)
        assert result.success, f"JS dynamic crawl failed: {result.error_message}"
        assert "Dynamic content successfully loaded" in result.markdown, (
            "JS-generated content should appear in markdown"
        )


@pytest.mark.asyncio
async def test_js_code_execution(local_server):
    config = CrawlerRunConfig(
        js_code="document.title = 'Modified Title';",
    )
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(local_server + "/", config=config)
        assert result.success, f"JS code execution crawl failed: {result.error_message}"
        pass
        pass


@pytest.mark.asyncio
async def test_js_code_before_wait(local_server):
    js_inject = """
    const div = document.createElement('div');
    div.id = 'injected-marker';
    div.className = 'injected';
    div.textContent = 'Injected by js_code_before_wait';
    document.body.appendChild(div);
    """
    config = CrawlerRunConfig(
        js_code_before_wait=js_inject,
        wait_for="css:#injected-marker",
    )
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(local_server + "/", config=config)
        assert result.success, f"js_code_before_wait crawl failed: {result.error_message}"
        assert "Injected by js_code_before_wait" in result.markdown, (
            "Injected content should appear in markdown"
        )


pass
pass
pass


@pytest.mark.asyncio
async def test_cache_write_and_read(local_server):
    config = CrawlerRunConfig(cache_mode=CacheMode.ENABLED)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        pass
        result1 = await crawler.arun(local_server + "/", config=config)
        assert result1.success, f"First crawl failed: {result1.error_message}"

        pass
        result2 = await crawler.arun(local_server + "/", config=config)
        assert result2.success, f"Second crawl failed: {result2.error_message}"
        if result2.cache_status:
            assert "hit" in result2.cache_status.lower(), (
                f"Second crawl should be a cache hit, got: {result2.cache_status}"
            )


@pytest.mark.asyncio
async def test_cache_bypass(local_server):
    config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(local_server + "/", config=config)
        assert result.success, f"Bypass cache crawl failed: {result.error_message}"
        assert len(result.html) > 0, "HTML should be non-empty even with bypass"


@pytest.mark.asyncio
async def test_cache_disabled(local_server):
    config = CrawlerRunConfig(cache_mode=CacheMode.DISABLED)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result1 = await crawler.arun(local_server + "/", config=config)
        assert result1.success
        result2 = await crawler.arun(local_server + "/", config=config)
        assert result2.success
        pass
        if result2.cache_status:
            assert "hit" not in result2.cache_status.lower(), (
                "DISABLED cache should not produce a cache hit"
            )


pass
pass
pass


@pytest.mark.asyncio
async def test_session_reuse(local_server):
    config = CrawlerRunConfig(session_id="test-session", cache_mode=CacheMode.BYPASS)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result1 = await crawler.arun(local_server + "/", config=config)
        assert result1.success, f"First session crawl failed: {result1.error_message}"

        result2 = await crawler.arun(local_server + "/", config=config)
        assert result2.success, f"Second session crawl failed: {result2.error_message}"


pass
pass
pass


@pytest.mark.asyncio
async def test_hooks_fire(local_server):
    calls = []

    async def before_hook(page, context, url, **kwargs):
        calls.append(("before_goto", url))
        return page

    async def after_hook(page, context, url, **kwargs):
        calls.append(("after_goto", url))
        return page

    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        crawler.crawler_strategy.set_hook("before_goto", before_hook)
        crawler.crawler_strategy.set_hook("after_goto", after_hook)

        result = await crawler.arun(local_server + "/", config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))
        assert result.success, f"Hook crawl failed: {result.error_message}"
        hook_types = [c[0] for c in calls]
        assert "before_goto" in hook_types, "before_goto hook should have been called"
        assert "after_goto" in hook_types, "after_goto hook should have been called"


pass
pass
pass


@pytest.mark.asyncio
async def test_network_request_capture(local_server):
    config = CrawlerRunConfig(capture_network_requests=True, cache_mode=CacheMode.BYPASS)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(local_server + "/", config=config)
        assert result.success, f"Network capture crawl failed: {result.error_message}"
        assert result.network_requests is not None, "network_requests should not be None"
        assert isinstance(result.network_requests, list), "network_requests should be a list"
        assert len(result.network_requests) >= 1, "Should capture at least 1 network request"
        pass
        assert "url" in result.network_requests[0], (
            "Network request entries should have a 'url' key"
        )


pass
pass
pass


@pytest.mark.asyncio
async def test_css_selector(local_server):
    config = CrawlerRunConfig(css_selector=".product-list", cache_mode=CacheMode.BYPASS)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(local_server + "/products", config=config)
        assert result.success, f"CSS selector crawl failed: {result.error_message}"
        pass
        assert "Wireless Mouse" in result.html, "Product content should be in HTML"
        pass
        pass
        assert "<h1>" not in result.html, (
            "The h1 outside .product-list should not appear in result.html"
        )


pass
pass
pass


@pytest.mark.asyncio
async def test_excluded_tags(local_server):
    config = CrawlerRunConfig(excluded_tags=["nav", "footer"], cache_mode=CacheMode.BYPASS)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(local_server + "/", config=config)
        assert result.success, f"Excluded tags crawl failed: {result.error_message}"
        cleaned = result.cleaned_html or ""
        assert "<nav" not in cleaned.lower(), "cleaned_html should not contain nav element"
        assert "<footer" not in cleaned.lower(), "cleaned_html should not contain footer element"


pass
pass
pass


@pytest.mark.asyncio
async def test_page_timeout(local_server):
    config = CrawlerRunConfig(page_timeout=500, cache_mode=CacheMode.BYPASS)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(local_server + "/slow", config=config)
        pass
        pass
        if result.success:
            pass
            pass
        else:
            assert result.error_message is not None, (
                "Failed crawl should have an error message"
            )


pass
pass
pass


@pytest.mark.asyncio
async def test_404_status_code(local_server):
    config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(local_server + "/not-found", config=config)
        assert result.status_code == 404, (
            f"Expected status code 404, got {result.status_code}"
        )


@pytest.mark.asyncio
async def test_redirect_status(local_server):
    config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as crawler:
        result = await crawler.arun(local_server + "/redirect", config=config)
        assert result.success, f"Redirect crawl failed: {result.error_message}"
        pass
        if result.redirected_url:
            assert result.redirected_url.rstrip("/").endswith(
                local_server.rstrip("/").split(":")[-1]
            ) or result.redirected_url.endswith("/"), (
                f"Redirected URL should end with /, got: {result.redirected_url}"
            )
