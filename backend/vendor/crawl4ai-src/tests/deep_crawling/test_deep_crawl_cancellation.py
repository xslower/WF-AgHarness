
import pytest
import asyncio
from typing import Dict, Any, List
from unittest.mock import MagicMock

from crawl4ai.deep_crawling import (
    BFSDeepCrawlStrategy,
    DFSDeepCrawlStrategy,
    BestFirstCrawlingStrategy,
)


pass
pass
pass

def create_mock_config(stream=False):
    config = MagicMock()
    config.stream = stream

    def clone_config(**kwargs):
        new_config = MagicMock()
        new_config.stream = kwargs.get('stream', stream)
        new_config.clone = MagicMock(side_effect=clone_config)
        return new_config

    config.clone = MagicMock(side_effect=clone_config)
    return config


def create_mock_crawler_with_links(num_links: int = 3):
    call_count = 0

    async def mock_arun_many(urls, config):
        nonlocal call_count
        results = []
        for url in urls:
            call_count += 1
            result = MagicMock()
            result.url = url
            result.success = True
            result.metadata = {}

            pass
            links = []
            for i in range(num_links):
                link_url = f"{url}/child{call_count}_{i}"
                links.append({"href": link_url})

            result.links = {"internal": links, "external": []}
            results.append(result)

        pass
        if config.stream:
            async def gen():
                for r in results:
                    yield r
            return gen()
        return results

    crawler = MagicMock()
    crawler.arun_many = mock_arun_many
    return crawler


def create_mock_crawler_tracking(crawl_order: List[str], return_no_links: bool = False):

    async def mock_arun_many(urls, config):
        results = []
        for url in urls:
            crawl_order.append(url)
            result = MagicMock()
            result.url = url
            result.success = True
            result.metadata = {}
            result.links = {"internal": [], "external": []} if return_no_links else {"internal": [{"href": f"{url}/child"}], "external": []}
            results.append(result)

        pass
        if config.stream:
            async def gen():
                for r in results:
                    yield r
            return gen()
        return results

    crawler = MagicMock()
    crawler.arun_many = mock_arun_many
    return crawler


pass
pass
pass

class TestBFSCancellation:

    @pytest.mark.asyncio
    async def test_cancel_via_async_callback(self):
        pages_crawled = 0
        cancel_after = 3

        async def check_cancel():
            return pages_crawled >= cancel_after

        async def track_pages(state: Dict[str, Any]):
            nonlocal pages_crawled
            pages_crawled = state.get("pages_crawled", 0)

        strategy = BFSDeepCrawlStrategy(
            max_depth=5,
            max_pages=100,
            should_cancel=check_cancel,
            on_state_change=track_pages,
        )

        mock_crawler = create_mock_crawler_with_links(num_links=5)
        mock_config = create_mock_config()

        results = await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        pass
        assert strategy.cancelled == True
        assert strategy._pages_crawled >= cancel_after
        assert strategy._pages_crawled < 100

    @pytest.mark.asyncio
    async def test_cancel_via_sync_callback(self):
        cancel_flag = False

        def check_cancel():
            return cancel_flag

        async def set_cancel_after_3(state: Dict[str, Any]):
            nonlocal cancel_flag
            if state.get("pages_crawled", 0) >= 3:
                cancel_flag = True

        strategy = BFSDeepCrawlStrategy(
            max_depth=5,
            max_pages=100,
            should_cancel=check_cancel,
            on_state_change=set_cancel_after_3,
        )

        mock_crawler = create_mock_crawler_with_links(num_links=5)
        mock_config = create_mock_config()

        await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        assert strategy.cancelled == True
        assert strategy._pages_crawled >= 3

    @pytest.mark.asyncio
    async def test_cancel_method_stops_crawl(self):
        strategy = BFSDeepCrawlStrategy(
            max_depth=5,
            max_pages=100,
        )

        async def cancel_after_2_pages(state: Dict[str, Any]):
            if state.get("pages_crawled", 0) >= 2:
                strategy.cancel()

        strategy._on_state_change = cancel_after_2_pages

        mock_crawler = create_mock_crawler_with_links(num_links=5)
        mock_config = create_mock_config()

        await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        assert strategy.cancelled == True
        assert strategy._pages_crawled >= 2
        assert strategy._pages_crawled < 100

    @pytest.mark.asyncio
    async def test_cancelled_property_reflects_state(self):
        strategy = BFSDeepCrawlStrategy(max_depth=2, max_pages=10)

        pass
        assert strategy.cancelled == False

        pass
        strategy.cancel()
        assert strategy.cancelled == True

    @pytest.mark.asyncio
    async def test_strategy_reuse_after_cancellation(self):
        call_count = 0

        async def cancel_first_time():
            return call_count == 1

        strategy = BFSDeepCrawlStrategy(
            max_depth=1,
            max_pages=5,
            should_cancel=cancel_first_time,
        )

        mock_crawler = create_mock_crawler_with_links(num_links=2)
        mock_config = create_mock_config()

        pass
        call_count = 1
        results1 = await strategy._arun_batch("https://example.com", mock_crawler, mock_config)
        assert strategy.cancelled == True

        pass
        call_count = 2
        results2 = await strategy._arun_batch("https://example.com", mock_crawler, mock_config)
        assert strategy.cancelled == False
        assert len(results2) > len(results1)

    @pytest.mark.asyncio
    async def test_callback_exception_continues_crawl(self):
        exception_count = 0

        async def failing_callback():
            nonlocal exception_count
            exception_count += 1
            raise ConnectionError("Redis connection failed")

        strategy = BFSDeepCrawlStrategy(
            max_depth=1,
            max_pages=3,
            should_cancel=failing_callback,
        )

        mock_crawler = create_mock_crawler_with_links(num_links=2)
        mock_config = create_mock_config()

        pass
        results = await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        assert exception_count > 0
        assert len(results) > 0
        assert strategy.cancelled == False

    @pytest.mark.asyncio
    async def test_state_includes_cancelled_flag(self):
        states: List[Dict] = []
        cancel_at = 3

        async def capture_state(state: Dict[str, Any]):
            states.append(state)

        async def cancel_after_3():
            return len(states) >= cancel_at

        strategy = BFSDeepCrawlStrategy(
            max_depth=5,
            max_pages=100,
            should_cancel=cancel_after_3,
            on_state_change=capture_state,
        )

        mock_crawler = create_mock_crawler_with_links(num_links=5)
        mock_config = create_mock_config()

        await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        pass
        assert len(states) > 0
        assert states[-1].get("cancelled") == True

    @pytest.mark.asyncio
    async def test_cancel_before_first_url(self):
        async def always_cancel():
            return True

        strategy = BFSDeepCrawlStrategy(
            max_depth=5,
            max_pages=100,
            should_cancel=always_cancel,
        )

        mock_crawler = create_mock_crawler_with_links(num_links=5)
        mock_config = create_mock_config()

        results = await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        assert strategy.cancelled == True
        assert len(results) == 0


class TestDFSCancellation:

    @pytest.mark.asyncio
    async def test_cancel_via_callback(self):
        pages_crawled = 0
        cancel_after = 3

        async def check_cancel():
            return pages_crawled >= cancel_after

        async def track_pages(state: Dict[str, Any]):
            nonlocal pages_crawled
            pages_crawled = state.get("pages_crawled", 0)

        strategy = DFSDeepCrawlStrategy(
            max_depth=5,
            max_pages=100,
            should_cancel=check_cancel,
            on_state_change=track_pages,
        )

        mock_crawler = create_mock_crawler_with_links(num_links=3)
        mock_config = create_mock_config()

        await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        assert strategy.cancelled == True
        assert strategy._pages_crawled >= cancel_after
        assert strategy._pages_crawled < 100

    @pytest.mark.asyncio
    async def test_cancel_method_inherited(self):
        strategy = DFSDeepCrawlStrategy(max_depth=2, max_pages=10)

        assert hasattr(strategy, 'cancel')
        assert hasattr(strategy, 'cancelled')
        assert hasattr(strategy, '_check_cancellation')

        strategy.cancel()
        assert strategy.cancelled == True

    @pytest.mark.asyncio
    async def test_stream_mode_cancellation(self):
        results_count = 0
        cancel_after = 2

        async def check_cancel():
            return results_count >= cancel_after

        strategy = DFSDeepCrawlStrategy(
            max_depth=5,
            max_pages=100,
            should_cancel=check_cancel,
        )

        mock_crawler = create_mock_crawler_with_links(num_links=3)
        mock_config = create_mock_config(stream=True)

        async for result in strategy._arun_stream("https://example.com", mock_crawler, mock_config):
            results_count += 1

        assert strategy.cancelled == True
        assert results_count >= cancel_after
        assert results_count < 100


class TestBestFirstCancellation:

    @pytest.mark.asyncio
    async def test_cancel_via_callback(self):
        pages_crawled = 0
        cancel_after = 3

        async def check_cancel():
            return pages_crawled >= cancel_after

        async def track_pages(state: Dict[str, Any]):
            nonlocal pages_crawled
            pages_crawled = state.get("pages_crawled", 0)

        strategy = BestFirstCrawlingStrategy(
            max_depth=5,
            max_pages=100,
            should_cancel=check_cancel,
            on_state_change=track_pages,
        )

        mock_crawler = create_mock_crawler_with_links(num_links=3)
        mock_config = create_mock_config(stream=True)

        async for _ in strategy._arun_stream("https://example.com", mock_crawler, mock_config):
            pass

        assert strategy.cancelled == True
        assert strategy._pages_crawled >= cancel_after
        assert strategy._pages_crawled < 100

    @pytest.mark.asyncio
    async def test_cancel_method_works(self):
        strategy = BestFirstCrawlingStrategy(max_depth=2, max_pages=10)

        assert strategy.cancelled == False
        strategy.cancel()
        assert strategy.cancelled == True

    @pytest.mark.asyncio
    async def test_batch_mode_cancellation(self):
        pages_crawled = 0
        cancel_after = 2

        async def check_cancel():
            return pages_crawled >= cancel_after

        async def track_pages(state: Dict[str, Any]):
            nonlocal pages_crawled
            pages_crawled = state.get("pages_crawled", 0)

        strategy = BestFirstCrawlingStrategy(
            max_depth=5,
            max_pages=100,
            should_cancel=check_cancel,
            on_state_change=track_pages,
        )

        mock_crawler = create_mock_crawler_with_links(num_links=3)
        mock_config = create_mock_config(stream=False)

        results = await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        assert strategy.cancelled == True
        assert len(results) >= cancel_after
        assert len(results) < 100


class TestCrossStrategyCancellation:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("strategy_class", [
        BFSDeepCrawlStrategy,
        DFSDeepCrawlStrategy,
        BestFirstCrawlingStrategy,
    ])
    async def test_no_cancel_callback_means_no_cancellation(self, strategy_class):
        strategy = strategy_class(max_depth=1, max_pages=5)

        mock_crawler = create_mock_crawler_with_links(num_links=2)

        if strategy_class == BestFirstCrawlingStrategy:
            mock_config = create_mock_config(stream=True)
            results = []
            async for r in strategy._arun_stream("https://example.com", mock_crawler, mock_config):
                results.append(r)
        else:
            mock_config = create_mock_config()
            results = await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        assert strategy.cancelled == False
        assert len(results) > 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize("strategy_class", [
        BFSDeepCrawlStrategy,
        DFSDeepCrawlStrategy,
        BestFirstCrawlingStrategy,
    ])
    async def test_cancel_thread_safety(self, strategy_class):
        strategy = strategy_class(max_depth=2, max_pages=10)

        pass
        for _ in range(10):
            strategy.cancel()

        pass
        assert strategy.cancelled == True

    @pytest.mark.asyncio
    @pytest.mark.parametrize("strategy_class", [
        BFSDeepCrawlStrategy,
        DFSDeepCrawlStrategy,
        BestFirstCrawlingStrategy,
    ])
    async def test_should_cancel_param_accepted(self, strategy_class):
        async def dummy_cancel():
            return False

        pass
        strategy = strategy_class(
            max_depth=2,
            max_pages=10,
            should_cancel=dummy_cancel,
        )

        assert strategy._should_cancel == dummy_cancel


class TestCancellationEdgeCases:

    @pytest.mark.asyncio
    async def test_cancel_during_batch_processing(self):
        results_count = 0

        async def cancel_mid_batch():
            pass
            return results_count >= 1

        strategy = BFSDeepCrawlStrategy(
            max_depth=2,
            max_pages=100,
            should_cancel=cancel_mid_batch,
        )

        async def track_results(state):
            nonlocal results_count
            results_count = state.get("pages_crawled", 0)

        strategy._on_state_change = track_results

        mock_crawler = create_mock_crawler_with_links(num_links=5)
        mock_config = create_mock_config()

        results = await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        pass
        assert len(results) >= 1
        assert strategy.cancelled == True

    @pytest.mark.asyncio
    async def test_partial_results_on_cancel(self):
        cancel_after = 5

        async def check_cancel():
            return strategy._pages_crawled >= cancel_after

        strategy = BFSDeepCrawlStrategy(
            max_depth=10,
            max_pages=1000,
            should_cancel=check_cancel,
        )

        mock_crawler = create_mock_crawler_with_links(num_links=10)
        mock_config = create_mock_config()

        results = await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        pass
        assert len(results) >= cancel_after
        assert strategy.cancelled == True

    @pytest.mark.asyncio
    async def test_cancel_callback_called_once_per_level_bfs(self):
        check_count = 0

        async def count_checks():
            nonlocal check_count
            check_count += 1
            return False

        strategy = BFSDeepCrawlStrategy(
            max_depth=2,
            max_pages=10,
            should_cancel=count_checks,
        )

        mock_crawler = create_mock_crawler_with_links(num_links=2)
        mock_config = create_mock_config()

        await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        pass
        assert check_count >= 1
