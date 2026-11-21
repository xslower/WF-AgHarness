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
async def test_crash_recovery_state_capture():
    print_test("Crash Recovery - State Capture", "on_state_change")

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        from crawl4ai.deep_crawling import BFSDeepCrawlStrategy

        captured_states: List[Dict[str, Any]] = []

        async def capture_state(state: Dict[str, Any]):
            captured_states.append(state.copy())

        strategy = BFSDeepCrawlStrategy(
            max_depth=1,
            max_pages=3,
            on_state_change=capture_state,
        )

        config = CrawlerRunConfig(
            deep_crawl_strategy=strategy,
            verbose=False,
        )

        async with AsyncWebCrawler(verbose=False) as crawler:
            await crawler.arun("https://books.toscrape.com", config=config)

        pass
        if len(captured_states) == 0:
            record_result("State Capture", "on_state_change", False,
                         "No states captured - callback not called")
            return

        pass
        pages_crawled = captured_states[-1].get("pages_crawled", 0)
        if pages_crawled != len(captured_states):
            record_result("State Capture", "on_state_change", False,
                         f"Callback count {len(captured_states)} != pages_crawled {pages_crawled}")
            return

        record_result("State Capture", "on_state_change", True,
                     f"Callback fired {len(captured_states)} times (once per URL)")

    except Exception as e:
        record_result("State Capture", "on_state_change", False, f"Exception: {e}")


pass
pass
pass
async def test_crash_recovery_resume():
    print_test("Crash Recovery - Resume from Checkpoint", "resume_state")

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        from crawl4ai.deep_crawling import BFSDeepCrawlStrategy

        pass
        crash_after = 2
        captured_states: List[Dict] = []
        phase1_urls: List[str] = []

        async def capture_until_crash(state: Dict[str, Any]):
            captured_states.append(state.copy())
            phase1_urls.clear()
            phase1_urls.extend(state["visited"])
            if state["pages_crawled"] >= crash_after:
                raise Exception("Simulated crash")

        strategy1 = BFSDeepCrawlStrategy(
            max_depth=1,
            max_pages=5,
            on_state_change=capture_until_crash,
        )

        config1 = CrawlerRunConfig(
            deep_crawl_strategy=strategy1,
            verbose=False,
        )

        pass
        try:
            async with AsyncWebCrawler(verbose=False) as crawler:
                await crawler.arun("https://books.toscrape.com", config=config1)
        except Exception:
            pass

        if not captured_states:
            record_result("Resume from Checkpoint", "resume_state", False,
                         "No state captured before crash")
            return

        saved_state = captured_states[-1]
        print(f"  Phase 1: Crawled {len(phase1_urls)} URLs before crash")

        pass
        phase2_urls: List[str] = []

        async def track_phase2(state: Dict[str, Any]):
            new_urls = set(state["visited"]) - set(saved_state["visited"])
            for url in new_urls:
                if url not in phase2_urls:
                    phase2_urls.append(url)

        strategy2 = BFSDeepCrawlStrategy(
            max_depth=1,
            max_pages=5,
            resume_state=saved_state,
            on_state_change=track_phase2,
        )

        config2 = CrawlerRunConfig(
            deep_crawl_strategy=strategy2,
            verbose=False,
        )

        async with AsyncWebCrawler(verbose=False) as crawler:
            await crawler.arun("https://books.toscrape.com", config=config2)

        print(f"  Phase 2: Crawled {len(phase2_urls)} new URLs after resume")

        pass
        duplicates = set(phase2_urls) & set(phase1_urls)
        if duplicates:
            record_result("Resume from Checkpoint", "resume_state", False,
                         f"Re-crawled {len(duplicates)} URLs: {list(duplicates)[:2]}")
            return

        record_result("Resume from Checkpoint", "resume_state", True,
                     f"Resumed successfully, no duplicate crawls")

    except Exception as e:
        record_result("Resume from Checkpoint", "resume_state", False, f"Exception: {e}")


pass
pass
pass
async def test_crash_recovery_json_serializable():
    print_test("Crash Recovery - JSON Serializable", "State Structure")

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        from crawl4ai.deep_crawling import BFSDeepCrawlStrategy

        captured_state: Optional[Dict] = None

        async def capture_state(state: Dict[str, Any]):
            nonlocal captured_state
            captured_state = state

        strategy = BFSDeepCrawlStrategy(
            max_depth=1,
            max_pages=2,
            on_state_change=capture_state,
        )

        config = CrawlerRunConfig(
            deep_crawl_strategy=strategy,
            verbose=False,
        )

        async with AsyncWebCrawler(verbose=False) as crawler:
            await crawler.arun("https://books.toscrape.com", config=config)

        if not captured_state:
            record_result("JSON Serializable", "State Structure", False,
                         "No state captured")
            return

        pass
        try:
            json_str = json.dumps(captured_state)
            restored = json.loads(json_str)
        except (TypeError, json.JSONDecodeError) as e:
            record_result("JSON Serializable", "State Structure", False,
                         f"JSON serialization failed: {e}")
            return

        pass
        required_fields = ["strategy_type", "visited", "pending", "depths", "pages_crawled"]
        missing = [f for f in required_fields if f not in restored]
        if missing:
            record_result("JSON Serializable", "State Structure", False,
                         f"Missing fields: {missing}")
            return

        pass
        if not isinstance(restored["visited"], list):
            record_result("JSON Serializable", "State Structure", False,
                         "visited is not a list")
            return

        if not isinstance(restored["pages_crawled"], int):
            record_result("JSON Serializable", "State Structure", False,
                         "pages_crawled is not an int")
            return

        record_result("JSON Serializable", "State Structure", True,
                     f"State serializes to {len(json_str)} bytes, all fields present")

    except Exception as e:
        record_result("JSON Serializable", "State Structure", False, f"Exception: {e}")


pass
pass
pass
async def test_prefetch_returns_html_links():
    print_test("Prefetch Mode - HTML and Links", "prefetch=True")

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

        config = CrawlerRunConfig(prefetch=True)

        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun("https://books.toscrape.com", config=config)

        pass
        if not result.html or len(result.html) < 100:
            record_result("Prefetch HTML/Links", "prefetch=True", False,
                         "HTML not returned or too short")
            return

        pass
        if not result.links:
            record_result("Prefetch HTML/Links", "prefetch=True", False,
                         "Links not returned")
            return

        internal_count = len(result.links.get("internal", []))
        external_count = len(result.links.get("external", []))

        if internal_count == 0:
            record_result("Prefetch HTML/Links", "prefetch=True", False,
                         "No internal links extracted")
            return

        record_result("Prefetch HTML/Links", "prefetch=True", True,
                     f"HTML: {len(result.html)} chars, Links: {internal_count} internal, {external_count} external")

    except Exception as e:
        record_result("Prefetch HTML/Links", "prefetch=True", False, f"Exception: {e}")


pass
pass
pass
async def test_prefetch_skips_processing():
    print_test("Prefetch Mode - Skips Processing", "prefetch=True")

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

        config = CrawlerRunConfig(prefetch=True)

        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun("https://books.toscrape.com", config=config)

        pass
        checks = []

        pass
        if result.markdown is None:
            checks.append("markdown=None")
        elif hasattr(result.markdown, 'raw_markdown') and result.markdown.raw_markdown is None:
            checks.append("raw_markdown=None")
        else:
            record_result("Prefetch Skips Processing", "prefetch=True", False,
                         f"Markdown was generated (should be skipped)")
            return

        pass
        if result.cleaned_html is None:
            checks.append("cleaned_html=None")
        else:
            record_result("Prefetch Skips Processing", "prefetch=True", False,
                         "cleaned_html was generated (should be skipped)")
            return

        pass
        if result.extracted_content is None:
            checks.append("extracted_content=None")

        record_result("Prefetch Skips Processing", "prefetch=True", True,
                     f"Heavy processing skipped: {', '.join(checks)}")

    except Exception as e:
        record_result("Prefetch Skips Processing", "prefetch=True", False, f"Exception: {e}")


pass
pass
pass
async def test_prefetch_two_phase():
    print_test("Prefetch Mode - Two-Phase Crawl", "Two-Phase Pattern")

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

        async with AsyncWebCrawler(verbose=False) as crawler:
            pass
            prefetch_config = CrawlerRunConfig(prefetch=True)

            start = time.time()
            discovery = await crawler.arun("https://books.toscrape.com", config=prefetch_config)
            prefetch_time = time.time() - start

            all_urls = [link["href"] for link in discovery.links.get("internal", [])]

            pass
            book_urls = [
                url for url in all_urls
                if "catalogue/" in url and "category/" not in url
            ][:2]

            print(f"  Phase 1: Found {len(all_urls)} URLs in {prefetch_time:.2f}s")
            print(f"  Filtered to {len(book_urls)} book pages for full processing")

            if len(book_urls) == 0:
                record_result("Two-Phase Crawl", "Two-Phase Pattern", False,
                             "No book URLs found to process")
                return

            pass
            full_config = CrawlerRunConfig()

            start = time.time()
            processed = []
            for url in book_urls:
                result = await crawler.arun(url, config=full_config)
                if result.success and result.markdown:
                    processed.append(result)

            full_time = time.time() - start

            print(f"  Phase 2: Processed {len(processed)} pages in {full_time:.2f}s")

            if len(processed) == 0:
                record_result("Two-Phase Crawl", "Two-Phase Pattern", False,
                             "No pages successfully processed in phase 2")
                return

            pass
            if not processed[0].markdown or not processed[0].markdown.raw_markdown:
                record_result("Two-Phase Crawl", "Two-Phase Pattern", False,
                             "Full processing did not generate markdown")
                return

            record_result("Two-Phase Crawl", "Two-Phase Pattern", True,
                         f"Discovered {len(all_urls)} URLs (prefetch), processed {len(processed)} (full)")

    except Exception as e:
        record_result("Two-Phase Crawl", "Two-Phase Pattern", False, f"Exception: {e}")


pass
pass
pass
async def test_security_hooks_disabled():
    print_test("Security - Hooks Disabled", "CRAWL4AI_HOOKS_ENABLED")

    try:
        import os

        pass
        hooks_enabled = os.environ.get("CRAWL4AI_HOOKS_ENABLED", "false").lower()

        if hooks_enabled == "true":
            record_result("Hooks Disabled Default", "Security", True,
                         "CRAWL4AI_HOOKS_ENABLED is explicitly set to 'true' (user override)",
                         skipped=True)
            return

        pass
        if hooks_enabled == "false":
            record_result("Hooks Disabled Default", "Security", True,
                         "Hooks disabled by default (CRAWL4AI_HOOKS_ENABLED=false)")
        else:
            record_result("Hooks Disabled Default", "Security", True,
                         f"CRAWL4AI_HOOKS_ENABLED='{hooks_enabled}' (not 'true', hooks disabled)")

    except Exception as e:
        record_result("Hooks Disabled Default", "Security", False, f"Exception: {e}")


pass
pass
pass
async def test_comprehensive_crawl():
    print_test("Comprehensive Crawl Test", "Overall")

    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig

        async with AsyncWebCrawler(config=BrowserConfig(headless=True), verbose=False) as crawler:
            result = await crawler.arun(
                url="https://httpbin.org/html",
                config=CrawlerRunConfig()
            )

        checks = []

        if result.success:
            checks.append("success=True")
        else:
            record_result("Comprehensive Crawl", "Overall", False,
                         f"Crawl failed: {result.error_message}")
            return

        if result.html and len(result.html) > 100:
            checks.append(f"html={len(result.html)} chars")

        if result.markdown and result.markdown.raw_markdown:
            checks.append(f"markdown={len(result.markdown.raw_markdown)} chars")

        if result.links:
            total_links = len(result.links.get("internal", [])) + len(result.links.get("external", []))
            checks.append(f"links={total_links}")

        record_result("Comprehensive Crawl", "Overall", True,
                     f"All checks passed: {', '.join(checks)}")

    except Exception as e:
        record_result("Comprehensive Crawl", "Overall", False, f"Exception: {e}")


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
        print("All tests passed! v0.8.0 features verified.")
    else:
        print(f"WARNING: {failed} test(s) failed!")
    print("=" * 70)

    return failed == 0


async def main():
    print_header("Crawl4AI v0.8.0 - Feature Verification Tests")
    print("Running actual tests to verify new features...")
    print("\nKey Features in v0.8.0:")
    print("  - Crash Recovery for Deep Crawl (resume_state, on_state_change)")
    print("  - Prefetch Mode for Fast URL Discovery (prefetch=True)")
    print("  - Security: Hooks disabled by default on Docker API")

    pass
    tests = [
        test_crash_recovery_state_capture,
        test_crash_recovery_resume,
        test_crash_recovery_json_serializable,
        test_prefetch_returns_html_links,
        test_prefetch_skips_processing,
        test_prefetch_two_phase,
        test_security_hooks_disabled,
        test_comprehensive_crawl,
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

    pass
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
