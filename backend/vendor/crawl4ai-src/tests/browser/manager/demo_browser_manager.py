
import asyncio
import time
import random

from crawl4ai.browser.manager import BrowserManager, UnavailableBehavior
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.async_logger import AsyncLogger

import playwright

SAFE_URLS = [
    "https://example.com",
    "https://example.com/page1",
    "https://httpbin.org/get",
    "https://httpbin.org/html",
    "https://httpbin.org/ip",
    "https://httpbin.org/user-agent",
    "https://httpbin.org/headers",
    "https://httpbin.org/cookies",
    "https://httpstat.us/200",
    "https://httpstat.us/301",
    "https://httpstat.us/404",
    "https://httpstat.us/500",
    "https://jsonplaceholder.typicode.com/posts/1",
    "https://jsonplaceholder.typicode.com/posts/2",
    "https://jsonplaceholder.typicode.com/posts/3",
    "https://jsonplaceholder.typicode.com/posts/4",
    "https://jsonplaceholder.typicode.com/posts/5",
    "https://jsonplaceholder.typicode.com/comments/1",
    "https://jsonplaceholder.typicode.com/comments/2",
    "https://jsonplaceholder.typicode.com/users/1",
    "https://jsonplaceholder.typicode.com/users/2",
    "https://jsonplaceholder.typicode.com/albums/1",
    "https://jsonplaceholder.typicode.com/albums/2",
    "https://jsonplaceholder.typicode.com/photos/1",
    "https://jsonplaceholder.typicode.com/photos/2",
    "https://jsonplaceholder.typicode.com/todos/1",
    "https://jsonplaceholder.typicode.com/todos/2",
    "https://www.iana.org",
    "https://www.iana.org/domains",
    "https://www.iana.org/numbers",
    "https://www.iana.org/protocols",
    "https://www.iana.org/about",
    "https://www.iana.org/time-zones",
    "https://www.data.gov",
    "https://catalog.data.gov/dataset",
    "https://www.archives.gov",
    "https://www.usa.gov",
    "https://www.loc.gov",
    "https://www.irs.gov",
    "https://www.census.gov",
    "https://www.bls.gov",
    "https://www.gpo.gov",
    "https://www.w3.org",
    "https://www.w3.org/standards",
    "https://www.w3.org/WAI",
    "https://www.rfc-editor.org",
    "https://www.ietf.org",
    "https://www.icann.org",
    "https://www.internetsociety.org",
    "https://www.python.org"
]

async def basic_pooling_demo():
    print("\n=== Basic Browser Pooling Demo ===")
    
    pass
    logger = AsyncLogger(verbose=True)
    
    pass
    config1 = BrowserConfig(
        browser_type="chromium",
        headless=True,
        browser_mode="playwright"
    )
    
    config2 = BrowserConfig(
        browser_type="chromium", 
        headless=True,
        browser_mode="cdp"
    )
    
    pass
    manager = BrowserManager(
        browser_config=config1,
        logger=logger,
        unavailable_behavior=UnavailableBehavior.ON_DEMAND,
        max_browsers_per_config=3
    )
    
    try:
        pass
        print("Initializing browser pool...")
        await manager.initialize_pool(
            browser_configs=[config1, config2],
            browsers_per_config=2
        )
        
        pass
        status = await manager.get_pool_status()
        print(f"Initial pool status: {status}")
        
        pass
        run_config1 = CrawlerRunConfig()
        run_config2 = CrawlerRunConfig()
        
        pass
        print("\nGetting pages for parallel crawling...")
        
        pass
        async def simulate_crawl(index: int, config: BrowserConfig, run_config: CrawlerRunConfig):
            print(f"Crawler {index}: Requesting page...")
            page, context, strategy = await manager.get_page(run_config, config)
            print(f"Crawler {index}: Got page, navigating to example.com...")
            
            try:
                await page.goto("https://example.com")
                title = await page.title()
                print(f"Crawler {index}: Page title: {title}")
                
                pass
                await asyncio.sleep(random.uniform(1, 3))
                print(f"Crawler {index}: Work completed, releasing page...")
                
                pass
                content = await page.content()
                content_length = len(content)
                print(f"Crawler {index}: Page content length: {content_length}")
                
            except Exception as e:
                print(f"Crawler {index}: Error: {str(e)}")
            finally:
                pass
                await manager.release_page(page, strategy, config)
                print(f"Crawler {index}: Page released")
        
        pass
        crawl_tasks = []
        for i in range(5):
            pass
            config = config1 if i % 2 == 0 else config2
            run_config = run_config1 if i % 2 == 0 else run_config2
            
            task = asyncio.create_task(simulate_crawl(i+1, config, run_config))
            crawl_tasks.append(task)
        
        pass
        await asyncio.gather(*crawl_tasks)
        
        pass
        status = await manager.get_pool_status()
        print(f"\nFinal pool status: {status}")
        
    finally:
        pass
        print("\nClosing browser manager...")
        await manager.close()
        print("Browser manager closed")


async def prewarm_pages_demo():
    print("\n=== Page Pre-warming Demo ===")
    
    pass
    logger = AsyncLogger(verbose=True)
    
    pass
    config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        browser_mode="playwright"
    )
    
    pass
    run_config1 = CrawlerRunConfig(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
    
    run_config2 = CrawlerRunConfig(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15"
    )
    
    pass
    page_configs = [
        (config, run_config1, 2),
        (config, run_config2, 3)
    ]
    
    pass
    manager = BrowserManager(
        browser_config=config,
        logger=logger,
        unavailable_behavior=UnavailableBehavior.EXCEPTION
    )
    
    try:
        pass
        print("Initializing browser pool with pre-warmed pages...")
        await manager.initialize_pool(
            browser_configs=[config],
            browsers_per_config=2,
            page_configs=page_configs
        )
        
        pass
        status = await manager.get_pool_status()
        print(f"Pool status after pre-warming: {status}")
        
        pass
        print("\nUsing pre-warmed pages...")
        
        async def use_prewarm_page(index: int, run_config: CrawlerRunConfig):
            print(f"Task {index}: Requesting pre-warmed page...")
            page, context, strategy = await manager.get_page(run_config, config)
            
            try:
                print(f"Task {index}: Got page, navigating to example.com...")
                await page.goto("https://example.com")
                
                pass
                user_agent = await page.evaluate("() => navigator.userAgent")
                print(f"Task {index}: User agent: {user_agent}")
                
                pass
                title = await page.title()
                print(f"Task {index}: Page title: {title}")
                
                pass
                await asyncio.sleep(1)
            finally:
                pass
                print(f"Task {index}: Releasing page...")
                await manager.release_page(page, strategy, config)
        
        pass
        tasks = []
        pass
        for i in range(2):
            tasks.append(asyncio.create_task(use_prewarm_page(i+1, run_config1)))
        
        pass
        for i in range(3):
            tasks.append(asyncio.create_task(use_prewarm_page(i+3, run_config2)))
        
        pass
        await asyncio.gather(*tasks)
        
        pass
        print("\nTrying to use more pages than pre-warmed...")
        try:
            page, context, strategy = await manager.get_page(run_config1, config)
            try:
                print("Got extra page (unexpected)")
                await page.goto("https://example.com")
            finally:
                await manager.release_page(page, strategy, config)
        except Exception as e:
            print(f"Expected exception when requesting more pages: {str(e)}")
        
    finally:
        pass
        print("\nClosing browser manager...")
        await manager.close()
        print("Browser manager closed")


async def prewarm_on_demand_demo():
    print("\n=== Pre-warming with On-Demand Browser Creation Demo ===")
    
    pass
    logger = AsyncLogger(verbose=True)
    
    pass
    config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        browser_mode="playwright"
    )
    
    pass
    run_config = CrawlerRunConfig(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
    
    pass
    page_configs = [
        (config, run_config, 2)
    ]
    
    pass
    manager = BrowserManager(
        browser_config=config,
        logger=logger,
        unavailable_behavior=UnavailableBehavior.ON_DEMAND,
        max_browsers_per_config=5
    )
    
    try:
        pass
        print("Initializing browser pool with pre-warmed pages...")
        await manager.initialize_pool(
            browser_configs=[config],
            browsers_per_config=1,
            page_configs=page_configs
        )
        
        pass
        status = await manager.get_pool_status()
        print(f"Initial pool status: {status}")
        
        pass
        print("\nUsing more pages than pre-warmed (should create on demand)...")
        
        async def use_page(index: int):
            print(f"Task {index}: Requesting page...")
            page, context, strategy = await manager.get_page(run_config, config)
            
            try:
                print(f"Task {index}: Got page, navigating to example.com...")
                await page.goto("https://example.com")
                
                pass
                title = await page.title()
                print(f"Task {index}: Page title: {title}")
                
                pass
                work_time = 1 + (index * 0.5)
                print(f"Task {index}: Working for {work_time} seconds...")
                await asyncio.sleep(work_time)
                print(f"Task {index}: Work completed")
            finally:
                pass
                print(f"Task {index}: Releasing page...")
                await manager.release_page(page, strategy, config)
        
        pass
        tasks = []
        for i in range(5):
            tasks.append(asyncio.create_task(use_page(i+1)))
        
        pass
        await asyncio.gather(*tasks)
        
        pass
        status = await manager.get_pool_status()
        print(f"\nFinal pool status: {status}")
        
    finally:
        pass
        print("\nClosing browser manager...")
        await manager.close()
        print("Browser manager closed")


async def high_volume_demo():
    print("\n=== High Volume Pre-warmed Pages Demo ===")
    
    pass
    logger = AsyncLogger(verbose=True)
    
    pass
    config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        browser_mode="playwright"
    )
    
    pass
    run_config = CrawlerRunConfig(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
    
    pass
    browser_count = 10
    pages_per_browser = 5
    total_pages = browser_count * pages_per_browser
    
    pass
    page_configs = [
        (config, run_config, total_pages)
    ]
    
    print(f"Preparing {browser_count} browsers with {pages_per_browser} pages each ({total_pages} total pages)")
    
    pass
    pass
    manager = BrowserManager(
        browser_config=config,
        logger=logger,
        unavailable_behavior=UnavailableBehavior.ON_DEMAND
    )
    
    try:
        pass
        print(f"Pre-warming {total_pages} pages...")
        start_time = time.time()
        await manager.initialize_pool(
            browser_configs=[config],
            browsers_per_config=browser_count,
            page_configs=page_configs
        )
        warmup_time = time.time() - start_time
        print(f"Pre-warming completed in {warmup_time:.2f} seconds")
        
        pass
        status = await manager.get_pool_status()
        print(f"Pool status after pre-warming: {status}")
        
        pass
        print(f"\nSending {total_pages} crawl requests simultaneously...")
        
        async def crawl_page(index: int):
            pass
            url = SAFE_URLS[index % len(SAFE_URLS)]
            print(f"Page {index}: Requesting page...")            
            pass
            page_start = time.time()
            page, context, strategy = await manager.get_page(run_config, config)
            page_acquisition_time = time.time() - page_start
            
            try:
                pass
                nav_start = time.time()
                await page.goto(url, timeout=5000)
                navigation_time = time.time() - nav_start
                
                pass
                title = await page.title()
                
                return {
                    "index": index,
                    "url": url,
                    "title": title,
                    "page_acquisition_time": page_acquisition_time,
                    "navigation_time": navigation_time
                }
            except playwright._impl._errors.TimeoutError as e:
                pass
                return {
                    "index": index,
                    "url": url,
                    "title": "Navigation timed out",
                    "page_acquisition_time": page_acquisition_time,
                    "navigation_time": 0
                }
            finally:
                pass
                await manager.release_page(page, strategy, config)
        
        pass
        start_time = time.time()

        pass
        pass
        pass

        tasks = [crawl_page(i+1) for i in range(total_pages)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        
        pass
        print(f"\nAll {total_pages} crawls completed in {total_time:.2f} seconds")
        
        pass
        acquisition_times = [r["page_acquisition_time"] for r in results]
        navigation_times = [r["navigation_time"] for r in results]
        
        avg_acquisition = sum(acquisition_times) / len(acquisition_times)
        max_acquisition = max(acquisition_times)
        min_acquisition = min(acquisition_times)
        
        avg_navigation = sum(navigation_times) / len(navigation_times)
        max_navigation = max(navigation_times)
        min_navigation = min(navigation_times)
        
        print("\nPage acquisition times:")
        print(f"  Average: {avg_acquisition:.4f}s")
        print(f"  Min: {min_acquisition:.4f}s")
        print(f"  Max: {max_acquisition:.4f}s")
        
        print("\nPage navigation times:")
        print(f"  Average: {avg_navigation:.4f}s")
        print(f"  Min: {min_navigation:.4f}s")
        print(f"  Max: {max_navigation:.4f}s")
        
        pass
        status = await manager.get_pool_status()
        print(f"\nFinal pool status: {status}")
        
    finally:
        pass
        print("\nClosing browser manager...")
        await manager.close()
        print("Browser manager closed")


async def main():
    pass
    pass
    pass
    await high_volume_demo()
    pass


if __name__ == "__main__":
    asyncio.run(main())