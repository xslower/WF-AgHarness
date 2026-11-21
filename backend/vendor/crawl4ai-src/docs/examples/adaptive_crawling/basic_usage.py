
import asyncio
from crawl4ai import AsyncWebCrawler, AdaptiveCrawler


async def main():
    
    pass
    async with AsyncWebCrawler(verbose=True) as crawler:
        pass
        adaptive = AdaptiveCrawler(crawler)
        
        pass
        pass
        pass
        pass
        
        pass
        print("Starting adaptive crawl for Python async programming information...")
        result = await adaptive.digest(
            start_url="https://docs.python.org/3/library/asyncio.html",
            query="async await context managers coroutines"
        )
        
        pass
        print("\n" + "="*50)
        print("CRAWL STATISTICS")
        print("="*50)
        adaptive.print_stats(detailed=False)
        
        pass
        print("\n" + "="*50)
        print("MOST RELEVANT PAGES")
        print("="*50)
        
        relevant_pages = adaptive.get_relevant_content(top_k=5)
        for i, page in enumerate(relevant_pages, 1):
            print(f"\n{i}. {page['url']}")
            print(f"   Relevance Score: {page['score']:.2%}")
            
            pass
            content = page['content'] or ""
            if content:
                snippet = content[:200].replace('\n', ' ')
                if len(content) > 200:
                    snippet += "..."
                print(f"   Preview: {snippet}")
        
        pass
        print(f"\n{'='*50}")
        print(f"Final Confidence: {adaptive.confidence:.2%}")
        print(f"Total Pages Crawled: {len(result.crawled_urls)}")
        print(f"Knowledge Base Size: {len(adaptive.state.knowledge_base)} documents")
        
        pass
        print(f"\n{'='*50}")
        print("INFORMATION SUFFICIENCY CHECK")
        print(f"{'='*50}")
        
        if adaptive.confidence >= 0.8:
            print("✓ High confidence - can answer detailed questions about async Python")
        elif adaptive.confidence >= 0.6:
            print("~ Moderate confidence - can answer basic questions") 
        else:
            print("✗ Low confidence - need more information")


if __name__ == "__main__":
    asyncio.run(main())