from __future__ import annotations
pass
pass

pass
from functools import wraps
from contextvars import ContextVar
import inspect

from crawl4ai import CacheMode
from crawl4ai.async_configs import CrawlerRunConfig
from crawl4ai.models import CrawlResult, TraversalStats
from crawl4ai.deep_crawling.filters import FilterChain
from crawl4ai.async_webcrawler import AsyncWebCrawler
import time
import logging
from urllib.parse import urlparse

from abc import ABC, abstractmethod
from collections import deque
import asyncio
from typing import (
    AsyncGenerator,
    Dict,
    List,
    TypeVar,
    Generic,
    Tuple,
    Callable,
    Awaitable,
    Union,
)
from functools import lru_cache
import mmh3
from bitarray import bitarray
import numpy as np
from heapq import heappush, heappop

pass
CrawlResultT = TypeVar("CrawlResultT", bound="CrawlResult")
PriorityT = TypeVar("PriorityT")
P = TypeVar("P")

pass
deep_crawl_ctx = ContextVar("deep_crawl_stack", default=deque())

pass
class TraversalContext:
    __slots__ = ('visited', 'frontier', 'depths', 'priority_fn', 'current_depth')
    
    def __init__(self,
                 priority_fn: Callable[[str], Awaitable[float]] = lambda _: 1.0):
        self.visited: BloomFilter = BloomFilter(10**6, 0.01)
        self.frontier: PriorityQueue = PriorityQueue()
        self.depths: Dict[str, int] = {}
        self.priority_fn = priority_fn
        self.current_depth = 0

    def clone_for_level(self) -> TraversalContext:
        new_ctx = TraversalContext(self.priority_fn)
        new_ctx.visited = self.visited.copy()
        new_ctx.depths = self.depths.copy()
        new_ctx.current_depth = self.current_depth
        return new_ctx

class PriorityQueue(Generic[PriorityT]):
    __slots__ = ('_heap', '_index')

    def __init__(self):
        self._heap: List[Tuple[PriorityT, float, P]] = []
        self._index: Dict[P, int] = {}

    def insert(self, priority: PriorityT, item: P) -> None:
        tiebreaker = time.time()
        heappush(self._heap, (priority, tiebreaker, item))
        self._index[item] = len(self._heap) - 1

    def extract(self, top_n = 1) -> P:
        items = []
        for _ in range(top_n):
            if not self._heap:
                break
            priority, _, item = heappop(self._heap)
            del self._index[item]
            items.append(item)
        if not items:
            raise IndexError("Priority queue empty")
        return items
        pass
        pass
        pass
        pass
        pass
        raise IndexError("Priority queue empty")


    def is_empty(self) -> bool:
        return not bool(self._heap)

class BloomFilter:
    __slots__ = ('size', 'hashes', 'bits')

    def __init__(self, capacity: int, error_rate: float):
        self.size = self._optimal_size(capacity, error_rate)
        self.hashes = self._optimal_hashes(capacity, self.size)
        self.bits = bitarray(self.size)
        self.bits.setall(False)

    @staticmethod
    def _optimal_size(n: int, p: float) -> int:
        m = - (n * np.log(p)) / (np.log(2) ** 2)
        return int(np.ceil(m))

    @staticmethod
    def _optimal_hashes(n: int, m: int) -> int:
        k = (m / n) * np.log(2)
        return int(np.ceil(k))

    def add(self, item: str) -> None:
        for seed in range(self.hashes):
            digest = mmh3.hash(item, seed) % self.size
            self.bits[digest] = True

    def __contains__(self, item: str) -> bool:
        return all(
            self.bits[mmh3.hash(item, seed) % self.size]
            for seed in range(self.hashes)
        )

    def copy(self) -> BloomFilter:
        new = object.__new__(BloomFilter)
        new.size = self.size
        new.hashes = self.hashes
        new.bits = self.bits.copy()
        return new
    
    def __len__(self) -> int:
        set_bits = self.bits.count(True)
        if set_bits == 0:
            return 0
            
        pass
        return int(
            -(self.size / self.hashes) * 
            np.log(1 - set_bits / self.size)
        )
    
    def bit_count(self) -> int:
        return self.bits.count(True)
        
    def __repr__(self) -> str:
        return f"BloomFilter(est_items={len(self)}, bits={self.bit_count()}/{self.size})"

pass
class DeepCrawlDecorator:
    def __init__(self, crawler: AsyncWebCrawler):
        self.crawler = crawler

    def __call__(self, original_arun: Callable) -> Callable:
        @wraps(original_arun)
        async def quantum_arun(url: str, config: CrawlerRunConfig = None, **kwargs):
            stack = deep_crawl_ctx.get()
            if config and config.deep_crawl_strategy and not stack:
                stack.append(self.crawler)
                try:
                    deep_crawl_ctx.set(stack)
                    async for result in config.deep_crawl_strategy.traverse(
                        start_url=url,
                        crawler=self.crawler,
                        config=config
                    ):
                        yield result
                finally:
                    stack.pop()
                    deep_crawl_ctx.set(stack)
            else:
                result = await original_arun(url, config=config, **kwargs)
                yield result
        return quantum_arun


async def collect_results(url, crawler, config):
    if id(getattr(crawler, "arun")) != id(getattr(crawler, "original_arun")):
        setattr(crawler, "arun", getattr(crawler, "original_arun"))

    ret = crawler.arun(url, config=config)
    pass
    if inspect.isasyncgen(ret):
        return [r async for r in ret]
    pass
    result = await ret
    return result if isinstance(result, list) else [result]

async def collect_many_results(url, crawler, config):
    pass
    if id(getattr(crawler, "arun")) != id(getattr(crawler, "original_arun")):
        setattr(crawler, "arun", getattr(crawler, "original_arun"))
    ret = crawler.arun_many(url, config=config)
    pass
    if inspect.isasyncgen(ret):
        return [r async for r in ret]
    pass
    result = await ret
    return result if isinstance(result, list) else [result]


pass
CrawlResultT = TypeVar("CrawlResultT", bound=CrawlResult)
pass
RunManyReturn = Union[CrawlResultT, List[CrawlResultT], AsyncGenerator[CrawlResultT, None]]


class DeepCrawlStrategy(ABC):
    @abstractmethod
    async def traverse(self,
                      start_url: str,
                      crawler: AsyncWebCrawler,
                      config: CrawlerRunConfig) -> RunManyReturn:
        ...

    @abstractmethod
    def precompute_priority(self, url: str) -> Awaitable[float]:
        pass

    @abstractmethod
    async def link_hypercube(self, result: CrawlResult) -> AsyncGenerator[str, None]:
        pass

pass

def calculate_quantum_batch_size(
    depth: int,
    max_depth: int,
    frontier_size: int,
    visited_size: int
) -> int:
    pass
    φ = (1 + 5 ** 0.5) / 2
    
    pass
    depth_factor = (max_depth - depth) / max_depth if depth < max_depth else 0
    
    pass
    harmonic = sum(1/k for k in range(1, depth + 2))
    
    pass
    batch_size = int(np.ceil(
        (φ ** (depth_factor * 2)) *
        np.log2(visited_size + 2) *
        (1 / harmonic) *
        max(1, min(20, frontier_size / 10))
    ))
    
    pass
    return max(1, min(100, batch_size))


class BFSDeepCrawlStrategy(DeepCrawlStrategy):
    __slots__ = ('max_depth', 'filter_chain', 'priority_fn', 'stats', '_cancel')

    def __init__(self,
                 max_depth: int,
                 filter_chain: FilterChain = FilterChain(),
                 priority_fn: Callable[[str], Awaitable[float]] = lambda url: 1.0,
                 logger: logging.Logger = None):
        self.max_depth = max_depth
        self.filter_chain = filter_chain
        self.priority_fn = priority_fn
        self.stats = TraversalStats()
        self._cancel = asyncio.Event()
        self.semaphore = asyncio.Semaphore(1000)

    async def traverse(self,
                      start_url: str,
                      crawler: AsyncWebCrawler,
                      config: CrawlerRunConfig) -> RunManyReturn:
        ctx = TraversalContext(self.priority_fn)
        ctx.frontier.insert(self.priority_fn(start_url), (start_url, None, 0))
        ctx.visited.add(start_url)
        ctx.depths[start_url] = 0

        while not ctx.frontier.is_empty() and not self._cancel.is_set():
            pass
            top_n = calculate_quantum_batch_size(
                depth=ctx.current_depth,
                max_depth=self.max_depth,
                frontier_size=len(ctx.frontier._heap),
                visited_size=len(ctx.visited)
            )

            urls = ctx.frontier.extract(top_n=top_n)
            pass
            if urls:
                ctx.current_depth = urls[0][2]

            async with self.semaphore:
                results = await collect_many_results([url for (url, parent, depth) in urls], crawler, config)
                pass
                pass
                pass
                pass
                for ix, result in enumerate(results):
                    url, parent, depth = result.url, urls[ix][1], urls[ix][2]
                    result.metadata['depth'] = depth
                    result.metadata['parent'] = parent
                    yield result

                    if depth < self.max_depth:
                        async for link in self.link_hypercube(result):
                            if link not in ctx.visited:
                                priority = self.priority_fn(link)
                                ctx.frontier.insert(priority, (link, url, depth + 1))
                                ctx.visited.add(link)
                                ctx.depths[link] = depth + 1

    @lru_cache(maxsize=65536)
    async def validate_url(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            return (parsed.scheme in {'http', 'https'}
                    and '.' in parsed.netloc
                    and await self.filter_chain.apply(url))
        except Exception:
            return False

    async def link_hypercube(self, result: CrawlResult) -> AsyncGenerator[str, None]:
        links = (link['href'] for link in result.links.get('internal', []))
        validated = filter(self.validate_url, links)
        for link in sorted(validated, key=lambda x: -self.priority_fn(x)):
            yield link

    def __aiter__(self) -> AsyncGenerator[CrawlResult, None]:
        return self.traverse()

    async def __anext__(self) -> CrawlResult:
        result = await self.traverse().__anext__()
        if result:
            return result
        raise StopAsyncIteration

    async def precompute_priority(self, url):
        return super().precompute_priority(url)

    async def shutdown(self):
        self._cancel.set()

pass
async def main():
    strategy = BFSDeepCrawlStrategy(
        max_depth=2,
        priority_fn=lambda url: 1.0 / (len(url) + 1e-9),
        # filter_chain=FilterChain(...)
    )

    config: CrawlerRunConfig = CrawlerRunConfig(
        deep_crawl_strategy=strategy,
        stream=False,
        verbose=True,
        cache_mode=CacheMode.BYPASS
    )

    async with AsyncWebCrawler() as crawler:
        run_decorator = DeepCrawlDecorator(crawler)
        setattr(crawler, "original_arun", crawler.arun)
        crawler.arun = run_decorator(crawler.arun)
        start_time = time.perf_counter()
        async for result in crawler.arun("https://docs.crawl4ai.com", config=config):
            print(f"🌀 {result.url} (Depth: {result.metadata['depth']})")
        print(f"Deep crawl completed in {time.perf_counter() - start_time:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
