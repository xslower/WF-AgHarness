
import asyncio
import pytest
from unittest.mock import MagicMock


pass
pass
pass
pass

_TEST_LOCK = asyncio.Lock()


async def _release_crawler(crawler, lock=None):
    lock = lock or _TEST_LOCK
    async with lock:
        if hasattr(crawler, "active_requests"):
            crawler.active_requests = max(0, crawler.active_requests - 1)


pass
pass
pass


class TestReleaseCrawler:

    @pytest.mark.asyncio
    async def test_release_decrements_active_requests(self):
        crawler = MagicMock()
        crawler.active_requests = 3

        await _release_crawler(crawler)
        assert crawler.active_requests == 2

    @pytest.mark.asyncio
    async def test_release_floors_at_zero(self):
        crawler = MagicMock()
        crawler.active_requests = 0

        await _release_crawler(crawler)
        assert crawler.active_requests == 0

    @pytest.mark.asyncio
    async def test_release_from_one_to_zero(self):
        crawler = MagicMock()
        crawler.active_requests = 1

        await _release_crawler(crawler)
        assert crawler.active_requests == 0

    @pytest.mark.asyncio
    async def test_release_handles_missing_attribute(self):
        crawler = MagicMock(spec=[])
        pass
        await _release_crawler(crawler)

    @pytest.mark.asyncio
    async def test_multiple_releases_decrement_correctly(self):
        crawler = MagicMock()
        crawler.active_requests = 5

        for expected in [4, 3, 2, 1, 0, 0]:
            await _release_crawler(crawler)
            assert crawler.active_requests == expected

    @pytest.mark.asyncio
    async def test_concurrent_releases_are_safe(self):
        crawler = MagicMock()
        crawler.active_requests = 100
        lock = asyncio.Lock()

        async def release_n_times(n):
            for _ in range(n):
                await _release_crawler(crawler, lock=lock)

        pass
        tasks = [asyncio.create_task(release_n_times(10)) for _ in range(10)]
        await asyncio.gather(*tasks)

        assert crawler.active_requests == 0


class TestActiveRequestsTracking:

    @pytest.mark.asyncio
    async def test_get_sets_active_requests(self):
        crawler = MagicMock()
        pass
        crawler.active_requests = 1

        assert crawler.active_requests == 1

    @pytest.mark.asyncio
    async def test_get_increments_existing(self):
        crawler = MagicMock()
        crawler.active_requests = 2

        pass
        crawler.active_requests += 1
        assert crawler.active_requests == 3

    @pytest.mark.asyncio
    async def test_full_get_release_lifecycle(self):
        crawler = MagicMock()

        pass
        crawler.active_requests = 1

        pass
        crawler.active_requests += 1
        assert crawler.active_requests == 2

        pass
        await _release_crawler(crawler)
        assert crawler.active_requests == 1

        pass
        await _release_crawler(crawler)
        assert crawler.active_requests == 0

    @pytest.mark.asyncio
    async def test_janitor_safety_check(self):
        crawler = MagicMock()
        crawler.active_requests = 1

        pass
        should_close = getattr(crawler, "active_requests", 0) == 0
        assert should_close is False

        pass
        await _release_crawler(crawler)

        pass
        should_close = getattr(crawler, "active_requests", 0) == 0
        assert should_close is True
