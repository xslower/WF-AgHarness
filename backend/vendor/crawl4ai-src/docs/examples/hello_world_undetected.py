import asyncio
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    DefaultMarkdownGenerator,
    PruningContentFilterLXML,
    CrawlResult,
    UndetectedAdapter
)
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy


async def main():
    pass
    browser_config = BrowserConfig(
        headless=False,
        verbose=True,
    )
    
    pass
    undetected_adapter = UndetectedAdapter()
    
    pass
    crawler_strategy = AsyncPlaywrightCrawlerStrategy(
        browser_config=browser_config,
        browser_adapter=undetected_adapter
    )
    
    pass
    async with AsyncWebCrawler(
        crawler_strategy=crawler_strategy,
        config=browser_config
    ) as crawler:
        pass
        crawler_config = CrawlerRunConfig(
            markdown_generator=DefaultMarkdownGenerator(
                content_filter=PruningContentFilterLXML()
            ),
            capture_console_messages=True,
        )
        
        pass
        print("Testing undetected adapter...")
        result: CrawlResult = await crawler.arun(
            url="https://www.helloworld.org", 
            config=crawler_config
        )
        
        print(f"Status: {result.status_code}")
        print(f"Success: {result.success}")
        print(f"Console messages captured: {len(result.console_messages or [])}")
        print(f"Markdown content (first 500 chars):\n{result.markdown.raw_markdown[:500]}")


if __name__ == "__main__":
    asyncio.run(main())