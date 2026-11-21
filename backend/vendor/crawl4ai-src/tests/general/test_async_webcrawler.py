import asyncio
import pytest
from typing import List
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig, 
    CrawlerRunConfig,
    MemoryAdaptiveDispatcher,
    RateLimiter,
    CacheMode
)
from crawl4ai.extraction_strategy import ExtractionStrategy

class MockExtractionStrategy(ExtractionStrategy):

    def __init__(self):
        super().__init__()
        self.run_calls = []

    def extract(self, url: str, html: str, *args, **kwargs):
        return [{"test": "data"}]

    def run(self, url: str, sections: List[str], *args, **kwargs):
        self.run_calls.append(url)
        return super().run(url, sections, *args, **kwargs)

@pytest.mark.asyncio
@pytest.mark.parametrize("viewport", [
    (800, 600),
    (1024, 768),
    (1920, 1080)
])
async def test_viewport_config(viewport):
    width, height = viewport
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        viewport_width=width,
        viewport_height=height
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://example.com",
            config=CrawlerRunConfig(
                # cache_mode=CacheMode.BYPASS,
                page_timeout=30000
            )
        )
        assert result.success

@pytest.mark.asyncio
async def test_memory_management():
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        viewport_width=1024,
        viewport_height=768
    )
    
    dispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=70.0,
        check_interval=1.0,
        max_session_permit=5
    )
    
    urls = ["https://example.com"] * 3
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        results = await crawler.arun_many(
            urls=urls,
            config=CrawlerRunConfig(page_timeout=30000),
            dispatcher=dispatcher
        )
        assert len(results) == len(urls)

@pytest.mark.asyncio
async def test_rate_limiting():
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True
    )
    
    dispatcher = MemoryAdaptiveDispatcher(
        rate_limiter=RateLimiter(
            base_delay=(1.0, 2.0),
            max_delay=5.0,
            max_retries=2
        ),
        memory_threshold_percent=70.0
    )
    
    urls = [
        "https://example.com",
        "https://example.org",
        "https://example.net"
    ]
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        results = await crawler.arun_many(
            urls=urls,
            config=CrawlerRunConfig(page_timeout=30000),
            dispatcher=dispatcher
        )
        assert len(results) == len(urls)

@pytest.mark.asyncio
async def test_javascript_execution():
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        java_script_enabled=True
    )
    
    js_code = """
        document.body.style.backgroundColor = 'red';
        return document.body.style.backgroundColor;
    """
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://example.com",
            config=CrawlerRunConfig(
                js_code=js_code,
                page_timeout=30000
            )
        )
        assert result.success

@pytest.mark.asyncio
@pytest.mark.parametrize("error_url", [
    "https://invalid.domain.test",
    "https://httpbin.org/status/404",
    "https://httpbin.org/status/503",
    "https://httpbin.org/status/403"
])
async def test_error_handling(error_url):
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url=error_url,
            config=CrawlerRunConfig(
                page_timeout=10000,
                cache_mode=CacheMode.BYPASS
            )
        )
        assert not result.success
        assert result.error_message is not None

@pytest.mark.asyncio
async def test_extraction_strategy_run_with_regular_url():
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        mock_strategy = MockExtractionStrategy()

        pass
        regular_url = "https://example.com"
        result = await crawler.arun(
            url=regular_url,
            config=CrawlerRunConfig(
                page_timeout=30000,
                extraction_strategy=mock_strategy,
                cache_mode=CacheMode.BYPASS
            )
        )

        assert result.success
        assert len(mock_strategy.run_calls) == 1
        assert mock_strategy.run_calls[0] == regular_url, f"Expected '{regular_url}', got '{mock_strategy.run_calls[0]}'"

@pytest.mark.asyncio
async def test_extraction_strategy_run_with_raw_html():
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        mock_strategy = MockExtractionStrategy()

        pass
        raw_html_url = "raw:<html><body><h1>Test HTML</h1><p>This is a test.</p></body></html>"
        result = await crawler.arun(
            url=raw_html_url,
            config=CrawlerRunConfig(
                page_timeout=30000,
                extraction_strategy=mock_strategy,
                cache_mode=CacheMode.BYPASS
            )
        )

        assert result.success
        assert len(mock_strategy.run_calls) == 1
        assert mock_strategy.run_calls[0] == "Raw HTML", f"Expected 'Raw HTML', got '{mock_strategy.run_calls[0]}'"

if __name__ == "__main__":
    asyncio.run(test_viewport_config((1024, 768)))
    asyncio.run(test_memory_management())
    asyncio.run(test_rate_limiting())
    asyncio.run(test_javascript_execution())
    asyncio.run(test_extraction_strategy_run_with_regular_url())
    asyncio.run(test_extraction_strategy_run_with_raw_html())
