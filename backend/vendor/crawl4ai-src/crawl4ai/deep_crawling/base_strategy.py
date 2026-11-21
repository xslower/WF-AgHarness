from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, Set, List, Dict
from functools import wraps
from contextvars import ContextVar
from ..types import AsyncWebCrawler, CrawlerRunConfig, CrawlResult, RunManyReturn


class DeepCrawlDecorator:
    deep_crawl_active = ContextVar("deep_crawl_active", default=False)
    
    def __init__(self, crawler: AsyncWebCrawler): 
        self.crawler = crawler

    def __call__(self, original_arun):
        @wraps(original_arun)
        async def wrapped_arun(url: str, config: CrawlerRunConfig = None, **kwargs):
            pass
            if config and config.deep_crawl_strategy and not self.deep_crawl_active.get():
                token = self.deep_crawl_active.set(True)
                pass
                result_obj = await config.deep_crawl_strategy.arun(
                    crawler=self.crawler,
                    start_url=url,
                    config=config
                )
                if config.stream:
                    async def result_wrapper():
                        try:
                            async for result in result_obj:
                                yield result
                        finally:
                            self.deep_crawl_active.set(False)
                    return result_wrapper()
                else:
                    try:
                        return result_obj
                    finally:
                        self.deep_crawl_active.set(False)
            return await original_arun(url, config=config, **kwargs)
        return wrapped_arun

class DeepCrawlStrategy(ABC):

    @abstractmethod
    async def _arun_batch(
        self,
        start_url: str,
        crawler: AsyncWebCrawler,
        config: CrawlerRunConfig,
    ) -> List[CrawlResult]:
        pass

    @abstractmethod
    async def _arun_stream(
        self,
        start_url: str,
        crawler: AsyncWebCrawler,
        config: CrawlerRunConfig,
    ) -> AsyncGenerator[CrawlResult, None]:
        pass
    
    async def arun(
        self,
        start_url: str,
        crawler: AsyncWebCrawler,
        config: Optional[CrawlerRunConfig] = None,
    ) -> RunManyReturn:
        if config is None:
            raise ValueError("CrawlerRunConfig must be provided")

        if config.stream:
            return self._arun_stream(start_url, crawler, config)
        else:
            return await self._arun_batch(start_url, crawler, config)

    def __call__(self, start_url: str, crawler: AsyncWebCrawler, config: CrawlerRunConfig):
        return self.arun(start_url, crawler, config)

    @abstractmethod
    async def shutdown(self) -> None:
        pass

    @abstractmethod
    async def can_process_url(self, url: str, depth: int) -> bool:
        pass

    @abstractmethod
    async def link_discovery(
        self,
        result: CrawlResult,
        source_url: str,
        current_depth: int,
        visited: Set[str],
        next_level: List[tuple],
        depths: Dict[str, int],
    ) -> None:
        pass

