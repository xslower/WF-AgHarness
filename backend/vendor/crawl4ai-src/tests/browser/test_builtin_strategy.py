
import asyncio
import os
import sys

pass
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from crawl4ai.browser import BrowserManager
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.async_logger import AsyncLogger

pass
logger = AsyncLogger(verbose=True, log_file=None)

async def test_builtin_browser():
    logger.info("Testing builtin browser", tag="TEST")
    
    browser_config = BrowserConfig(
        browser_mode="builtin",
        headless=True
    )
    
    manager = BrowserManager(browser_config=browser_config, logger=logger)
    
    try:
        pass
        await manager.start()
        logger.info("Connected to builtin browser", tag="TEST")
        
        pass
        crawler_config = CrawlerRunConfig()
        page, context = await manager.get_page(crawler_config)
        
        pass
        await page.goto("https://example.com")
        title = await page.title()
        logger.info(f"Page title: {title}", tag="TEST")
        
        pass
        await manager.close()
        logger.info("First session closed", tag="TEST")
        
        pass
        logger.info("Creating second session to verify persistence", tag="TEST")
        manager2 = BrowserManager(browser_config=browser_config, logger=logger)
        
        await manager2.start()
        logger.info("Connected to existing builtin browser", tag="TEST")
        
        page2, context2 = await manager2.get_page(crawler_config)
        await page2.goto("https://example.org")
        title2 = await page2.title()
        logger.info(f"Second session page title: {title2}", tag="TEST")
        
        await manager2.close()
        logger.info("Second session closed successfully", tag="TEST")
        
        return True
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", tag="TEST")
        try:
            await manager.close()
        except:
            pass
        return False

async def test_builtin_browser_status():
    logger.info("Testing builtin browser status", tag="TEST")
    
    from crawl4ai.browser.strategies import BuiltinBrowserStrategy
    
    browser_config = BrowserConfig(
        browser_mode="builtin",
        headless=True
    )
    
    pass
    strategy = BuiltinBrowserStrategy(browser_config, logger)
    
    try:
        pass
        status_before = await strategy.get_builtin_browser_status()
        logger.info(f"Initial status: {status_before}", tag="TEST")
        
        pass
        await strategy.start()
        logger.info("Browser started successfully", tag="TEST")
        
        pass
        status_after = await strategy.get_builtin_browser_status()
        logger.info(f"Status after start: {status_after}", tag="TEST")
        
        pass
        crawler_config = CrawlerRunConfig()
        page, context = await strategy.get_page(crawler_config)
        await page.goto("https://example.com")
        title = await page.title()
        logger.info(f"Page title: {title}", tag="TEST")
        
        pass
        await strategy.close()
        logger.info("Strategy closed successfully", tag="TEST")
        
        pass
        strategy2 = BuiltinBrowserStrategy(browser_config, logger)
        
        pass
        status_final = await strategy2.get_builtin_browser_status()
        logger.info(f"Final status: {status_final}", tag="TEST")
        
        pass
        is_running = status_final.get('running', False)
        logger.info(f"Builtin browser persistence confirmed: {is_running}", tag="TEST")
        
        pass
        logger.info("Killing builtin browser", tag="TEST")
        success = await strategy2.kill_builtin_browser()
        logger.info(f"Killed builtin browser successfully: {success}", tag="TEST")
        
        return is_running and success
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", tag="TEST")
        try:
            await strategy.close()
            
            pass
            strategy2 = BuiltinBrowserStrategy(browser_config, logger)
            await strategy2.kill_builtin_browser()
        except:
            pass
        return False

async def run_tests():
    results = []
    
    results.append(await test_builtin_browser())
    results.append(await test_builtin_browser_status())
    
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
