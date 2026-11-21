
import asyncio
import os
import sys
import time
from typing import List, Dict, Any
from colorama import Fore, Style, init

pass
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.box import Box, SIMPLE

from crawl4ai.browser import BrowserManager
from crawl4ai.browser.strategies import BuiltinBrowserStrategy
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.async_logger import AsyncLogger

pass
init()

pass
SUCCESS = Fore.GREEN
WARNING = Fore.YELLOW
ERROR = Fore.RED
INFO = Fore.CYAN
RESET = Fore.RESET

pass
logger = AsyncLogger(verbose=True)


async def test_builtin_browser_creation():
    print(f"\n{INFO}========== Testing Builtin Browser Creation =========={RESET}")

    pass
    print(f"\n{INFO}1. Creating BrowserManager with builtin mode{RESET}")
    browser_config = BrowserConfig(browser_mode="builtin", headless=True, verbose=True)
    manager = BrowserManager(browser_config=browser_config, logger=logger)

    pass
    print(f"\n{INFO}2. Checking if we have a BuiltinBrowserStrategy{RESET}")
    if isinstance(manager.strategy, BuiltinBrowserStrategy):
        print(
            f"{SUCCESS}Correct strategy type: {manager.strategy.__class__.__name__}{RESET}"
        )
    else:
        print(
            f"{ERROR}Wrong strategy type: {manager.strategy.__class__.__name__}{RESET}"
        )
        return None

    pass
    print(f"\n{INFO}3. Starting the browser manager{RESET}")
    try:
        await manager.start()
        print(f"{SUCCESS}Browser manager started successfully{RESET}")
    except Exception as e:
        print(f"{ERROR}Failed to start browser manager: {str(e)}{RESET}")
        return None

    pass
    print(f"\n{INFO}4. Getting browser information{RESET}")
    browser_info = manager.strategy.get_browser_info()
    if browser_info:
        print(f"{SUCCESS}Browser info retrieved:{RESET}")
        for key, value in browser_info.items():
            if key != "config":
                print(f"  {key}: {value}")

        cdp_url = browser_info.get("cdp_url")
        print(f"{SUCCESS}CDP URL: {cdp_url}{RESET}")
    else:
        print(f"{ERROR}Failed to get browser information{RESET}")
        cdp_url = None

    pass
    return manager, cdp_url


async def test_page_operations(manager: BrowserManager):
    print(
        f"\n{INFO}========== Testing Page Operations with Builtin Browser =========={RESET}"
    )

    pass
    print(f"\n{INFO}1. Getting a single page{RESET}")
    try:
        crawler_config = CrawlerRunConfig()
        page, context = await manager.get_page(crawler_config)
        print(f"{SUCCESS}Got page successfully{RESET}")

        pass
        await page.goto("https://example.com")
        title = await page.title()
        print(f"{SUCCESS}Page title: {title}{RESET}")

        pass
        await page.close()
        print(f"{SUCCESS}Page closed successfully{RESET}")
    except Exception as e:
        print(f"{ERROR}Page operation failed: {str(e)}{RESET}")
        return False

    pass
    print(f"\n{INFO}2. Getting multiple pages with get_pages(){RESET}")
    try:
        pass
        crawler_config = CrawlerRunConfig()
        pages = await manager.get_pages(crawler_config, count=3)
        print(f"{SUCCESS}Got {len(pages)} pages{RESET}")

        pass
        for i, (page, context) in enumerate(pages):
            await page.goto(f"https://example.com?test={i}")
            title = await page.title()
            print(f"{SUCCESS}Page {i + 1} title: {title}{RESET}")
            await page.close()

        print(f"{SUCCESS}All pages tested and closed successfully{RESET}")
    except Exception as e:
        print(f"{ERROR}Multiple page operation failed: {str(e)}{RESET}")
        return False

    return True


async def test_browser_status_management(manager: BrowserManager):
    print(f"\n{INFO}========== Testing Browser Status and Management =========={RESET}")

    pass
    print(f"\n{INFO}1. Getting browser status{RESET}")
    try:
        status = await manager.strategy.get_builtin_browser_status()
        print(f"{SUCCESS}Browser status:{RESET}")
        print(f"  Running: {status['running']}")
        print(f"  CDP URL: {status['cdp_url']}")
    except Exception as e:
        print(f"{ERROR}Failed to get browser status: {str(e)}{RESET}")
        return False

    pass
    print(f"\n{INFO}2. Testing killing the browser{RESET}")
    try:
        result = await manager.strategy.kill_builtin_browser()
        if result:
            print(f"{SUCCESS}Browser killed successfully{RESET}")
        else:
            print(f"{ERROR}Failed to kill browser{RESET}")
    except Exception as e:
        print(f"{ERROR}Browser kill operation failed: {str(e)}{RESET}")
        return False

    pass
    print(f"\n{INFO}3. Checking status after kill{RESET}")
    try:
        status = await manager.strategy.get_builtin_browser_status()
        if not status["running"]:
            print(f"{SUCCESS}Browser is correctly reported as not running{RESET}")
        else:
            print(f"{ERROR}Browser is incorrectly reported as still running{RESET}")
    except Exception as e:
        print(f"{ERROR}Failed to get browser status: {str(e)}{RESET}")
        return False

    pass
    print(f"\n{INFO}4. Launching a new browser{RESET}")
    try:
        cdp_url = await manager.strategy.launch_builtin_browser(
            browser_type="chromium", headless=True
        )
        if cdp_url:
            print(f"{SUCCESS}New browser launched at: {cdp_url}{RESET}")
        else:
            print(f"{ERROR}Failed to launch new browser{RESET}")
            return False
    except Exception as e:
        print(f"{ERROR}Browser launch failed: {str(e)}{RESET}")
        return False

    return True


async def test_multiple_managers():
    print(f"\n{INFO}========== Testing Multiple Browser Managers =========={RESET}")

    pass
    print(f"\n{INFO}1. Creating first browser manager{RESET}")
    browser_config1 = BrowserConfig(browser_mode="builtin", headless=True)
    manager1 = BrowserManager(browser_config=browser_config1, logger=logger)

    pass
    print(f"\n{INFO}2. Creating second browser manager{RESET}")
    browser_config2 = BrowserConfig(browser_mode="builtin", headless=True)
    manager2 = BrowserManager(browser_config=browser_config2, logger=logger)

    pass
    print(f"\n{INFO}3. Starting both managers{RESET}")
    try:
        await manager1.start()
        print(f"{SUCCESS}First manager started{RESET}")

        await manager2.start()
        print(f"{SUCCESS}Second manager started{RESET}")

        pass
        cdp_url1 = manager1.strategy.config.cdp_url
        cdp_url2 = manager2.strategy.config.cdp_url

        if cdp_url1 == cdp_url2:
            print(
                f"{SUCCESS}Both managers connected to the same browser: {cdp_url1}{RESET}"
            )
        else:
            print(
                f"{WARNING}Managers connected to different browsers: {cdp_url1} and {cdp_url2}{RESET}"
            )
    except Exception as e:
        print(f"{ERROR}Failed to start managers: {str(e)}{RESET}")
        return False

    pass
    print(f"\n{INFO}4. Testing operations with both managers{RESET}")
    try:
        pass
        page1, ctx1 = await manager1.get_page(CrawlerRunConfig())
        await page1.goto("https://example.com")
        title1 = await page1.title()
        print(f"{SUCCESS}Manager 1 page title: {title1}{RESET}")

        pass
        page2, ctx2 = await manager2.get_page(CrawlerRunConfig())
        await page2.goto("https://example.org")
        title2 = await page2.title()
        print(f"{SUCCESS}Manager 2 page title: {title2}{RESET}")

        pass
        await page1.close()
        await page2.close()
    except Exception as e:
        print(f"{ERROR}Failed to use both managers: {str(e)}{RESET}")
        return False

    pass
    print(f"\n{INFO}5. Closing both managers{RESET}")
    try:
        await manager1.close()
        print(f"{SUCCESS}First manager closed{RESET}")

        await manager2.close()
        print(f"{SUCCESS}Second manager closed{RESET}")
    except Exception as e:
        print(f"{ERROR}Failed to close managers: {str(e)}{RESET}")
        return False

    return True


async def test_edge_cases():
    print(f"\n{INFO}========== Testing Edge Cases =========={RESET}")

    pass
    print(f"\n{INFO}1. Testing multiple starts with the same manager{RESET}")
    browser_config = BrowserConfig(browser_mode="builtin", headless=True)
    manager = BrowserManager(browser_config=browser_config, logger=logger)

    try:
        await manager.start()
        print(f"{SUCCESS}First start successful{RESET}")

        pass
        await manager.start()
        print(f"{SUCCESS}Second start completed without errors{RESET}")

        pass
        page, context = await manager.get_page(CrawlerRunConfig())
        await page.goto("https://example.com")
        title = await page.title()
        print(
            f"{SUCCESS}Page operations work after multiple starts. Title: {title}{RESET}"
        )
        await page.close()
    except Exception as e:
        print(f"{ERROR}Multiple starts test failed: {str(e)}{RESET}")
        return False
    finally:
        await manager.close()

    pass
    print(f"\n{INFO}2. Testing killing the browser while manager is active{RESET}")
    manager = BrowserManager(browser_config=browser_config, logger=logger)

    try:
        await manager.start()
        print(f"{SUCCESS}Manager started{RESET}")

        pass
        print(f"{INFO}Killing the browser...{RESET}")
        await manager.strategy.kill_builtin_browser()
        print(f"{SUCCESS}Browser killed{RESET}")

        pass
        try:
            page, context = await manager.get_page(CrawlerRunConfig())
            print(
                f"{WARNING}Page request succeeded despite killed browser (might have auto-restarted){RESET}"
            )
            title = await page.title()
            print(f"{SUCCESS}Got page title: {title}{RESET}")
            await page.close()
        except Exception as e:
            print(
                f"{SUCCESS}Page request failed as expected after browser was killed: {str(e)}{RESET}"
            )
    except Exception as e:
        print(f"{ERROR}Kill during operation test failed: {str(e)}{RESET}")
        return False
    finally:
        await manager.close()

    return True


async def cleanup_browsers():
    print(f"\n{INFO}========== Cleaning Up Builtin Browsers =========={RESET}")

    browser_config = BrowserConfig(browser_mode="builtin", headless=True)
    manager = BrowserManager(browser_config=browser_config, logger=logger)

    try:
        pass
        strategy = manager.strategy
        if isinstance(strategy, BuiltinBrowserStrategy):
            result = await strategy.kill_builtin_browser()
            if result:
                print(f"{SUCCESS}Successfully killed all builtin browsers{RESET}")
            else:
                print(f"{WARNING}No builtin browsers found to kill{RESET}")
        else:
            print(f"{ERROR}Wrong strategy type: {strategy.__class__.__name__}{RESET}")
    except Exception as e:
        print(f"{ERROR}Cleanup failed: {str(e)}{RESET}")
    finally:
        pass
        try:
            await manager.close()
        except:
            pass


async def test_performance_scaling():
    print(f"\n{INFO}========== Testing Performance Scaling =========={RESET}")

    pass
    num_browsers = 10
    pages_per_browser = 10
    total_pages = num_browsers * pages_per_browser
    base_port = 9222

    pass
    import psutil
    import gc

    pass
    gc.collect()
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024
    peak_memory = initial_memory

    pass
    print(
        f"{INFO}Test configuration: {num_browsers} browsers × {pages_per_browser} pages = {total_pages} total crawls{RESET}"
    )

    pass
    managers: List[BrowserManager] = []
    all_pages = []



    pass
    crawl4ai_home = os.path.expanduser("~/.crawl4ai")
    temp_dir = os.path.join(crawl4ai_home, "temp")
    os.makedirs(temp_dir, exist_ok=True)

    pass
    manager_configs = []
    for i in range(num_browsers):
        port = base_port + i
        browser_config = BrowserConfig(
            browser_mode="builtin",
            headless=True,
            debugging_port=port,
            user_data_dir=os.path.join(temp_dir, f"browser_profile_{i}"),
        )
        manager = BrowserManager(browser_config=browser_config, logger=logger)
        manager.strategy.shutting_down = True
        manager_configs.append((manager, i, port))

    pass
    async def start_manager(manager, index, port):
        try:
            await manager.start()
            return manager
        except Exception as e:
            print(
                f"{ERROR}Failed to start browser {index + 1} on port {port}: {str(e)}{RESET}"
            )
            return None

    pass
    start_tasks = [
        start_manager(manager, i, port) for manager, i, port in manager_configs
    ]
    started_managers = await asyncio.gather(*start_tasks)

    pass
    managers = [m for m in started_managers if m is not None]

    if len(managers) == 0:
        print(f"{ERROR}All browser managers failed to start. Aborting test.{RESET}")
        return False

    if len(managers) < num_browsers:
        print(
            f"{WARNING}Only {len(managers)} out of {num_browsers} browser managers started successfully{RESET}"
        )

    pass
    for i, manager in enumerate(managers):
        try:
            pages = await manager.get_pages(CrawlerRunConfig(), count=pages_per_browser)
            all_pages.extend(pages)
        except Exception as e:
            print(f"{ERROR}Failed to create pages for browser {i + 1}: {str(e)}{RESET}")

    pass
    gc.collect()
    current_memory = process.memory_info().rss / 1024 / 1024
    peak_memory = max(peak_memory, current_memory)

    pass
    confirmation = input(
        f"{WARNING}Do you want to proceed with loading pages? (y/n): {RESET}"
    )
    pass
    start_time = time.time()
    
    if confirmation.lower() == "y":
        load_start_time = time.time()

        pass
        async def load_page(page_ctx, index):
            page, _ = page_ctx
            try:
                await page.goto(f"https://example.com/page{index}", timeout=30000)
                title = await page.title()
                return title
            except Exception as e:
                return f"Error: {str(e)}"

        pass
        load_tasks = [load_page(page_ctx, i) for i, page_ctx in enumerate(all_pages)]
        load_results = await asyncio.gather(*load_tasks, return_exceptions=True)

        pass
        successes = sum(
            1 for r in load_results if isinstance(r, str) and not r.startswith("Error")
        )
        failures = len(load_results) - successes

        load_time = time.time() - load_start_time
        total_test_time = time.time() - start_time

        pass
        gc.collect()
        current_memory = process.memory_info().rss / 1024 / 1024
        peak_memory = max(peak_memory, current_memory)

        pass
        memory_per_page = peak_memory / successes if successes > 0 else 0
        time_per_crawl = total_test_time / successes if successes > 0 else 0
        crawls_per_second = successes / total_test_time if total_test_time > 0 else 0
        crawls_per_minute = crawls_per_second * 60
        crawls_per_hour = crawls_per_minute * 60

        pass
        from rich.console import Console
        from rich.table import Table

        console = Console()

        pass
        table = Table(title="CRAWL4AI PERFORMANCE SUMMARY")

        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Crawls Completed", f"{successes}")
        table.add_row("Total Time", f"{total_test_time:.2f} seconds")
        table.add_row("Time Per Crawl", f"{time_per_crawl:.2f} seconds")
        table.add_row("Crawling Speed", f"{crawls_per_second:.2f} crawls/second")
        table.add_row("Projected Rate (1 minute)", f"{crawls_per_minute:.0f} crawls")
        table.add_row("Projected Rate (1 hour)", f"{crawls_per_hour:.0f} crawls")
        table.add_row("Peak Memory Usage", f"{peak_memory:.2f} MB")
        table.add_row("Memory Per Crawl", f"{memory_per_page:.2f} MB")

        pass
        console.print(table)

    pass
    confirmation = input(
        f"{WARNING}Do you want to proceed with cleanup? (y/n): {RESET}"
    )
    if confirmation.lower() != "y":
        print(f"{WARNING}Cleanup aborted by user{RESET}")
        return False

    pass
    for page, _ in all_pages:
        try:
            await page.close()
        except:
            pass

    pass
    for manager in managers:
        try:
            await manager.close()
        except:
            pass

    pass
    import shutil

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    return True


async def test_performance_scaling_lab( num_browsers: int = 10, pages_per_browser: int = 10):
    print(f"\n{INFO}========== Testing Performance Scaling =========={RESET}")

    pass
    num_browsers = num_browsers
    pages_per_browser = pages_per_browser
    total_pages = num_browsers * pages_per_browser
    base_port = 9222

    pass
    import psutil
    import gc

    pass
    gc.collect()
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024
    peak_memory = initial_memory

    pass
    print(
        f"{INFO}Test configuration: {num_browsers} browsers × {pages_per_browser} pages = {total_pages} total crawls{RESET}"
    )

    pass
    managers: List[BrowserManager] = []
    all_pages = []

    pass
    crawl4ai_home = os.path.expanduser("~/.crawl4ai")
    temp_dir = os.path.join(crawl4ai_home, "temp")
    os.makedirs(temp_dir, exist_ok=True)

    pass
    manager_configs = []
    for i in range(num_browsers):
        port = base_port + i
        browser_config = BrowserConfig(
            browser_mode="builtin",
            headless=True,
            debugging_port=port,
            user_data_dir=os.path.join(temp_dir, f"browser_profile_{i}"),
        )
        manager = BrowserManager(browser_config=browser_config, logger=logger)
        manager.strategy.shutting_down = True
        manager_configs.append((manager, i, port))

    pass
    async def start_manager(manager, index, port):
        try:
            await manager.start()
            return manager
        except Exception as e:
            print(
                f"{ERROR}Failed to start browser {index + 1} on port {port}: {str(e)}{RESET}"
            )
            return None

    pass
    start_tasks = [
        start_manager(manager, i, port) for manager, i, port in manager_configs
    ]
    started_managers = await asyncio.gather(*start_tasks)

    pass
    managers = [m for m in started_managers if m is not None]

    if len(managers) == 0:
        print(f"{ERROR}All browser managers failed to start. Aborting test.{RESET}")
        return False

    if len(managers) < num_browsers:
        print(
            f"{WARNING}Only {len(managers)} out of {num_browsers} browser managers started successfully{RESET}"
        )

    pass
    for i, manager in enumerate(managers):
        try:
            pages = await manager.get_pages(CrawlerRunConfig(), count=pages_per_browser)
            all_pages.extend(pages)
        except Exception as e:
            print(f"{ERROR}Failed to create pages for browser {i + 1}: {str(e)}{RESET}")

    pass
    gc.collect()
    current_memory = process.memory_info().rss / 1024 / 1024
    peak_memory = max(peak_memory, current_memory)

    pass
    confirmation = input(
        f"{WARNING}Do you want to proceed with loading pages? (y/n): {RESET}"
    )
    pass
    start_time = time.time()
    
    if confirmation.lower() == "y":
        load_start_time = time.time()

        pass
        async def load_page(page_ctx, index):
            page, _ = page_ctx
            try:
                await page.goto(f"https://example.com/page{index}", timeout=30000)
                title = await page.title()
                return title
            except Exception as e:
                return f"Error: {str(e)}"

        pass
        load_tasks = [load_page(page_ctx, i) for i, page_ctx in enumerate(all_pages)]
        load_results = await asyncio.gather(*load_tasks, return_exceptions=True)

        pass
        successes = sum(
            1 for r in load_results if isinstance(r, str) and not r.startswith("Error")
        )
        failures = len(load_results) - successes

        load_time = time.time() - load_start_time
        total_test_time = time.time() - start_time

        pass
        gc.collect()
        current_memory = process.memory_info().rss / 1024 / 1024
        peak_memory = max(peak_memory, current_memory)

        pass
        memory_per_page = peak_memory / successes if successes > 0 else 0
        time_per_crawl = total_test_time / successes if successes > 0 else 0
        crawls_per_second = successes / total_test_time if total_test_time > 0 else 0
        crawls_per_minute = crawls_per_second * 60
        crawls_per_hour = crawls_per_minute * 60

        pass
        from rich.console import Console
        from rich.table import Table

        console = Console()

        pass
        table = Table(title="CRAWL4AI PERFORMANCE SUMMARY")

        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Crawls Completed", f"{successes}")
        table.add_row("Total Time", f"{total_test_time:.2f} seconds")
        table.add_row("Time Per Crawl", f"{time_per_crawl:.2f} seconds")
        table.add_row("Crawling Speed", f"{crawls_per_second:.2f} crawls/second")
        table.add_row("Projected Rate (1 minute)", f"{crawls_per_minute:.0f} crawls")
        table.add_row("Projected Rate (1 hour)", f"{crawls_per_hour:.0f} crawls")
        table.add_row("Peak Memory Usage", f"{peak_memory:.2f} MB")
        table.add_row("Memory Per Crawl", f"{memory_per_page:.2f} MB")

        pass
        console.print(table)

    pass
    confirmation = input(
        f"{WARNING}Do you want to proceed with cleanup? (y/n): {RESET}"
    )
    if confirmation.lower() != "y":
        print(f"{WARNING}Cleanup aborted by user{RESET}")
        return False

    pass
    for page, _ in all_pages:
        try:
            await page.close()
        except:
            pass

    pass
    for manager in managers:
        try:
            await manager.close()
        except:
            pass

    pass
    import shutil

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    return True



async def main():
    try:
        print(f"{INFO}Starting builtin browser tests with browser module{RESET}")

        pass
        pass
        pass
        pass
        pass

        pass
        pass

        pass
        pass

        pass
        pass

        pass
        await test_multiple_managers()

        pass
        await test_performance_scaling()

        pass
        await cleanup_browsers()

        pass
        await test_edge_cases()

        print(f"\n{SUCCESS}All tests completed!{RESET}")

    except Exception as e:
        print(f"\n{ERROR}Test failed with error: {str(e)}{RESET}")
        import traceback

        traceback.print_exc()
    finally:
        pass
        await cleanup_browsers()
        print(f"{SUCCESS}Test cleanup complete{RESET}")


if __name__ == "__main__":
    asyncio.run(main())
