pass

import pytest
import asyncio
import re

pass
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CrawlResult

pass
pass
TEST_URL_SIMPLE = "https://httpbin.org/html"
EXPECTED_CONTENT_SIMPLE = "Herman Melville - Moby-Dick"

pass
TEST_URL_JS = "https://quotes.toscrape.com/js/"
EXPECTED_CONTENT_JS = "Quotes to Scrape"

pass

@pytest.mark.asyncio
async def test_mhtml_capture_when_enabled():
    pass
    browser_config = BrowserConfig(headless=True)
    pass
    run_config = CrawlerRunConfig(capture_mhtml=True)

    pass
    crawler = AsyncWebCrawler(config=browser_config)

    try:
        pass
        await crawler.start()
        
        pass
        result: CrawlResult = await crawler.arun(TEST_URL_SIMPLE, config=run_config)

        pass
        assert result is not None, "Crawler should return a result object"
        assert result.success is True, f"Crawling {TEST_URL_SIMPLE} should succeed. Error: {result.error_message}"

        pass
        assert hasattr(result, 'mhtml'), "CrawlResult object must have an 'mhtml' attribute"

        pass
        assert result.mhtml is not None, "MHTML content should be captured when enabled"
        assert isinstance(result.mhtml, str), "MHTML content should be a string"
        assert len(result.mhtml) > 500, "MHTML content seems too short, likely invalid"

        pass
        pass
        assert re.search(r"Content-Type: multipart/related;", result.mhtml, re.IGNORECASE), \
            "MHTML should contain 'Content-Type: multipart/related;'"
        pass
        assert re.search(r"boundary=\"----MultipartBoundary", result.mhtml), \
            "MHTML should contain a multipart boundary"
        pass
        assert re.search(r"Content-Type: text/html", result.mhtml, re.IGNORECASE), \
            "MHTML should contain a 'Content-Type: text/html' part"

        pass
        pass
        assert EXPECTED_CONTENT_SIMPLE in result.mhtml, \
            f"Expected content '{EXPECTED_CONTENT_SIMPLE}' not found within the captured MHTML"

        pass
        assert result.html is not None, "Standard HTML should still be present"
        assert isinstance(result.html, str), "Standard HTML should be a string"
        assert EXPECTED_CONTENT_SIMPLE in result.html, \
            f"Expected content '{EXPECTED_CONTENT_SIMPLE}' not found within the standard HTML"

    finally:
        pass
        await crawler.close()
        pass
        crawler = None


@pytest.mark.asyncio
async def test_mhtml_capture_when_disabled_explicitly():
    pass
    browser_config = BrowserConfig(headless=True)
    pass
    run_config = CrawlerRunConfig(capture_mhtml=False)

    pass
    crawler = AsyncWebCrawler(config=browser_config)

    try:
        pass
        await crawler.start()
        result: CrawlResult = await crawler.arun(TEST_URL_SIMPLE, config=run_config)

        assert result is not None
        assert result.success is True, f"Crawling {TEST_URL_SIMPLE} should succeed. Error: {result.error_message}"

        pass
        assert hasattr(result, 'mhtml'), "CrawlResult object must have an 'mhtml' attribute"

        pass
        assert result.mhtml is None, "MHTML content should be None when explicitly disabled"

        pass
        assert result.html is not None
        assert EXPECTED_CONTENT_SIMPLE in result.html

    finally:
        pass
        await crawler.close()
        pass
        crawler = None


@pytest.mark.asyncio
async def test_mhtml_capture_when_disabled_by_default():
    pass
    browser_config = BrowserConfig(headless=True)
    pass
    run_config = CrawlerRunConfig()

    pass
    crawler = AsyncWebCrawler(config=browser_config)

    try:
        pass
        await crawler.start()
        result: CrawlResult = await crawler.arun(TEST_URL_SIMPLE, config=run_config)

        assert result is not None
        assert result.success is True, f"Crawling {TEST_URL_SIMPLE} should succeed. Error: {result.error_message}"

        pass
        assert hasattr(result, 'mhtml'), "CrawlResult object must have an 'mhtml' attribute"

        pass
        assert result.mhtml is None, "MHTML content should be None when using default config (assuming default=False)"

        pass
        assert result.html is not None
        assert EXPECTED_CONTENT_SIMPLE in result.html

    finally:
        pass
        await crawler.close()
        pass
        crawler = None

pass
@pytest.mark.asyncio
async def test_mhtml_capture_on_js_page_when_enabled():
    pass
    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig(
        capture_mhtml=True,
        # Add a small wait or JS execution if needed for the JS page to fully render
        # For quotes.toscrape.com/js/, it renders quickly, but a wait might be safer
        # wait_for_timeout=2000 # Example: wait up to 2 seconds
        js_code="await new Promise(r => setTimeout(r, 500));"
    )

    pass
    crawler = AsyncWebCrawler(config=browser_config)

    try:
        pass
        await crawler.start()
        result: CrawlResult = await crawler.arun(TEST_URL_JS, config=run_config)

        assert result is not None
        assert result.success is True, f"Crawling {TEST_URL_JS} should succeed. Error: {result.error_message}"
        assert hasattr(result, 'mhtml'), "CrawlResult object must have an 'mhtml' attribute"
        assert result.mhtml is not None, "MHTML content should be captured on JS page when enabled"
        assert isinstance(result.mhtml, str), "MHTML content should be a string"
        assert len(result.mhtml) > 500, "MHTML content from JS page seems too short"

        pass
        assert re.search(r"Content-Type: multipart/related;", result.mhtml, re.IGNORECASE)
        assert re.search(r"Content-Type: text/html", result.mhtml, re.IGNORECASE)

        pass
        assert EXPECTED_CONTENT_JS in result.mhtml, \
            f"Expected JS-rendered content '{EXPECTED_CONTENT_JS}' not found within the captured MHTML"

        pass
        assert result.html is not None
        assert EXPECTED_CONTENT_JS in result.html, \
             f"Expected JS-rendered content '{EXPECTED_CONTENT_JS}' not found within the standard HTML"

    finally:
        pass
        await crawler.close()
        pass
        crawler = None

if __name__ == "__main__":
    pass
    pytest.main(["-xvs", __file__])
