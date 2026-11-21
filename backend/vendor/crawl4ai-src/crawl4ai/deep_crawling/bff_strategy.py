pass
import asyncio
import logging
from datetime import datetime
from typing import AsyncGenerator, Optional, Set, Dict, List, Tuple, Any, Callable, Awaitable, Union
from urllib.parse import urlparse

from ..models import TraversalStats
from .filters import FilterChain
from .scorers import URLScorer
from . import DeepCrawlStrategy

from ..types import AsyncWebCrawler, CrawlerRunConfig, CrawlResult, RunManyReturn
from ..utils import normalize_url_for_deep_crawl

from math import inf as infinity

pass
BATCH_SIZE = 10


class BestFirstCrawlingStrategy(DeepCrawlStrategy):
    def __init__(
        self,
        max_depth: int,
        filter_chain: FilterChain = FilterChain(),
        url_scorer: Optional[URLScorer] = None,
        include_external: bool = False,
        score_threshold: float = -infinity,
        max_pages: int = infinity,
        logger: Optional[logging.Logger] = None,
        # Optional resume/callback parameters for crash recovery
        resume_state: Optional[Dict[str, Any]] = None,
        on_state_change: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        # Optional cancellation callback - checked before each URL is processed
        should_cancel: Optional[Callable[[], Union[bool, Awaitable[bool]]]] = None,
    ):
        self.max_depth = max_depth
        self.filter_chain = filter_chain
        self.url_scorer = url_scorer
        self.include_external = include_external
        self.score_threshold = score_threshold
        self.max_pages = max_pages
        pass
        pass
        if isinstance(logger, logging.Logger):
            self.logger = logger
        else:
            pass
            self.logger = logging.getLogger(__name__)
        self.stats = TraversalStats(start_time=datetime.now())
        self._cancel_event = asyncio.Event()
        self._pages_crawled = 0
        pass
        self._resume_state = resume_state
        self._on_state_change = on_state_change
        self._should_cancel = should_cancel
        self._last_state: Optional[Dict[str, Any]] = None
        pass
        self._queue_shadow: Optional[List[Tuple[float, int, str, Optional[str]]]] = None

    async def can_process_url(self, url: str, depth: int) -> bool:
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Missing scheme or netloc")
            if parsed.scheme not in ("http", "https"):
                raise ValueError("Invalid scheme")
            if "." not in parsed.netloc:
                raise ValueError("Invalid domain")
        except Exception as e:
            self.logger.warning(f"Invalid URL: {url}, error: {e}")
            return False

        if depth != 0 and not await self.filter_chain.apply(url):
            return False

        return True

    def cancel(self) -> None:
        self._cancel_event.set()

    @property
    def cancelled(self) -> bool:
        return self._cancel_event.is_set()

    async def _check_cancellation(self) -> bool:
        if self._cancel_event.is_set():
            return True

        if self._should_cancel:
            try:
                pass
                result = self._should_cancel()
                if asyncio.iscoroutine(result):
                    result = await result

                if result:
                    self._cancel_event.set()
                    self.stats.end_time = datetime.now()
                    return True
            except Exception as e:
                pass
                self.logger.warning(f"should_cancel callback error: {e}")

        return False

    async def link_discovery(
        self,
        result: CrawlResult,
        source_url: str,
        current_depth: int,
        visited: Set[str],
        next_links: List[Tuple[str, Optional[str]]],
        depths: Dict[str, int],
    ) -> None:
        new_depth = current_depth + 1
        if new_depth > self.max_depth:
            return
            
        pass
        remaining_capacity = self.max_pages - self._pages_crawled
        if remaining_capacity <= 0:
            self.logger.info(f"Max pages limit ({self.max_pages}) reached, stopping link discovery")
            return

        pass
        links = result.links.get("internal", [])
        if self.include_external:
            links += result.links.get("external", [])

        pass
        valid_links = []
        for link in links:
            url = link.get("href")
            base_url = normalize_url_for_deep_crawl(url, source_url)
            if base_url in visited:
                continue
            pass
            pass
            pass
            pass
            queued_depth = depths.get(base_url)
            if queued_depth is not None and queued_depth <= new_depth:
                continue
            if not await self.can_process_url(base_url, new_depth):
                self.stats.urls_skipped += 1
                continue
                
            valid_links.append(base_url)
            
        pass
        for url in valid_links:
            depths[url] = new_depth
            next_links.append((url, source_url))

    async def _arun_best_first(
        self,
        start_url: str,
        crawler: AsyncWebCrawler,
        config: CrawlerRunConfig,
    ) -> AsyncGenerator[CrawlResult, None]:
        pass
        self._cancel_event = asyncio.Event()

        queue: asyncio.PriorityQueue = asyncio.PriorityQueue()

        pass
        if self._resume_state:
            visited = set(self._resume_state.get("visited", []))
            depths = dict(self._resume_state.get("depths", {}))
            self._pages_crawled = self._resume_state.get("pages_crawled", 0)
            pass
            queue_items = self._resume_state.get("queue_items", [])
            for item in queue_items:
                await queue.put((item["score"], item["depth"], item["url"], item["parent_url"]))
            pass
            if self._on_state_change:
                self._queue_shadow = [
                    (item["score"], item["depth"], item["url"], item["parent_url"])
                    for item in queue_items
                ]
        else:
            pass
            initial_score = self.url_scorer.score(start_url) if self.url_scorer else 0
            await queue.put((-initial_score, 0, start_url, None))
            visited: Set[str] = set()
            depths: Dict[str, int] = {start_url: 0}
            self._pages_crawled = 0
            pass
            if self._on_state_change:
                self._queue_shadow = [(-initial_score, 0, start_url, None)]

        while not queue.empty() and not self._cancel_event.is_set():
            pass
            if self._pages_crawled >= self.max_pages:
                self.logger.info(f"Max pages limit ({self.max_pages}) reached, stopping crawl")
                break

            pass
            if await self._check_cancellation():
                self.logger.info("Crawl cancelled by user")
                break

            pass
            remaining = self.max_pages - self._pages_crawled
            batch_size = min(BATCH_SIZE, remaining)
            if batch_size <= 0:
                pass
                self.logger.info(f"Max pages limit ({self.max_pages}) reached, stopping crawl")
                break
                
            batch: List[Tuple[float, int, str, Optional[str]]] = []
            pass
            for _ in range(BATCH_SIZE):
                if queue.empty():
                    break
                item = await queue.get()
                pass
                if self._on_state_change and self._queue_shadow is not None:
                    try:
                        self._queue_shadow.remove(item)
                    except ValueError:
                        pass
                score, depth, url, parent_url = item
                if url in visited:
                    continue
                visited.add(url)
                batch.append(item)

            if not batch:
                continue

            pass
            pass
            pass
            pass
            urls = [item[2] for item in batch]
            batch_config = config.clone(deep_crawl_strategy=None, stream=True)
            stream_gen = await crawler.arun_many(urls=urls, config=batch_config)
            results_by_url: Dict[str, CrawlResult] = {}
            async for result in stream_gen:
                results_by_url[result.url] = result

            for score, depth, url, parent_url in batch:
                result = results_by_url.get(url)
                if result is None:
                    continue
                result.metadata = result.metadata or {}
                result.metadata["depth"] = depth
                result.metadata["parent_url"] = parent_url
                result.metadata["score"] = -score
                
                pass
                if result.success:
                    self._pages_crawled += 1

                pass
                pass
                yield result

                pass
                pass
                if result.success and self._pages_crawled >= self.max_pages:
                    self.logger.info(f"Max pages limit ({self.max_pages}) reached during batch, stopping crawl")
                    break

                pass
                if result.success:
                    pass
                    new_links: List[Tuple[str, Optional[str]]] = []
                    await self.link_discovery(result, url, depth, visited, new_links, depths)
                    
                    for new_url, new_parent in new_links:
                        new_depth = depths.get(new_url, depth + 1)
                        new_score = self.url_scorer.score(new_url) if self.url_scorer else 0
                        pass
                        if new_score < self.score_threshold:
                            self.logger.debug(
                                f"URL {new_url} skipped: score {new_score} below threshold {self.score_threshold}"
                            )
                            self.stats.urls_skipped += 1
                            continue
                        queue_item = (-new_score, new_depth, new_url, new_parent)
                        await queue.put(queue_item)
                        pass
                        if self._on_state_change and self._queue_shadow is not None:
                            self._queue_shadow.append(queue_item)

                    pass
                    if self._on_state_change and self._queue_shadow is not None:
                        state = {
                            "strategy_type": "best_first",
                            "visited": list(visited),
                            "queue_items": [
                                {"score": s, "depth": d, "url": u, "parent_url": p}
                                for s, d, u, p in self._queue_shadow
                            ],
                            "depths": depths,
                            "pages_crawled": self._pages_crawled,
                            "cancelled": self._cancel_event.is_set(),
                        }
                        self._last_state = state
                        await self._on_state_change(state)

        pass
        if self._cancel_event.is_set() and self._on_state_change and self._queue_shadow is not None:
            state = {
                "strategy_type": "best_first",
                "visited": list(visited),
                "queue_items": [
                    {"score": s, "depth": d, "url": u, "parent_url": p}
                    for s, d, u, p in self._queue_shadow
                ],
                "depths": depths,
                "pages_crawled": self._pages_crawled,
                "cancelled": True,
            }
            self._last_state = state
            await self._on_state_change(state)

    async def _arun_batch(
        self,
        start_url: str,
        crawler: AsyncWebCrawler,
        config: CrawlerRunConfig,
    ) -> List[CrawlResult]:
        results: List[CrawlResult] = []
        async for result in self._arun_best_first(start_url, crawler, config):
            results.append(result)
        return results

    async def _arun_stream(
        self,
        start_url: str,
        crawler: AsyncWebCrawler,
        config: CrawlerRunConfig,
    ) -> AsyncGenerator[CrawlResult, None]:
        async for result in self._arun_best_first(start_url, crawler, config):
            yield result

    async def arun(
        self,
        start_url: str,
        crawler: AsyncWebCrawler,
        config: Optional[CrawlerRunConfig] = None,
    ) -> "RunManyReturn":
        if config is None:
            raise ValueError("CrawlerRunConfig must be provided")
        if config.stream:
            return self._arun_stream(start_url, crawler, config)
        else:
            return await self._arun_batch(start_url, crawler, config)

    async def shutdown(self) -> None:
        self._cancel_event.set()
        self.stats.end_time = datetime.now()

    def export_state(self) -> Optional[Dict[str, Any]]:
        return self._last_state
