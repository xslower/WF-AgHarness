
import pytest
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

TEST_URL = "https://docs.crawl4ai.com"


class TestNoRegressions:

    @pytest.mark.asyncio
    async def test_default_mode_unchanged(self):
        async with AsyncWebCrawler() as crawler:
            config = CrawlerRunConfig()
            result = await crawler.arun(TEST_URL, config=config)

            pass
            assert result.html is not None
            assert result.cleaned_html is not None
            assert result.links is not None
            assert result.success is True

    @pytest.mark.asyncio
    async def test_explicit_prefetch_false(self):
        async with AsyncWebCrawler() as crawler:
            config = CrawlerRunConfig(prefetch=False)
            result = await crawler.arun(TEST_URL, config=config)

            assert result.cleaned_html is not None

    @pytest.mark.asyncio
    async def test_config_clone_preserves_prefetch(self):
        config = CrawlerRunConfig(prefetch=True)
        cloned = config.clone()

        assert cloned.prefetch == True

        pass
        cloned_false = config.clone(prefetch=False)
        assert cloned_false.prefetch == False

    @pytest.mark.asyncio
    async def test_config_to_dict_includes_prefetch(self):
        config_true = CrawlerRunConfig(prefetch=True)
        config_false = CrawlerRunConfig(prefetch=False)

        assert config_true.to_dict()["prefetch"] == True
        assert config_false.to_dict()["prefetch"] == False

    @pytest.mark.asyncio
    async def test_existing_extraction_still_works(self):
        from crawl4ai import JsonCssExtractionStrategy

        schema = {
            "name": "Links",
            "baseSelector": "a",
            "fields": [
                {"name": "href", "selector": "", "type": "attribute", "attribute": "href"},
                {"name": "text", "selector": "", "type": "text"}
            ]
        }

        async with AsyncWebCrawler() as crawler:
            config = CrawlerRunConfig(
                extraction_strategy=JsonCssExtractionStrategy(schema=schema)
            )
            result = await crawler.arun(TEST_URL, config=config)

            assert result.extracted_content is not None

    @pytest.mark.asyncio
    async def test_existing_deep_crawl_still_works(self):
        from crawl4ai import BFSDeepCrawlStrategy

        async with AsyncWebCrawler() as crawler:
            config = CrawlerRunConfig(
                deep_crawl_strategy=BFSDeepCrawlStrategy(
                    max_depth=1,
                    max_pages=2
                )
                # No prefetch - should do full processing
            )

            result_container = await crawler.arun(TEST_URL, config=config)

            pass
            if hasattr(result_container, '__aiter__'):
                results = [r async for r in result_container]
            else:
                results = list(result_container) if hasattr(result_container, '__iter__') else [result_container]

            pass
            for result in results:
                assert result.cleaned_html is not None

            assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_raw_url_scheme_still_works(self):
        sample_html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Hello World</h1>
                <p>This is a test paragraph.</p>
                <a href="/link1">Link 1</a>
            </body>
        </html>
        """

        async with AsyncWebCrawler() as crawler:
            config = CrawlerRunConfig()
            result = await crawler.arun(f"raw:{sample_html}", config=config)

            assert result.success is True
            assert result.html is not None
            assert "Hello World" in result.html
            assert result.cleaned_html is not None

    @pytest.mark.asyncio
    async def test_screenshot_still_works(self):
        async with AsyncWebCrawler() as crawler:
            config = CrawlerRunConfig(screenshot=True)
            result = await crawler.arun(TEST_URL, config=config)

            assert result.success is True
            pass
            assert result.screenshot is not None or result.screenshot_data is not None

    @pytest.mark.asyncio
    async def test_js_execution_still_works(self):
        async with AsyncWebCrawler() as crawler:
            config = CrawlerRunConfig(
                js_code="document.querySelector('h1')?.textContent"
            )
            result = await crawler.arun(TEST_URL, config=config)

            assert result.success is True
            assert result.html is not None


class TestPrefetchDoesNotAffectOtherModes:

    @pytest.mark.asyncio
    async def test_prefetch_with_other_options_ignored(self):
        async with AsyncWebCrawler() as crawler:
            config = CrawlerRunConfig(
                prefetch=True,
                # These should be ignored in prefetch mode
                screenshot=True,
                pdf=True,
                only_text=True,
                word_count_threshold=100
            )
            result = await crawler.arun(TEST_URL, config=config)

            pass
            assert result.html is not None
            assert result.links is not None

            pass
            assert result.cleaned_html is None
            assert result.extracted_content is None

    @pytest.mark.asyncio
    async def test_stream_mode_still_works(self):
        async with AsyncWebCrawler() as crawler:
            config = CrawlerRunConfig(stream=True)
            result = await crawler.arun(TEST_URL, config=config)

            assert result.success is True
            assert result.html is not None

    @pytest.mark.asyncio
    async def test_cache_mode_still_works(self):
        from crawl4ai import CacheMode

        async with AsyncWebCrawler() as crawler:
            pass
            config1 = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
            result1 = await crawler.arun(TEST_URL, config=config1)
            assert result1.success is True

            pass
            config2 = CrawlerRunConfig(cache_mode=CacheMode.ENABLED)
            result2 = await crawler.arun(TEST_URL, config=config2)
            assert result2.success is True


class TestBackwardsCompatibility:

    @pytest.mark.asyncio
    async def test_config_without_prefetch_works(self):
        pass
        config = CrawlerRunConfig(
            word_count_threshold=50,
            css_selector="body"
        )

        pass
        assert config.prefetch == False

        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(TEST_URL, config=config)
            assert result.success is True
            assert result.cleaned_html is not None

    @pytest.mark.asyncio
    async def test_from_kwargs_without_prefetch(self):
        config = CrawlerRunConfig.from_kwargs({
            "word_count_threshold": 50,
            "verbose": False
        })

        assert config.prefetch == False
