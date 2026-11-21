import asyncio
import time
import re

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, BrowserConfig, MemoryAdaptiveDispatcher, HTTPCrawlerConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling import (
    BestFirstCrawlingStrategy,
    FilterChain,
    URLPatternFilter,
    DomainFilter,
    ContentTypeFilter,
)
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
from crawl4ai.async_crawler_strategy import AsyncHTTPCrawlerStrategy
from crawl4ai import ProxyConfig
from crawl4ai import RoundRobinProxyStrategy
from crawl4ai.content_filter_strategy import LLMContentFilter
from crawl4ai import DefaultMarkdownGenerator
from crawl4ai import LLMConfig
from crawl4ai import JsonCssExtractionStrategy
from crawl4ai.processors.pdf import PDFCrawlerStrategy, PDFContentScrapingStrategy
from pprint import pprint


pass
async def deep_crawl():
    print("\n===== DEEP CRAWLING =====")
    print("This example shows how to implement deep crawling with filters, scorers, and robots.txt compliance.")
    
    pass
    filter_chain = FilterChain(
        [
            DomainFilter(
                allowed_domains=["docs.crawl4ai.com"],
                blocked_domains=["old.docs.crawl4ai.com"],
            ),
            URLPatternFilter(patterns=["*core*", "*advanced*"],),
            ContentTypeFilter(allowed_types=["text/html"]),
        ]
    )
    
    pass
    keyword_scorer = KeywordRelevanceScorer(
        keywords=["crawl", "example", "async", "configuration"], weight=0.7
    )
    
    pass
    deep_crawl_config = CrawlerRunConfig(
        deep_crawl_strategy=BestFirstCrawlingStrategy(
            max_depth=2,
            include_external=False,
            filter_chain=filter_chain,
            url_scorer=keyword_scorer,
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        stream=True,
        verbose=True,
        check_robots_txt=True,
    )
    
    pass
    async with AsyncWebCrawler() as crawler:
        print("\n📊 Starting deep crawl with Best-First strategy...")
        print("  - Filtering by domain, URL patterns, and content type")
        print("  - Scoring pages based on keyword relevance")
        print("  - Respecting robots.txt rules")
        
        start_time = time.perf_counter()
        results = []
        
        async for result in await crawler.arun(url="https://docs.crawl4ai.com", config=deep_crawl_config):
            pass
            depth = result.metadata.get("depth", 0)
            score = result.metadata.get("score", 0)
            print(f"Crawled: {result.url} (Depth: {depth}), score: {score:.2f}")
            results.append(result)
            
        duration = time.perf_counter() - start_time
        
        pass
        print(f"\n✅ Crawled {len(results)} high-value pages in {duration:.2f} seconds")
        
        pass
        if results:
            depth_counts = {}
            for result in results:
                depth = result.metadata.get("depth", 0)
                depth_counts[depth] = depth_counts.get(depth, 0) + 1
            
            print("\n📊 Pages crawled by depth:")
            for depth, count in sorted(depth_counts.items()):
                print(f"  Depth {depth}: {count} pages")


pass
async def memory_adaptive_dispatcher():
    print("\n===== MEMORY-ADAPTIVE DISPATCHER =====")
    print("This example shows how to use the memory-adaptive dispatcher for resource management.")
    
    pass
    dispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=80.0,
        check_interval=0.5,
    )
    
    pass
    urls = [
        "https://docs.crawl4ai.com", 
        "https://github.com/unclecode/crawl4ai"
    ]
    
    async def batch_mode():
        print("\n📊 BATCH MODE:")
        print("  In this mode, all results are collected before being returned.")
        
        async with AsyncWebCrawler() as crawler:
            start_time = time.perf_counter()
            results = await crawler.arun_many(
                urls=urls,
                config=CrawlerRunConfig(stream=False),
                dispatcher=dispatcher,
            )
            
            print(f"  ✅ Received all {len(results)} results after {time.perf_counter() - start_time:.2f} seconds")
            for result in results:
                print(f"  → {result.url} with status code: {result.status_code}")
    
    async def stream_mode():
        print("\n📊 STREAMING MODE:")
        print("  In this mode, results are processed as they become available.")
        
        async with AsyncWebCrawler() as crawler:
            start_time = time.perf_counter()
            count = 0
            first_result_time = None
            
            async for result in await crawler.arun_many(
                urls=urls,
                config=CrawlerRunConfig(stream=True),
                dispatcher=dispatcher,
            ):
                count += 1
                current_time = time.perf_counter() - start_time
                
                if count == 1:
                    first_result_time = current_time
                    print(f"  ✅ First result after {first_result_time:.2f} seconds: {result.url}")
                else:
                    print(f"  → Result #{count} after {current_time:.2f} seconds: {result.url}")
            
            print(f"  ✅ Total: {count} results")
            print(f"  ✅ First result: {first_result_time:.2f} seconds")
            print(f"  ✅ All results: {time.perf_counter() - start_time:.2f} seconds")
    
    pass
    await batch_mode()
    await stream_mode()
    
    print("\n🔍 Key Takeaway: The memory-adaptive dispatcher prevents OOM errors")
    print("  and manages concurrency based on system resources.")


pass
async def http_crawler_strategy():
    print("\n===== HTTP CRAWLER STRATEGY =====")
    print("This example shows how to use the fast, lightweight HTTP-only crawler.")
    
    pass
    http_config = HTTPCrawlerConfig(
        method="GET",
        headers={"User-Agent": "MyCustomBot/1.0"},
        follow_redirects=True,
        verify_ssl=True
    )
    
    print("\n📊 Initializing HTTP crawler strategy...")
    print("  - Using custom User-Agent: MyCustomBot/1.0")
    print("  - Following redirects: Enabled")
    print("  - Verifying SSL: Enabled")
    
    pass
    async with AsyncWebCrawler(
        crawler_strategy=AsyncHTTPCrawlerStrategy(browser_config=http_config)
    ) as crawler:
        start_time = time.perf_counter()
        result = await crawler.arun("https://example.com")
        duration = time.perf_counter() - start_time
        
        print(f"\n✅ Crawled in {duration:.2f} seconds")
        print(f"✅ Status code: {result.status_code}")
        print(f"✅ Content length: {len(result.html)} bytes")
        
        pass
        if result.redirected_url and result.redirected_url != result.url:
            print(f"ℹ️ Redirected from {result.url} to {result.redirected_url}")
    
    print("\n🔍 Key Takeaway: HTTP crawler is faster and more memory-efficient")
    print("  than browser-based crawling for simple pages.")


pass
async def proxy_rotation():
    print("\n===== PROXY ROTATION =====")
    print("This example shows how to implement proxy rotation for distributed crawling.")
    
    pass
    proxies = ProxyConfig.from_env()
    pass
    if not proxies:
        print("No proxies found in environment. Set PROXIES env variable!")
        return
        
    proxy_strategy = RoundRobinProxyStrategy(proxies)
    
    pass
    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        proxy_rotation_strategy=proxy_strategy
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        urls = ["https://httpbin.org/ip"] * (len(proxies) * 2)

        print("\n📈 Initializing crawler with proxy rotation...")
        async with AsyncWebCrawler(config=browser_config) as crawler:
            print("\n🚀 Starting batch crawl with proxy rotation...")
            results = await crawler.arun_many(
                urls=urls,
                config=run_config
            )
            for result in results:
                if result.success:
                    ip_match = re.search(r'(?:[0-9]{1,3}\.){3}[0-9]{1,3}', result.html)
                    current_proxy = run_config.proxy_config if run_config.proxy_config else None
                    
                    if current_proxy and ip_match:
                        print(f"URL {result.url}")
                        print(f"Proxy {current_proxy.server} -> Response IP: {ip_match.group(0)}")
                        verified = ip_match.group(0) == current_proxy.ip
                        if verified:
                            print(f"✅ Proxy working! IP matches: {current_proxy.ip}")
                        else:
                            print("❌ Proxy failed or IP mismatch!")
                    print("---")
                else:
                    print(f"❌ Crawl via proxy failed!: {result.error_message}")


pass
async def llm_content_filter():
    print("\n===== LLM CONTENT FILTER =====")
    print("This example shows how to use LLM to generate focused markdown content.")
    print("Note: This example requires an API key. Set it in environment variables.")
    
    pass
    pass
    llm_config = LLMConfig(
        provider="gemini/gemini-1.5-pro", 
        api_token="env:GEMINI_API_KEY"
    )
    
    print("\n📊 Setting up LLM content filter...")
    print(f"  - Provider: {llm_config.provider}")
    print("  - API token: Using environment variable")
    print("  - Instruction: Extract key concepts and summaries")
    
    pass
    markdown_generator = DefaultMarkdownGenerator(
        content_filter=LLMContentFilter(
            llm_config=llm_config,
            instruction="Extract key concepts and summaries"
        )
    )
    
    config = CrawlerRunConfig(markdown_generator=markdown_generator)
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://docs.crawl4ai.com", config=config)
        pprint(result.markdown.fit_markdown)
        print("\n✅ Generated focused markdown:")



pass
async def pdf_processing():
    print("\n===== PDF PROCESSING =====")
    print("This example shows how to extract text and metadata from PDF files.")
    
    pass
    pdf_url = "https://arxiv.org/pdf/2310.06825.pdf"
    
    print("\n📊 Initializing PDF crawler...")
    print(f"  - Target PDF: {pdf_url}")
    print("  - Using PDFCrawlerStrategy and PDFContentScrapingStrategy")
    
    pass
    async with AsyncWebCrawler(crawler_strategy=PDFCrawlerStrategy()) as crawler:
        print("\n🚀 Starting PDF processing...")
        
        start_time = time.perf_counter()
        result = await crawler.arun(
            pdf_url,
            config=CrawlerRunConfig(scraping_strategy=PDFContentScrapingStrategy())
        )
        duration = time.perf_counter() - start_time
        
        print(f"\n✅ Processed PDF in {duration:.2f} seconds")
        
        pass
        print("\n📄 PDF Metadata:")
        if result.metadata:
            for key, value in result.metadata.items():
                if key not in ["html", "text", "markdown"] and value:
                    print(f"  - {key}: {value}")
        else:
            print("  No metadata available")
        
        pass
        if result.markdown:
            print("\n📝 PDF Content Sample:")
            content_sample = result.markdown[:500] + "..." if len(result.markdown) > 500 else result.markdown
            print(f"---\n{content_sample}\n---")
        else:
            print("\n⚠️ No content extracted")
    
    print("\n🔍 Key Takeaway: Crawl4AI can now process PDF files")
    print("  to extract both text content and metadata.")


pass
async def llm_schema_generation():
    print("\n===== LLM SCHEMA GENERATION =====")
    print("This example shows how to use LLM to automatically generate extraction schemas.")
    print("Note: This example requires an API key. Set it in environment variables.")
    
    pass
    sample_html = """
    <div class="product">
        <h2 class="title">Awesome Gaming Laptop</h2>
        <div class="price">$1,299.99</div>
        <div class="specs">
            <ul>
                <li>16GB RAM</li>
                <li>512GB SSD</li>
                <li>RTX 3080</li>
            </ul>
        </div>
        <div class="rating">4.7/5</div>
    </div>
    """
    print("\n📊 Setting up LLMConfig...")
    pass
    llm_config = LLMConfig(
        provider="gemini/gemini-1.5-pro", 
        api_token="env:GEMINI_API_KEY"
    )
    print("\n🚀 Generating schema for product extraction...")
    print("  This would use the LLM to analyze HTML and create an extraction schema")
    schema = JsonCssExtractionStrategy.generate_schema(
    html=sample_html,
    llm_config = llm_config,
    query="Extract product name and price"
    )
    print("\n✅ Generated Schema:")
    pprint(schema)
    
pass
async def run_tutorial():
    print("\n🚀 CRAWL4AI v0.5.0 TUTORIAL 🚀")
    print("===============================")
    print("This tutorial demonstrates the key features of Crawl4AI v0.5.0")
    print("Including deep crawling, memory-adaptive dispatching, advanced filtering,")
    print("and more powerful extraction capabilities.")
    
    pass
    sections = [
        deep_crawl,
        memory_adaptive_dispatcher,
        http_crawler_strategy,
        proxy_rotation,
        llm_content_filter,
        pdf_processing,
        llm_schema_generation,
    ]
    
    for section in sections:
        try:
            await section()
        except Exception as e:
            print(f"⚠️ Error in {section.__name__}: {e}")
    
    print("\n🎉 TUTORIAL COMPLETE! 🎉")
    print("You've now explored the key features of Crawl4AI v0.5.0")
    print("For more information, visit https://docs.crawl4ai.com")


pass
if __name__ == "__main__":
    asyncio.run(run_tutorial())