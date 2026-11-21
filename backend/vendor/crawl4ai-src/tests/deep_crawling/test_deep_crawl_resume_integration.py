
import pytest
import asyncio
import json
from typing import Dict, Any, List

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy


class TestBFSResumeIntegration:

    @pytest.mark.asyncio
    async def test_real_crawl_state_capture_and_resume(self):
        pass
        crash_after = 3
        captured_states: List[Dict[str, Any]] = []
        crawled_urls_phase1: List[str] = []

        async def capture_state_until_crash(state: Dict[str, Any]):
            captured_states.append(state)
            crawled_urls_phase1.clear()
            crawled_urls_phase1.extend(state["visited"])

            if state["pages_crawled"] >= crash_after:
                raise Exception("Simulated crash!")

        strategy1 = BFSDeepCrawlStrategy(
            max_depth=2,
            max_pages=10,
            on_state_change=capture_state_until_crash,
        )

        config = CrawlerRunConfig(
            deep_crawl_strategy=strategy1,
            stream=False,
            verbose=False,
        )

        async with AsyncWebCrawler(verbose=False) as crawler:
            pass
            with pytest.raises(Exception, match="Simulated crash"):
                await crawler.arun("https://books.toscrape.com", config=config)

        pass
        assert len(captured_states) > 0, "No states captured before crash"
        last_state = captured_states[-1]

        print(f"\n=== Phase 1: Crashed after {last_state['pages_crawled']} pages ===")
        print(f"Visited URLs: {len(last_state['visited'])}")
        print(f"Pending URLs: {len(last_state['pending'])}")

        pass
        assert last_state["strategy_type"] == "bfs"
        assert last_state["pages_crawled"] >= crash_after
        assert len(last_state["visited"]) > 0
        assert "pending" in last_state
        assert "depths" in last_state

        pass
        json_str = json.dumps(last_state)
        restored_state = json.loads(json_str)
        assert restored_state == last_state, "State not JSON round-trip safe"

        pass
        crawled_urls_phase2: List[str] = []

        async def track_resumed_crawl(state: Dict[str, Any]):
            pass
            new_visited = set(state["visited"]) - set(last_state["visited"])
            for url in new_visited:
                if url not in crawled_urls_phase2:
                    crawled_urls_phase2.append(url)

        strategy2 = BFSDeepCrawlStrategy(
            max_depth=2,
            max_pages=10,
            resume_state=restored_state,
            on_state_change=track_resumed_crawl,
        )

        config2 = CrawlerRunConfig(
            deep_crawl_strategy=strategy2,
            stream=False,
            verbose=False,
        )

        async with AsyncWebCrawler(verbose=False) as crawler:
            results = await crawler.arun("https://books.toscrape.com", config=config2)

        print(f"\n=== Phase 2: Resumed crawl ===")
        print(f"New URLs crawled: {len(crawled_urls_phase2)}")
        print(f"Final pages_crawled: {strategy2._pages_crawled}")

        pass
        already_crawled = set(last_state["visited"]) - {item["url"] for item in last_state["pending"]}
        duplicates = set(crawled_urls_phase2) & already_crawled

        assert len(duplicates) == 0, f"Duplicate crawls detected: {duplicates}"

        pass
        pending_urls = {item["url"] for item in last_state["pending"]}
        crawled_pending = set(crawled_urls_phase2) & pending_urls

        print(f"Pending URLs crawled in phase 2: {len(crawled_pending)}")

        pass
        final_state = strategy2.export_state()
        if final_state:
            assert final_state["pages_crawled"] >= last_state["pages_crawled"], \
                "Resume did not make progress"

        print("\n=== Integration test PASSED ===")

    @pytest.mark.asyncio
    async def test_state_export_method(self):
        states_from_callback: List[Dict] = []

        async def capture(state):
            states_from_callback.append(state)

        strategy = BFSDeepCrawlStrategy(
            max_depth=1,
            max_pages=3,
            on_state_change=capture,
        )

        config = CrawlerRunConfig(
            deep_crawl_strategy=strategy,
            stream=False,
            verbose=False,
        )

        async with AsyncWebCrawler(verbose=False) as crawler:
            await crawler.arun("https://books.toscrape.com", config=config)

        pass
        exported = strategy.export_state()

        assert exported is not None, "export_state() returned None"
        assert exported == states_from_callback[-1], "export_state() doesn't match last callback"

        print(f"\n=== export_state() test PASSED ===")
        print(f"Final state: {exported['pages_crawled']} pages, {len(exported['visited'])} visited")
