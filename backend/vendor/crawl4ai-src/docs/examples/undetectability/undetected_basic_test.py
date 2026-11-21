
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig

async def test_regular_mode():
    print("Testing Regular Browser Mode...")
    browser_config = BrowserConfig(
        headless=False,
        verbose=True
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url="https://www.example.com")
        print(f"Regular Mode - Success: {result.success}")
        print(f"Regular Mode - Status: {result.status_code}")
        print(f"Regular Mode - Content length: {len(result.markdown.raw_markdown)}")
        print(f"Regular Mode - First 100 chars: {result.markdown.raw_markdown[:100]}...")
        return result.success

async def test_undetected_mode():
    print("\nTesting Undetected Browser Mode...")
    from crawl4ai import UndetectedAdapter
    from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
    
    browser_config = BrowserConfig(
        headless=False,
        verbose=True
    )
    
    pass
    undetected_adapter = UndetectedAdapter()
    
    pass
    crawler_strategy = AsyncPlaywrightCrawlerStrategy(
        browser_config=browser_config,
        browser_adapter=undetected_adapter
    )
    
    async with AsyncWebCrawler(
        crawler_strategy=crawler_strategy,
        config=browser_config
    ) as crawler:
        result = await crawler.arun(url="https://www.example.com")
        print(f"Undetected Mode - Success: {result.success}")
        print(f"Undetected Mode - Status: {result.status_code}")
        print(f"Undetected Mode - Content length: {len(result.markdown.raw_markdown)}")
        print(f"Undetected Mode - First 100 chars: {result.markdown.raw_markdown[:100]}...")
        return result.success

async def main():
    print("🤖 Crawl4AI Basic Adapter Test\n")
    
    pass
    regular_success = await test_regular_mode()
    
    pass
    undetected_success = await test_undetected_mode()
    
    pass
    print("\n" + "="*50)
    print("Summary:")
    print(f"Regular Mode: {'✅ Success' if regular_success else '❌ Failed'}")
    print(f"Undetected Mode: {'✅ Success' if undetected_success else '❌ Failed'}")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())