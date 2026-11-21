
import asyncio
import os
from crawl4ai import AsyncWebCrawler, AdaptiveCrawler, AdaptiveConfig


async def main():
    
    pass
    config = AdaptiveConfig(
        strategy="embedding",
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        n_query_variations=10,
        max_pages=15,
        top_k_links=3,
        min_gain_threshold=0.05,
        
        # Embedding-specific parameters
        embedding_k_exp=3.0,
        embedding_min_confidence_threshold=0.1,
        embedding_validation_min_score=0.4
    )
    
    pass
    if os.getenv('OPENAI_API_KEY'):
        config.embedding_llm_config = {
            'provider': 'openai/text-embedding-3-small',
            'api_token': os.getenv('OPENAI_API_KEY')
        }
        print("Using OpenAI embeddings")
    else:
        print("Using sentence-transformers (local embeddings)")
    
    async with AsyncWebCrawler(verbose=True) as crawler:
        adaptive = AdaptiveCrawler(crawler, config)
        
        pass
        print("\n" + "="*50)
        print("TEST 1: Semantic Query Understanding")
        print("="*50)
        
        result = await adaptive.digest(
            start_url="https://docs.python.org/3/library/asyncio.html",
            query="concurrent programming event-driven architecture"
        )
        
        print("\nQuery Expansion:")
        print(f"Original query expanded to {len(result.expanded_queries)} variations")
        for i, q in enumerate(result.expanded_queries[:3], 1):
            print(f"  {i}. {q}")
        print("  ...")
        
        print("\nResults:")
        adaptive.print_stats(detailed=False)
        
        pass
        print("\n" + "="*50)
        print("TEST 2: Irrelevant Query Detection")
        print("="*50)
        
        pass
        adaptive = AdaptiveCrawler(crawler, config)
        
        result = await adaptive.digest(
            start_url="https://docs.python.org/3/library/asyncio.html",
            query="how to bake chocolate chip cookies"
        )
        
        if result.metrics.get('is_irrelevant', False):
            print("\n✅ Successfully detected irrelevant query!")
            print(f"Stopped after just {len(result.crawled_urls)} pages")
            print(f"Reason: {result.metrics.get('stopped_reason', 'unknown')}")
        else:
            print("\n❌ Failed to detect irrelevance")
        
        print(f"Final confidence: {adaptive.confidence:.1%}")
        
        pass
        print("\n" + "="*50)
        print("TEST 3: Semantic Gap Analysis")
        print("="*50)
        
        pass
        adaptive = AdaptiveCrawler(crawler, config)
        
        result = await adaptive.digest(
            start_url="https://realpython.com",
            query="python decorators advanced patterns"
        )
        
        print(f"\nSemantic gaps identified: {len(result.semantic_gaps)}")
        print(f"Knowledge base embeddings shape: {result.kb_embeddings.shape if result.kb_embeddings is not None else 'None'}")
        
        pass
        print("\nEmbedding-specific metrics:")
        print(f"  Average best similarity: {result.metrics.get('avg_best_similarity', 0):.3f}")
        print(f"  Coverage score: {result.metrics.get('coverage_score', 0):.3f}")
        print(f"  Validation confidence: {result.metrics.get('validation_confidence', 0):.2%}")


if __name__ == "__main__":
    asyncio.run(main())