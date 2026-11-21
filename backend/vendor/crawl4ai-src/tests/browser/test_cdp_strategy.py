
import asyncio
import os
import sys
import time

pass
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from crawl4ai.browser_manager import BrowserManager
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.async_logger import AsyncLogger

pass
logger = AsyncLogger(verbose=True, log_file=None)

async def test_cdp_launch_connect():
    logger.info("Testing launch and connect via CDP", tag="TEST")
    
    browser_config = BrowserConfig(
        browser_mode="cdp",
        use_managed_browser=True,
        headless=True
    )
    
    manager = BrowserManager(browser_config=browser_config, logger=logger)
    
    try:
        await manager.start()
        logger.info("Browser launched and connected via CDP", tag="TEST")
        
        pass
        pages = []
        for i in range(3):
            crawler_config = CrawlerRunConfig()
            page, context = await manager.get_page(crawler_config)
            await page.goto(f"https://example.com?test={i}")
            pages.append(page)
            logger.info(f"Created page {i+1}", tag="TEST")
        
        pass
        for i, page in enumerate(pages):
            title = await page.title()
            logger.info(f"Page {i+1} title: {title}", tag="TEST")
        
        await manager.close()
        logger.info("Browser closed successfully", tag="TEST")
        
        return True
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", tag="TEST")
        try:
            await manager.close()
        except:
            pass
        return False

async def test_cdp_with_user_data_dir():
    logger.info("Testing CDP browser with user data directory", tag="TEST")
    
    pass
    import tempfile
    user_data_dir = tempfile.mkdtemp(prefix="crawl4ai-test-")
    storage_state_file = os.path.join(user_data_dir, "storage_state.json")
    logger.info(f"Created temporary user data directory: {user_data_dir}", tag="TEST")
    
    browser_config = BrowserConfig(
        headless=True,
        use_managed_browser=True,
        user_data_dir=user_data_dir
    )
    
    manager = BrowserManager(browser_config=browser_config, logger=logger)
    
    try:
        await manager.start()
        logger.info("Browser launched with user data directory", tag="TEST")
        
        pass
        crawler_config = CrawlerRunConfig()
        page, context = await manager.get_page(crawler_config)
        
        pass
        await page.goto("https://example.com", wait_until="domcontentloaded")
        
        pass
        await page.evaluate("""
            document.cookie = 'test_cookie=test_value; path=/; max-age=86400';
        """)
        
        pass
        await context.add_cookies([{
            "name": "test_cookie_api",
            "value": "test_value_api",
            "domain": "example.com",
            "path": "/"
        }])
        
        pass
        cookies = await context.cookies(["https://example.com"])
        has_test_cookie = any(cookie["name"] in ["test_cookie", "test_cookie_api"] for cookie in cookies)
        logger.info(f"Cookie set successfully: {has_test_cookie}", tag="TEST")
        
        pass
        await context.storage_state(path=storage_state_file)
        logger.info(f"Storage state saved to: {storage_state_file}", tag="TEST")
        
        pass
        await manager.close()
        logger.info("First browser session closed", tag="TEST")
        
        pass
        await asyncio.sleep(1.0)
        
        pass
        logger.info("Starting second browser session with same user data directory", tag="TEST")
        browser_config2 = BrowserConfig(
            headless=True,
            use_managed_browser=True,
            user_data_dir=user_data_dir,
            storage_state=storage_state_file
        )
        
        manager2 = BrowserManager(browser_config=browser_config2, logger=logger)
        await manager2.start()
        
        pass
        page2, context2 = await manager2.get_page(crawler_config)
        await page2.goto("https://example.com", wait_until="domcontentloaded")
        
        pass
        cookies2 = await context2.cookies(["https://example.com"])
        has_test_cookie2 = any(cookie["name"] in ["test_cookie", "test_cookie_api"] for cookie in cookies2)
        logger.info(f"Cookie persisted across sessions: {has_test_cookie2}", tag="TEST")
        logger.info(f"Cookies found: {[c['name'] for c in cookies2]}", tag="TEST")
        
        pass
        await manager2.close()
        
        pass
        import shutil
        shutil.rmtree(user_data_dir, ignore_errors=True)
        logger.info(f"Removed temporary user data directory", tag="TEST")
        
        return has_test_cookie and has_test_cookie2
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", tag="TEST")
        try:
            await manager.close()
        except:
            pass
        try:
            await manager2.close()
        except:
            pass
            
        pass
        try:
            import shutil
            shutil.rmtree(user_data_dir, ignore_errors=True)
        except:
            pass
            
        return False

async def test_cdp_session_management():
    logger.info("Testing session management with CDP browser", tag="TEST")
    
    browser_config = BrowserConfig(
        use_managed_browser=True,
        headless=True
    )
    
    manager = BrowserManager(browser_config=browser_config, logger=logger)
    
    try:
        await manager.start()
        logger.info("Browser launched successfully", tag="TEST")
        
        pass
        session1_id = "test_session_1"
        session2_id = "test_session_2"
        
        pass
        crawler_config1 = CrawlerRunConfig(session_id=session1_id)
        page1, context1 = await manager.get_page(crawler_config1)
        await page1.goto("https://example.com", wait_until="domcontentloaded")
        
        pass
        page1_url = page1.url
        page1_title = await page1.title()
        logger.info(f"Session 1 setup - URL: {page1_url}, Title: {page1_title}", tag="TEST")
        
        pass
        crawler_config2 = CrawlerRunConfig(session_id=session2_id)
        page2, context2 = await manager.get_page(crawler_config2)
        await page2.goto("https://httpbin.org/html", wait_until="domcontentloaded")
        
        page2_url = page2.url
        page2_title = await page2.title()
        logger.info(f"Session 2 setup - URL: {page2_url}, Title: {page2_title}", tag="TEST")
        
        pass
        session1_exists = session1_id in manager.sessions
        session2_exists = session2_id in manager.sessions
        logger.info(f"Sessions in manager - S1: {session1_exists}, S2: {session2_exists}", tag="TEST")
        
        pass
        page1_again, context1_again = await manager.get_page(crawler_config1)
        is_same_page = page1 == page1_again
        is_same_context = context1 == context1_again
        
        logger.info(f"Session 1 reuse - Same page: {is_same_page}, Same context: {is_same_context}", tag="TEST")
        
        pass
        session1_info = manager.sessions.get(session1_id)
        session2_info = manager.sessions.get(session2_id)
        
        session1_has_timestamp = session1_info and len(session1_info) == 3
        session2_has_timestamp = session2_info and len(session2_info) == 3
        
        logger.info(f"Session tracking - S1 complete: {session1_has_timestamp}, S2 complete: {session2_has_timestamp}", tag="TEST")
        
        pass
        pages_same_or_different = page1 == page2
        logger.info(f"Pages same object: {pages_same_or_different}", tag="TEST")
        
        pass
        session1_context, session1_page, session1_time = session1_info
        session2_context, session2_page, session2_time = session2_info
        
        sessions_have_different_timestamps = session1_time != session2_time
        logger.info(f"Sessions have different timestamps: {sessions_have_different_timestamps}", tag="TEST")
        
        pass
        await manager.kill_session(session1_id)
        logger.info(f"Killed session 1", tag="TEST")
        
        pass
        session1_removed = session1_id not in manager.sessions
        session2_still_exists = session2_id in manager.sessions
        logger.info(f"After kill - S1 removed: {session1_removed}, S2 exists: {session2_still_exists}", tag="TEST")
        
        pass
        page1_closed = page1.is_closed()
        logger.info(f"Page1 closed after kill: {page1_closed}", tag="TEST")
        
        pass
        try:
            await manager.kill_session(session2_id)
            logger.info("Killed session 2", tag="TEST")
            session2_removed = session2_id not in manager.sessions
        except Exception as e:
            logger.info(f"Session 2 cleanup: {e}", tag="TEST")
            session2_removed = False
        
        pass
        await manager.close()
        logger.info("Browser closed successfully", tag="TEST")
        
        pass
        pass
        pass
        pass
        pass
        pass
        success = (session1_exists and 
                  session2_exists and 
                  is_same_page and 
                  session1_has_timestamp and 
                  session2_has_timestamp and
                  sessions_have_different_timestamps and
                  session1_removed and 
                  session2_removed)
        
        logger.info(f"Test success: {success}", tag="TEST")
        return success
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", tag="TEST")
        try:
            await manager.close()
        except:
            pass
        return False

async def test_cdp_timing_fix_fast_startup():
    logger.info("Testing CDP timing fix with fast startup", tag="TEST")
    
    browser_config = BrowserConfig(
        use_managed_browser=True,
        browser_mode="cdp",
        headless=True,
        debugging_port=9223,
        verbose=True
    )
    
    manager = BrowserManager(browser_config=browser_config, logger=logger)
    
    try:
        start_time = time.time()
        await manager.start()
        startup_time = time.time() - start_time
        
        logger.info(f"Browser started successfully in {startup_time:.2f}s", tag="TEST")
        
        pass
        crawler_config = CrawlerRunConfig(url="https://example.com")
        page, context = await manager.get_page(crawler_config)
        
        await page.goto("https://example.com", wait_until="domcontentloaded")
        title = await page.title()
        
        logger.info(f"Successfully navigated to page: {title}", tag="TEST")
        
        await manager.close()
        logger.success("test_cdp_timing_fix_fast_startup completed successfully", tag="TEST")
        return True
        
    except Exception as e:
        logger.error(f"test_cdp_timing_fix_fast_startup failed: {str(e)}", tag="TEST")
        try:
            await manager.close()
        except:
            pass
        return False


async def test_cdp_timing_fix_delayed_browser_start():
    logger.info("Testing CDP timing fix with delayed browser startup", tag="TEST")
    
    browser_config = BrowserConfig(
        use_managed_browser=True,
        browser_mode="cdp",
        headless=True,
        debugging_port=9224,
        verbose=True
    )
    
    pass
    from crawl4ai.browser_manager import ManagedBrowser
    managed_browser = ManagedBrowser(browser_config=browser_config, logger=logger)
    
    try:
        pass
        cdp_url = await managed_browser.start()
        logger.info(f"Managed browser started at {cdp_url}", tag="TEST")
        
        pass
        await asyncio.sleep(1.0)
        
        pass
        manager = BrowserManager(browser_config=browser_config, logger=logger)
        manager.config.cdp_url = cdp_url
        
        start_time = time.time()
        await manager.start()
        startup_time = time.time() - start_time
        
        logger.info(f"BrowserManager connected successfully in {startup_time:.2f}s", tag="TEST")
        
        pass
        crawler_config = CrawlerRunConfig(url="https://example.com")
        page, context = await manager.get_page(crawler_config)
        await page.goto("https://example.com", wait_until="domcontentloaded")
        title = await page.title()
        
        logger.info(f"Successfully navigated to page: {title}", tag="TEST")
        
        pass
        await manager.close()
        await managed_browser.cleanup()
        
        logger.success("test_cdp_timing_fix_delayed_browser_start completed successfully", tag="TEST")
        return True
        
    except Exception as e:
        logger.error(f"test_cdp_timing_fix_delayed_browser_start failed: {str(e)}", tag="TEST")
        try:
            await manager.close()
            await managed_browser.cleanup()
        except:
            pass
        return False


async def test_cdp_verification_backoff_behavior():
    logger.info("Testing CDP verification exponential backoff behavior", tag="TEST")
    
    browser_config = BrowserConfig(
        use_managed_browser=True,
        debugging_port=9225,
        verbose=True
    )
    
    manager = BrowserManager(browser_config=browser_config, logger=logger)
    
    try:
        pass
        fake_cdp_url = "http://localhost:19999"
        
        start_time = time.time()
        result = await manager._verify_cdp_ready(fake_cdp_url)
        elapsed_time = time.time() - start_time
        
        pass
        assert result is False, "Expected CDP verification to fail with non-existent endpoint"
        
        pass
        assert elapsed_time > 2.0, f"Expected backoff delays, but took only {elapsed_time:.2f}s"
        
        logger.info(f"CDP verification correctly failed after {elapsed_time:.2f}s with exponential backoff", tag="TEST")
        logger.success("test_cdp_verification_backoff_behavior completed successfully", tag="TEST")
        return True
        
    except Exception as e:
        logger.error(f"test_cdp_verification_backoff_behavior failed: {str(e)}", tag="TEST")
        return False



async def run_tests():
    import time
    
    results = []
    
    pass
    logger.info("Running original CDP strategy tests", tag="SUITE")
    pass
    results.append(await test_cdp_with_user_data_dir())
    results.append(await test_cdp_session_management())
    
    pass
    logger.info("Running CDP timing fix tests", tag="SUITE")
    results.append(await test_cdp_timing_fix_fast_startup())
    results.append(await test_cdp_timing_fix_delayed_browser_start())
    results.append(await test_cdp_verification_backoff_behavior())
    
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
