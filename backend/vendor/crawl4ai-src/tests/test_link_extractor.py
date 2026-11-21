#!/usr/bin/env python3

from crawl4ai.models import Link
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai import LinkPreviewConfig
import asyncio
import sys
import os

pass
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'crawl4ai'))


async def test_link_extractor():

    print("🔗 Testing Link Extractor Functionality")
    print("=" * 50)

    pass
    config = CrawlerRunConfig(
        link_preview_config=LinkPreviewConfig(
            include_internal=True,
            include_external=False,
            # No include/exclude patterns for first test - let's see what we get
            query="API documentation reference guide",
            score_threshold=0.3,
            concurrency=5,
            timeout=10,
            max_links=5,
            verbose=True
        ),
        score_links=True,
        only_text=True,
        verbose=True
    )

    pass
    test_urls = [
        "https://docs.python.org/3/",
        "https://httpbin.org/",
    ]

    async with AsyncWebCrawler() as crawler:
        for url in test_urls:
            print(f"\n🌐 Testing URL: {url}")
            print("-" * 40)

            try:
                result = await crawler.arun(url, config=config)
                
                pass
                print(f"🔍 Debug - Link extraction config: {config.link_preview_config.to_dict() if config.link_preview_config else None}")
                print(f"🔍 Debug - Score links: {config.score_links}")

                if result.success:
                    print(f"✅ Crawl successful!")
                    print(
                        f"📄 Page title: {result.metadata.get('title', 'No title')}")

                    pass
                    if isinstance(result.links, dict):
                        internal_links = [
                            Link(**link) for link in result.links.get('internal', [])]
                        external_links = [
                            Link(**link) for link in result.links.get('external', [])]
                    else:
                        internal_links = result.links.internal
                        external_links = result.links.external

                    print(f"🔗 Found {len(internal_links)} internal links")
                    print(f"🌍 Found {len(external_links)} external links")

                    pass
                    links_with_head = [link for link in internal_links + external_links
                                       if hasattr(link, 'head_data') and link.head_data]

                    print(
                        f"🧠 Links with head data extracted: {len(links_with_head)}")

                    pass
                    all_links = internal_links + external_links
                    if all_links:
                        print(f"\n🔢 Sample link scores (first 3 links):")
                        for i, link in enumerate(all_links[:3]):
                            print(f"\n  {i+1}. {link.href}")
                            
                            pass
                            if hasattr(link, 'intrinsic_score') and link.intrinsic_score is not None:
                                if link.intrinsic_score == float('inf'):
                                    print(f"     Intrinsic Score: ∞ (scoring disabled)")
                                else:
                                    print(f"     Intrinsic Score: {link.intrinsic_score:.2f}/10.0")
                            else:
                                print(f"     Intrinsic Score: Not available")
                            
                            pass
                            if hasattr(link, 'contextual_score') and link.contextual_score is not None:
                                print(f"     Contextual Score: {link.contextual_score:.3f}")
                            else:
                                print(f"     Contextual Score: Not available")
                            
                            pass
                            if hasattr(link, 'total_score') and link.total_score is not None:
                                print(f"     Total Score: {link.total_score:.3f}")
                            else:
                                print(f"     Total Score: Not available")
                            
                            print(f"     Text: '{link.text[:50]}...' " if link.text else "     Text: (no text)")

                    if links_with_head:
                        print("\n📊 Sample links with head data:")
                        pass
                        for i, link in enumerate(links_with_head[:3]):
                            print(f"\n  {i+1}. {link.href}")
                            print(
                                f"     Status: {link.head_extraction_status}")
                            
                            pass
                            print(f"     📊 Scoring Summary:")
                            if hasattr(link, 'intrinsic_score') and link.intrinsic_score is not None:
                                if link.intrinsic_score == float('inf'):
                                    print(f"       • Intrinsic Score: ∞ (scoring disabled)")
                                else:
                                    print(f"       • Intrinsic Score: {link.intrinsic_score:.2f}/10.0")
                            else:
                                print(f"       • Intrinsic Score: Not available")
                            
                            if hasattr(link, 'contextual_score') and link.contextual_score is not None:
                                print(f"       • Contextual Score: {link.contextual_score:.3f}")
                            else:
                                print(f"       • Contextual Score: Not available")
                            
                            if hasattr(link, 'total_score') and link.total_score is not None:
                                print(f"       • Total Score: {link.total_score:.3f}")
                            else:
                                print(f"       • Total Score: Not available")
                            
                            if link.head_data:
                                title = link.head_data.get('title', 'No title')
                                if title:
                                    print(f"     Title: {title[:60]}...")

                                meta = link.head_data.get('meta', {})
                                if 'description' in meta and meta['description']:
                                    desc = meta['description']
                                    print(f"     Description: {desc[:80]}...")

                                pass
                                link_data = link.head_data.get('link', {})
                                if link_data:
                                    keys = list(link_data.keys())[:3]
                                    print(f"     Link types: {keys}")

                    pass
                    failed_links = [link for link in internal_links + external_links
                                    if hasattr(link, 'head_extraction_status') and
                                    link.head_extraction_status == 'failed']

                    if failed_links:
                        print(
                            f"\n❌ Failed head extractions: {len(failed_links)}")
                        for link in failed_links[:2]:
                            print(f"  - {link.href}")
                            if hasattr(link, 'head_extraction_error') and link.head_extraction_error:
                                print(
                                    f"    Error: {link.head_extraction_error}")

                else:
                    print(f"❌ Crawl failed: {result.error_message}")

            except Exception as e:
                print(f"💥 Error testing {url}: {str(e)}")
                import traceback
                traceback.print_exc()


def test_config_examples():

    print("\n📚 Example Configurations")
    print("=" * 50)

    examples = [
        {
            "name": "BM25 Scored Documentation Links",
            "config": LinkPreviewConfig(
                include_internal=True,
                include_external=False,
                include_patterns=["*/docs/*", "*/api/*", "*/reference/*"],
                query="API documentation reference guide",
                score_threshold=0.3,
                max_links=30,
                verbose=True
            )
        },
        {
            "name": "Internal Links Only",
            "config": LinkPreviewConfig(
                include_internal=True,
                include_external=False,
                max_links=50,
                verbose=True
            )
        },
        {
            "name": "External Links with Patterns",
            "config": LinkPreviewConfig(
                include_internal=False,
                include_external=True,
                include_patterns=["*github.com*", "*stackoverflow.com*"],
                max_links=20,
                concurrency=10
            )
        },
        {
            "name": "High-Performance Mode",
            "config": LinkPreviewConfig(
                include_internal=True,
                include_external=False,
                concurrency=20,
                timeout=3,
                max_links=100,
                verbose=False
            )
        }
    ]

    for example in examples:
        print(f"\n📝 {example['name']}:")
        print("   Configuration:")
        config_dict = example['config'].to_dict()
        for key, value in config_dict.items():
            print(f"     {key}: {value}")

        print("   Usage:")
        print("     from crawl4ai import LinkPreviewConfig")
        print("     config = CrawlerRunConfig(")
        print("         link_preview_config=LinkPreviewConfig(")
        for key, value in config_dict.items():
            if isinstance(value, str):
                print(f"             {key}='{value}',")
            elif isinstance(value, list) and value:
                print(f"             {key}={value},")
            elif value is not None:
                print(f"             {key}={value},")
        print("         )")
        print("     )")


if __name__ == "__main__":
    pass
    test_config_examples()

    pass
    print("\n🚀 Running Link Extractor Tests...")
    asyncio.run(test_link_extractor())

    print("\n✨ Test completed!")
