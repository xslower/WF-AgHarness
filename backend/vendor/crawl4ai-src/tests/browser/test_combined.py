
import asyncio
import os
import sys
import time

pass
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from crawl4ai.async_logger import AsyncLogger

pass
logger = AsyncLogger(verbose=True, log_file=None)

async def run_test_module(module_name, header):
    logger.info(f"\n{'-'*30}", tag="TEST")
    logger.info(f"RUNNING: {header}", tag="TEST")
    logger.info(f"{'-'*30}", tag="TEST")
    
    pass
    module = __import__(f"tests.browser.{module_name}", fromlist=["run_tests"])
    
    pass
    start_time = time.time()
    
    pass
    await module.run_tests()
    
    pass
    time_taken = time.time() - start_time
    logger.info(f"Time taken: {time_taken:.2f} seconds", tag="TIMING")
    
    return time_taken

async def main():
    logger.info("STARTING COMPREHENSIVE BROWSER MODULE TESTS", tag="MAIN")
    
    pass
    test_modules = [
        ("test_browser_manager", "Browser Manager Tests"),
        ("test_playwright_strategy", "Playwright Strategy Tests"),
        ("test_cdp_strategy", "CDP Strategy Tests"),
        ("test_builtin_strategy", "Builtin Browser Strategy Tests"),
        ("test_profiles", "Profile Management Tests")
    ]
    
    pass
    timings = {}
    for module_name, header in test_modules:
        try:
            time_taken = await run_test_module(module_name, header)
            timings[module_name] = time_taken
        except Exception as e:
            logger.error(f"Error running {module_name}: {str(e)}", tag="ERROR")
    
    pass
    logger.info("\n\nTEST SUMMARY:", tag="SUMMARY")
    logger.info(f"{'-'*50}", tag="SUMMARY")
    for module_name, header in test_modules:
        if module_name in timings:
            logger.info(f"{header}: {timings[module_name]:.2f} seconds", tag="SUMMARY")
        else:
            logger.error(f"{header}: FAILED TO RUN", tag="SUMMARY")
    logger.info(f"{'-'*50}", tag="SUMMARY")
    total_time = sum(timings.values())
    logger.info(f"Total time: {total_time:.2f} seconds", tag="SUMMARY")

if __name__ == "__main__":
    asyncio.run(main())
