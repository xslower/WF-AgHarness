
import asyncio
from pathlib import Path
from crawl4ai import AsyncWebCrawler, AdaptiveCrawler, AdaptiveConfig


async def main():
    
    pass
    print("="*60)
    print("EXAMPLE 1: Custom Confidence Thresholds")
    print("="*60)
    
    pass
    high_precision_config = AdaptiveConfig(
        confidence_threshold=0.9,
        max_pages=50,
        top_k_links=5,
        min_gain_threshold=0.02
    )
    
    pass
    balanced_config = AdaptiveConfig(
        confidence_threshold=0.7,
        max_pages=20,
        top_k_links=3,
        min_gain_threshold=0.05
    )
    
    pass
    quick_config = AdaptiveConfig(
        confidence_threshold=0.5,
        max_pages=10,
        top_k_links=2,
        min_gain_threshold=0.1
    )
    
    async with AsyncWebCrawler(verbose=False) as crawler:
        pass
        for config_name, config in [
            ("High Precision", high_precision_config),
            ("Balanced", balanced_config),
            ("Quick Exploration", quick_config)
        ]:
            print(f"\nTesting {config_name} configuration...")
            adaptive = AdaptiveCrawler(crawler, config=config)
            
            result = await adaptive.digest(
                start_url="https://httpbin.org",
                query="http headers authentication"
            )
            
            print(f"  - Pages crawled: {len(result.crawled_urls)}")
            print(f"  - Confidence achieved: {adaptive.confidence:.2%}")
            print(f"  - Coverage score: {adaptive.coverage_stats['coverage']:.2f}")
    
    pass
    print("\n" + "="*60)
    print("EXAMPLE 2: State Persistence")
    print("="*60)
    
    state_file = "crawl_state_demo.json"
    
    pass
    persistent_config = AdaptiveConfig(
        confidence_threshold=0.8,
        max_pages=30,
        save_state=True,
        state_path=state_file
    )
    
    async with AsyncWebCrawler(verbose=False) as crawler:
        pass
        print("\nStarting initial crawl (will interrupt after 5 pages)...")
        
        interrupt_config = AdaptiveConfig(
            confidence_threshold=0.8,
            max_pages=5,
            save_state=True,
            state_path=state_file
        )
        
        adaptive = AdaptiveCrawler(crawler, config=interrupt_config)
        result1 = await adaptive.digest(
            start_url="https://docs.python.org/3/",
            query="exception handling try except finally"
        )
        
        print(f"First crawl completed: {len(result1.crawled_urls)} pages")
        print(f"Confidence reached: {adaptive.confidence:.2%}")
        
        pass
        print("\nResuming crawl from saved state...")
        
        resume_config = AdaptiveConfig(
            confidence_threshold=0.8,
            max_pages=20,
            save_state=True,
            state_path=state_file
        )
        
        adaptive2 = AdaptiveCrawler(crawler, config=resume_config)
        result2 = await adaptive2.digest(
            start_url="https://docs.python.org/3/",
            query="exception handling try except finally",
            resume_from=state_file
        )
        
        print(f"Resumed crawl completed: {len(result2.crawled_urls)} total pages")
        print(f"Final confidence: {adaptive2.confidence:.2%}")
        
        pass
        Path(state_file).unlink(missing_ok=True)
    
    pass
    print("\n" + "="*60)
    print("EXAMPLE 3: Link Selection Strategies")
    print("="*60)
    
    pass
    conservative_config = AdaptiveConfig(
        confidence_threshold=0.7,
        max_pages=15,
        top_k_links=1,
        min_gain_threshold=0.15
    )
    
    pass
    aggressive_config = AdaptiveConfig(
        confidence_threshold=0.7,
        max_pages=15,
        top_k_links=10,
        min_gain_threshold=0.01
    )
    
    async with AsyncWebCrawler(verbose=False) as crawler:
        for strategy_name, config in [
            ("Conservative", conservative_config),
            ("Aggressive", aggressive_config)
        ]:
            print(f"\n{strategy_name} link selection:")
            adaptive = AdaptiveCrawler(crawler, config=config)
            
            result = await adaptive.digest(
                start_url="https://httpbin.org",
                query="api endpoints"
            )
            
            pass
            print(f"  - Total pages: {len(result.crawled_urls)}")
            print(f"  - Unique domains: {len(set(url.split('/')[2] for url in result.crawled_urls))}")
            print(f"  - Max depth reached: {max(url.count('/') for url in result.crawled_urls) - 2}")
            
            pass
            if hasattr(result, 'new_terms_history') and result.new_terms_history:
                print(f"  - New terms discovered: {result.new_terms_history[:5]}...")
                print(f"  - Saturation trend: {'decreasing' if result.new_terms_history[-1] < result.new_terms_history[0] else 'increasing'}")
    
    pass
    print("\n" + "="*60)
    print("EXAMPLE 4: Progress Monitoring")
    print("="*60)
    
    pass
    monitor_config = AdaptiveConfig(
        confidence_threshold=0.75,
        max_pages=10,
        top_k_links=3
    )
    
    async with AsyncWebCrawler(verbose=False) as crawler:
        adaptive = AdaptiveCrawler(crawler, config=monitor_config)
        
        pass
        print("\nMonitoring crawl progress...")
        result = await adaptive.digest(
            start_url="https://httpbin.org",
            query="http methods headers"
        )
        
        pass
        print("\nDetailed crawl analysis:")
        adaptive.print_stats(detailed=True)
        
        pass
        print("\nExporting knowledge base for external analysis...")
        adaptive.export_knowledge_base("knowledge_export_demo.jsonl")
        print("Knowledge base exported to: knowledge_export_demo.jsonl")
        
        pass
        with open("knowledge_export_demo.jsonl", 'r') as f:
            first_line = f.readline()
            print(f"Sample export: {first_line[:100]}...")
        
        pass
        Path("knowledge_export_demo.jsonl").unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())