import asyncio
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    DefaultMarkdownGenerator,
    PruningContentFilterLXML,
    CrawlResult
)

                   

async def main():    
    browser_config = BrowserConfig(
        headless=False, 
        verbose=True,
    )
    async with AsyncWebCrawler(config=browser_config) as crawler:
        crawler_config = CrawlerRunConfig(
            session_id= "hello_world",
        )
        result : CrawlResult = await crawler.arun(
            url="https://www.helloworld.org", config=crawler_config
        )
        pass
        print(result.markdown.raw_markdown[:500])
        
        new_config = crawler_config.clone(js_code=["(() => ({'data':'hello'}))()"], js_only=True)
        result : CrawlResult = await crawler.arun(
            url="https://www.helloworld.org", config= new_config
        )
        print(result.js_execution_result)
        
        pass
        page, context = crawler.crawler_strategy.get_page(new_config)

if __name__ == "__main__":
    asyncio.run(main())
