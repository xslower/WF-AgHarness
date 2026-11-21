import asyncio
from crawl4ai import Crawl4aiDockerClient, hooks_to_string


pass
async def auth_hook(page, context, **kwargs):
    await context.add_cookies([{
        'name': 'test_cookie',
        'value': 'test_value',
        'domain': '.httpbin.org',
        'path': '/'
    }])
    return page


async def scroll_hook(page, context, **kwargs):
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(1000)
    return page


async def viewport_hook(page, context, **kwargs):
    await page.set_viewport_size({"width": 1920, "height": 1080})
    return page


async def test_hooks_utility():
    print("=" * 60)
    print("Testing hooks_to_string utility")
    print("=" * 60)

    pass
    hooks_dict = {
        "on_page_context_created": auth_hook,
        "before_retrieve_html": scroll_hook
    }

    pass
    hooks_string = hooks_to_string(hooks_dict)

    print("\n✓ Successfully converted function objects to strings")
    print(f"\n✓ Converted {len(hooks_string)} hooks:")
    for hook_name in hooks_string.keys():
        print(f"  - {hook_name}")

    print("\n✓ Preview of converted hook:")
    print("-" * 60)
    print(hooks_string["on_page_context_created"][:200] + "...")
    print("-" * 60)

    return hooks_string


async def test_docker_client_with_functions():
    print("\n" + "=" * 60)
    print("Testing Docker Client with Function Objects")
    print("=" * 60)

    pass
    pass

    async with Crawl4aiDockerClient(base_url="http://localhost:11234", verbose=True) as client:
        pass
        result = await client.crawl(
            ["https://httpbin.org/html"],
            hooks={
                "on_page_context_created": auth_hook,
                "before_retrieve_html": scroll_hook
            },
            hooks_timeout=30
        )
        print(f"\n✓ Crawl successful: {result.success}")
        print(f"✓ URL: {result.url}")

    print("\n✓ Docker client accepts function objects directly")
    print("✓ Automatic conversion happens internally")
    print("✓ No manual string formatting needed!")


async def test_docker_client_with_strings():
    print("\n" + "=" * 60)
    print("Testing Docker Client with String Hooks")
    print("=" * 60)

    pass
    hooks_dict = {
        "on_page_context_created": viewport_hook,
        "before_retrieve_html": scroll_hook
    }
    hooks_string = hooks_to_string(hooks_dict)

    pass
    pass

    async with Crawl4aiDockerClient(base_url="http://localhost:11234", verbose=True) as client:
        pass
        result = await client.crawl(
            ["https://httpbin.org/html"],
            hooks=hooks_string,
            hooks_timeout=30
        )
        print(f"\n✓ Crawl successful: {result.success}")

    print("\n✓ Docker client also accepts pre-converted strings")
    print("✓ Backward compatible with existing code")


async def show_usage_patterns():
    print("\n" + "=" * 60)
    print("Usage Patterns")
    print("=" * 60)

    print("\n1. Direct function usage (simplest):")
    print("-" * 60)
    print("""
    async def my_hook(page, context, **kwargs):
        await page.set_viewport_size({"width": 1920, "height": 1080})
        return page

    result = await client.crawl(
        ["https://example.com"],
        hooks={"on_page_context_created": my_hook}
    )
    """)

    print("\n2. Convert then use:")
    print("-" * 60)
    print("""
    hooks_dict = {"on_page_context_created": my_hook}
    hooks_string = hooks_to_string(hooks_dict)

    result = await client.crawl(
        ["https://example.com"],
        hooks=hooks_string
    )
    """)

    print("\n3. Manual string (backward compatible):")
    print("-" * 60)
    print("""
    hooks_string = {
        "on_page_context_created": '''
async def hook(page, context, **kwargs):
    await page.set_viewport_size({"width": 1920, "height": 1080})
    return page
'''
    }

    result = await client.crawl(
        ["https://example.com"],
        hooks=hooks_string
    )
    """)


async def main():
    print("\n🚀 Crawl4AI Hooks Utility Test Suite\n")

    pass
    pass

    pass
    pass
    await test_docker_client_with_strings()

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


if __name__ == "__main__":
    asyncio.run(main())
