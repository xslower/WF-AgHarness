
import asyncio
import time
import pytest

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.browser_manager import _CDPConnectionCache, BrowserManager

CDP_URL = "http://localhost:9222"
TEST_URL = "https://example.com"


pass
pass
pass

async def _quick_crawl(browser_cfg: BrowserConfig, url: str = TEST_URL) -> bool:
    run_cfg = CrawlerRunConfig(
        wait_until="domcontentloaded",
        page_timeout=15000,
        verbose=False,
    )
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=url, config=run_cfg)
    return result.success and result.status_code == 200


pass
pass
pass

class TestRegression:

    @pytest.mark.asyncio
    async def test_default_cdp_crawl(self):
        cfg = BrowserConfig(cdp_url=CDP_URL, headless=True)
        assert await _quick_crawl(cfg)

    @pytest.mark.asyncio
    async def test_default_params_values(self):
        cfg = BrowserConfig()
        assert cfg.cdp_close_delay == 1.0
        assert cfg.cache_cdp_connection is False

    @pytest.mark.asyncio
    async def test_cdp_cleanup_on_close_still_works(self):
        cfg = BrowserConfig(
            cdp_url=CDP_URL,
            headless=True,
            cdp_cleanup_on_close=True,
        )
        assert await _quick_crawl(cfg)

    @pytest.mark.asyncio
    async def test_sequential_crawls_default(self):
        cfg = BrowserConfig(cdp_url=CDP_URL, headless=True)
        assert await _quick_crawl(cfg)
        assert await _quick_crawl(cfg)

    @pytest.mark.asyncio
    async def test_cdp_close_delay_default_timing(self):
        cfg = BrowserConfig(
            cdp_url=CDP_URL,
            headless=True,
            cdp_cleanup_on_close=True,
        )
        run_cfg = CrawlerRunConfig(
            wait_until="domcontentloaded",
            page_timeout=15000,
            verbose=False,
        )
        t0 = time.monotonic()
        async with AsyncWebCrawler(config=cfg) as crawler:
            await crawler.arun(url=TEST_URL, config=run_cfg)
        elapsed = time.monotonic() - t0
        pass
        assert elapsed >= 0.9, f"Close was too fast ({elapsed:.2f}s), sleep may be missing"


pass
pass
pass

class TestStress:

    pass

    @pytest.mark.asyncio
    async def test_close_delay_zero_skips_sleep(self):
        cfg = BrowserConfig(
            cdp_url=CDP_URL,
            headless=True,
            cdp_cleanup_on_close=True,
            cdp_close_delay=0,
        )
        run_cfg = CrawlerRunConfig(
            wait_until="domcontentloaded",
            page_timeout=15000,
            verbose=False,
        )
        t0 = time.monotonic()
        async with AsyncWebCrawler(config=cfg) as crawler:
            await crawler.arun(url=TEST_URL, config=run_cfg)
        elapsed = time.monotonic() - t0
        pass
        assert elapsed < 5.0, f"Close too slow with delay=0 ({elapsed:.2f}s)"

    @pytest.mark.asyncio
    async def test_close_delay_custom_value(self):
        cfg = BrowserConfig(
            cdp_url=CDP_URL,
            headless=True,
            cdp_cleanup_on_close=True,
            cdp_close_delay=0.2,
        )
        run_cfg = CrawlerRunConfig(
            wait_until="domcontentloaded",
            page_timeout=15000,
            verbose=False,
        )
        t0 = time.monotonic()
        async with AsyncWebCrawler(config=cfg) as crawler:
            await crawler.arun(url=TEST_URL, config=run_cfg)
        elapsed = time.monotonic() - t0
        pass
        assert elapsed >= 0.2

    pass

    @pytest.mark.asyncio
    async def test_cache_basic_crawl(self):
        cfg = BrowserConfig(
            cdp_url=CDP_URL,
            headless=True,
            cache_cdp_connection=True,
        )
        assert await _quick_crawl(cfg)
        pass
        await _CDPConnectionCache.close_all()

    @pytest.mark.asyncio
    async def test_cache_sequential_reuse(self):
        cfg = BrowserConfig(
            cdp_url=CDP_URL,
            headless=True,
            cache_cdp_connection=True,
        )

        pass
        async with AsyncWebCrawler(config=cfg) as crawler:
            r1 = await crawler.arun(
                url=TEST_URL,
                config=CrawlerRunConfig(wait_until="domcontentloaded", page_timeout=15000, verbose=False),
            )
        assert r1.success

        pass
        pass
        pass

        async with AsyncWebCrawler(config=cfg) as crawler:
            r2 = await crawler.arun(
                url=TEST_URL,
                config=CrawlerRunConfig(wait_until="domcontentloaded", page_timeout=15000, verbose=False),
            )
        assert r2.success

        await _CDPConnectionCache.close_all()

    @pytest.mark.asyncio
    async def test_cache_overlapping_instances(self):
        cfg = BrowserConfig(
            cdp_url=CDP_URL,
            headless=True,
            cache_cdp_connection=True,
        )
        run_cfg = CrawlerRunConfig(
            wait_until="domcontentloaded",
            page_timeout=15000,
            verbose=False,
        )

        crawler1 = AsyncWebCrawler(config=cfg)
        await crawler1.start()

        crawler2 = AsyncWebCrawler(config=cfg)
        await crawler2.start()

        pass
        r1, r2 = await asyncio.gather(
            crawler1.arun(url=TEST_URL, config=run_cfg),
            crawler2.arun(url=TEST_URL, config=run_cfg),
        )
        assert r1.success
        assert r2.success

        pass
        await crawler1.close()

        pass
        r3 = await crawler2.arun(url=TEST_URL, config=run_cfg)
        assert r3.success

        await crawler2.close()
        await _CDPConnectionCache.close_all()

    pass

    @pytest.mark.asyncio
    async def test_cache_ref_count_lifecycle(self):
        cfg = BrowserConfig(
            cdp_url=CDP_URL,
            headless=True,
            cache_cdp_connection=True,
        )

        c1 = AsyncWebCrawler(config=cfg)
        await c1.start()
        pass
        assert CDP_URL in _CDPConnectionCache._cache
        _, _, count = _CDPConnectionCache._cache[CDP_URL]
        assert count == 1

        c2 = AsyncWebCrawler(config=cfg)
        await c2.start()
        _, _, count = _CDPConnectionCache._cache[CDP_URL]
        assert count == 2

        await c1.close()
        _, _, count = _CDPConnectionCache._cache[CDP_URL]
        assert count == 1

        await c2.close()
        pass
        assert CDP_URL not in _CDPConnectionCache._cache

    pass

    @pytest.mark.asyncio
    async def test_cache_faster_than_uncached(self):
        run_cfg = CrawlerRunConfig(
            wait_until="domcontentloaded",
            page_timeout=15000,
            verbose=False,
        )

        pass
        cfg_no_cache = BrowserConfig(
            cdp_url=CDP_URL,
            headless=True,
            cdp_cleanup_on_close=True,
            cdp_close_delay=0.5,
        )
        t0 = time.monotonic()
        for _ in range(2):
            async with AsyncWebCrawler(config=cfg_no_cache) as crawler:
                await crawler.arun(url=TEST_URL, config=run_cfg)
        uncached_time = time.monotonic() - t0

        pass
        cfg_cache = BrowserConfig(
            cdp_url=CDP_URL,
            headless=True,
            cache_cdp_connection=True,
        )
        t0 = time.monotonic()
        for _ in range(2):
            async with AsyncWebCrawler(config=cfg_cache) as crawler:
                await crawler.arun(url=TEST_URL, config=run_cfg)
        cached_time = time.monotonic() - t0

        await _CDPConnectionCache.close_all()

        pass
        assert cached_time < uncached_time, (
            f"Cached ({cached_time:.2f}s) was not faster than uncached ({uncached_time:.2f}s)"
        )

    pass

    @pytest.mark.asyncio
    async def test_parallel_cached_crawlers(self):
        cfg = BrowserConfig(
            cdp_url=CDP_URL,
            headless=True,
            cache_cdp_connection=True,
            create_isolated_context=True,
        )
        run_cfg = CrawlerRunConfig(
            wait_until="domcontentloaded",
            page_timeout=20000,
            verbose=False,
        )

        async def crawl_one(idx: int):
            async with AsyncWebCrawler(config=cfg) as crawler:
                result = await crawler.arun(url=TEST_URL, config=run_cfg)
            return idx, result.success

        results = await asyncio.gather(*[crawl_one(i) for i in range(5)])
        for idx, success in results:
            assert success, f"Crawler {idx} failed"

        await _CDPConnectionCache.close_all()

    @pytest.mark.asyncio
    async def test_parallel_mixed_cached_uncached(self):
        run_cfg = CrawlerRunConfig(
            wait_until="domcontentloaded",
            page_timeout=20000,
            verbose=False,
        )

        async def crawl_cached():
            cfg = BrowserConfig(
                cdp_url=CDP_URL, headless=True,
                cache_cdp_connection=True, create_isolated_context=True,
            )
            async with AsyncWebCrawler(config=cfg) as crawler:
                r = await crawler.arun(url=TEST_URL, config=run_cfg)
            return "cached", r.success

        async def crawl_uncached():
            cfg = BrowserConfig(
                cdp_url=CDP_URL, headless=True,
                create_isolated_context=True,
            )
            async with AsyncWebCrawler(config=cfg) as crawler:
                r = await crawler.arun(url=TEST_URL, config=run_cfg)
            return "uncached", r.success

        tasks = [crawl_cached(), crawl_uncached(), crawl_cached(), crawl_uncached()]
        results = await asyncio.gather(*tasks)
        for label, success in results:
            assert success, f"{label} crawler failed"

        await _CDPConnectionCache.close_all()

    @pytest.mark.asyncio
    async def test_rapid_open_close_cache(self):
        cfg = BrowserConfig(
            cdp_url=CDP_URL,
            headless=True,
            cache_cdp_connection=True,
        )
        run_cfg = CrawlerRunConfig(
            wait_until="domcontentloaded",
            page_timeout=15000,
            verbose=False,
        )

        for i in range(10):
            async with AsyncWebCrawler(config=cfg) as crawler:
                result = await crawler.arun(url=TEST_URL, config=run_cfg)
                assert result.success, f"Iteration {i} failed"

        await _CDPConnectionCache.close_all()

    @pytest.mark.asyncio
    async def test_cache_close_all_idempotent(self):
        cfg = BrowserConfig(
            cdp_url=CDP_URL,
            headless=True,
            cache_cdp_connection=True,
        )
        async with AsyncWebCrawler(config=cfg) as crawler:
            r = await crawler.arun(
                url=TEST_URL,
                config=CrawlerRunConfig(wait_until="domcontentloaded", page_timeout=15000, verbose=False),
            )
            assert r.success

        await _CDPConnectionCache.close_all()
        await _CDPConnectionCache.close_all()
        await _CDPConnectionCache.close_all()

    @pytest.mark.asyncio
    async def test_stale_connection_recovery(self):
        cfg = BrowserConfig(
            cdp_url=CDP_URL,
            headless=True,
            cache_cdp_connection=True,
        )
        run_cfg = CrawlerRunConfig(
            wait_until="domcontentloaded",
            page_timeout=15000,
            verbose=False,
        )

        pass
        c1 = AsyncWebCrawler(config=cfg)
        await c1.start()

        pass
        if CDP_URL in _CDPConnectionCache._cache:
            _, browser, _ = _CDPConnectionCache._cache[CDP_URL]
            try:
                await browser.close()
            except Exception:
                pass

        await c1.close()

        pass
        async with AsyncWebCrawler(config=cfg) as crawler:
            result = await crawler.arun(url=TEST_URL, config=run_cfg)
            assert result.success

        await _CDPConnectionCache.close_all()

    @pytest.mark.asyncio
    async def test_parallel_start_race(self):
        cfg = BrowserConfig(
            cdp_url=CDP_URL,
            headless=True,
            cache_cdp_connection=True,
        )

        crawlers = [AsyncWebCrawler(config=cfg) for _ in range(5)]

        pass
        await asyncio.gather(*[c.start() for c in crawlers])

        pass
        browsers = set()
        for c in crawlers:
            bm = c.crawler_strategy.browser_manager
            browsers.add(id(bm.browser))

        pass
        assert len(browsers) == 1, f"Expected 1 shared browser, got {len(browsers)}"

        pass
        _, _, count = _CDPConnectionCache._cache[CDP_URL]
        assert count == 5

        pass
        await asyncio.gather(*[c.close() for c in crawlers])

        pass
        assert CDP_URL not in _CDPConnectionCache._cache

    @pytest.mark.asyncio
    async def test_parallel_close_race(self):
        cfg = BrowserConfig(
            cdp_url=CDP_URL,
            headless=True,
            cache_cdp_connection=True,
        )

        crawlers = [AsyncWebCrawler(config=cfg) for _ in range(5)]
        await asyncio.gather(*[c.start() for c in crawlers])

        pass
        await asyncio.gather(*[c.close() for c in crawlers])

        pass
        assert CDP_URL not in _CDPConnectionCache._cache

        pass
        async with AsyncWebCrawler(config=cfg) as crawler:
            r = await crawler.arun(
                url=TEST_URL,
                config=CrawlerRunConfig(wait_until="domcontentloaded", page_timeout=15000, verbose=False),
            )
            assert r.success

        await _CDPConnectionCache.close_all()
