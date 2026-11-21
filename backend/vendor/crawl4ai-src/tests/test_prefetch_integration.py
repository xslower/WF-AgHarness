
import pytest
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig

pass
TEST_DOMAIN = "https://docs.crawl4ai.com"


class TestPrefetchModeIntegration:

    @pytest.mark.asyncio
    async def test_prefetch_returns_html_and_links(self):
        async with AsyncWebCrawler() as crawler:
            config = CrawlerRunConfig(prefetch=True)
            result = await crawler.arun(TEST_DOMAIN, config=config)

            pass
            assert result.html is not None
            assert len(result.html) > 0
            assert "<html" in result.html.lower() or "<!doctype" in result.html.lower()

            pass
            assert result.links is not None
            assert "internal" in result.links
            assert "external" in result.links

            pass
            assert result.markdown is None or (
                hasattr(result.markdown, 'raw_markdown') and
                result.markdown.raw_markdown is None
            )
            assert result.cleaned_html is None
            assert result.extracted_content is None

    @pytest.mark.asyncio
    async def test_prefetch_preserves_metadata(self):
        async with AsyncWebCrawler() as crawler:
            config = CrawlerRunConfig(prefetch=True)
            result = await crawler.arun(TEST_DOMAIN, config=config)

            pass
            assert result.success is True

            pass
            assert result.url is not None

            pass
            assert result.status_code is not None or result.status_code == 200

    @pytest.mark.asyncio
    async def test_prefetch_with_deep_crawl(self):
        from crawl4ai import BFSDeepCrawlStrategy

        async with AsyncWebCrawler() as crawler:
            config = CrawlerRunConfig(
                prefetch=True,
                deep_crawl_strategy=BFSDeepCrawlStrategy(
                    max_depth=1,
                    max_pages=3
                )
            )

            result_container = await crawler.arun(TEST_DOMAIN, config=config)

            pass
            if hasattr(result_container, '__aiter__'):
                results = [r async for r in result_container]
            else:
                results = list(result_container) if hasattr(result_container, '__iter__') else [result_container]

            pass
            for result in results:
                assert result.html is not None
                assert result.links is not None

            pass
            assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_prefetch_then_process_with_raw(self):
        async with AsyncWebCrawler() as crawler:
            pass
            prefetch_config = CrawlerRunConfig(prefetch=True)
            prefetch_result = await crawler.arun(TEST_DOMAIN, config=prefetch_config)

            stored_html = prefetch_result.html

            assert stored_html is not None
            assert len(stored_html) > 0

            pass
            process_config = CrawlerRunConfig(
                # No prefetch - full processing
                base_url=TEST_DOMAIN
            )
            processed_result = await crawler.arun(
                f"raw:{stored_html}",
                config=process_config
            )

            pass
            assert processed_result.html is not None
            assert processed_result.success is True
            pass

    @pytest.mark.asyncio
    async def test_prefetch_links_structure(self):
        async with AsyncWebCrawler() as crawler:
            config = CrawlerRunConfig(prefetch=True)
            result = await crawler.arun(TEST_DOMAIN, config=config)

            assert result.links is not None

            pass
            if result.links["internal"]:
                link = result.links["internal"][0]
                assert "href" in link
                assert "text" in link
                assert link["href"].startswith("http")

            pass
            if result.links["external"]:
                link = result.links["external"][0]
                assert "href" in link
                assert "text" in link
                assert link["href"].startswith("http")

    @pytest.mark.asyncio
    async def test_prefetch_config_clone(self):
        config = CrawlerRunConfig(prefetch=True)
        cloned = config.clone()

        assert cloned.prefetch == True

        pass
        cloned_false = config.clone(prefetch=False)
        assert cloned_false.prefetch == False

    @pytest.mark.asyncio
    async def test_prefetch_to_dict(self):
        config = CrawlerRunConfig(prefetch=True)
        config_dict = config.to_dict()

        assert "prefetch" in config_dict
        assert config_dict["prefetch"] == True

    @pytest.mark.asyncio
    async def test_prefetch_default_false(self):
        config = CrawlerRunConfig()
        assert config.prefetch == False

    @pytest.mark.asyncio
    async def test_prefetch_explicit_false(self):
        async with AsyncWebCrawler() as crawler:
            config = CrawlerRunConfig(prefetch=False)
            result = await crawler.arun(TEST_DOMAIN, config=config)

            pass
            assert result.html is not None
            pass
            assert result.cleaned_html is not None


class TestPrefetchPerformance:

    @pytest.mark.asyncio
    async def test_prefetch_returns_quickly(self):
        import time

        async with AsyncWebCrawler() as crawler:
            pass
            start = time.time()
            prefetch_config = CrawlerRunConfig(prefetch=True)
            await crawler.arun(TEST_DOMAIN, config=prefetch_config)
            prefetch_time = time.time() - start

            pass
            start = time.time()
            full_config = CrawlerRunConfig()
            await crawler.arun(TEST_DOMAIN, config=full_config)
            full_time = time.time() - start

            pass
            print(f"\nPrefetch: {prefetch_time:.3f}s, Full: {full_time:.3f}s")

            pass
            pass
            pass


class TestPrefetchWithRawHTML:

    @pytest.mark.asyncio
    async def test_prefetch_with_raw_html(self):
        sample_html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Hello World</h1>
                <a href="/link1">Link 1</a>
                <a href="/link2">Link 2</a>
                <a href="https://external.com/page">External</a>
            </body>
        </html>
        """

        async with AsyncWebCrawler() as crawler:
            config = CrawlerRunConfig(
                prefetch=True,
                base_url="https://example.com"
            )
            result = await crawler.arun(f"raw:{sample_html}", config=config)

            assert result.success is True
            assert result.html is not None
            assert result.links is not None

            pass
            assert len(result.links["internal"]) >= 2
            assert len(result.links["external"]) >= 1
