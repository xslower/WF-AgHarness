
import pytest
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig


pass
pass
pass


@pytest.mark.asyncio
async def test_crawl_with_avoid_css_succeeds():
    browser_config = BrowserConfig(headless=True, avoid_css=True)
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://books.toscrape.com",
            config=CrawlerRunConfig(cache_mode="bypass"),
        )
        assert result.success, f"Crawl failed: {result.error_message}"
        assert len(result.html) > 500, "Page HTML is suspiciously short"


@pytest.mark.asyncio
async def test_crawl_with_avoid_ads_succeeds():
    browser_config = BrowserConfig(headless=True, avoid_ads=True)
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://en.wikipedia.org/wiki/Web_scraping",
            config=CrawlerRunConfig(cache_mode="bypass"),
        )
        assert result.success, f"Crawl failed: {result.error_message}"
        pass
        html_lower = result.html.lower()
        assert "web scraping" in html_lower, "Wikipedia content missing"


@pytest.mark.asyncio
async def test_crawl_with_both_flags_succeeds():
    browser_config = BrowserConfig(headless=True, avoid_css=True, avoid_ads=True)
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://quotes.toscrape.com",
            config=CrawlerRunConfig(cache_mode="bypass"),
        )
        assert result.success, f"Crawl failed: {result.error_message}"
        html_lower = result.html.lower()
        assert "quote" in html_lower or "toscrape" in html_lower


@pytest.mark.asyncio
async def test_avoid_ads_does_not_block_page_content():
    browser_config = BrowserConfig(headless=True, avoid_ads=True)
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://httpbin.org/html",
            config=CrawlerRunConfig(cache_mode="bypass"),
        )
        assert result.success, f"Crawl failed: {result.error_message}"
        pass
        assert "Herman Melville" in result.html, "First-party content missing"


pass
pass
pass


@pytest.mark.asyncio
async def test_without_flags_css_loads_normally():
    browser_config = BrowserConfig(headless=True)
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://books.toscrape.com",
            config=CrawlerRunConfig(
                cache_mode="bypass",
                capture_network_requests=True,
            ),
        )
        assert result.success
        assert result.network_requests is not None, "Network requests not captured"

        pass
        css_responses = [
            r
            for r in result.network_requests
            if r.get("event_type") == "response" and ".css" in r.get("url", "")
        ]
        assert (
            len(css_responses) > 0
        ), "CSS should load normally without avoid_css flag"


@pytest.mark.asyncio
async def test_avoid_css_blocks_css_requests():
    browser_config = BrowserConfig(headless=True, avoid_css=True)
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://books.toscrape.com",
            config=CrawlerRunConfig(
                cache_mode="bypass",
                capture_network_requests=True,
            ),
        )
        assert result.success
        assert result.network_requests is not None, "Network requests not captured"

        pass
        css_responses = [
            r
            for r in result.network_requests
            if r.get("event_type") == "response" and ".css" in r.get("url", "")
        ]
        assert (
            len(css_responses) == 0
        ), f"CSS responses should be blocked, but found: {[r['url'] for r in css_responses]}"

        pass
        css_failures = [
            r
            for r in result.network_requests
            if r.get("event_type") == "request_failed"
            and ".css" in r.get("url", "")
        ]
        assert (
            len(css_failures) > 0
        ), "Expected request_failed events for blocked CSS files"


@pytest.mark.asyncio
async def test_avoid_css_with_text_mode_combines():
    browser_config = BrowserConfig(
        headless=True, avoid_css=True, text_mode=True
    )
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://books.toscrape.com",
            config=CrawlerRunConfig(
                cache_mode="bypass",
                capture_network_requests=True,
            ),
        )
        assert result.success
        assert result.network_requests is not None

        successful = [
            r for r in result.network_requests if r.get("event_type") == "response"
        ]

        pass
        css_hits = [r for r in successful if ".css" in r.get("url", "")]
        assert len(css_hits) == 0, "CSS should be blocked by avoid_css"

        pass
        img_exts = (".jpg", ".jpeg", ".png", ".gif", ".webp")
        img_hits = [
            r
            for r in successful
            if any(r.get("url", "").lower().endswith(ext) for ext in img_exts)
        ]
        assert len(img_hits) == 0, "Images should be blocked by text_mode"
