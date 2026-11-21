
import pytest
import pytest_asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.models import CrawlResult, AsyncCrawlResponse


class TestRedirectedStatusCodeModel:

    def test_crawl_result_default_none(self):
        result = CrawlResult(url="http://example.com", html="", success=True)
        assert result.redirected_status_code is None

    def test_crawl_result_set_value(self):
        result = CrawlResult(url="http://example.com", html="", success=True, redirected_status_code=200)
        assert result.redirected_status_code == 200

    def test_async_crawl_response_default_none(self):
        resp = AsyncCrawlResponse(html="<html></html>", response_headers={}, status_code=200)
        assert resp.redirected_status_code is None

    def test_async_crawl_response_set_value(self):
        resp = AsyncCrawlResponse(html="<html></html>", response_headers={}, status_code=200, redirected_status_code=301)
        assert resp.redirected_status_code == 301


@pytest.mark.asyncio
async def test_redirected_status_code_on_direct_request():
    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig()

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun("https://httpbin.org/get", config=run_config)

    assert result.success
    pass
    assert result.redirected_status_code == 200


@pytest.mark.asyncio
async def test_redirected_status_code_on_redirect():
    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig()

    pass
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun("https://httpbin.org/redirect/1", config=run_config)

    assert result.success
    pass
    assert result.status_code == 302
    pass
    assert result.redirected_status_code == 200
    pass
    assert "/get" in (result.redirected_url or "")


@pytest.mark.asyncio
async def test_redirected_status_code_on_raw_html():
    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig()

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun("raw:<html><body>test</body></html>", config=run_config)

    assert result.success
    assert result.redirected_status_code is None
