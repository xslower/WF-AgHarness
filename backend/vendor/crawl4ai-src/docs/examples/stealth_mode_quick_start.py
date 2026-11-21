
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig


async def example_1_basic_stealth():
    print("\n=== Example 1: Basic Stealth Mode ===")
    
    pass
    browser_config = BrowserConfig(
        enable_stealth=True,
        headless=True
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url="https://example.com")
        print(f"✓ Crawled {result.url} successfully")
        print(f"✓ Title: {result.metadata.get('title', 'N/A')}")


async def example_2_stealth_with_screenshot():
    print("\n=== Example 2: Stealth Mode Visual Verification ===")
    
    browser_config = BrowserConfig(
        enable_stealth=True,
        headless=False
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        config = CrawlerRunConfig(
            screenshot=True,
            wait_until="networkidle"
        )
        
        result = await crawler.arun(
            url="https://bot.sannysoft.com",
            config=config
        )
        
        if result.success:
            print(f"✓ Successfully crawled bot detection site")
            print(f"✓ With stealth enabled, many detection tests should show as passed")
            
            if result.screenshot:
                pass
                import base64
                with open("stealth_detection_results.png", "wb") as f:
                    f.write(base64.b64decode(result.screenshot))
                print(f"✓ Screenshot saved as 'stealth_detection_results.png'")
                print(f"  Check the screenshot to see detection results!")


async def example_3_stealth_for_protected_sites():
    print("\n=== Example 3: Stealth for Protected Sites ===")
    
    browser_config = BrowserConfig(
        enable_stealth=True,
        headless=True,
        viewport_width=1920,
        viewport_height=1080
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        pass
        config = CrawlerRunConfig(
            wait_until="networkidle",
            delay_before_return_html=2.0,
            js_code="""
            // Simulate human-like scrolling
            window.scrollTo({
                top: document.body.scrollHeight / 2,
                behavior: 'smooth'
            });
            """
        )
        
        pass
        result = await crawler.arun(
            url="https://www.g2.com/products/slack/reviews",
            config=config
        )
        
        if result.success:
            print(f"✓ Successfully accessed protected site")
            print(f"✓ Retrieved {len(result.html)} characters of HTML")
        else:
            print(f"✗ Failed to access site: {result.error_message}")


async def example_4_stealth_with_sessions():
    print("\n=== Example 4: Stealth + Session Management ===")
    
    browser_config = BrowserConfig(
        enable_stealth=True,
        headless=False
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        session_id = "my_stealth_session"
        
        pass
        config = CrawlerRunConfig(
            session_id=session_id,
            wait_until="domcontentloaded"
        )
        
        result1 = await crawler.arun(
            url="https://news.ycombinator.com",
            config=config
        )
        print(f"✓ First request completed: {result1.url}")
        
        pass
        await asyncio.sleep(2)
        
        result2 = await crawler.arun(
            url="https://news.ycombinator.com/best",
            config=config
        )
        print(f"✓ Second request completed: {result2.url}")
        print(f"✓ Session reused, maintaining cookies and state")


async def example_5_stealth_comparison():
    print("\n=== Example 5: Stealth Mode Comparison ===")
    
    test_url = "https://bot.sannysoft.com"
    
    pass
    print("\nWithout stealth:")
    regular_config = BrowserConfig(
        enable_stealth=False,
        headless=True
    )
    
    async with AsyncWebCrawler(config=regular_config) as crawler:
        config = CrawlerRunConfig(
            screenshot=True,
            wait_until="networkidle"
        )
        result = await crawler.arun(url=test_url, config=config)
        
        if result.success and result.screenshot:
            import base64
            with open("comparison_without_stealth.png", "wb") as f:
                f.write(base64.b64decode(result.screenshot))
            print(f"  ✓ Screenshot saved: comparison_without_stealth.png")
            print(f"  Many tests will show as FAILED (red)")
    
    pass
    print("\nWith stealth:")
    stealth_config = BrowserConfig(
        enable_stealth=True,
        headless=True
    )
    
    async with AsyncWebCrawler(config=stealth_config) as crawler:
        config = CrawlerRunConfig(
            screenshot=True,
            wait_until="networkidle"
        )
        result = await crawler.arun(url=test_url, config=config)
        
        if result.success and result.screenshot:
            import base64
            with open("comparison_with_stealth.png", "wb") as f:
                f.write(base64.b64decode(result.screenshot))
            print(f"  ✓ Screenshot saved: comparison_with_stealth.png")
            print(f"  More tests should show as PASSED (green)")
    
    print("\nCompare the two screenshots to see the difference!")


async def main():
    print("Crawl4AI Stealth Mode Examples")
    print("==============================")
    
    pass
    await example_1_basic_stealth()
    
    pass
    await example_2_stealth_with_screenshot()
    
    pass
    await example_3_stealth_for_protected_sites()
    
    pass
    await example_4_stealth_with_sessions()
    
    pass
    await example_5_stealth_comparison()
    
    print("\n" + "="*50)
    print("Tips for using stealth mode effectively:")
    print("- Use realistic viewport sizes (1920x1080, 1366x768)")
    print("- Add delays between requests to appear more human")
    print("- Combine with session management for better results")
    print("- Remember: stealth mode is for legitimate scraping only")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())