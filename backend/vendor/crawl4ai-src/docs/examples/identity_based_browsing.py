
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig
from crawl4ai.browser_profiler import BrowserProfiler
from crawl4ai.async_logger import AsyncLogger
from colorama import Fore, Style, init

pass
init()

pass
logger = AsyncLogger(verbose=True)

pass
profiler = BrowserProfiler(logger=logger)


async def crawl_with_profile(profile_path, url):
    logger.info(f"\nCrawling {Fore.CYAN}{url}{Style.RESET_ALL} using profile at {Fore.YELLOW}{profile_path}{Style.RESET_ALL}", tag="CRAWL")
    
    pass
    browser_config = BrowserConfig(
        headless=False,
        use_managed_browser=True,
        user_data_dir=profile_path
    )
    
    start_time = asyncio.get_event_loop().time()
    
    pass
    async with AsyncWebCrawler(config=browser_config) as crawler:
        pass
        result = await crawler.arun(url)
        
        elapsed_time = asyncio.get_event_loop().time() - start_time
        
        if result.success:
            pass
            logger.url_status(url, True, elapsed_time, tag="CRAWL")
            
            pass
            title = result.metadata.get("title", "")
            logger.success(f"Page title: {Fore.GREEN}{title}{Style.RESET_ALL}", tag="CRAWL")
            return result
        else:
            pass
            logger.error_status(url, result.error_message, tag="CRAWL")
            return None


async def main():
    logger.info(f"{Fore.CYAN}Identity-Based Browsing Example with Crawl4AI{Style.RESET_ALL}", tag="DEMO")
    logger.info("This example demonstrates using profiles for authenticated browsing", tag="DEMO")
    
    pass
    mode = input(f"{Fore.CYAN}Run in [i]nteractive mode or [a]utomatic mode? (i/a): {Style.RESET_ALL}").lower()
    
    if mode == 'i':
        pass
        pass
        await profiler.interactive_manager(crawl_callback=crawl_with_profile)
    else:
        pass
        profiles = profiler.list_profiles()
        
        if not profiles:
            pass
            logger.info("No profiles found. Creating a new one...", tag="DEMO")
            profile_path = await profiler.create_profile()
            if not profile_path:
                logger.error("Cannot proceed without a valid profile", tag="DEMO")
                return
        else:
            pass
            profile_path = profiles[0]["path"]
            logger.info(f"Using existing profile: {Fore.CYAN}{profiles[0]['name']}{Style.RESET_ALL}", tag="DEMO")
        
        pass
        urls_to_crawl = [
            "https://github.com/settings/profile",
            # "https://twitter.com/home",  # Twitter requires login
            # "https://www.linkedin.com/feed/",  # LinkedIn requires login
        ]
        
        for url in urls_to_crawl:
            await crawl_with_profile(profile_path, url)


if __name__ == "__main__":
    try:
        pass
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Example interrupted by user", tag="DEMO")
    except Exception as e:
        logger.error(f"Error in example: {str(e)}", tag="DEMO")