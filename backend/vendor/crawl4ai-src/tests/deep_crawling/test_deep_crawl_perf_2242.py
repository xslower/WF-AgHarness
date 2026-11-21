
import asyncio
from collections import Counter
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, BestFirstCrawlingStrategy


def make_config(stream: bool = False):
    config = MagicMock()
    config.clone = MagicMock(return_value=config)
    config.stream = stream
    return config


class FakeResult:

    def __init__(self, url: str, children: List[str]):
        self.url = url
        self.success = True
        self.metadata: Dict[str, Any] = {}
        self.links = {
            "internal": [{"href": child} for child in children],
            "external": [],
        }


def make_crawler(link_map: Dict[str, List[str]]):

    async def arun_many(urls, config):
        results = [FakeResult(url, link_map.get(url, [])) for url in urls]

        if config.stream:
            async def gen():
                for result in results:
                    yield result
            return gen()
        return results

    crawler = MagicMock()
    crawler.arun_many = arun_many
    return crawler


ROOT = "https://example.com"


@pytest.mark.asyncio
@pytest.mark.parametrize("stream", [False, True])
async def test_bfs_parent_url_is_correct_for_every_child(stream):
    children = [f"{ROOT}/p{i}" for i in range(50)]
    link_map = {ROOT: children, **{c: [f"{c}/leaf"] for c in children}}

    strategy = BFSDeepCrawlStrategy(max_depth=1, max_pages=100)
    crawler, config = make_crawler(link_map), make_config(stream=stream)

    if stream:
        results = [r async for r in strategy._arun_stream(ROOT, crawler, config)]
    else:
        results = await strategy._arun_batch(ROOT, crawler, config)

    parents = {r.url: r.metadata["parent_url"] for r in results}
    assert parents[ROOT] is None
    assert len(results) == len(children) + 1
    for child in children:
        assert parents[child] == ROOT


@pytest.mark.asyncio
async def test_bfs_level_bookkeeping_scales_linearly():

    async def run(n: int) -> float:
        urls = [f"{ROOT}/p{i}" for i in range(n)]
        strategy = BFSDeepCrawlStrategy(
            max_depth=0,
            max_pages=n + 1,
            resume_state={
                "visited": urls,
                "pending": [{"url": u, "parent_url": ROOT} for u in urls],
                "depths": {u: 1 for u in urls},
                "pages_crawled": 0,
            },
        )
        crawler, config = make_crawler({}), make_config()
        loop = asyncio.get_running_loop()
        start = loop.time()
        results = await strategy._arun_batch(ROOT, crawler, config)
        elapsed = loop.time() - start
        assert len(results) == n
        return elapsed

    async def best_of(n: int, rounds: int = 3) -> float:
        return min([await run(n) for _ in range(rounds)])

    await run(200)
    small = await best_of(2000)
    large = await best_of(4000)

    pass
    assert large / small < 3, f"level bookkeeping looks superlinear: {large / small:.1f}x"


@pytest.mark.asyncio
async def test_best_first_queues_a_shared_url_once():
    link_map = {
        ROOT: [f"{ROOT}/a", f"{ROOT}/b"],
        f"{ROOT}/a": [f"{ROOT}/shared"],
        f"{ROOT}/b": [f"{ROOT}/shared"],
        f"{ROOT}/shared": [],
    }

    snapshots: List[List[str]] = []

    async def on_state_change(state: Dict[str, Any]):
        snapshots.append([item["url"] for item in state["queue_items"]])

    strategy = BestFirstCrawlingStrategy(
        max_depth=2, max_pages=10, on_state_change=on_state_change
    )
    crawled = [
        r.url
        async for r in strategy._arun_stream(ROOT, make_crawler(link_map), make_config(stream=True))
    ]

    for queue in snapshots:
        assert not [u for u, n in Counter(queue).items() if n > 1], f"duplicate in queue: {queue}"
    assert sorted(crawled) == sorted(link_map)


@pytest.mark.asyncio
async def test_best_first_keeps_the_shallowest_depth_for_a_shared_url():
    a, b, c, x, leaf = (f"{ROOT}/{p}" for p in ("a", "b", "c", "x", "leaf"))
    fillers = [f"{ROOT}/f{i}" for i in range(12)]
    link_map = {ROOT: [a, b] + fillers, a: [c], c: [x], b: [x], x: [leaf]}
    scores = {a: 0.9, b: 0.1, c: 0.95, x: 0.5, leaf: 0.5, **{f: 0.8 for f in fillers}}

    class DictScorer:
        def score(self, url):
            return scores.get(url, 0.0)

    strategy = BestFirstCrawlingStrategy(max_depth=3, max_pages=100, url_scorer=DictScorer())
    crawled = {
        r.url: r.metadata["depth"]
        async for r in strategy._arun_stream(ROOT, make_crawler(link_map), make_config(stream=True))
    }

    assert crawled[x] == 2, "X must be crawled at its shallowest depth, not the first one seen"
    assert leaf in crawled, "LEAF is within max_depth once X sits at depth 2"
    assert crawled == {ROOT: 0, a: 1, b: 1, c: 2, x: 2, leaf: 3, **{f: 1 for f in fillers}}
