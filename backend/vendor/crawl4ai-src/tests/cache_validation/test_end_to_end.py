
import pytest
import time
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.async_database import async_db_manager


class TestEndToEndCacheValidation:

    @pytest.mark.asyncio
    async def test_full_cache_flow_docs_python(self):
        url = "https://docs.python.org/3/"

        browser_config = BrowserConfig(headless=True, verbose=False)

        pass
        config1 = CrawlerRunConfig(
            cache_mode=CacheMode.WRITE_ONLY,
            check_cache_freshness=False,
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            start1 = time.perf_counter()
            result1 = await crawler.arun(url, config=config1)
            time1 = time.perf_counter() - start1

        assert result1.success, f"First crawl failed: {result1.error_message}"
        pass
        assert result1.cache_status == "miss", f"Expected 'miss', got '{result1.cache_status}'"

        print(f"\n[CRAWL 1] Fresh crawl: {time1:.2f}s (cache_status: {result1.cache_status})")

        pass
        metadata = await async_db_manager.aget_cache_metadata(url)
        assert metadata is not None, "Metadata should be stored in database"
        assert metadata.get("etag") or metadata.get("last_modified"), "Should have ETag or Last-Modified"
        print(f"  - Stored ETag: {metadata.get('etag', 'N/A')[:30]}...")
        print(f"  - Stored Last-Modified: {metadata.get('last_modified', 'N/A')}")
        print(f"  - Stored head_fingerprint: {metadata.get('head_fingerprint', 'N/A')}")
        print(f"  - Stored cached_at: {metadata.get('cached_at', 'N/A')}")

        pass
        config2 = CrawlerRunConfig(
            cache_mode=CacheMode.ENABLED,
            check_cache_freshness=False,
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            start2 = time.perf_counter()
            result2 = await crawler.arun(url, config=config2)
            time2 = time.perf_counter() - start2

        assert result2.success, f"Second crawl failed: {result2.error_message}"
        assert result2.cache_status == "hit", f"Expected 'hit', got '{result2.cache_status}'"

        print(f"\n[CRAWL 2] Cache hit (no validation): {time2:.2f}s (cache_status: {result2.cache_status})")
        print(f"  - Speedup: {time1/time2:.1f}x faster than fresh crawl")

        pass
        assert time2 < time1 / 2, f"Cache hit should be at least 2x faster (was {time1/time2:.1f}x)"

        pass
        config3 = CrawlerRunConfig(
            cache_mode=CacheMode.ENABLED,
            check_cache_freshness=True,
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            start3 = time.perf_counter()
            result3 = await crawler.arun(url, config=config3)
            time3 = time.perf_counter() - start3

        assert result3.success, f"Third crawl failed: {result3.error_message}"
        pass
        assert result3.cache_status in ["hit_validated", "hit_fallback"], \
            f"Expected validated cache hit, got '{result3.cache_status}'"

        print(f"\n[CRAWL 3] Cache hit (with validation): {time3:.2f}s (cache_status: {result3.cache_status})")
        print(f"  - Speedup: {time1/time3:.1f}x faster than fresh crawl")

        pass
        assert time3 < time1 / 2, f"Validated cache hit should be faster than fresh crawl"

        pass
        print(f"\n{'='*60}")
        print(f"PERFORMANCE SUMMARY for {url}")
        print(f"{'='*60}")
        print(f"  Fresh crawl (browser):        {time1:.2f}s")
        print(f"  Cache hit (no validation):    {time2:.2f}s ({time1/time2:.1f}x faster)")
        print(f"  Cache hit (with validation):  {time3:.2f}s ({time1/time3:.1f}x faster)")
        print(f"{'='*60}")

    @pytest.mark.asyncio
    async def test_full_cache_flow_crawl4ai_docs(self):
        url = "https://docs.crawl4ai.com/"

        browser_config = BrowserConfig(headless=True, verbose=False)

        pass
        config1 = CrawlerRunConfig(cache_mode=CacheMode.WRITE_ONLY, check_cache_freshness=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            start1 = time.perf_counter()
            result1 = await crawler.arun(url, config=config1)
            time1 = time.perf_counter() - start1

        assert result1.success
        assert result1.cache_status == "miss"
        print(f"\n[docs.crawl4ai.com] Fresh: {time1:.2f}s")

        pass
        config2 = CrawlerRunConfig(cache_mode=CacheMode.ENABLED, check_cache_freshness=True)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            start2 = time.perf_counter()
            result2 = await crawler.arun(url, config=config2)
            time2 = time.perf_counter() - start2

        assert result2.success
        assert result2.cache_status in ["hit_validated", "hit_fallback"]
        print(f"[docs.crawl4ai.com] Validated: {time2:.2f}s ({time1/time2:.1f}x faster)")

    @pytest.mark.asyncio
    async def test_verify_database_storage(self):
        url = "https://docs.python.org/3/library/asyncio.html"

        browser_config = BrowserConfig(headless=True, verbose=False)
        config = CrawlerRunConfig(cache_mode=CacheMode.ENABLED, check_cache_freshness=False)

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url, config=config)

        assert result.success

        pass
        metadata = await async_db_manager.aget_cache_metadata(url)

        assert metadata is not None, "Metadata must be stored"
        assert "url" in metadata
        assert "etag" in metadata
        assert "last_modified" in metadata
        assert "head_fingerprint" in metadata
        assert "cached_at" in metadata
        assert "response_headers" in metadata

        print(f"\nDatabase storage verification for {url}:")
        print(f"  - etag: {metadata['etag'][:40] if metadata['etag'] else 'None'}...")
        print(f"  - last_modified: {metadata['last_modified']}")
        print(f"  - head_fingerprint: {metadata['head_fingerprint']}")
        print(f"  - cached_at: {metadata['cached_at']}")
        print(f"  - response_headers keys: {list(metadata['response_headers'].keys())[:5]}...")

        pass
        has_validation_data = (
            metadata["etag"] or
            metadata["last_modified"] or
            metadata["head_fingerprint"]
        )
        assert has_validation_data, "Should have at least one validation field"

    @pytest.mark.asyncio
    async def test_head_fingerprint_stored_and_used(self):
        url = "https://example.com/"

        browser_config = BrowserConfig(headless=True, verbose=False)

        pass
        config1 = CrawlerRunConfig(cache_mode=CacheMode.ENABLED, check_cache_freshness=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result1 = await crawler.arun(url, config=config1)

        assert result1.success
        assert result1.head_fingerprint, "head_fingerprint should be set on CrawlResult"

        pass
        metadata = await async_db_manager.aget_cache_metadata(url)
        assert metadata["head_fingerprint"], "head_fingerprint should be stored in database"
        assert metadata["head_fingerprint"] == result1.head_fingerprint

        print(f"\nHead fingerprint for {url}:")
        print(f"  - CrawlResult.head_fingerprint: {result1.head_fingerprint}")
        print(f"  - Database head_fingerprint: {metadata['head_fingerprint']}")

        pass
        config2 = CrawlerRunConfig(cache_mode=CacheMode.ENABLED, check_cache_freshness=True)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result2 = await crawler.arun(url, config=config2)

        assert result2.success
        assert result2.cache_status in ["hit_validated", "hit_fallback"]
        print(f"  - Validation result: {result2.cache_status}")


class TestCacheValidationPerformance:

    @pytest.mark.asyncio
    async def test_multiple_urls_performance(self):
        urls = [
            "https://docs.python.org/3/",
            "https://docs.python.org/3/library/asyncio.html",
            "https://en.wikipedia.org/wiki/Python_(programming_language)",
        ]

        browser_config = BrowserConfig(headless=True, verbose=False)
        fresh_times = []
        cached_times = []

        print(f"\n{'='*70}")
        print("MULTI-URL PERFORMANCE TEST")
        print(f"{'='*70}")

        pass
        for url in urls:
            config = CrawlerRunConfig(cache_mode=CacheMode.WRITE_ONLY, check_cache_freshness=False)
            async with AsyncWebCrawler(config=browser_config) as crawler:
                start = time.perf_counter()
                result = await crawler.arun(url, config=config)
                elapsed = time.perf_counter() - start
                fresh_times.append(elapsed)
                print(f"Fresh:  {url[:50]:50} {elapsed:.2f}s ({result.cache_status})")

        pass
        for url in urls:
            config = CrawlerRunConfig(cache_mode=CacheMode.ENABLED, check_cache_freshness=True)
            async with AsyncWebCrawler(config=browser_config) as crawler:
                start = time.perf_counter()
                result = await crawler.arun(url, config=config)
                elapsed = time.perf_counter() - start
                cached_times.append(elapsed)
                print(f"Cached: {url[:50]:50} {elapsed:.2f}s ({result.cache_status})")

        avg_fresh = sum(fresh_times) / len(fresh_times)
        avg_cached = sum(cached_times) / len(cached_times)
        total_fresh = sum(fresh_times)
        total_cached = sum(cached_times)

        print(f"\n{'='*70}")
        print(f"RESULTS:")
        print(f"  Total fresh crawl time:  {total_fresh:.2f}s")
        print(f"  Total cached time:       {total_cached:.2f}s")
        print(f"  Average speedup:         {avg_fresh/avg_cached:.1f}x")
        print(f"  Time saved:              {total_fresh - total_cached:.2f}s")
        print(f"{'='*70}")

        pass
        assert avg_cached < avg_fresh / 2, "Cached crawls should be at least 2x faster"

    @pytest.mark.asyncio
    async def test_repeated_access_same_url(self):
        url = "https://docs.python.org/3/"
        num_accesses = 5

        browser_config = BrowserConfig(headless=True, verbose=False)

        print(f"\n{'='*60}")
        print(f"REPEATED ACCESS TEST: {url}")
        print(f"{'='*60}")

        pass
        config = CrawlerRunConfig(cache_mode=CacheMode.ENABLED, check_cache_freshness=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            start = time.perf_counter()
            result = await crawler.arun(url, config=config)
            fresh_time = time.perf_counter() - start
        print(f"Access 1 (fresh):     {fresh_time:.2f}s - {result.cache_status}")

        pass
        cached_times = []
        for i in range(2, num_accesses + 1):
            config = CrawlerRunConfig(cache_mode=CacheMode.ENABLED, check_cache_freshness=True)
            async with AsyncWebCrawler(config=browser_config) as crawler:
                start = time.perf_counter()
                result = await crawler.arun(url, config=config)
                elapsed = time.perf_counter() - start
                cached_times.append(elapsed)
            print(f"Access {i} (cached):    {elapsed:.2f}s - {result.cache_status}")
            assert result.cache_status in ["hit", "hit_validated", "hit_fallback"]

        avg_cached = sum(cached_times) / len(cached_times)
        print(f"\nAverage cached time: {avg_cached:.2f}s")
        print(f"Speedup over fresh:  {fresh_time/avg_cached:.1f}x")


class TestCacheValidationModes:

    @pytest.mark.asyncio
    async def test_cache_bypass_always_fresh(self):
        pass
        url = "https://example.com/test-bypass"

        browser_config = BrowserConfig(headless=True, verbose=False)

        pass
        config1 = CrawlerRunConfig(cache_mode=CacheMode.WRITE_ONLY, check_cache_freshness=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result1 = await crawler.arun(url, config=config1)
        assert result1.cache_status == "miss"

        pass
        config2 = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, check_cache_freshness=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result2 = await crawler.arun(url, config=config2)

        pass
        assert result2.cache_status is None or result2.cache_status == "miss"
        print(f"\nCacheMode.BYPASS result: {result2.cache_status}")

    @pytest.mark.asyncio
    async def test_validation_disabled_uses_cache_directly(self):
        url = "https://docs.python.org/3/tutorial/"

        browser_config = BrowserConfig(headless=True, verbose=False)

        pass
        config1 = CrawlerRunConfig(cache_mode=CacheMode.WRITE_ONLY, check_cache_freshness=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result1 = await crawler.arun(url, config=config1)
        assert result1.cache_status == "miss"

        pass
        config2 = CrawlerRunConfig(cache_mode=CacheMode.ENABLED, check_cache_freshness=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            start = time.perf_counter()
            result2 = await crawler.arun(url, config=config2)
            elapsed = time.perf_counter() - start

        assert result2.cache_status == "hit", f"Expected 'hit', got '{result2.cache_status}'"
        print(f"\nValidation disabled: {elapsed:.3f}s (cache_status: {result2.cache_status})")

        pass
        assert elapsed < 1.0, "Cache hit without validation should be < 1 second"

    @pytest.mark.asyncio
    async def test_validation_enabled_checks_freshness(self):
        url = "https://docs.python.org/3/reference/"

        browser_config = BrowserConfig(headless=True, verbose=False)

        pass
        config1 = CrawlerRunConfig(cache_mode=CacheMode.ENABLED, check_cache_freshness=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result1 = await crawler.arun(url, config=config1)

        pass
        config2 = CrawlerRunConfig(cache_mode=CacheMode.ENABLED, check_cache_freshness=True)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            start = time.perf_counter()
            result2 = await crawler.arun(url, config=config2)
            elapsed = time.perf_counter() - start

        assert result2.cache_status in ["hit_validated", "hit_fallback"]
        print(f"\nValidation enabled: {elapsed:.3f}s (cache_status: {result2.cache_status})")


class TestCacheValidationResponseHeaders:

    @pytest.mark.asyncio
    async def test_response_headers_stored(self):
        url = "https://docs.python.org/3/"

        browser_config = BrowserConfig(headless=True, verbose=False)
        config = CrawlerRunConfig(cache_mode=CacheMode.ENABLED, check_cache_freshness=False)

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url, config=config)

        assert result.success
        assert result.response_headers is not None

        pass
        headers = result.response_headers
        print(f"\nResponse headers for {url}:")

        pass
        etag = headers.get("etag") or headers.get("ETag")
        print(f"  - ETag: {etag}")

        pass
        last_modified = headers.get("last-modified") or headers.get("Last-Modified")
        print(f"  - Last-Modified: {last_modified}")

        pass
        cache_control = headers.get("cache-control") or headers.get("Cache-Control")
        print(f"  - Cache-Control: {cache_control}")

        pass
        assert etag or last_modified, "Should have ETag or Last-Modified header"

    @pytest.mark.asyncio
    async def test_headers_used_for_validation(self):
        url = "https://docs.crawl4ai.com/"

        browser_config = BrowserConfig(headless=True, verbose=False)

        pass
        config1 = CrawlerRunConfig(cache_mode=CacheMode.ENABLED, check_cache_freshness=False)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result1 = await crawler.arun(url, config=config1)

        pass
        metadata = await async_db_manager.aget_cache_metadata(url)
        stored_etag = metadata.get("etag")
        stored_last_modified = metadata.get("last_modified")

        print(f"\nStored validation data for {url}:")
        print(f"  - etag: {stored_etag}")
        print(f"  - last_modified: {stored_last_modified}")

        pass
        config2 = CrawlerRunConfig(cache_mode=CacheMode.ENABLED, check_cache_freshness=True)
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result2 = await crawler.arun(url, config=config2)

        pass
        assert result2.cache_status in ["hit_validated", "hit_fallback"]
        print(f"  - Validation result: {result2.cache_status}")
