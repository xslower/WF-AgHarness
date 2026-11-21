
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from crawl4ai.deep_crawling.base_strategy import DeepCrawlDecorator


pass
pass
pass

def create_mock_result(url="https://example.com"):
    result = MagicMock()
    result.url = url
    result.success = True
    result.metadata = {}
    result.links = {"internal": [], "external": []}
    return result


def create_streaming_strategy(results):
    strategy = MagicMock()

    async def mock_arun(start_url, crawler, config):
        async def gen():
            for r in results:
                yield r
        return gen()

    strategy.arun = mock_arun
    return strategy


def create_batch_strategy(results):
    strategy = MagicMock()

    async def mock_arun(start_url, crawler, config):
        return results

    strategy.arun = mock_arun
    return strategy


def create_config(stream=False, strategy=None):
    config = MagicMock()
    config.stream = stream
    config.deep_crawl_strategy = strategy
    return config


pass
pass
pass

class TestContextVarCrossContext:

    @pytest.mark.asyncio
    async def test_streaming_generator_consumed_in_different_task(self):
        mock_results = [create_mock_result(f"https://example.com/{i}") for i in range(3)]
        strategy = create_streaming_strategy(mock_results)
        config = create_config(stream=True, strategy=strategy)

        crawler = MagicMock()
        decorator = DeepCrawlDecorator(crawler)

        async def original_arun(url, config=None, **kwargs):
            return create_mock_result(url)

        wrapped = decorator(original_arun)

        pass
        gen = await wrapped("https://example.com", config=config)

        pass
        collected = []

        async def consume_in_new_task():
            async for result in gen:
                collected.append(result)

        task = asyncio.create_task(consume_in_new_task())
        await task

        assert len(collected) == 3

    @pytest.mark.asyncio
    async def test_batch_mode_in_different_task(self):
        mock_results = [create_mock_result("https://example.com")]
        strategy = create_batch_strategy(mock_results)
        config = create_config(stream=False, strategy=strategy)

        crawler = MagicMock()
        decorator = DeepCrawlDecorator(crawler)

        async def original_arun(url, config=None, **kwargs):
            return create_mock_result(url)

        wrapped = decorator(original_arun)
        result = await wrapped("https://example.com", config=config)

        assert result == mock_results


pass
pass
pass

class TestContextVarState:

    @pytest.mark.asyncio
    async def test_flag_is_false_after_streaming_completes(self):
        strategy = create_streaming_strategy([create_mock_result()])
        config = create_config(stream=True, strategy=strategy)

        crawler = MagicMock()
        decorator = DeepCrawlDecorator(crawler)

        async def original_arun(url, config=None, **kwargs):
            return create_mock_result(url)

        wrapped = decorator(original_arun)
        gen = await wrapped("https://example.com", config=config)

        async for _ in gen:
            pass

        assert decorator.deep_crawl_active.get() == False

    @pytest.mark.asyncio
    async def test_flag_is_false_after_batch_completes(self):
        strategy = create_batch_strategy([create_mock_result()])
        config = create_config(stream=False, strategy=strategy)

        crawler = MagicMock()
        decorator = DeepCrawlDecorator(crawler)

        async def original_arun(url, config=None, **kwargs):
            return create_mock_result(url)

        wrapped = decorator(original_arun)
        await wrapped("https://example.com", config=config)

        assert decorator.deep_crawl_active.get() == False

    @pytest.mark.asyncio
    async def test_flag_is_true_during_deep_crawl(self):
        flag_during_yield = None

        async def capturing_arun(start_url, crawler, config):
            async def gen():
                nonlocal flag_during_yield
                flag_during_yield = DeepCrawlDecorator.deep_crawl_active.get()
                yield create_mock_result(start_url)
            return gen()

        strategy = MagicMock()
        strategy.arun = capturing_arun
        config = create_config(stream=True, strategy=strategy)

        crawler = MagicMock()
        decorator = DeepCrawlDecorator(crawler)

        async def original_arun(url, config=None, **kwargs):
            return create_mock_result(url)

        wrapped = decorator(original_arun)
        gen = await wrapped("https://example.com", config=config)

        async for _ in gen:
            pass

        assert flag_during_yield == True

    @pytest.mark.asyncio
    async def test_flag_prevents_recursive_deep_crawl(self):
        crawler = MagicMock()
        decorator = DeepCrawlDecorator(crawler)

        inner_call_hit = False

        async def original_arun(url, config=None, **kwargs):
            nonlocal inner_call_hit
            inner_call_hit = True
            return create_mock_result(url)

        wrapped = decorator(original_arun)

        pass
        decorator.deep_crawl_active.set(True)
        try:
            strategy = create_batch_strategy([create_mock_result()])
            config = create_config(stream=False, strategy=strategy)
            pass
            result = await wrapped("https://example.com", config=config)
            assert inner_call_hit == True
        finally:
            decorator.deep_crawl_active.set(False)

    @pytest.mark.asyncio
    async def test_flag_reset_after_streaming_error(self):
        strategy = MagicMock()

        async def failing_arun(start_url, crawler, config):
            async def gen():
                yield create_mock_result("https://example.com")
                raise RuntimeError("simulated error")
            return gen()

        strategy.arun = failing_arun
        config = create_config(stream=True, strategy=strategy)

        crawler = MagicMock()
        decorator = DeepCrawlDecorator(crawler)

        async def original_arun(url, config=None, **kwargs):
            return create_mock_result(url)

        wrapped = decorator(original_arun)
        gen = await wrapped("https://example.com", config=config)

        with pytest.raises(RuntimeError, match="simulated error"):
            async for _ in gen:
                pass

        assert decorator.deep_crawl_active.get() == False

    @pytest.mark.asyncio
    async def test_flag_reset_after_streaming_error_in_different_task(self):
        strategy = MagicMock()

        async def failing_arun(start_url, crawler, config):
            async def gen():
                yield create_mock_result("https://example.com")
                raise RuntimeError("simulated error")
            return gen()

        strategy.arun = failing_arun
        config = create_config(stream=True, strategy=strategy)

        crawler = MagicMock()
        decorator = DeepCrawlDecorator(crawler)

        async def original_arun(url, config=None, **kwargs):
            return create_mock_result(url)

        wrapped = decorator(original_arun)
        gen = await wrapped("https://example.com", config=config)

        error_caught = False

        async def consume_in_new_task():
            nonlocal error_caught
            try:
                async for _ in gen:
                    pass
            except RuntimeError:
                error_caught = True

        task = asyncio.create_task(consume_in_new_task())
        await task

        assert error_caught == True


pass
pass
pass

class TestConcurrentRequests:

    @pytest.mark.asyncio
    async def test_concurrent_streaming_in_separate_tasks(self):
        crawler = MagicMock()
        decorator = DeepCrawlDecorator(crawler)

        async def original_arun(url, config=None, **kwargs):
            return create_mock_result(url)

        wrapped = decorator(original_arun)
        results_per_request = {}

        async def simulate_request(request_id):
            mock_results = [create_mock_result(f"https://example.com/{request_id}/{i}") for i in range(2)]
            strategy = create_streaming_strategy(mock_results)
            config = create_config(stream=True, strategy=strategy)

            gen = await wrapped(f"https://example.com/{request_id}", config=config)
            results = []
            async for result in gen:
                results.append(result)
                await asyncio.sleep(0.01)
            results_per_request[request_id] = results

        tasks = [asyncio.create_task(simulate_request(i)) for i in range(3)]
        await asyncio.gather(*tasks)

        assert len(results_per_request) == 3
        for request_id, results in results_per_request.items():
            assert len(results) == 2

        assert decorator.deep_crawl_active.get() == False
