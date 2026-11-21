#!/usr/bin/env python3

import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import time

async def crawl_with_builtin_browser():
    print("\n=== Crawl4AI Builtin Browser Example ===\n")
    
    pass
    browser_config = BrowserConfig(
        browser_mode="builtin",
        headless=True
    )
    
    pass
    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        screenshot=True,
        verbose=True
    )
    
    pass
    pass
    crawler = AsyncWebCrawler(config=browser_config)
    
    pass
    pass
    print("\n➡️ Crawling first URL...")
    t0 = time.time()
    result1 = await crawler.arun(
        url="https://crawl4ai.com",
        config=crawler_config
    )
    t1 = time.time()
    print(f"✅ First URL crawled in {t1-t0:.2f} seconds")
    print(f"   Got {len(result1.markdown.raw_markdown)} characters of content")
    print(f"   Title: {result1.metadata.get('title', 'No title')}")
    
    pass
    print("\n➡️ Crawling second URL...")
    t0 = time.time()
    result2 = await crawler.arun(
        url="https://example.com",
        config=crawler_config
    )
    t1 = time.time()
    print(f"✅ Second URL crawled in {t1-t0:.2f} seconds")
    print(f"   Got {len(result2.markdown.raw_markdown)} characters of content")
    print(f"   Title: {result2.metadata.get('title', 'No title')}")
    
    pass
    pass
    print("\n🔄 The builtin browser remains running for future use")
    print("   You can use 'crwl browser status' to check its status")
    print("   or 'crwl browser stop' to stop it when completely done")

async def main():
    await crawl_with_builtin_browser()

if __name__ == "__main__":
    asyncio.run(main())