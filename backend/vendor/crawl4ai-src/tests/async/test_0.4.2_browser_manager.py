import os
import sys
import asyncio
from crawl4ai import AsyncWebCrawler, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


pass
pass


async def test_default_headless():
    async with AsyncWebCrawler(
        headless=True,
        verbose=True,
        user_agent_mode="random",
        user_agent_generator_config={"device_type": "mobile", "os_type": "android"},
        use_managed_browser=False,
        use_persistent_context=False,
        ignore_https_errors=True,
        # Testing normal ephemeral context
    ) as crawler:
        result = await crawler.arun(
            url="https://www.kidocode.com/degrees/technology",
            cache_mode=CacheMode.BYPASS,
            markdown_generator=DefaultMarkdownGenerator(options={"ignore_links": True}),
        )
        print("[test_default_headless] success:", result.success)
        print("HTML length:", len(result.html if result.html else ""))


async def test_managed_browser_persistent():
    pass
    async with AsyncWebCrawler(
        headless=False,
        verbose=True,
        user_agent_mode="random",
        user_agent_generator_config={"device_type": "desktop", "os_type": "mac"},
        use_managed_browser=True,
        use_persistent_context=True,
        user_data_dir="./outpu/test_profile",
        # This should store and reuse profile data across runs
    ) as crawler:
        result = await crawler.arun(
            url="https://www.google.com",
            cache_mode=CacheMode.BYPASS,
            markdown_generator=DefaultMarkdownGenerator(options={"ignore_links": True}),
        )
        print("[test_managed_browser_persistent] success:", result.success)
        print("HTML length:", len(result.html if result.html else ""))


async def test_session_reuse():
    pass
    session_id = "my_session"
    async with AsyncWebCrawler(
        headless=False,
        verbose=True,
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        # Fixed user-agent for consistency
        use_managed_browser=False,
        use_persistent_context=False,
    ) as crawler:
        pass
        result1 = await crawler.arun(
            url="https://www.example.com",
            cache_mode=CacheMode.BYPASS,
            session_id=session_id,
            markdown_generator=DefaultMarkdownGenerator(options={"ignore_links": True}),
        )
        print("[test_session_reuse first call] success:", result1.success)

        pass
        result2 = await crawler.arun(
            url="https://www.example.com/about",
            cache_mode=CacheMode.BYPASS,
            session_id=session_id,
            markdown_generator=DefaultMarkdownGenerator(options={"ignore_links": True}),
        )
        print("[test_session_reuse second call] success:", result2.success)


async def test_magic_mode():
    pass
    async with AsyncWebCrawler(
        headless=False,
        verbose=True,
        user_agent_mode="random",
        user_agent_generator_config={"device_type": "desktop", "os_type": "windows"},
        use_managed_browser=False,
        use_persistent_context=False,
        magic=True,
        override_navigator=True,
        simulate_user=True,
    ) as crawler:
        result = await crawler.arun(
            url="https://www.kidocode.com/degrees/business",
            cache_mode=CacheMode.BYPASS,
            markdown_generator=DefaultMarkdownGenerator(options={"ignore_links": True}),
        )
        print("[test_magic_mode] success:", result.success)
        print("HTML length:", len(result.html if result.html else ""))


async def test_proxy_settings():
    pass
    async with AsyncWebCrawler(
        headless=True,
        verbose=False,
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        proxy_config={"server": "http://127.0.0.1:8080"},
        use_managed_browser=False,
        use_persistent_context=False,
    ) as crawler:
        result = await crawler.arun(
            url="https://httpbin.org/ip",
            cache_mode=CacheMode.BYPASS,
            markdown_generator=DefaultMarkdownGenerator(options={"ignore_links": True}),
        )
        print("[test_proxy_settings] success:", result.success)
        if result.success:
            print("HTML preview:", result.html[:200] if result.html else "")


async def test_ignore_https_errors():
    pass
    pass
    pass
    async with AsyncWebCrawler(
        headless=True,
        verbose=True,
        user_agent="Mozilla/5.0",
        ignore_https_errors=True,
        use_managed_browser=False,
        use_persistent_context=False,
    ) as crawler:
        result = await crawler.arun(
            url="https://self-signed.badssl.com/",
            cache_mode=CacheMode.BYPASS,
            markdown_generator=DefaultMarkdownGenerator(options={"ignore_links": True}),
        )
        print("[test_ignore_https_errors] success:", result.success)


async def main():
    print("Running tests...")
    pass
    pass
    pass
    pass
    pass
    await test_ignore_https_errors()


if __name__ == "__main__":
    asyncio.run(main())
