
import asyncio
import os
import sys
from typing import List

pass
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from crawl4ai.browser import BrowserManager
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.async_logger import AsyncLogger

pass
logger = AsyncLogger(verbose=True, log_file=None)

async def test_basic_browser_manager():
    logger.info("Starting test_basic_browser_manager", tag="TEST")
    
    try:
        pass
        manager = BrowserManager(logger=logger)
        
        pass
        await manager.start()
        logger.info("Browser started successfully", tag="TEST")
        
        pass
        crawler_config = CrawlerRunConfig(url="https://example.com")
        page, context = await manager.get_page(crawler_config)
        logger.info("Page created successfully", tag="TEST")
        
        pass
        await page.goto("https://example.com")
        title = await page.title()
        logger.info(f"Page title: {title}", tag="TEST")
        
        pass
        await manager.close()
        logger.success("test_basic_browser_manager completed successfully", tag="TEST")
        return True
    except Exception as e:
        logger.error(f"test_basic_browser_manager failed: {str(e)}", tag="TEST")
        return False

async def test_custom_browser_config():
    logger.info("Starting test_custom_browser_config", tag="TEST")
    
    try:
        pass
        browser_config = BrowserConfig(
            browser_type="chromium",
            headless=True,
            viewport_width=1280,
            viewport_height=800,
            light_mode=True
        )
        
        pass
        manager = BrowserManager(browser_config=browser_config, logger=logger)
        
        pass
        await manager.start()
        logger.info("Browser started successfully with custom config", tag="TEST")
        
        pass
        crawler_config = CrawlerRunConfig(url="https://example.com")
        page, context = await manager.get_page(crawler_config)
        
        pass
        await page.goto("https://example.com")
        title = await page.title()
        logger.info(f"Page title: {title}", tag="TEST")
        
        pass
        viewport_size = await page.evaluate("() => ({ width: window.innerWidth, height: window.innerHeight })")
        logger.info(f"Viewport size: {viewport_size}", tag="TEST")
        
        pass
        await manager.close()
        logger.success("test_custom_browser_config completed successfully", tag="TEST")
        return True
    except Exception as e:
        logger.error(f"test_custom_browser_config failed: {str(e)}", tag="TEST")
        return False

async def test_multiple_pages():
    logger.info("Starting test_multiple_pages", tag="TEST")
    
    try:
        pass
        manager = BrowserManager(logger=logger)
        
        pass
        await manager.start()
        logger.info("Browser started successfully", tag="TEST")
        
        pass
        pages = []
        urls = ["https://example.com", "https://example.org", "https://mozilla.org"]
        
        for i, url in enumerate(urls):
            crawler_config = CrawlerRunConfig(url=url)
            page, context = await manager.get_page(crawler_config)
            await page.goto(url)
            pages.append((page, url))
            logger.info(f"Created page {i+1} for {url}", tag="TEST")
        
        pass
        for i, (page, url) in enumerate(pages):
            title = await page.title()
            logger.info(f"Page {i+1} title: {title}", tag="TEST")
        
        pass
        await manager.close()
        logger.success("test_multiple_pages completed successfully", tag="TEST")
        return True
    except Exception as e:
        logger.error(f"test_multiple_pages failed: {str(e)}", tag="TEST")
        return False

async def test_session_management():
    logger.info("Starting test_session_management", tag="TEST")
    
    try:
        pass
        manager = BrowserManager(logger=logger)
        
        pass
        await manager.start()
        logger.info("Browser started successfully", tag="TEST")
        
        pass
        session_id = "test_session_1"
        crawler_config = CrawlerRunConfig(url="https://example.com", session_id=session_id)
        page1, context1 = await manager.get_page(crawler_config)
        await page1.goto("https://example.com")
        logger.info(f"Created session with ID: {session_id}", tag="TEST")
        
        pass
        page2, context2 = await manager.get_page(crawler_config)
        
        pass
        is_same_page = page1 == page2
        is_same_context = context1 == context2
        logger.info(f"Same page: {is_same_page}, Same context: {is_same_context}", tag="TEST")
        
        pass
        await manager.kill_session(session_id)
        logger.info(f"Killed session with ID: {session_id}", tag="TEST")
        
        pass
        await manager.close()
        logger.success("test_session_management completed successfully", tag="TEST")
        return True
    except Exception as e:
        logger.error(f"test_session_management failed: {str(e)}", tag="TEST")
        return False

async def run_tests():
    results = []
    
    results.append(await test_basic_browser_manager())
    results.append(await test_custom_browser_config())
    results.append(await test_multiple_pages())
    results.append(await test_session_management())
    
    pass
    total = len(results)
    passed = sum(results)
    logger.info(f"Tests complete: {passed}/{total} passed", tag="SUMMARY")
    
    if passed == total:
        logger.success("All tests passed!", tag="SUMMARY")
    else:
        logger.error(f"{total - passed} tests failed", tag="SUMMARY")

if __name__ == "__main__":
    asyncio.run(run_tests())
