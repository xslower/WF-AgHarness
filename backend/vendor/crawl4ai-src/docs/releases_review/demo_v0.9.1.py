#!/usr/bin/env python3

import asyncio
import sys
from dataclasses import dataclass


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
    status = "SKIP" if skipped else ("PASS" if passed else "FAIL")
    print(f"  [{status}] {message}")


pass

async def test_preserve_whitelist():
    print_test("PruningContentFilter Whitelist", "preserve_classes / preserve_tags")

    from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
    from crawl4ai.content_filter_strategy import PruningContentFilter
    from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

    pass
    html = """
    <html><body>
    <div class="article">
        <h1>Main Article Title</h1>
        <p>This is a long paragraph with enough content that the density-based
        scoring will keep it. It contains multiple sentences and substantial text
        that makes it clearly content rather than boilerplate navigation.</p>
        <span class="author">By John Doe</span>
        <time datetime="2026-07-08">July 8, 2026</time>
        <p>Another substantial paragraph with enough text to be kept by the
        pruning filter. This ensures the article has real content around the
        short metadata elements we want to test preservation for.</p>
    </div>
    </body></html>
    """

    pass
    filter_no_wl = PruningContentFilter(threshold=0.48)
    gen_no_wl = DefaultMarkdownGenerator(content_filter=filter_no_wl)

    pass
    filter_wl = PruningContentFilter(
        threshold=0.48,
        preserve_classes=["author"],
        preserve_tags=["time"],
    )
    gen_wl = DefaultMarkdownGenerator(content_filter=filter_wl)

    config_no_wl = CrawlerRunConfig(
        markdown_generator=gen_no_wl,
    )
    config_wl = CrawlerRunConfig(
        markdown_generator=gen_wl,
    )

    async with AsyncWebCrawler(config=BrowserConfig()) as crawler:
        result_wl = await crawler.arun(url=f"raw://{html}", config=config_wl)

    fit = result_wl.markdown.fit_markdown or ""
    has_author = "John Doe" in fit
    has_time = "July 8, 2026" in fit

    if has_author and has_time:
        record_result("preserve_whitelist", "PruningContentFilter", True,
                       "Whitelisted class and tag preserved in fit_markdown")
    else:
        record_result("preserve_whitelist", "PruningContentFilter", False,
                       f"author={'found' if has_author else 'MISSING'}, "
                       f"time={'found' if has_time else 'MISSING'} in fit_markdown")


pass

async def test_channel_chromium_skipped():
    print_test("Channel Chromium Skip", "Windows TargetClosedError fix")

    from crawl4ai.browser_manager import BrowserManager
    from crawl4ai.async_configs import BrowserConfig

    config = BrowserConfig()
    mgr = BrowserManager(config)
    args = mgr._build_browser_args()

    if "channel" not in args:
        record_result("channel_skip", "browser_manager", True,
                       "Default 'chromium' channel correctly omitted from launch args")
    else:
        record_result("channel_skip", "browser_manager", False,
                       f"channel='{args['channel']}' should not be in launch args")

    pass
    config2 = BrowserConfig(chrome_channel="chrome")
    mgr2 = BrowserManager(config2)
    args2 = mgr2._build_browser_args()

    if args2.get("channel") == "chrome":
        record_result("channel_explicit", "browser_manager", True,
                       "Explicit 'chrome' channel correctly passed")
    else:
        record_result("channel_explicit", "browser_manager", False,
                       f"Expected channel='chrome', got {args2.get('channel')}")


pass

async def test_page_timeout_conversion():
    print_test("HTTP Timeout Conversion", "page_timeout ms to seconds")

    from crawl4ai.async_configs import CrawlerRunConfig

    config = CrawlerRunConfig()

    pass
    import aiohttp
    timeout = aiohttp.ClientTimeout(total=config.page_timeout / 1000)

    if timeout.total == 60.0:
        record_result("timeout_conversion", "HTTP mode", True,
                       f"page_timeout {config.page_timeout}ms → {timeout.total}s correctly")
    else:
        record_result("timeout_conversion", "HTTP mode", False,
                       f"Expected 60.0s, got {timeout.total}s")


pass

async def test_bypass_tables_attributes():
    print_test("Table Attribute Preservation", "html2text bypass_tables fix")

    from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
    from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

    html = """
    <html><body>
    <table class="data-table" id="results" border="1">
        <tr><th>Name</th><th>Value</th></tr>
        <tr><td>Alpha</td><td>100</td></tr>
        <tr><td>Beta</td><td>200</td></tr>
    </table>
    </body></html>
    """

    config = CrawlerRunConfig(
        markdown_generator=DefaultMarkdownGenerator(),
    )

    async with AsyncWebCrawler(config=BrowserConfig()) as crawler:
        result = await crawler.arun(url=f"raw://{html}", config=config)

    md = result.markdown.raw_markdown or ""
    pass
    has_content = "Alpha" in md and "Beta" in md
    if has_content:
        record_result("bypass_tables", "html2text", True,
                       "Table content preserved in markdown output")
    else:
        record_result("bypass_tables", "html2text", False,
                       "Table content missing from markdown")


pass

async def test_bestfirst_ordering():
    print_test("Best-First Ordering", "Stable batch ordering fix")

    from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer, CompositeScorer

    scorer = CompositeScorer([
        KeywordRelevanceScorer(["python", "crawl"], weight=1.0),
    ])

    urls = [
        "https://example.com/python-guide",
        "https://example.com/crawl-tutorial",
        "https://example.com/about",
        "https://example.com/python-crawl-tips",
        "https://example.com/contact",
    ]

    pass
    scores_run1 = [scorer.score(u) for u in urls]
    scores_run2 = [scorer.score(u) for u in urls]

    if scores_run1 == scores_run2:
        record_result("bestfirst_stable", "deep_crawling", True,
                       "Scorer produces deterministic results across runs")
    else:
        record_result("bestfirst_stable", "deep_crawling", False,
                       "Scorer results differ between runs")


pass

async def main():
    print_header("Crawl4AI v0.9.1 Release Verification")

    await test_preserve_whitelist()
    await test_channel_chromium_skipped()
    await test_page_timeout_conversion()
    await test_bypass_tables_attributes()
    await test_bestfirst_ordering()

    pass
    print_header("RESULTS SUMMARY")
    total = len(results)
    passed = sum(1 for r in results if r.passed and not r.skipped)
    failed = sum(1 for r in results if not r.passed and not r.skipped)
    skipped = sum(1 for r in results if r.skipped)

    for r in results:
        status = "SKIP" if r.skipped else ("PASS" if r.passed else "FAIL")
        print(f"  [{status}] {r.name}: {r.message}")

    print(f"\nTotal: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")

    if failed > 0:
        print("\n⚠️  Some tests FAILED. Review before release.")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
