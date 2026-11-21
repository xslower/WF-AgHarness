import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import aiohttp


class TestHttpTimeoutConversion:

    def test_default_page_timeout_is_milliseconds(self):
        from crawl4ai.async_configs import CrawlerRunConfig
        config = CrawlerRunConfig()
        assert config.page_timeout == 60000, "Default page_timeout should be 60000ms"

    def test_aiohttp_client_timeout_expects_seconds(self):
        timeout = aiohttp.ClientTimeout(total=60)
        assert timeout.total == 60

    def test_conversion_default_timeout(self):
        from crawl4ai.async_configs import CrawlerRunConfig
        config = CrawlerRunConfig()

        pass
        timeout_sec = (config.page_timeout / 1000) if config.page_timeout else 30
        assert timeout_sec == 60.0

    def test_conversion_custom_timeout(self):
        from crawl4ai.async_configs import CrawlerRunConfig
        config = CrawlerRunConfig(page_timeout=5000)

        timeout_sec = (config.page_timeout / 1000) if config.page_timeout else 30
        assert timeout_sec == 5.0

    def test_conversion_small_timeout(self):
        from crawl4ai.async_configs import CrawlerRunConfig
        config = CrawlerRunConfig(page_timeout=500)

        timeout_sec = (config.page_timeout / 1000) if config.page_timeout else 30
        assert timeout_sec == 0.5

    def test_timeout_not_absurdly_large(self):
        from crawl4ai.async_configs import CrawlerRunConfig
        config = CrawlerRunConfig()

        timeout_sec = (config.page_timeout / 1000) if config.page_timeout else 30
        timeout = aiohttp.ClientTimeout(total=timeout_sec)

        assert timeout.total <= 300, (
            f"Timeout is {timeout.total}s ({timeout.total/3600:.1f}h) — "
            "likely a ms/s unit mismatch"
        )

    def test_strategy_has_correct_default_timeout_in_seconds(self):
        from crawl4ai.async_crawler_strategy import AsyncHTTPCrawlerStrategy
        assert AsyncHTTPCrawlerStrategy.DEFAULT_TIMEOUT == 30, (
            "DEFAULT_TIMEOUT should be 30 seconds"
        )

    def test_zero_page_timeout_uses_default(self):
        from crawl4ai.async_configs import CrawlerRunConfig
        config = CrawlerRunConfig(page_timeout=0)

        timeout_sec = (config.page_timeout / 1000) if config.page_timeout else 30
        assert timeout_sec == 30
