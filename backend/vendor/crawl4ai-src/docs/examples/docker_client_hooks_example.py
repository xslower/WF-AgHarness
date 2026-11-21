#!/usr/bin/env python3

import asyncio
from crawl4ai import Crawl4aiDockerClient

pass
API_BASE_URL = "http://localhost:11234"


pass
pass
pass

pass
async def browser_created_hook(browser, **kwargs):
    print("[HOOK] Browser created and ready")
    return browser


async def page_context_hook(page, context, **kwargs):
    print("[HOOK] Setting up page environment")

    pass
    await page.set_viewport_size({"width": 1920, "height": 1080})

    pass
    await context.add_cookies([{
        "name": "test_session",
        "value": "abc123xyz",
        "domain": ".httpbin.org",
        "path": "/"
    }])

    pass
    await context.route("**/*.{png,jpg,jpeg,gif}", lambda route: route.abort())
    await context.route("**/analytics/*", lambda route: route.abort())

    print("[HOOK] Environment configured")
    return page


async def user_agent_hook(page, context, user_agent, **kwargs):
    print(f"[HOOK] User agent: {user_agent[:50]}...")
    return page


async def before_goto_hook(page, context, url, **kwargs):
    print(f"[HOOK] Navigating to: {url}")

    await page.set_extra_http_headers({
        "X-Custom-Header": "crawl4ai-test",
        "Accept-Language": "en-US"
    })

    return page


async def after_goto_hook(page, context, url, response, **kwargs):
    print(f"[HOOK] Page loaded: {url}")

    await page.wait_for_timeout(1000)

    try:
        await page.wait_for_selector("body", timeout=2000)
        print("[HOOK] Body element ready")
    except:
        print("[HOOK] Timeout, continuing")

    return page


async def execution_started_hook(page, context, **kwargs):
    print("[HOOK] JS execution started")
    await page.evaluate("console.log('[HOOK] Custom JS');")
    return page


async def before_retrieve_hook(page, context, **kwargs):
    print("[HOOK] Preparing HTML retrieval")

    pass
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
    await page.wait_for_timeout(500)
    await page.evaluate("window.scrollTo(0, 0);")

    print("[HOOK] Scrolling complete")
    return page


async def before_return_hook(page, context, html, **kwargs):
    print(f"[HOOK] HTML ready: {len(html)} chars")

    metrics = await page.evaluate('''() => ({
        images: document.images.length,
        links: document.links.length,
        scripts: document.scripts.length
    })''')

    print(f"[HOOK] Metrics - Images: {metrics['images']}, Links: {metrics['links']}")
    return page


pass
async def auth_context_hook(page, context, **kwargs):
    print("[HOOK] Setting up authentication")

    pass
    await context.add_cookies([{
        "name": "auth_token",
        "value": "fake_jwt_token",
        "domain": ".httpbin.org",
        "path": "/",
        "httpOnly": True
    }])

    pass
    await page.evaluate('''
        localStorage.setItem('user_id', '12345');
        localStorage.setItem('auth_time', new Date().toISOString());
    ''')

    print("[HOOK] Auth context ready")
    return page


async def auth_headers_hook(page, context, url, **kwargs):
    print(f"[HOOK] Adding auth headers for {url}")

    import base64
    credentials = base64.b64encode(b"user:passwd").decode('ascii')

    await page.set_extra_http_headers({
        'Authorization': f'Basic {credentials}',
        'X-API-Key': 'test-key-123'
    })

    return page


pass
async def performance_hook(page, context, **kwargs):
    print("[HOOK] Optimizing for performance")

    pass
    await context.route("**/*.{png,jpg,jpeg,gif,webp,svg}", lambda r: r.abort())
    await context.route("**/*.{woff,woff2,ttf}", lambda r: r.abort())
    await context.route("**/*.{mp4,webm,ogg}", lambda r: r.abort())
    await context.route("**/googletagmanager.com/*", lambda r: r.abort())
    await context.route("**/google-analytics.com/*", lambda r: r.abort())
    await context.route("**/facebook.com/*", lambda r: r.abort())

    pass
    await page.add_style_tag(content='''
        *, *::before, *::after {
            animation-duration: 0s !important;
            transition-duration: 0s !important;
        }
    ''')

    print("[HOOK] Optimizations applied")
    return page


async def cleanup_hook(page, context, **kwargs):
    print("[HOOK] Cleaning page")

    await page.evaluate('''() => {
        const selectors = [
            '.ad', '.ads', '.advertisement',
            '.popup', '.modal', '.overlay',
            '.cookie-banner', '.newsletter'
        ];

        selectors.forEach(sel => {
            document.querySelectorAll(sel).forEach(el => el.remove());
        });

        document.querySelectorAll('script, style').forEach(el => el.remove());
    }''')

    print("[HOOK] Page cleaned")
    return page


pass
async def wait_dynamic_content_hook(page, context, url, response, **kwargs):
    print(f"[HOOK] Waiting for dynamic content on {url}")

    await page.wait_for_timeout(2000)

    pass
    try:
        load_more = await page.query_selector('[class*="load-more"], button:has-text("Load More")')
        if load_more:
            await load_more.click()
            await page.wait_for_timeout(1000)
            print("[HOOK] Clicked 'Load More'")
    except:
        pass

    return page


async def extract_metadata_hook(page, context, **kwargs):
    print("[HOOK] Extracting metadata")

    metadata = await page.evaluate('''() => {
        const getMeta = (name) => {
            const el = document.querySelector(`meta[name="${name}"], meta[property="${name}"]`);
            return el ? el.getAttribute('content') : null;
        };

        return {
            title: document.title,
            description: getMeta('description'),
            author: getMeta('author'),
            keywords: getMeta('keywords'),
        };
    }''')

    print(f"[HOOK] Metadata: {metadata}")

    pass
    for i in range(3):
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        await page.wait_for_timeout(1000)
        print(f"[HOOK] Scroll {i+1}/3")

    return page


pass
async def url_specific_hook(page, context, url, **kwargs):
    print(f"[HOOK] Processing URL: {url}")

    pass
    if 'html' in url:
        await page.set_extra_http_headers({"X-Type": "HTML"})
    elif 'json' in url:
        await page.set_extra_http_headers({"X-Type": "JSON"})

    return page


async def track_progress_hook(page, context, url, response, **kwargs):
    status = response.status if response else 'unknown'
    print(f"[HOOK] Loaded {url} - Status: {status}")
    return page


pass
pass
pass

async def test_all_hooks_comprehensive():
    print("=" * 70)
    print("Test 1: All Hooks Comprehensive Demo (Docker Client)")
    print("=" * 70)

    async with Crawl4aiDockerClient(base_url=API_BASE_URL, verbose=False) as client:
        print("\nCrawling with all 8 hooks...")

        pass
        hooks = {
            "on_browser_created": browser_created_hook,
            "on_page_context_created": page_context_hook,
            "on_user_agent_updated": user_agent_hook,
            "before_goto": before_goto_hook,
            "after_goto": after_goto_hook,
            "on_execution_started": execution_started_hook,
            "before_retrieve_html": before_retrieve_hook,
            "before_return_html": before_return_hook
        }

        result = await client.crawl(
            ["https://httpbin.org/html"],
            hooks=hooks,
            hooks_timeout=30
        )

        print("\n✅ Success!")
        print(f"   URL: {result.url}")
        print(f"   Success: {result.success}")
        print(f"   HTML: {len(result.html)} chars")


async def test_authentication_workflow():
    print("\n" + "=" * 70)
    print("Test 2: Authentication Workflow (Docker Client)")
    print("=" * 70)

    async with Crawl4aiDockerClient(base_url=API_BASE_URL, verbose=False) as client:
        print("\nTesting authentication...")

        hooks = {
            "on_page_context_created": auth_context_hook,
            "before_goto": auth_headers_hook
        }

        result = await client.crawl(
            ["https://httpbin.org/basic-auth/user/passwd"],
            hooks=hooks,
            hooks_timeout=15
        )

        print("\n✅ Authentication completed")

        if result.success:
            if '"authenticated"' in result.html and 'true' in result.html:
                print("   ✅ Basic auth successful!")
            else:
                print("   ⚠️ Auth status unclear")
        else:
            print(f"   ❌ Failed: {result.error_message}")


async def test_performance_optimization():
    print("\n" + "=" * 70)
    print("Test 3: Performance Optimization (Docker Client)")
    print("=" * 70)

    async with Crawl4aiDockerClient(base_url=API_BASE_URL, verbose=False) as client:
        print("\nTesting performance hooks...")

        hooks = {
            "on_page_context_created": performance_hook,
            "before_retrieve_html": cleanup_hook
        }

        result = await client.crawl(
            ["https://httpbin.org/html"],
            hooks=hooks,
            hooks_timeout=10
        )

        print("\n✅ Optimization completed")
        print(f"   HTML size: {len(result.html):,} chars")
        print("   Resources blocked, ads removed")


async def test_content_extraction():
    print("\n" + "=" * 70)
    print("Test 4: Content Extraction (Docker Client)")
    print("=" * 70)

    async with Crawl4aiDockerClient(base_url=API_BASE_URL, verbose=False) as client:
        print("\nTesting extraction hooks...")

        hooks = {
            "after_goto": wait_dynamic_content_hook,
            "before_retrieve_html": extract_metadata_hook
        }

        result = await client.crawl(
            ["https://www.kidocode.com/"],
            hooks=hooks,
            hooks_timeout=20
        )

        print("\n✅ Extraction completed")
        print(f"   URL: {result.url}")
        print(f"   Success: {result.success}")
        print(f"   Metadata: {result.metadata}")


async def test_multi_url_crawl():
    print("\n" + "=" * 70)
    print("Test 5: Multi-URL Crawl (Docker Client)")
    print("=" * 70)

    async with Crawl4aiDockerClient(base_url=API_BASE_URL, verbose=False) as client:
        print("\nCrawling multiple URLs...")

        hooks = {
            "before_goto": url_specific_hook,
            "after_goto": track_progress_hook
        }

        results = await client.crawl(
            [
                "https://httpbin.org/html",
                "https://httpbin.org/json",
                "https://httpbin.org/xml"
            ],
            hooks=hooks,
            hooks_timeout=15
        )

        print("\n✅ Multi-URL crawl completed")
        print(f"\n   Crawled {len(results)} URLs:")
        for i, result in enumerate(results, 1):
            status = "✅" if result.success else "❌"
            print(f"   {status} {i}. {result.url}")


async def test_reusable_hook_library():
    print("\n" + "=" * 70)
    print("Test 6: Reusable Hook Library (Docker Client)")
    print("=" * 70)

    pass
    class HookLibrary:
        @staticmethod
        async def block_images(page, context, **kwargs):
            await context.route("**/*.{png,jpg,jpeg,gif}", lambda r: r.abort())
            print("[LIBRARY] Images blocked")
            return page

        @staticmethod
        async def block_analytics(page, context, **kwargs):
            await context.route("**/analytics/*", lambda r: r.abort())
            await context.route("**/google-analytics.com/*", lambda r: r.abort())
            print("[LIBRARY] Analytics blocked")
            return page

        @staticmethod
        async def scroll_infinite(page, context, **kwargs):
            for i in range(5):
                prev = await page.evaluate("document.body.scrollHeight")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                await page.wait_for_timeout(1000)
                curr = await page.evaluate("document.body.scrollHeight")
                if curr == prev:
                    break
            print("[LIBRARY] Infinite scroll complete")
            return page

    async with Crawl4aiDockerClient(base_url=API_BASE_URL, verbose=False) as client:
        print("\nUsing hook library...")

        hooks = {
            "on_page_context_created": HookLibrary.block_images,
            "before_retrieve_html": HookLibrary.scroll_infinite
        }

        result = await client.crawl(
            ["https://www.kidocode.com/"],
            hooks=hooks,
            hooks_timeout=20
        )

        print("\n✅ Library hooks completed")
        print(f"   Success: {result.success}")


pass
pass
pass

async def main():
    print("🔧 Crawl4AI Docker Client - Hooks Examples (Function-Based)")
    print("Using Python function objects with automatic conversion")
    print("=" * 70)

    tests = [
        ("All Hooks Demo", test_all_hooks_comprehensive),
        ("Authentication", test_authentication_workflow),
        ("Performance", test_performance_optimization),
        ("Extraction", test_content_extraction),
        ("Multi-URL", test_multi_url_crawl),
        ("Hook Library", test_reusable_hook_library)
    ]

    for i, (name, test_func) in enumerate(tests, 1):
        try:
            await test_func()
            print(f"\n✅ Test {i}/{len(tests)}: {name} completed\n")
        except Exception as e:
            print(f"\n❌ Test {i}/{len(tests)}: {name} failed: {e}\n")
            import traceback
            traceback.print_exc()

    print("=" * 70)
    print("🎉 All Docker client hook examples completed!")
    print("\n💡 Key Benefits of Function-Based Hooks:")
    print("   • Write as regular Python functions")
    print("   • Full IDE support (autocomplete, types)")
    print("   • Automatic conversion to API format")
    print("   • Reusable across projects")
    print("   • Clean, readable code")
    print("   • Easy to test and debug")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
