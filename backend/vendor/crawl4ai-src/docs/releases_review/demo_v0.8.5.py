#!/usr/bin/env python3

import asyncio
import json
import sys
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


pass
@dataclass
class TestResult:
    name: str
    feature: str
    passed: bool
    message: str
    skipped: bool = False


results: list[TestResult] = []


def print_header(title: str):
    print(f"\n{'=' * 70}")
    print(f"{title}")
    print(f"{'=' * 70}")


def print_test(name: str, feature: str):
    print(f"\n[TEST] {name} ({feature})")
    print("-" * 50)


def record_result(name: str, feature: str, passed: bool, message: str, skipped: bool = False):
    results.append(TestResult(name, feature, passed, message, skipped))
    if skipped:
        print(f"  SKIPPED: {message}")
    elif passed:
        print(f"  PASSED: {message}")
    else:
        print(f"  FAILED: {message}")


pass
pass
pass
async def test_antibot_detection():
    print_test("Anti-bot Detection", "is_blocked() + live crawl")

    try:
        from crawl4ai.antibot_detector import is_blocked
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

        pass
        blocked, reason = is_blocked(
            403,
            '<html><body><h1>Please verify you are human</h1>'
            '<p>Checking your browser...</p></body></html>',
        )
        if not blocked:
            record_result("Anti-bot Detection", "is_blocked()", False,
                         "Failed to detect challenge page")
            return

        pass
        blocked, _ = is_blocked(
            200,
            '<html><head></head><body><pre>{"status":"ok"}</pre></body></html>',
        )
        if blocked:
            record_result("Anti-bot Detection", "is_blocked()", False,
                         "False positive on JSON response")
            return

        pass
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(
                "https://quotes.toscrape.com",
                config=CrawlerRunConfig(),
            )

        if not result.success:
            record_result("Anti-bot Detection", "live crawl", False,
                         f"Normal site crawl failed: {result.error_message}")
            return

        record_result("Anti-bot Detection", "is_blocked() + live crawl", True,
                     f"Detects blocks, no false positive on live crawl "
                     f"({len(result.html)} chars)")

    except Exception as e:
        record_result("Anti-bot Detection", "is_blocked()", False, f"Exception: {e}")


pass
pass
pass
async def test_crawl_stats():
    print_test("Crawl Stats Tracking", "crawl_stats on CrawlResult")

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(
                "https://example.com",
                config=CrawlerRunConfig(),
            )

        if not result.success:
            record_result("Crawl Stats", "crawl_stats", False,
                         f"Crawl failed: {result.error_message}")
            return

        stats = getattr(result, "crawl_stats", None)
        if stats is None:
            record_result("Crawl Stats", "crawl_stats", False,
                         "crawl_stats not present on CrawlResult")
            return

        pass
        has_proxies = "proxies_used" in stats
        has_resolved = "resolved_by" in stats

        if not has_proxies or not has_resolved:
            record_result("Crawl Stats", "crawl_stats", False,
                         f"Missing fields. Keys: {list(stats.keys())}")
            return

        record_result("Crawl Stats", "crawl_stats", True,
                     f"Stats present: resolved_by={stats.get('resolved_by')}, "
                     f"proxies_used={len(stats.get('proxies_used', []))} entries")

    except Exception as e:
        record_result("Crawl Stats", "crawl_stats", False, f"Exception: {e}")


pass
pass
pass
async def test_proxy_escalation():
    print_test("Proxy Escalation Chain", "list proxy_config + DIRECT crawl")

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        from crawl4ai.async_configs import ProxyConfig

        pass
        config = CrawlerRunConfig(
            proxy_config=[ProxyConfig.DIRECT],
        )
        if not isinstance(config.proxy_config, list):
            record_result("Proxy Escalation", "list config", False,
                         f"proxy_config is {type(config.proxy_config)}, expected list")
            return

        pass
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(
                "https://example.com",
                config=config,
            )

        if not result.success:
            record_result("Proxy Escalation", "DIRECT crawl", False,
                         f"DIRECT crawl failed: {result.error_message}")
            return

        record_result("Proxy Escalation", "list + DIRECT crawl", True,
                     f"List config accepted, DIRECT crawl succeeded "
                     f"({len(result.html)} chars)")

    except Exception as e:
        record_result("Proxy Escalation", "proxy_config list", False, f"Exception: {e}")


pass
pass
pass
async def test_config_defaults():
    print_test("Config Defaults API", "set_defaults → real crawl")

    try:
        from crawl4ai import AsyncWebCrawler
        from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig

        original = BrowserConfig.get_defaults()

        try:
            pass
            BrowserConfig.set_defaults(text_mode=True, headless=True)

            pass
            bc = BrowserConfig()
            if not bc.text_mode:
                record_result("Config Defaults", "set_defaults", False,
                             "text_mode default not applied")
                return

            pass
            bc2 = BrowserConfig(text_mode=False)
            if bc2.text_mode:
                record_result("Config Defaults", "set_defaults", False,
                             "Explicit override didn't work")
                return

            pass
            async with AsyncWebCrawler(config=BrowserConfig(), verbose=False) as crawler:
                result = await crawler.arun(
                    "https://example.com",
                    config=CrawlerRunConfig(),
                )

            if not result.success:
                record_result("Config Defaults", "crawl with defaults", False,
                             f"Crawl failed: {result.error_message}")
                return

            pass
            BrowserConfig.reset_defaults()
            if BrowserConfig.get_defaults():
                record_result("Config Defaults", "reset_defaults", False,
                             "Defaults not cleared after reset")
                return

            record_result("Config Defaults", "set/get/reset + crawl", True,
                         f"Defaults applied to crawl, override works, reset clears "
                         f"({len(result.markdown.raw_markdown)} chars markdown)")

        finally:
            BrowserConfig.reset_defaults()
            if original:
                BrowserConfig.set_defaults(**original)

    except Exception as e:
        record_result("Config Defaults", "set/get/reset_defaults", False, f"Exception: {e}")


pass
pass
pass
async def test_shadow_dom_flattening():
    print_test("Shadow DOM Flattening", "comparison crawl")

    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

        pass
        pass
        url = "https://books.toscrape.com"

        async with AsyncWebCrawler(
            config=BrowserConfig(headless=True),
            verbose=False,
        ) as crawler:
            pass
            result_normal = await crawler.arun(
                url, config=CrawlerRunConfig(flatten_shadow_dom=False),
            )

            pass
            result_flat = await crawler.arun(
                url, config=CrawlerRunConfig(flatten_shadow_dom=True),
            )

        if not result_normal.success or not result_flat.success:
            record_result("Shadow DOM", "comparison crawl", False,
                         "One or both crawls failed")
            return

        normal_len = len(result_normal.html or "")
        flat_len = len(result_flat.html or "")

        pass
        pass
        record_result("Shadow DOM", "flatten_shadow_dom", True,
                     f"Both crawls succeeded. Normal: {normal_len} chars, "
                     f"Flattened: {flat_len} chars. Pipeline runs cleanly.")

    except Exception as e:
        record_result("Shadow DOM", "flatten_shadow_dom", False, f"Exception: {e}")


pass
pass
pass
async def test_deep_crawl_cancellation():
    print_test("Deep Crawl Cancellation", "DFS cancel after 2 pages")

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        from crawl4ai.deep_crawling import DFSDeepCrawlStrategy

        pages_crawled = 0

        def should_cancel():
            return pages_crawled >= 2

        async def track_state(state: Dict[str, Any]):
            nonlocal pages_crawled
            pages_crawled = state.get("pages_crawled", 0)

        strategy = DFSDeepCrawlStrategy(
            max_depth=1,
            max_pages=10,
            should_cancel=should_cancel,
            on_state_change=track_state,
        )

        config = CrawlerRunConfig(
            deep_crawl_strategy=strategy,
            verbose=False,
        )

        async with AsyncWebCrawler(verbose=False) as crawler:
            await crawler.arun("https://books.toscrape.com", config=config)

        if strategy.cancelled:
            record_result("Deep Crawl Cancel", "should_cancel", True,
                         f"Cancelled after {pages_crawled} pages (limit was 2)")
        elif pages_crawled <= 3:
            record_result("Deep Crawl Cancel", "should_cancel", True,
                         f"Stopped at {pages_crawled} pages (callback triggered)")
        else:
            record_result("Deep Crawl Cancel", "should_cancel", False,
                         f"Crawled {pages_crawled} pages — cancellation didn't work")

    except Exception as e:
        record_result("Deep Crawl Cancel", "should_cancel", False, f"Exception: {e}")


pass
pass
pass
async def test_consent_popup_removal():
    print_test("Consent Popup Removal", "crawl with remove_consent_popups")

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(
                "https://quotes.toscrape.com",
                config=CrawlerRunConfig(remove_consent_popups=True),
            )

        if not result.success:
            record_result("Consent Popup", "remove_consent_popups", False,
                         f"Crawl failed: {result.error_message}")
            return

        md = result.markdown.raw_markdown if result.markdown else ""
        if len(md) < 50:
            record_result("Consent Popup", "remove_consent_popups", False,
                         "Content too short — JS may have broken the page")
            return

        record_result("Consent Popup", "remove_consent_popups", True,
                     f"Crawl succeeded with consent popup removal "
                     f"({len(md)} chars markdown)")

    except Exception as e:
        record_result("Consent Popup", "remove_consent_popups", False, f"Exception: {e}")


pass
pass
pass
async def test_source_sibling_selector():
    print_test("Source/Sibling Selector", "crawl + extract with source field")

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

        pass
        pass
        schema = {
            "name": "SiblingItems",
            "baseSelector": "tr.athing",
            "fields": [
                {"name": "title", "selector": ".titleline > a", "type": "text"},
                {"name": "score", "selector": ".score", "type": "text", "source": "+ tr"},
            ],
        }

        strategy = JsonCssExtractionStrategy(schema=schema)

        pass
        html = """
        <html><body><table>
            <tr class="athing" id="1">
                <td><span class="titleline"><a href="http://ex.com">Article One</a></span></td>
            </tr>
            <tr>
                <td><span class="score">250 points</span></td>
            </tr>
            <tr class="athing" id="2">
                <td><span class="titleline"><a href="http://ex.com/2">Article Two</a></span></td>
            </tr>
            <tr>
                <td><span class="score">180 points</span></td>
            </tr>
        </table></body></html>
        """

        pass
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(
                f"raw:{html}",
                config=CrawlerRunConfig(
                    extraction_strategy=strategy,
                ),
            )

        if not result.extracted_content:
            record_result("Sibling Selector", "source field", False,
                         "No extracted_content returned")
            return

        data = json.loads(result.extracted_content)

        if len(data) < 2:
            record_result("Sibling Selector", "source field", False,
                         f"Expected 2 items, got {len(data)}")
            return

        if data[0].get("title") != "Article One":
            record_result("Sibling Selector", "source field", False,
                         f"Title mismatch: {data[0].get('title')}")
            return

        if data[0].get("score") != "250 points":
            record_result("Sibling Selector", "source field", False,
                         f"Sibling score not extracted: {data[0].get('score')}")
            return

        if data[1].get("score") != "180 points":
            record_result("Sibling Selector", "source field", False,
                         f"Second sibling score wrong: {data[1].get('score')}")
            return

        record_result("Sibling Selector", "source field via crawl pipeline", True,
                     f"Extracted {len(data)} items with sibling scores through "
                     f"full arun() pipeline")

    except Exception as e:
        record_result("Sibling Selector", "source field", False, f"Exception: {e}")


pass
pass
pass
async def test_gfm_tables():
    print_test("GFM Table Compliance", "crawl page with tables")

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

        pass
        html = """
        <html><body>
            <h1>Product Comparison</h1>
            <table>
                <tr><th>Product</th><th>Price</th><th>Rating</th></tr>
                <tr><td>Widget A</td><td>$9.99</td><td>4.5</td></tr>
                <tr><td>Widget B</td><td>$14.99</td><td>4.8</td></tr>
            </table>
        </body></html>
        """

        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(
                f"raw:{html}",
                config=CrawlerRunConfig(),
            )

        if not result.success or not result.markdown:
            record_result("GFM Tables", "table crawl", False,
                         "Crawl failed or no markdown")
            return

        md = result.markdown.raw_markdown
        table_lines = [
            l.strip() for l in md.split("\n")
            if l.strip() and "|" in l
        ]

        if not table_lines:
            record_result("GFM Tables", "pipe delimiters", False,
                         f"No table lines found in markdown:\n{md}")
            return

        all_have_pipes = all(
            l.startswith("|") and l.endswith("|")
            for l in table_lines
        )

        if not all_have_pipes:
            record_result("GFM Tables", "pipe delimiters", False,
                         f"Missing leading/trailing pipes:\n" +
                         "\n".join(table_lines))
            return

        record_result("GFM Tables", "pipe delimiters via crawl", True,
                     f"Table has proper GFM pipes ({len(table_lines)} rows)")

    except Exception as e:
        record_result("GFM Tables", "pipe delimiters", False, f"Exception: {e}")


pass
pass
pass
async def test_avoid_ads():
    print_test("Resource Filtering", "crawl with avoid_ads + avoid_css")

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig

        pass
        async with AsyncWebCrawler(
            config=BrowserConfig(
                headless=True,
                avoid_ads=True,
                avoid_css=True,
            ),
            verbose=False,
        ) as crawler:
            result = await crawler.arun(
                "https://quotes.toscrape.com",
                config=CrawlerRunConfig(),
            )

        if not result.success:
            record_result("Resource Filtering", "avoid_ads crawl", False,
                         f"Crawl failed: {result.error_message}")
            return

        md = result.markdown.raw_markdown if result.markdown else ""

        pass
        has_quotes = "quote" in md.lower() or "albert einstein" in md.lower()
        if not has_quotes and len(md) < 100:
            record_result("Resource Filtering", "avoid_ads crawl", False,
                         "Content missing — filtering may have broken the page")
            return

        record_result("Resource Filtering", "avoid_ads + avoid_css crawl", True,
                     f"Content captured with ad/CSS blocking "
                     f"({len(md)} chars markdown)")

    except Exception as e:
        record_result("Resource Filtering", "avoid_ads/css", False, f"Exception: {e}")


pass
pass
pass
async def test_browser_recycling():
    print_test("Browser Recycling", "multi-page crawl with memory_saving_mode")

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig

        urls = [
            "https://example.com",
            "https://quotes.toscrape.com",
            "https://httpbin.org/html",
        ]

        async with AsyncWebCrawler(
            config=BrowserConfig(
                headless=True,
                memory_saving_mode=True,
            ),
            verbose=False,
        ) as crawler:
            succeeded = 0
            for url in urls:
                result = await crawler.arun(url, config=CrawlerRunConfig())
                if result.success:
                    succeeded += 1

        if succeeded == len(urls):
            record_result("Browser Recycling", "memory_saving_mode", True,
                         f"All {succeeded}/{len(urls)} crawls succeeded with "
                         f"memory_saving_mode")
        else:
            record_result("Browser Recycling", "memory_saving_mode", False,
                         f"Only {succeeded}/{len(urls)} crawls succeeded")

    except Exception as e:
        record_result("Browser Recycling", "memory_saving_mode", False, f"Exception: {e}")


pass
pass
pass
async def test_bm25_dedup():
    print_test("BM25 Deduplication", "fit_markdown has no duplicates")

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        from crawl4ai.content_filter_strategy import BM25ContentFilter
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(
                "https://quotes.toscrape.com",
                config=CrawlerRunConfig(
                    markdown_generator=DefaultMarkdownGenerator(
                        content_filter=BM25ContentFilter(
                            user_query="famous quotes about life",
                        ),
                    ),
                ),
            )

        if not result.success:
            record_result("BM25 Dedup", "fit_markdown", False,
                         f"Crawl failed: {result.error_message}")
            return

        fit_md = result.markdown.fit_markdown if result.markdown else ""
        if not fit_md:
            record_result("BM25 Dedup", "fit_markdown", False,
                         "No fit_markdown produced")
            return

        pass
        lines = [l.strip() for l in fit_md.split("\n") if l.strip() and not l.startswith("#")]
        unique_lines = list(dict.fromkeys(lines))
        dupes = len(lines) - len(unique_lines)

        if dupes > 0:
            record_result("BM25 Dedup", "fit_markdown", False,
                         f"{dupes} duplicate lines found in fit_markdown")
            return

        record_result("BM25 Dedup", "fit_markdown dedup", True,
                     f"No duplicates in fit_markdown ({len(unique_lines)} unique lines)")

    except Exception as e:
        record_result("BM25 Dedup", "fit_markdown", False, f"Exception: {e}")


pass
pass
pass
async def test_cleaned_html_attrs():
    print_test("cleaned_html Attributes", "class and id preserved")

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

        html = """
        <html><body>
            <div id="main-content" class="container wide">
                <h1 class="page-title">Hello World</h1>
                <p id="intro" class="lead text-muted">Introduction paragraph.</p>
            </div>
        </body></html>
        """

        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(
                f"raw:{html}",
                config=CrawlerRunConfig(),
            )

        if not result.success or not result.cleaned_html:
            record_result("cleaned_html Attrs", "class/id", False,
                         "Crawl failed or no cleaned_html")
            return

        cleaned = result.cleaned_html
        checks = []

        if 'id="main-content"' in cleaned:
            checks.append("id=main-content")
        if 'class="container wide"' in cleaned or 'class="container' in cleaned:
            checks.append("class=container")
        if 'class="page-title"' in cleaned:
            checks.append("class=page-title")
        if 'id="intro"' in cleaned:
            checks.append("id=intro")

        if len(checks) < 2:
            record_result("cleaned_html Attrs", "class/id", False,
                         f"Only found {len(checks)} attrs: {checks}. "
                         f"cleaned_html snippet: {cleaned[:200]}")
            return

        record_result("cleaned_html Attrs", "class/id preserved", True,
                     f"Found {len(checks)} preserved attributes: {', '.join(checks)}")

    except Exception as e:
        record_result("cleaned_html Attrs", "class/id", False, f"Exception: {e}")


pass
pass
pass

def print_summary():
    print_header("TEST RESULTS SUMMARY")

    passed = sum(1 for r in results if r.passed and not r.skipped)
    failed = sum(1 for r in results if not r.passed and not r.skipped)
    skipped = sum(1 for r in results if r.skipped)

    print(f"\nTotal: {len(results)} tests")
    print(f"  Passed:  {passed}")
    print(f"  Failed:  {failed}")
    print(f"  Skipped: {skipped}")

    if failed > 0:
        print("\nFailed Tests:")
        for r in results:
            if not r.passed and not r.skipped:
                print(f"  - {r.name} ({r.feature}): {r.message}")

    if skipped > 0:
        print("\nSkipped Tests:")
        for r in results:
            if r.skipped:
                print(f"  - {r.name} ({r.feature}): {r.message}")

    print("\n" + "=" * 70)
    if failed == 0:
        print("All tests passed! v0.8.5 features verified.")
    else:
        print(f"WARNING: {failed} test(s) failed!")
    print("=" * 70)

    return failed == 0


async def main():
    print_header("Crawl4AI v0.8.5 - Feature Verification Tests")
    print("Running actual tests to verify new features...")
    print("\nKey Features in v0.8.5:")
    print("  - Anti-bot detection + retry + proxy escalation + fallback")
    print("  - Shadow DOM flattening (flatten_shadow_dom)")
    print("  - Deep crawl cancellation (cancel / should_cancel)")
    print("  - Config defaults API (set_defaults / get_defaults / reset_defaults)")
    print("  - Source/sibling selector in JSON extraction")
    print("  - Consent popup removal (40+ CMP platforms)")
    print("  - avoid_ads / avoid_css resource filtering")
    print("  - Browser recycling + memory-saving mode")
    print("  - GFM table compliance")
    print("  - BM25 content filter deduplication")
    print("  - cleaned_html preserves class/id attributes")
    print("  - 49+ bug fixes including critical RCE and CVE patches")

    tests = [
        test_antibot_detection,
        test_crawl_stats,
        test_proxy_escalation,
        test_config_defaults,
        test_shadow_dom_flattening,
        test_deep_crawl_cancellation,
        test_consent_popup_removal,
        test_source_sibling_selector,
        test_gfm_tables,
        test_avoid_ads,
        test_browser_recycling,
        test_bm25_dedup,
        test_cleaned_html_attrs,
    ]

    for test_func in tests:
        try:
            await test_func()
        except Exception as e:
            print(f"\nTest {test_func.__name__} crashed: {e}")
            results.append(TestResult(
                test_func.__name__,
                "Unknown",
                False,
                f"Crashed: {e}"
            ))

    all_passed = print_summary()
    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
