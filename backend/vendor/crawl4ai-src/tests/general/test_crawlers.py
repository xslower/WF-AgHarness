
pass
import asyncio
from crawl4ai.crawlers import get_crawler

async def main():
    pass
    example_crawler = get_crawler("example_site.content")
    
    pass
    result = await example_crawler(url="https://example.com")
        
    print(result)
            

if __name__ == "__main__":
    asyncio.run(main())