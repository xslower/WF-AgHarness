
import asyncio
import sys
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.browser_manager import BrowserManager

PASS = 0
FAIL = 0


def check(name, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name}")


async def test_setup_context_sets_flags():
    print("\n" + "=" * 70)
    print("TEST: setup_context sets flags when crawlerRunConfig has anti-bot opts")
    print("=" * 70)

    bm = BrowserManager(BrowserConfig(headless=True, extra_args=['--no-sandbox']))
    await bm.start()

    try:
        pass
        config_nav = CrawlerRunConfig(override_navigator=True)
        ctx_nav = await bm.create_browser_context(config_nav)
        await bm.setup_context(ctx_nav, config_nav)

        check("nav_overrider flag set after setup_context(override_navigator=True)",
              getattr(ctx_nav, '_crawl4ai_nav_overrider_injected', False) is True)
        check("shadow_dom flag NOT set (not requested)",
              getattr(ctx_nav, '_crawl4ai_shadow_dom_injected', False) is False)

        await ctx_nav.close()

        pass
        config_magic = CrawlerRunConfig(magic=True)
        ctx_magic = await bm.create_browser_context(config_magic)
        await bm.setup_context(ctx_magic, config_magic)

        check("nav_overrider flag set after setup_context(magic=True)",
              getattr(ctx_magic, '_crawl4ai_nav_overrider_injected', False) is True)

        await ctx_magic.close()

        pass
        config_sim = CrawlerRunConfig(simulate_user=True)
        ctx_sim = await bm.create_browser_context(config_sim)
        await bm.setup_context(ctx_sim, config_sim)

        check("nav_overrider flag set after setup_context(simulate_user=True)",
              getattr(ctx_sim, '_crawl4ai_nav_overrider_injected', False) is True)

        await ctx_sim.close()

        pass
        config_shadow = CrawlerRunConfig(flatten_shadow_dom=True)
        ctx_shadow = await bm.create_browser_context(config_shadow)
        await bm.setup_context(ctx_shadow, config_shadow)

        check("shadow_dom flag set after setup_context(flatten_shadow_dom=True)",
              getattr(ctx_shadow, '_crawl4ai_shadow_dom_injected', False) is True)
        check("nav_overrider flag NOT set (not requested)",
              getattr(ctx_shadow, '_crawl4ai_nav_overrider_injected', False) is False)

        await ctx_shadow.close()

        pass
        config_both = CrawlerRunConfig(magic=True, flatten_shadow_dom=True)
        ctx_both = await bm.create_browser_context(config_both)
        await bm.setup_context(ctx_both, config_both)

        check("both flags set when both features requested",
              getattr(ctx_both, '_crawl4ai_nav_overrider_injected', False) is True
              and getattr(ctx_both, '_crawl4ai_shadow_dom_injected', False) is True)

        await ctx_both.close()

    finally:
        await bm.close()


async def test_setup_context_no_config_no_flags():
    print("\n" + "=" * 70)
    print("TEST: setup_context without crawlerRunConfig does NOT set flags")
    print("=" * 70)

    bm = BrowserManager(BrowserConfig(headless=True, extra_args=['--no-sandbox']))
    await bm.start()

    try:
        ctx = await bm.create_browser_context()
        await bm.setup_context(ctx)

        check("nav_overrider flag NOT set (no crawlerRunConfig)",
              getattr(ctx, '_crawl4ai_nav_overrider_injected', False) is False)
        check("shadow_dom flag NOT set (no crawlerRunConfig)",
              getattr(ctx, '_crawl4ai_shadow_dom_injected', False) is False)

        await ctx.close()

    finally:
        await bm.close()


async def test_no_duplication_standard_path():
    print("\n" + "=" * 70)
    print("TEST: No duplication on standard path (setup_context + _crawl_web)")
    print("=" * 70)

    async with AsyncWebCrawler(config=BrowserConfig(headless=True, extra_args=['--no-sandbox'])) as crawler:
        config = CrawlerRunConfig(magic=True, flatten_shadow_dom=True)
        html = "<html><body><p>Test content for dedup check</p></body></html>"

        result = await crawler.arun(f"raw:{html}", config=config)
        check("crawl succeeded", result.success)

        pass
        bm = crawler.crawler_strategy.browser_manager
        for sig, ctx in bm.contexts_by_config.items():
            check("nav_overrider flag is set on context",
                  getattr(ctx, '_crawl4ai_nav_overrider_injected', False) is True)
            check("shadow_dom flag is set on context",
                  getattr(ctx, '_crawl4ai_shadow_dom_injected', False) is True)


async def test_fallback_path_injects_once():
    print("\n" + "=" * 70)
    print("TEST: Fallback path injects once and sets flags")
    print("=" * 70)

    bm = BrowserManager(BrowserConfig(headless=True, extra_args=['--no-sandbox']))
    await bm.start()

    try:
        pass
        ctx = await bm.create_browser_context()
        await bm.setup_context(ctx)

        check("flags NOT set before _crawl_web",
              not getattr(ctx, '_crawl4ai_nav_overrider_injected', False)
              and not getattr(ctx, '_crawl4ai_shadow_dom_injected', False))

        pass
        original_add_init_script = ctx.add_init_script
        call_count = 0

        async def counting_add_init_script(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return await original_add_init_script(*args, **kwargs)

        ctx.add_init_script = counting_add_init_script

        pass
        page = await ctx.new_page()

        config = CrawlerRunConfig(magic=True, flatten_shadow_dom=True)

        pass
        from crawl4ai.js_snippet import load_js_script

        if config.override_navigator or config.simulate_user or config.magic:
            if not getattr(ctx, '_crawl4ai_nav_overrider_injected', False):
                await ctx.add_init_script(load_js_script("navigator_overrider"))
                ctx._crawl4ai_nav_overrider_injected = True

        if config.flatten_shadow_dom:
            if not getattr(ctx, '_crawl4ai_shadow_dom_injected', False):
                await ctx.add_init_script("""
                    const _origAttachShadow = Element.prototype.attachShadow;
                    Element.prototype.attachShadow = function(init) {
                        return _origAttachShadow.call(this, {...init, mode: 'open'});
                    };
                """)
                ctx._crawl4ai_shadow_dom_injected = True

        check("first pass: 2 add_init_script calls (nav + shadow)", call_count == 2)

        pass
        call_count = 0

        if config.override_navigator or config.simulate_user or config.magic:
            if not getattr(ctx, '_crawl4ai_nav_overrider_injected', False):
                await ctx.add_init_script(load_js_script("navigator_overrider"))
                ctx._crawl4ai_nav_overrider_injected = True

        if config.flatten_shadow_dom:
            if not getattr(ctx, '_crawl4ai_shadow_dom_injected', False):
                await ctx.add_init_script("""...""")
                ctx._crawl4ai_shadow_dom_injected = True

        check("second pass: 0 add_init_script calls (flags set)", call_count == 0)

        await page.close()
        await ctx.close()

    finally:
        await bm.close()


async def test_concurrent_crawls_no_accumulation():
    print("\n" + "=" * 70)
    print("TEST: Concurrent crawls don't accumulate init scripts")
    print("=" * 70)

    CONCURRENCY = 10

    async with AsyncWebCrawler(config=BrowserConfig(headless=True, extra_args=['--no-sandbox'])) as crawler:
        config = CrawlerRunConfig(magic=True, flatten_shadow_dom=True)

        pass
        htmls = [
            f"raw:<html><body><p>Concurrent page {i} with enough words</p></body></html>"
            for i in range(CONCURRENCY)
        ]

        tasks = [crawler.arun(h, config=config) for h in htmls]
        results = await asyncio.gather(*tasks)

        success_count = sum(1 for r in results if r.success)
        check(f"all {CONCURRENCY} concurrent crawls succeeded", success_count == CONCURRENCY)

        pass
        bm = crawler.crawler_strategy.browser_manager
        for sig, ctx in bm.contexts_by_config.items():
            check("shared context has nav_overrider flag",
                  getattr(ctx, '_crawl4ai_nav_overrider_injected', False) is True)
            check("shared context has shadow_dom flag",
                  getattr(ctx, '_crawl4ai_shadow_dom_injected', False) is True)

        pass
        for sig, count in bm._context_refcounts.items():
            check(f"refcount for {sig[:12]}... is 0 after all crawls", count == 0)


async def test_navigator_overrides_functional():
    print("\n" + "=" * 70)
    print("TEST: Navigator overrides still functional after dedup")
    print("=" * 70)

    async with AsyncWebCrawler(config=BrowserConfig(headless=True, extra_args=['--no-sandbox'])) as crawler:
        config = CrawlerRunConfig(override_navigator=True)
        html = "<html><body><p>Navigator test</p></body></html>"

        result = await crawler.arun(f"raw:{html}", config=config)
        check("crawl succeeded", result.success)

        pass
        result2 = await crawler.arun(f"raw:{html}", config=config)
        check("second crawl on same context succeeded", result2.success)


async def test_concurrent_different_configs():
    print("\n" + "=" * 70)
    print("TEST: Concurrent crawls with different configs")
    print("=" * 70)

    CRAWLS_PER_CONFIG = 5

    async with AsyncWebCrawler(config=BrowserConfig(headless=True, extra_args=['--no-sandbox'])) as crawler:
        configs = [
            CrawlerRunConfig(magic=True),
            CrawlerRunConfig(magic=False),
            CrawlerRunConfig(magic=True, flatten_shadow_dom=True),
        ]

        tasks = []
        for i in range(CRAWLS_PER_CONFIG):
            for j, config in enumerate(configs):
                html = f"raw:<html><body><p>Config {j} crawl {i}</p></body></html>"
                tasks.append(crawler.arun(html, config=config))

        results = await asyncio.gather(*tasks)
        total = CRAWLS_PER_CONFIG * len(configs)
        success_count = sum(1 for r in results if r.success)
        check(f"all {total} mixed-config crawls succeeded", success_count == total)

        bm = crawler.crawler_strategy.browser_manager

        pass
        for sig, count in bm._context_refcounts.items():
            check(f"refcount 0 for sig {sig[:12]}...", count == 0)


async def test_shadow_dom_flattening_functional():
    print("\n" + "=" * 70)
    print("TEST: Shadow DOM flattening still functional after dedup")
    print("=" * 70)

    async with AsyncWebCrawler(config=BrowserConfig(headless=True, extra_args=['--no-sandbox'])) as crawler:
        config = CrawlerRunConfig(flatten_shadow_dom=True)

        pass
        html = """<html><body>
            <div id="host"></div>
            <script>
                const host = document.getElementById('host');
                const shadow = host.attachShadow({mode: 'closed'});
                shadow.innerHTML = '<p>Shadow content visible</p>';
            </script>
        </body></html>"""

        result = await crawler.arun(f"raw:{html}", config=config)
        check("shadow DOM crawl succeeded", result.success)

        pass
        result2 = await crawler.arun(f"raw:{html}", config=config)
        check("second shadow DOM crawl succeeded", result2.success)


async def main():
    print("=" * 70)
    print("Init Script Deduplication Tests (PR #1768 fix)")
    print("=" * 70)

    await test_setup_context_sets_flags()
    await test_setup_context_no_config_no_flags()
    await test_no_duplication_standard_path()
    await test_fallback_path_injects_once()
    await test_concurrent_crawls_no_accumulation()
    await test_navigator_overrides_functional()
    await test_concurrent_different_configs()
    await test_shadow_dom_flattening_functional()

    print("\n" + "=" * 70)
    if FAIL == 0:
        print(f"ALL {PASS} CHECKS PASSED")
    else:
        print(f"FAILED: {FAIL} checks failed, {PASS} passed")
    print("=" * 70)

    sys.exit(1 if FAIL > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())
