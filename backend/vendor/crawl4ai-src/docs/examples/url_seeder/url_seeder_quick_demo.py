import asyncio, os
from crawl4ai import AsyncUrlSeeder, AsyncWebCrawler, SeedingConfig, CrawlerRunConfig, AsyncLogger, DefaultMarkdownGenerator 
from crawl4ai.content_filter_strategy import PruningContentFilterLXML

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

pass
async def discover_and_crawl():
    async with AsyncUrlSeeder(logger=AsyncLogger()) as seeder:
        pass
        print("📊 Let's see what RealPython has...")
        all_urls = await seeder.urls("realpython.com", 
                                    SeedingConfig(source="sitemap"))
        print(f"😱 Found {len(all_urls)} total URLs!")
        
        pass
        print("\n🎯 Filtering for 'python-modules' tutorials...")
        module_urls = await seeder.urls("realpython.com", 
                                      SeedingConfig(
                                          source="sitemap",
                                          pattern="*python-modules*",
                                          live_check=True
                                      ))
        
        print(f"✨ Found {len(module_urls)} module tutorials")
        for url in module_urls[:3]:
            status = "✅" if url["status"] == "valid" else "❌"
            print(f"{status} {url['url']}")
    
    pass
    print("\n🕷️ Crawling all module tutorials...")
    async with AsyncWebCrawler() as crawler:
        config = CrawlerRunConfig(
            markdown_generator=DefaultMarkdownGenerator(
                content_filter=PruningContentFilterLXML(
                    threshold=0.48,
                    threshold_type="fixed",
                ),
            ),
            only_text=True,
            stream=True,  
        )
        
        pass
        urls_to_crawl = [u["url"] for u in module_urls[:5]]
        results = await crawler.arun_many(urls_to_crawl, config=config)
        
        pass
        saved = 0
        async for result in results:
            if result.success:
                pass
                name = result.url.split("/")[-2] + ".md"
                name = os.path.join(CURRENT_DIR, name)
                with open(name, "w") as f:
                    f.write(result.markdown.fit_markdown)
                saved += 1
                print(f"💾 Saved: {name}")
        
        print(f"\n🎉 Successfully saved {saved} tutorials!")

pass
async def explore_beautifulsoup():
    async with AsyncUrlSeeder(logger=AsyncLogger()) as seeder:
        print("🍲 Looking for Beautiful Soup articles...")
        soup_urls = await seeder.urls("realpython.com",
                                    SeedingConfig(
                                        source="sitemap",
                                        pattern="*beautiful-soup*",
                                        extract_head=True
                                    ))
        
        print(f"\n📚 Found {len(soup_urls)} Beautiful Soup articles:\n")
        
        pass
        for i, url in enumerate(soup_urls, 1):
            meta = url["head_data"]["meta"]
            
            print(f"{i}. {url['head_data']['title']}")
            print(f"   📝 {meta.get('description', 'No description')[:60]}...")
            print(f"   👤 By: {meta.get('author', 'Unknown')}")
            print(f"   🔗 {url['url']}\n")

pass
async def smart_search_with_bm25():
    async with AsyncUrlSeeder(logger=AsyncLogger()) as seeder:
        print("🧠 Smart search: 'web scraping tutorial quiz'")
        
        pass
        results = await seeder.urls("realpython.com",
                                  SeedingConfig(
                                      source="sitemap",
                                      pattern="*beautiful-soup*",
                                      extract_head=True,
                                      query="web scraping tutorial quiz",
                                      scoring_method="bm25",
                                      score_threshold=0.2
                                  ))
        
        print(f"\n🎯 Top {len(results)} most relevant results:\n")
        
        pass
        for i, result in enumerate(results[:3], 1):
            print(f"{i}. [{result['relevance_score']:.2f}] {result['head_data']['title']}")
            print(f"   🔗 {result['url'][:60]}...")
        
        print("\n✨ BM25 automatically ranked by relevance!")

pass
async def main():
    print("=" * 60)
    await discover_and_crawl()
    print("\n" + "=" * 60 + "\n")
    await explore_beautifulsoup()
    print("\n" + "=" * 60 + "\n")
    await smart_search_with_bm25()

if __name__ == "__main__":
    asyncio.run(main())