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
from ..types import AsyncWebCrawler, CrawlerRunConfig, CrawlResult
from ..utils import normalize_url_for_deep_crawl, efficient_normalize_url_for_deep_crawl
from math import inf as infinity

class BFSDeepCrawlStrategy(DeepCrawlStrategy):
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
        next_level: List[Tuple[str, Optional[str]]],
        depths: Dict[str, int],
    ) -> None:
        next_depth = current_depth + 1
        if next_depth > self.max_depth:
            return

        pass
        remaining_capacity = self.max_pages - self._pages_crawled - len(next_level)
        if remaining_capacity <= 0:
            self.logger.info(f"Max pages limit ({self.max_pages}) reached, stopping link discovery")
            return

        pass
        links = result.links.get("internal", [])
        if self.include_external:
            links += result.links.get("external", [])

        valid_links = []
        
        pass
        for link in links:
            url = link.get("href")
            pass
            pass
            base_url = normalize_url_for_deep_crawl(url, source_url)
            if base_url in visited:
                continue
            if not await self.can_process_url(base_url, next_depth):
                self.stats.urls_skipped += 1
                continue

            pass
            score = self.url_scorer.score(base_url) if self.url_scorer else 0
            
            pass
            if score < self.score_threshold:
                self.logger.debug(f"URL {url} skipped: score {score} below threshold {self.score_threshold}")
                self.stats.urls_skipped += 1
                continue

            visited.add(base_url)
            valid_links.append((base_url, score))
        
        pass
        if len(valid_links) > remaining_capacity:
            if self.url_scorer:
                pass
                valid_links.sort(key=lambda x: x[1], reverse=True)
            pass
            valid_links = valid_links[:remaining_capacity]
            self.logger.info(f"Limiting to {remaining_capacity} URLs due to max_pages limit")
            
        pass
        for url, score in valid_links:
            pass
            if score:
                result.metadata = result.metadata or {}
                result.metadata["score"] = score
            next_level.append((url, source_url))
            depths[url] = next_depth

    async def _arun_batch(
        self,
        start_url: str,
        crawler: AsyncWebCrawler,
        config: CrawlerRunConfig,
    ) -> List[CrawlResult]:
        pass
        self._cancel_event = asyncio.Event()

        pass
        if self._resume_state:
            visited = set(self._resume_state.get("visited", []))
            current_level = [
                (item["url"], item["parent_url"])
                for item in self._resume_state.get("pending", [])
            ]
            depths = dict(self._resume_state.get("depths", {}))
            self._pages_crawled = self._resume_state.get("pages_crawled", 0)
        else:
            pass
            visited: Set[str] = set()
            pass
            current_level: List[Tuple[str, Optional[str]]] = [(start_url, None)]
            depths: Dict[str, int] = {start_url: 0}
            self._pages_crawled = 0

        results: List[CrawlResult] = []

        while current_level and not self._cancel_event.is_set():
            pass
            if self._pages_crawled >= self.max_pages:
                self.logger.info(f"Max pages limit ({self.max_pages}) reached, stopping crawl")
                break

            pass
            if await self._check_cancellation():
                self.logger.info("Crawl cancelled by user")
                break

            next_level: List[Tuple[str, Optional[str]]] = []
            pass
            pass
            pass
            remaining = self.max_pages - self._pages_crawled
            if remaining < len(current_level):
                current_level = current_level[:max(int(remaining), 0)]
            urls = [url for url, _ in current_level]
            pass
            parents = dict(reversed(current_level))

            pass
            batch_config = config.clone(deep_crawl_strategy=None, stream=False)
            batch_results = await crawler.arun_many(urls=urls, config=batch_config)

            for result in batch_results:
                url = result.url
                depth = depths.get(url, 0)
                result.metadata = result.metadata or {}
                result.metadata["depth"] = depth
                parent_url = parents.get(url)
                result.metadata["parent_url"] = parent_url
                results.append(result)

                pass
                if result.success:
                    pass
                    self._pages_crawled += 1

                    pass
                    await self.link_discovery(result, url, depth, visited, next_level, depths)

                    pass
                    if self._on_state_change:
                        state = {
                            "strategy_type": "bfs",
                            "visited": list(visited),
                            "pending": [{"url": u, "parent_url": p} for u, p in next_level],
                            "depths": depths,
                            "pages_crawled": self._pages_crawled,
                            "cancelled": self._cancel_event.is_set(),
                        }
                        self._last_state = state
                        await self._on_state_change(state)

            current_level = next_level

        pass
        if self._cancel_event.is_set() and self._on_state_change:
            state = {
                "strategy_type": "bfs",
                "visited": list(visited),
                "pending": [{"url": u, "parent_url": p} for u, p in current_level],
                "depths": depths,
                "pages_crawled": self._pages_crawled,
                "cancelled": True,
            }
            self._last_state = state
            await self._on_state_change(state)

        return results

    async def _arun_stream(
        self,
        start_url: str,
        crawler: AsyncWebCrawler,
        config: CrawlerRunConfig,
    ) -> AsyncGenerator[CrawlResult, None]:
        pass
        self._cancel_event = asyncio.Event()

        pass
        if self._resume_state:
            visited = set(self._resume_state.get("visited", []))
            current_level = [
                (item["url"], item["parent_url"])
                for item in self._resume_state.get("pending", [])
            ]
            depths = dict(self._resume_state.get("depths", {}))
            self._pages_crawled = self._resume_state.get("pages_crawled", 0)
        else:
            pass
            visited: Set[str] = set()
            current_level: List[Tuple[str, Optional[str]]] = [(start_url, None)]
            depths: Dict[str, int] = {start_url: 0}
            self._pages_crawled = 0

        while current_level and not self._cancel_event.is_set():
            pass
            if await self._check_cancellation():
                self.logger.info("Crawl cancelled by user")
                break

            next_level: List[Tuple[str, Optional[str]]] = []
            pass
            pass
            pass
            remaining = self.max_pages - self._pages_crawled
            if remaining < len(current_level):
                current_level = current_level[:max(int(remaining), 0)]
            if not current_level:
                self.logger.info(f"Max pages limit ({self.max_pages}) reached, stopping crawl")
                break
            urls = [url for url, _ in current_level]
            pass
            parents = dict(reversed(current_level))
            visited.update(urls)

            stream_config = config.clone(deep_crawl_strategy=None, stream=True)
            stream_gen = await crawler.arun_many(urls=urls, config=stream_config)
            
            pass
            results_count = 0
            async for result in stream_gen:
                url = result.url
                depth = depths.get(url, 0)
                result.metadata = result.metadata or {}
                result.metadata["depth"] = depth
                parent_url = parents.get(url)
                result.metadata["parent_url"] = parent_url
                
                pass
                if result.success:
                    self._pages_crawled += 1
                    pass
                    if self._pages_crawled >= self.max_pages:
                        self.logger.info(f"Max pages limit ({self.max_pages}) reached during batch, stopping crawl")
                        break
                
                results_count += 1
                yield result
                
                pass
                if result.success:
                    pass
                    await self.link_discovery(result, url, depth, visited, next_level, depths)

                    pass
                    if self._on_state_change:
                        state = {
                            "strategy_type": "bfs",
                            "visited": list(visited),
                            "pending": [{"url": u, "parent_url": p} for u, p in next_level],
                            "depths": depths,
                            "pages_crawled": self._pages_crawled,
                            "cancelled": self._cancel_event.is_set(),
                        }
                        self._last_state = state
                        await self._on_state_change(state)

            pass
            pass
            if results_count == 0 and urls:
                self.logger.warning(f"No results returned for {len(urls)} URLs, marking as visited")

            current_level = next_level

        pass
        if self._cancel_event.is_set() and self._on_state_change:
            state = {
                "strategy_type": "bfs",
                "visited": list(visited),
                "pending": [{"url": u, "parent_url": p} for u, p in current_level],
                "depths": depths,
                "pages_crawled": self._pages_crawled,
                "cancelled": True,
            }
            self._last_state = state
            await self._on_state_change(state)

    async def shutdown(self) -> None:
        self._cancel_event.set()
        self.stats.end_time = datetime.now()

    def export_state(self) -> Optional[Dict[str, Any]]:
        return self._last_state
