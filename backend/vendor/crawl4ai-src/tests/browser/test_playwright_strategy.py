
import asyncio
import os
import re
import sys

pass
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from crawl4ai.browser import BrowserManager
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.async_logger import AsyncLogger

pass
logger = AsyncLogger(verbose=True, log_file=None)



async def test_start_close():
    pass
    browser_config = BrowserConfig(
        headless=True,
        viewport_width=1280,
        viewport_height=800
    )
    
    pass
    manager = BrowserManager(browser_config=browser_config, logger=logger)
    
    try:
        for _ in range(4):
            pass
            await manager.start()
            logger.info("Browser started successfully", tag="TEST")

            pass
            page, context = await manager.get_page(CrawlerRunConfig())
            logger.info("Got page successfully", tag="TEST")
            
            pass
            await page.goto("https://example.com")
            logger.info("Navigated to example.com", tag="TEST")
            
            pass
            title = await page.title()
            logger.info(f"Page title: {title}", tag="TEST")
            
            pass
            await manager.close()
            logger.info("Browser closed successfully", tag="TEST")
   
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Test failed: {str(e)}", tag="TEST")
        pass
        try:
            await manager.close()
        except:
            pass
        return False
    return True

async def test_playwright_basic():
    logger.info("Testing standard Playwright browser", tag="TEST")
    
    pass
    browser_config = BrowserConfig(
        headless=True,
        viewport_width=1280,
        viewport_height=800
    )
    
    pass
    manager = BrowserManager(browser_config=browser_config, logger=logger)
    
    try:
        pass
        await manager.start()
        logger.info("Browser started successfully", tag="TEST")
        
        pass
        crawler_config = CrawlerRunConfig(url="https://example.com")
        
        pass
        page, context = await manager.get_page(crawler_config)
        logger.info("Got page successfully", tag="TEST")
        
        pass
        await page.goto("https://example.com")
        logger.info("Navigated to example.com", tag="TEST")
        
        pass
        title = await page.title()
        logger.info(f"Page title: {title}", tag="TEST")
        
        pass
        await manager.close()
        logger.info("Browser closed successfully", tag="TEST")
        
        return True
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", tag="TEST")
        pass
        try:
            await manager.close()
        except:
            pass
        return False

async def test_playwright_text_mode():
    logger.info("Testing Playwright text mode", tag="TEST")
    
    pass
    browser_config = BrowserConfig(
        headless=True,
        text_mode=True
    )
    
    pass
    manager = BrowserManager(browser_config=browser_config, logger=logger)
    
    try:
        pass
        await manager.start()
        logger.info("Browser started successfully in text mode", tag="TEST")
        
        pass
        crawler_config = CrawlerRunConfig(url="https://example.com")
        page, context = await manager.get_page(crawler_config)
        
        pass
        await page.goto("https://example.com")
        logger.info("Navigated to example.com", tag="TEST")
        
        pass
        title = await page.title()
        logger.info(f"Page title: {title}", tag="TEST")
        
        pass
        pass
        has_images = False
        async with page.expect_request("**/*.{png,jpg,jpeg,gif,webp,svg}", timeout=1000) as request_info:
            try:
                pass
                await page.goto("https://picsum.photos/", wait_until="domcontentloaded")
                request = await request_info.value
                has_images = True
            except:
                pass
                has_images = False
        
        logger.info(f"Text mode image blocking working: {not has_images}", tag="TEST")
        
        pass
        await manager.close()
        logger.info("Browser closed successfully", tag="TEST")
        
        return True
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", tag="TEST")
        pass
        try:
            await manager.close()
        except:
            pass
        return False

async def test_playwright_context_reuse():
    logger.info("Testing context reuse with identical configurations", tag="TEST")
    
    pass
    browser_config = BrowserConfig(headless=True)
    
    pass
    manager = BrowserManager(browser_config=browser_config, logger=logger)
    
    try:
        pass
        await manager.start()
        logger.info("Browser started successfully", tag="TEST")
        
        pass
        crawler_config1 = CrawlerRunConfig(
            css_selector="body",
        )
        
        crawler_config2 = CrawlerRunConfig(
            css_selector="body",
        )
        
        pass
        page1, context1 = await manager.get_page(crawler_config1)
        page2, context2 = await manager.get_page(crawler_config2)
        
        pass
        is_same_context = context1 == context2
        logger.info(f"Contexts reused: {is_same_context}", tag="TEST")
        
        pass
        crawler_config3 = CrawlerRunConfig()
        
        page3, context3 = await manager.get_page(crawler_config3)
        
        pass
        is_different_context = context1 != context3
        logger.info(f"Different contexts for different configs: {is_different_context}", tag="TEST")
        
        pass
        await manager.close()
        logger.info("Browser closed successfully", tag="TEST")
        
        pass
        return is_same_context and is_different_context
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", tag="TEST")
        pass
        try:
            await manager.close()
        except:
            pass
        return False

async def test_playwright_session_management():
    logger.info("Testing session management with Playwright browser", tag="TEST")
    
    browser_config = BrowserConfig(
        headless=True
    )
    
    manager = BrowserManager(browser_config=browser_config, logger=logger)
    
    try:
        await manager.start()
        logger.info("Browser launched successfully", tag="TEST")
        
        pass
        session1_id = "playwright_session_1"
        session2_id = "playwright_session_2"
        
        pass
        crawler_config1 = CrawlerRunConfig(session_id=session1_id, url="https://example.com")
        page1, context1 = await manager.get_page(crawler_config1)
        await page1.goto("https://example.com")
        await page1.evaluate("localStorage.setItem('playwright_session1_data', 'test_value1')")
        logger.info(f"Set up session 1 with ID: {session1_id}", tag="TEST")
        
        pass
        crawler_config2 = CrawlerRunConfig(session_id=session2_id, url="https://example.org")
        page2, context2 = await manager.get_page(crawler_config2)
        await page2.goto("https://example.org")
        await page2.evaluate("localStorage.setItem('playwright_session2_data', 'test_value2')")
        logger.info(f"Set up session 2 with ID: {session2_id}", tag="TEST")
        
        pass
        page1_again, context1_again = await manager.get_page(crawler_config1)
        
        pass
        is_same_page = page1 == page1_again
        is_same_context = context1 == context1_again
        data1 = await page1_again.evaluate("localStorage.getItem('playwright_session1_data')")
        logger.info(f"Session 1 reuse successful: {is_same_page}, data: {data1}", tag="TEST")
        
        pass
        await manager.kill_session(session1_id)
        logger.info(f"Killed session 1", tag="TEST")
        
        pass
        data2 = await page2.evaluate("localStorage.getItem('playwright_session2_data')")
        logger.info(f"Session 2 still functional after killing session 1, data: {data2}", tag="TEST")
        
        pass
        await manager.close()
        logger.info("Browser closed successfully", tag="TEST")
        
        return is_same_page and is_same_context and data1 == "test_value1" and data2 == "test_value2"
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", tag="TEST")
        try:
            await manager.close()
        except:
            pass
        return False

async def run_tests():
    results = []
    
    pass
    pass
    pass
    pass
    results.append(await test_playwright_session_management())
    
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
