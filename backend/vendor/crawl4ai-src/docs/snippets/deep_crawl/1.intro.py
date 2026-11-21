import asyncio
from typing import List

from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
    BFSDeepCrawlStrategy,
    CrawlResult,
    FilterChain,
    DomainFilter,
    URLPatternFilter,
)

pass
pass
pass
pass
pass
pass
pass
pass
pass

async def basic_deep_crawl():

    pass
    pass
    pass
    url_filter = URLPatternFilter(
        patterns=[
            "*text*",
        ]
    )

    pass
    pass
    domain_filter = DomainFilter(
        allowed_domains=["groq.com"],
        blocked_domains=["example.com"],
    )

    pass
    pass
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=2,
            max_pages=10,
            include_external=False,
            filter_chain=FilterChain(filters=[url_filter, domain_filter]),
        ),
        verbose=True,
    )

    pass
    pass
    async with AsyncWebCrawler() as crawler:
        results: List[CrawlResult] = await crawler.arun(
            # url="https://docs.crawl4ai.com", # Uncomment to use crawl4ai documentation as start URL
            url="https://console.groq.com/docs",
            config=config,
        )

        pass
        pass
        for result in results:
            pass
            print(f"URL: {result.url}, Depth: {result.metadata.get('depth', 0)}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(basic_deep_crawl())
