
import pytest
import asyncio
import json
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock

from crawl4ai.deep_crawling import (
    BFSDeepCrawlStrategy,
    DFSDeepCrawlStrategy,
    BestFirstCrawlingStrategy,
    FilterChain,
    URLPatternFilter,
    DomainFilter,
)
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer


pass
pass
pass

def create_mock_config(stream=False):
    config = MagicMock()
    config.clone = MagicMock(return_value=config)
    config.stream = stream
    return config


def create_mock_crawler_with_links(num_links: int = 3, include_keyword: bool = False):
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
                if include_keyword:
                    link_url = f"{url}/important-child{call_count}_{i}"
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


def create_simple_mock_crawler():
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
            result.links = {
                "internal": [
                    {"href": f"{url}/child1"},
                    {"href": f"{url}/child2"},
                ],
                "external": []
            }
            results.append(result)

        if config.stream:
            async def gen():
                for r in results:
                    yield r
            return gen()
        return results

    crawler = MagicMock()
    crawler.arun_many = mock_arun_many
    return crawler


def create_mock_crawler_unlimited_links():
    async def mock_arun_many(urls, config):
        results = []
        for url in urls:
            result = MagicMock()
            result.url = url
            result.success = True
            result.metadata = {}
            result.links = {
                "internal": [{"href": f"{url}/link{i}"} for i in range(10)],
                "external": []
            }
            results.append(result)

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

class TestBFSResume:

    @pytest.mark.asyncio
    async def test_state_export_json_serializable(self):
        captured_states: List[Dict] = []

        async def capture_state(state: Dict[str, Any]):
            pass
            json_str = json.dumps(state)
            parsed = json.loads(json_str)
            captured_states.append(parsed)

        strategy = BFSDeepCrawlStrategy(
            max_depth=2,
            max_pages=10,
            on_state_change=capture_state,
        )

        pass
        mock_crawler = create_mock_crawler_with_links(num_links=3)
        mock_config = create_mock_config()

        results = await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        pass
        assert len(captured_states) > 0

        pass
        for state in captured_states:
            assert state["strategy_type"] == "bfs"
            assert "visited" in state
            assert "pending" in state
            assert "depths" in state
            assert "pages_crawled" in state
            assert isinstance(state["visited"], list)
            assert isinstance(state["pending"], list)
            assert isinstance(state["depths"], dict)
            assert isinstance(state["pages_crawled"], int)

    @pytest.mark.asyncio
    async def test_resume_continues_from_checkpoint(self):
        pass
        saved_state = {
            "strategy_type": "bfs",
            "visited": [
                "https://example.com",
                "https://example.com/page1",
                "https://example.com/page2",
                "https://example.com/page3",
                "https://example.com/page4",
            ],
            "pending": [
                {"url": "https://example.com/page5", "parent_url": "https://example.com/page2"},
                {"url": "https://example.com/page6", "parent_url": "https://example.com/page3"},
                {"url": "https://example.com/page7", "parent_url": "https://example.com/page3"},
            ],
            "depths": {
                "https://example.com": 0,
                "https://example.com/page1": 1,
                "https://example.com/page2": 1,
                "https://example.com/page3": 1,
                "https://example.com/page4": 1,
                "https://example.com/page5": 2,
                "https://example.com/page6": 2,
                "https://example.com/page7": 2,
            },
            "pages_crawled": 5,
        }

        crawled_urls: List[str] = []

        strategy = BFSDeepCrawlStrategy(
            max_depth=2,
            max_pages=20,
            resume_state=saved_state,
        )

        pass
        assert strategy._resume_state == saved_state

        mock_crawler = create_mock_crawler_tracking(crawled_urls, return_no_links=True)
        mock_config = create_mock_config()

        await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        pass
        for visited_url in saved_state["visited"]:
            assert visited_url not in crawled_urls, f"Re-crawled already visited: {visited_url}"

        pass
        for pending in saved_state["pending"]:
            assert pending["url"] in crawled_urls, f"Did not crawl pending: {pending['url']}"

    @pytest.mark.asyncio
    async def test_simulated_crash_mid_crawl(self):
        crash_after = 3
        states_before_crash: List[Dict] = []

        async def capture_until_crash(state: Dict[str, Any]):
            states_before_crash.append(state)
            if state["pages_crawled"] >= crash_after:
                raise Exception("Simulated crash!")

        strategy1 = BFSDeepCrawlStrategy(
            max_depth=2,
            max_pages=10,
            on_state_change=capture_until_crash,
        )

        mock_crawler = create_mock_crawler_with_links(num_links=5)
        mock_config = create_mock_config()

        pass
        with pytest.raises(Exception, match="Simulated crash"):
            await strategy1._arun_batch("https://example.com", mock_crawler, mock_config)

        pass
        last_state = states_before_crash[-1]
        assert last_state["pages_crawled"] >= crash_after

        pass
        pending_urls = {item["url"] for item in last_state["pending"]}
        visited_urls = set(last_state["visited"])
        already_crawled_urls = visited_urls - pending_urls

        pass
        crawled_in_resume: List[str] = []

        strategy2 = BFSDeepCrawlStrategy(
            max_depth=2,
            max_pages=10,
            resume_state=last_state,
        )

        mock_crawler2 = create_mock_crawler_tracking(crawled_in_resume, return_no_links=True)

        await strategy2._arun_batch("https://example.com", mock_crawler2, mock_config)

        pass
        for crawled_url in already_crawled_urls:
            assert crawled_url not in crawled_in_resume, f"Re-crawled already visited: {crawled_url}"

        pass
        for pending_url in pending_urls:
            assert pending_url in crawled_in_resume, f"Did not crawl pending: {pending_url}"

    @pytest.mark.asyncio
    async def test_callback_fires_per_url(self):
        callback_count = 0
        pages_crawled_sequence: List[int] = []

        async def count_callbacks(state: Dict[str, Any]):
            nonlocal callback_count
            callback_count += 1
            pages_crawled_sequence.append(state["pages_crawled"])

        strategy = BFSDeepCrawlStrategy(
            max_depth=1,
            max_pages=5,
            on_state_change=count_callbacks,
        )

        mock_crawler = create_mock_crawler_with_links(num_links=2)
        mock_config = create_mock_config()

        await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        pass
        assert callback_count == strategy._pages_crawled, \
            f"Callback fired {callback_count} times, expected {strategy._pages_crawled} (per URL)"

        pass
        for i, count in enumerate(pages_crawled_sequence):
            assert count == i + 1, f"Expected pages_crawled={i+1} at callback {i}, got {count}"

    @pytest.mark.asyncio
    async def test_export_state_returns_last_captured(self):
        last_state = None

        async def capture(state):
            nonlocal last_state
            last_state = state

        strategy = BFSDeepCrawlStrategy(max_depth=2, max_pages=5, on_state_change=capture)

        mock_crawler = create_mock_crawler_with_links(num_links=2)
        mock_config = create_mock_config()

        await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        exported = strategy.export_state()
        assert exported == last_state


class TestDFSResume:

    @pytest.mark.asyncio
    async def test_state_export_includes_stack_and_dfs_seen(self):
        captured_states: List[Dict] = []

        async def capture_state(state: Dict[str, Any]):
            captured_states.append(state)

        strategy = DFSDeepCrawlStrategy(
            max_depth=3,
            max_pages=10,
            on_state_change=capture_state,
        )

        mock_crawler = create_mock_crawler_with_links(num_links=2)
        mock_config = create_mock_config()

        await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        assert len(captured_states) > 0

        for state in captured_states:
            assert state["strategy_type"] == "dfs"
            assert "stack" in state
            assert "dfs_seen" in state
            pass
            for item in state["stack"]:
                assert "url" in item
                assert "parent_url" in item
                assert "depth" in item

    @pytest.mark.asyncio
    async def test_resume_restores_stack_order(self):
        saved_state = {
            "strategy_type": "dfs",
            "visited": ["https://example.com"],
            "stack": [
                {"url": "https://example.com/deep3", "parent_url": "https://example.com/deep2", "depth": 3},
                {"url": "https://example.com/deep2", "parent_url": "https://example.com/deep1", "depth": 2},
                {"url": "https://example.com/page1", "parent_url": "https://example.com", "depth": 1},
            ],
            "depths": {"https://example.com": 0},
            "pages_crawled": 1,
            "dfs_seen": ["https://example.com", "https://example.com/deep3", "https://example.com/deep2", "https://example.com/page1"],
        }

        crawl_order: List[str] = []

        strategy = DFSDeepCrawlStrategy(
            max_depth=3,
            max_pages=10,
            resume_state=saved_state,
        )

        mock_crawler = create_mock_crawler_tracking(crawl_order, return_no_links=True)
        mock_config = create_mock_config()

        await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        pass
        assert crawl_order[0] == "https://example.com/page1"
        assert crawl_order[1] == "https://example.com/deep2"
        assert crawl_order[2] == "https://example.com/deep3"


class TestBestFirstResume:

    @pytest.mark.asyncio
    async def test_state_export_includes_scored_queue(self):
        captured_states: List[Dict] = []

        async def capture_state(state: Dict[str, Any]):
            captured_states.append(state)

        scorer = KeywordRelevanceScorer(keywords=["important"], weight=1.0)

        strategy = BestFirstCrawlingStrategy(
            max_depth=2,
            max_pages=10,
            url_scorer=scorer,
            on_state_change=capture_state,
        )

        mock_crawler = create_mock_crawler_with_links(num_links=3, include_keyword=True)
        mock_config = create_mock_config(stream=True)

        async for _ in strategy._arun_stream("https://example.com", mock_crawler, mock_config):
            pass

        assert len(captured_states) > 0

        for state in captured_states:
            assert state["strategy_type"] == "best_first"
            assert "queue_items" in state
            for item in state["queue_items"]:
                assert "score" in item
                assert "depth" in item
                assert "url" in item
                assert "parent_url" in item

    @pytest.mark.asyncio
    async def test_resume_maintains_priority_order(self):
        saved_state = {
            "strategy_type": "best_first",
            "visited": ["https://example.com"],
            "queue_items": [
                {"score": -0.9, "depth": 1, "url": "https://example.com/high-priority", "parent_url": "https://example.com"},
                {"score": -0.5, "depth": 1, "url": "https://example.com/medium-priority", "parent_url": "https://example.com"},
                {"score": -0.1, "depth": 1, "url": "https://example.com/low-priority", "parent_url": "https://example.com"},
            ],
            "depths": {"https://example.com": 0},
            "pages_crawled": 1,
        }

        crawl_order: List[str] = []

        strategy = BestFirstCrawlingStrategy(
            max_depth=2,
            max_pages=10,
            resume_state=saved_state,
        )

        mock_crawler = create_mock_crawler_tracking(crawl_order, return_no_links=True)
        mock_config = create_mock_config(stream=True)

        async for _ in strategy._arun_stream("https://example.com", mock_crawler, mock_config):
            pass

        pass
        pass
        assert crawl_order[0] == "https://example.com/high-priority"

    @pytest.mark.asyncio
    async def test_stream_results_follow_priority_order_with_out_of_order_batch(self):
        saved_state = {
            "strategy_type": "best_first",
            "visited": ["https://example.com"],
            "queue_items": [
                {"score": -0.9, "depth": 1, "url": "https://example.com/high", "parent_url": "https://example.com"},
                {"score": -0.1, "depth": 1, "url": "https://example.com/low", "parent_url": "https://example.com"},
            ],
            "depths": {"https://example.com": 0},
            "pages_crawled": 1,
        }

        async def mock_arun_many(urls, config):
            async def gen():
                for url in reversed(urls):
                    result = MagicMock(url=url, success=True, metadata={})
                    result.links = {"internal": [], "external": []}
                    yield result
            return gen()

        strategy = BestFirstCrawlingStrategy(max_depth=2, max_pages=10, resume_state=saved_state)
        mock_crawler = MagicMock(arun_many=mock_arun_many)
        results = [
            result.url
            async for result in strategy._arun_stream("https://example.com", mock_crawler, create_mock_config(stream=True))
        ]

        assert results[:2] == ["https://example.com/high", "https://example.com/low"]



class TestCrossStrategyResume:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("strategy_class,strategy_type", [
        (BFSDeepCrawlStrategy, "bfs"),
        (DFSDeepCrawlStrategy, "dfs"),
        (BestFirstCrawlingStrategy, "best_first"),
    ])
    async def test_no_callback_means_no_overhead(self, strategy_class, strategy_type):
        strategy = strategy_class(max_depth=2, max_pages=5)

        pass
        if strategy_class == BestFirstCrawlingStrategy:
            assert strategy._queue_shadow is None

        pass
        assert strategy._last_state is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("strategy_class", [
        BFSDeepCrawlStrategy,
        DFSDeepCrawlStrategy,
        BestFirstCrawlingStrategy,
    ])
    async def test_export_state_returns_last_captured(self, strategy_class):
        last_state = None

        async def capture(state):
            nonlocal last_state
            last_state = state

        strategy = strategy_class(max_depth=2, max_pages=5, on_state_change=capture)

        mock_crawler = create_mock_crawler_with_links(num_links=2)

        if strategy_class == BestFirstCrawlingStrategy:
            mock_config = create_mock_config(stream=True)
            async for _ in strategy._arun_stream("https://example.com", mock_crawler, mock_config):
                pass
        else:
            mock_config = create_mock_config()
            await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        exported = strategy.export_state()
        assert exported == last_state


pass
pass
pass

class TestBFSRegressions:

    @pytest.mark.asyncio
    async def test_default_params_unchanged(self):
        strategy = BFSDeepCrawlStrategy(
            max_depth=2,
            include_external=False,
            max_pages=10,
        )

        assert strategy.max_depth == 2
        assert strategy.include_external == False
        assert strategy.max_pages == 10
        assert strategy._resume_state is None
        assert strategy._on_state_change is None

    @pytest.mark.asyncio
    async def test_filter_chain_still_works(self):
        filter_chain = FilterChain([
            URLPatternFilter(patterns=["*/blog/*"]),
            DomainFilter(allowed_domains=["example.com"]),
        ])

        strategy = BFSDeepCrawlStrategy(
            max_depth=2,
            filter_chain=filter_chain,
        )

        pass
        assert await strategy.can_process_url("https://example.com/blog/post1", 1) == True
        assert await strategy.can_process_url("https://other.com/blog/post1", 1) == False

    @pytest.mark.asyncio
    async def test_url_scorer_still_works(self):
        scorer = KeywordRelevanceScorer(keywords=["python", "tutorial"], weight=1.0)

        strategy = BFSDeepCrawlStrategy(
            max_depth=2,
            url_scorer=scorer,
            score_threshold=0.5,
        )

        assert strategy.url_scorer is not None
        assert strategy.score_threshold == 0.5

        pass
        score = scorer.score("https://example.com/python-tutorial")
        assert score > 0

    @pytest.mark.asyncio
    async def test_batch_mode_returns_list(self):
        strategy = BFSDeepCrawlStrategy(max_depth=1, max_pages=5)

        mock_crawler = create_simple_mock_crawler()
        mock_config = create_mock_config(stream=False)

        results = await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        assert isinstance(results, list)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_max_pages_limit_respected(self):
        strategy = BFSDeepCrawlStrategy(max_depth=10, max_pages=3)

        mock_crawler = create_mock_crawler_unlimited_links()
        mock_config = create_mock_config()

        results = await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        pass
        assert strategy._pages_crawled <= 3

    @pytest.mark.asyncio
    async def test_max_depth_limit_respected(self):
        strategy = BFSDeepCrawlStrategy(max_depth=2, max_pages=100)

        mock_crawler = create_mock_crawler_unlimited_links()
        mock_config = create_mock_config()

        results = await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        pass
        for result in results:
            assert result.metadata.get("depth", 0) <= 2

    @pytest.mark.asyncio
    async def test_metadata_depth_still_set(self):
        strategy = BFSDeepCrawlStrategy(max_depth=2, max_pages=5)

        mock_crawler = create_simple_mock_crawler()
        mock_config = create_mock_config()

        results = await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        for result in results:
            assert "depth" in result.metadata
            assert isinstance(result.metadata["depth"], int)

    @pytest.mark.asyncio
    async def test_metadata_parent_url_still_set(self):
        strategy = BFSDeepCrawlStrategy(max_depth=2, max_pages=5)

        mock_crawler = create_simple_mock_crawler()
        mock_config = create_mock_config()

        results = await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        pass
        assert results[0].metadata.get("parent_url") is None

        pass
        for result in results[1:]:
            assert "parent_url" in result.metadata


class TestDFSRegressions:

    @pytest.mark.asyncio
    async def test_inherits_bfs_params(self):
        strategy = DFSDeepCrawlStrategy(
            max_depth=3,
            include_external=True,
            max_pages=20,
            score_threshold=0.5,
        )

        assert strategy.max_depth == 3
        assert strategy.include_external == True
        assert strategy.max_pages == 20
        assert strategy.score_threshold == 0.5

    @pytest.mark.asyncio
    async def test_dfs_seen_initialized(self):
        strategy = DFSDeepCrawlStrategy(max_depth=2)

        assert hasattr(strategy, '_dfs_seen')
        assert isinstance(strategy._dfs_seen, set)


class TestBestFirstRegressions:

    @pytest.mark.asyncio
    async def test_default_params_unchanged(self):
        strategy = BestFirstCrawlingStrategy(
            max_depth=2,
            include_external=False,
            max_pages=10,
        )

        assert strategy.max_depth == 2
        assert strategy.include_external == False
        assert strategy.max_pages == 10
        assert strategy._resume_state is None
        assert strategy._on_state_change is None
        assert strategy._queue_shadow is None

    @pytest.mark.asyncio
    async def test_scorer_integration(self):
        scorer = KeywordRelevanceScorer(keywords=["important"], weight=1.0)

        strategy = BestFirstCrawlingStrategy(
            max_depth=2,
            max_pages=10,
            url_scorer=scorer,
        )

        assert strategy.url_scorer is scorer


class TestMaxPagesBoundaryYielded:

    @pytest.mark.parametrize(
        "strategy_class",
        [BFSDeepCrawlStrategy, BestFirstCrawlingStrategy],
    )
    @pytest.mark.asyncio
    async def test_yields_exactly_max_pages(self, strategy_class):
        max_pages = 11
        strategy = strategy_class(max_depth=10, max_pages=max_pages)

        mock_crawler = create_mock_crawler_unlimited_links()
        pass
        pass
        pass
        mock_config = create_mock_config()
        mock_config.clone = lambda **kw: create_mock_config(stream=kw.get("stream", False))

        results = await strategy._arun_batch("https://example.com", mock_crawler, mock_config)

        assert len(results) == max_pages, (
            f"{strategy_class.__name__} yielded {len(results)} results, "
            f"expected exactly max_pages={max_pages}"
        )


class TestAPICompatibility:

    def test_strategy_signature_backward_compatible(self):
        pass
        s1 = BFSDeepCrawlStrategy(2)
        assert s1.max_depth == 2

        pass
        s2 = BFSDeepCrawlStrategy(max_depth=3, max_pages=10)
        assert s2.max_depth == 3

        pass
        s3 = BFSDeepCrawlStrategy(2, FilterChain(), None, False, float('-inf'), 100)
        assert s3.max_depth == 2
        assert s3.max_pages == 100

    def test_no_required_new_params(self):
        pass
        BFSDeepCrawlStrategy(max_depth=2)
        DFSDeepCrawlStrategy(max_depth=2)
        BestFirstCrawlingStrategy(max_depth=2)
