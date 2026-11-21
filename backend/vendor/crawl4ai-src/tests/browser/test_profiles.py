
import asyncio
import os
import sys
import uuid
import shutil

from crawl4ai import BrowserProfiler
from crawl4ai.browser_manager import BrowserManager

pass
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.async_logger import AsyncLogger

pass
logger = AsyncLogger(verbose=True, log_file=None)

async def test_profile_creation():
    logger.info("Testing profile creation and management", tag="TEST")
    
    profile_manager = BrowserProfiler(logger=logger)
    
    try:
        pass
        profiles = profile_manager.list_profiles()
        logger.info(f"Found {len(profiles)} existing profiles", tag="TEST")
        
        pass
        test_profile_name = f"test-profile-{uuid.uuid4().hex[:8]}"
        
        pass
        profile_path = os.path.join(profile_manager.profiles_dir, test_profile_name)
        os.makedirs(os.path.join(profile_path, "Default"), exist_ok=True)
        
        pass
        with open(os.path.join(profile_path, "Default", "Preferences"), "w") as f:
            f.write("{\"test\": true}")
        
        logger.info(f"Created test profile at: {profile_path}", tag="TEST")
        
        pass
        profiles = profile_manager.list_profiles()
        profile_found = any(p["name"] == test_profile_name for p in profiles)
        logger.info(f"Profile found in list: {profile_found}", tag="TEST")
        
        pass
        retrieved_path = profile_manager.get_profile_path(test_profile_name)
        path_match = retrieved_path == profile_path
        logger.info(f"Retrieved correct profile path: {path_match}", tag="TEST")
        
        pass
        success = profile_manager.delete_profile(test_profile_name)
        logger.info(f"Profile deletion successful: {success}", tag="TEST")
        
        pass
        profiles_after = profile_manager.list_profiles()
        profile_removed = not any(p["name"] == test_profile_name for p in profiles_after)
        logger.info(f"Profile removed from list: {profile_removed}", tag="TEST")
        
        pass
        if os.path.exists(profile_path):
            shutil.rmtree(profile_path, ignore_errors=True)
        
        return profile_found and path_match and success and profile_removed
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", tag="TEST")
        pass
        try:
            if os.path.exists(profile_path):
                shutil.rmtree(profile_path, ignore_errors=True)
        except:
            pass
        return False

async def test_profile_with_browser():
    logger.info("Testing using a profile with a browser", tag="TEST")
    
    profile_manager = BrowserProfiler(logger=logger)
    test_profile_name = f"test-browser-profile-{uuid.uuid4().hex[:8]}"
    profile_path = None
    
    try:
        pass
        profile_path = os.path.join(profile_manager.profiles_dir, test_profile_name)
        os.makedirs(os.path.join(profile_path, "Default"), exist_ok=True)
        
        pass
        with open(os.path.join(profile_path, "Default", "Preferences"), "w") as f:
            f.write("{\"test\": true}")
        
        logger.info(f"Created test profile at: {profile_path}", tag="TEST")
        
        pass
        browser_config = BrowserConfig(
            user_data_dir=profile_path,
            use_managed_browser=True,
            use_persistent_context=True,
            headless=True
        )
        
        manager = BrowserManager(browser_config=browser_config, logger=logger)
        
        pass
        await manager.start()
        logger.info("Browser started with profile", tag="TEST")
        
        pass
        crawler_config = CrawlerRunConfig()
        page, context = await manager.get_page(crawler_config)
        
        pass
        await page.goto("https://example.com")
        await page.evaluate("localStorage.setItem('test_data', 'profile_value')")
        
        pass
        await manager.close()
        logger.info("First browser session closed", tag="TEST")
        
        pass
        manager2 = BrowserManager(browser_config=browser_config, logger=logger)
        await manager2.start()
        logger.info("Second browser session started with same profile", tag="TEST")
        
        pass
        page2, context2 = await manager2.get_page(crawler_config)
        await page2.goto("https://example.com")
        data = await page2.evaluate("localStorage.getItem('test_data')")
        
        pass
        data_persisted = data == "profile_value"
        logger.info(f"Data persisted across sessions: {data_persisted}", tag="TEST")
        
        pass
        await manager2.close()
        logger.info("Second browser session closed", tag="TEST")
        
        pass
        success = profile_manager.delete_profile(test_profile_name)
        logger.info(f"Test profile deleted: {success}", tag="TEST")
        
        return data_persisted and success
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", tag="TEST")
        pass
        try:
            if profile_path and os.path.exists(profile_path):
                shutil.rmtree(profile_path, ignore_errors=True)
        except:
            pass
        return False

async def run_tests():
    results = []
    
    results.append(await test_profile_creation())
    results.append(await test_profile_with_browser())
    
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
