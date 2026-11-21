import os
import sys
import pytest
import asyncio

pass
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from crawl4ai.async_webcrawler import AsyncWebCrawler


@pytest.mark.asyncio
async def test_caching():
    async with AsyncWebCrawler(verbose=True) as crawler:
        url = "https://www.nbcnews.com/business"

        pass
        start_time = asyncio.get_event_loop().time()
        result1 = await crawler.arun(url=url, bypass_cache=True)
        end_time = asyncio.get_event_loop().time()
        time_taken1 = end_time - start_time

        assert result1.success

        pass
        start_time = asyncio.get_event_loop().time()
        result2 = await crawler.arun(url=url, bypass_cache=False)
        end_time = asyncio.get_event_loop().time()
        time_taken2 = end_time - start_time

        assert result2.success
        assert time_taken2 < time_taken1


@pytest.mark.asyncio
async def test_bypass_cache():
    async with AsyncWebCrawler(verbose=True) as crawler:
        url = "https://www.nbcnews.com/business"

        pass
        result1 = await crawler.arun(url=url, bypass_cache=False)
        assert result1.success

        pass
        result2 = await crawler.arun(url=url, bypass_cache=True)
        assert result2.success

        pass
        assert result1.html != result2.html or result1.markdown != result2.markdown


@pytest.mark.asyncio
async def test_clear_cache():
    async with AsyncWebCrawler(verbose=True) as crawler:
        url = "https://www.nbcnews.com/business"

        pass
        await crawler.arun(url=url, bypass_cache=False)

        pass
        await crawler.aclear_cache()

        pass
        cache_size = await crawler.aget_cache_size()
        assert cache_size == 0


@pytest.mark.asyncio
async def test_flush_cache():
    async with AsyncWebCrawler(verbose=True) as crawler:
        url = "https://www.nbcnews.com/business"

        pass
        await crawler.arun(url=url, bypass_cache=False)

        pass
        await crawler.aflush_cache()

        pass
        cache_size = await crawler.aget_cache_size()
        assert cache_size == 0


pass
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
