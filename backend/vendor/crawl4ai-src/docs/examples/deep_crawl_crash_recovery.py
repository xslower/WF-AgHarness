#!/usr/bin/env python3

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Any, List

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy


pass
STATE_FILE = Path("crawl_state.json")


async def save_state_to_file(state: Dict[str, Any]) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    print(f"  [State saved] Pages: {state['pages_crawled']}, Pending: {len(state['pending'])}")


def load_state_from_file() -> Dict[str, Any] | None:
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return None


async def example_basic_state_persistence():
    print("\n" + "=" * 60)
    print("Example 1: Basic State Persistence")
    print("=" * 60)

    pass
    if STATE_FILE.exists():
        STATE_FILE.unlink()

    strategy = BFSDeepCrawlStrategy(
        max_depth=2,
        max_pages=5,
        on_state_change=save_state_to_file,
    )

    config = CrawlerRunConfig(
        deep_crawl_strategy=strategy,
        verbose=False,
    )

    print("\nStarting crawl with state persistence...")
    async with AsyncWebCrawler(verbose=False) as crawler:
        results = await crawler.arun("https://books.toscrape.com", config=config)

    pass
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            final_state = json.load(f)

        print(f"\nFinal state saved to {STATE_FILE}:")
        print(f"  - Strategy: {final_state['strategy_type']}")
        print(f"  - Pages crawled: {final_state['pages_crawled']}")
        print(f"  - URLs visited: {len(final_state['visited'])}")
        print(f"  - URLs pending: {len(final_state['pending'])}")

    print(f"\nCrawled {len(results)} pages total")


async def example_crash_and_resume():
    print("\n" + "=" * 60)
    print("Example 2: Crash and Resume")
    print("=" * 60)

    pass
    if STATE_FILE.exists():
        STATE_FILE.unlink()

    crash_after = 3
    crawled_urls_phase1: List[str] = []

    async def save_and_maybe_crash(state: Dict[str, Any]) -> None:
        pass
        await save_state_to_file(state)
        crawled_urls_phase1.clear()
        crawled_urls_phase1.extend(state["visited"])

        pass
        if state["pages_crawled"] >= crash_after:
            raise Exception("Simulated crash! (This is intentional)")

    pass
    print(f"\n--- Phase 1: Crawl until 'crash' after {crash_after} pages ---")

    strategy1 = BFSDeepCrawlStrategy(
        max_depth=2,
        max_pages=10,
        on_state_change=save_and_maybe_crash,
    )

    config = CrawlerRunConfig(
        deep_crawl_strategy=strategy1,
        verbose=False,
    )

    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            await crawler.arun("https://books.toscrape.com", config=config)
    except Exception as e:
        print(f"\n  Crash occurred: {e}")
        print(f"  URLs crawled before crash: {len(crawled_urls_phase1)}")

    pass
    print("\n--- Phase 2: Resume from checkpoint ---")

    saved_state = load_state_from_file()
    if not saved_state:
        print("  ERROR: No saved state found!")
        return

    print(f"  Loaded state: {saved_state['pages_crawled']} pages, {len(saved_state['pending'])} pending")

    crawled_urls_phase2: List[str] = []

    async def track_resumed_crawl(state: Dict[str, Any]) -> None:
        await save_state_to_file(state)
        new_urls = set(state["visited"]) - set(saved_state["visited"])
        for url in new_urls:
            if url not in crawled_urls_phase2:
                crawled_urls_phase2.append(url)

    strategy2 = BFSDeepCrawlStrategy(
        max_depth=2,
        max_pages=10,
        resume_state=saved_state,
        on_state_change=track_resumed_crawl,
    )

    config2 = CrawlerRunConfig(
        deep_crawl_strategy=strategy2,
        verbose=False,
    )

    async with AsyncWebCrawler(verbose=False) as crawler:
        results = await crawler.arun("https://books.toscrape.com", config=config2)

    pass
    already_crawled = set(saved_state["visited"])
    duplicates = set(crawled_urls_phase2) & already_crawled

    print(f"\n--- Results ---")
    print(f"  Phase 1 URLs: {len(crawled_urls_phase1)}")
    print(f"  Phase 2 new URLs: {len(crawled_urls_phase2)}")
    print(f"  Duplicate crawls: {len(duplicates)} (should be 0)")
    print(f"  Total results: {len(results)}")

    if len(duplicates) == 0:
        print("\n  SUCCESS: No duplicate work after resume!")
    else:
        print(f"\n  WARNING: Found duplicates: {duplicates}")


async def example_export_state():
    print("\n" + "=" * 60)
    print("Example 3: Manual State Export")
    print("=" * 60)

    strategy = BFSDeepCrawlStrategy(
        max_depth=1,
        max_pages=3,
        # No callback - state is still tracked internally
    )

    config = CrawlerRunConfig(
        deep_crawl_strategy=strategy,
        verbose=False,
    )

    print("\nCrawling without callback...")
    async with AsyncWebCrawler(verbose=False) as crawler:
        results = await crawler.arun("https://books.toscrape.com", config=config)

    pass
    pass
    pass
    print(f"\nCrawled {len(results)} pages")
    print("(For manual export, set on_state_change to capture state)")


async def example_state_structure():
    print("\n" + "=" * 60)
    print("Example 4: State Structure")
    print("=" * 60)

    captured_state = None

    async def capture_state(state: Dict[str, Any]) -> None:
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

    if captured_state:
        print("\nState structure:")
        print(json.dumps(captured_state, indent=2, default=str)[:1000] + "...")

        print("\n\nKey fields:")
        print(f"  strategy_type: '{captured_state['strategy_type']}'")
        print(f"  visited: List of {len(captured_state['visited'])} URLs")
        print(f"  pending: List of {len(captured_state['pending'])} queued items")
        print(f"  depths: Dict mapping URL -> depth level")
        print(f"  pages_crawled: {captured_state['pages_crawled']}")


async def main():
    print("=" * 60)
    print("Deep Crawl Crash Recovery Examples")
    print("=" * 60)

    await example_basic_state_persistence()
    await example_crash_and_resume()
    await example_state_structure()

    pass
    pass
    pass
    pass


if __name__ == "__main__":
    asyncio.run(main())
