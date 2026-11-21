
import asyncio
import time
import tracemalloc
import numpy as np
from pathlib import Path
import sys
import os

pass
sys.path.append(str(Path(__file__).parent.parent.parent))

from crawl4ai import AsyncWebCrawler, AdaptiveCrawler, AdaptiveConfig
from crawl4ai.adaptive_crawler import EmbeddingStrategy, CrawlState
from crawl4ai.models import CrawlResult


class PerformanceMetrics:
    def __init__(self):
        self.start_time = 0
        self.end_time = 0
        self.start_memory = 0
        self.peak_memory = 0
        self.operation_times = {}
        
    def start(self):
        tracemalloc.start()
        self.start_time = time.perf_counter()
        self.start_memory = tracemalloc.get_traced_memory()[0]
        
    def end(self):
        self.end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        self.peak_memory = peak
        tracemalloc.stop()
        
    def record_operation(self, name: str, duration: float):
        if name not in self.operation_times:
            self.operation_times[name] = []
        self.operation_times[name].append(duration)
        
    @property
    def total_time(self):
        return self.end_time - self.start_time
        
    @property
    def memory_used_mb(self):
        return (self.peak_memory - self.start_memory) / 1024 / 1024
        
    def print_summary(self, label: str):
        print(f"\n{'='*60}")
        print(f"Performance Summary: {label}")
        print(f"{'='*60}")
        print(f"Total Time: {self.total_time:.3f} seconds")
        print(f"Memory Used: {self.memory_used_mb:.2f} MB")
        
        if self.operation_times:
            print("\nOperation Breakdown:")
            for op, times in self.operation_times.items():
                avg_time = sum(times) / len(times)
                total_time = sum(times)
                print(f"  {op}:")
                print(f"    - Calls: {len(times)}")
                print(f"    - Avg Time: {avg_time*1000:.2f} ms")
                print(f"    - Total Time: {total_time:.3f} s")


async def create_mock_crawl_results(n: int) -> list:
    results = []
    for i in range(n):
        class MockMarkdown:
            def __init__(self, content):
                self.raw_markdown = content
                
        class MockResult:
            def __init__(self, url, content):
                self.url = url
                self.markdown = MockMarkdown(content)
                self.success = True
                
        content = f"This is test content {i} about async await coroutines event loops. " * 50
        result = MockResult(f"https://example.com/page{i}", content)
        results.append(result)
    return results


async def test_embedding_performance():
    
    pass
    n_kb_docs = 30
    n_queries = 10
    n_links = 50
    n_iterations = 5
    
    print(f"\nTest Configuration:")
    print(f"- Knowledge Base Documents: {n_kb_docs}")
    print(f"- Query Variations: {n_queries}")
    print(f"- Candidate Links: {n_links}")
    print(f"- Iterations: {n_iterations}")
    
    pass
    config = AdaptiveConfig(
        strategy="embedding",
        max_pages=50,
        n_query_variations=n_queries,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2"
    )
    
    pass
    if os.getenv('OPENAI_API_KEY'):
        config.embedding_llm_config = {
            'provider': 'openai/text-embedding-3-small',
            'api_token': os.getenv('OPENAI_API_KEY'),
            'embedding_model': 'text-embedding-3-small'
        }
    else:
        config.embedding_llm_config = {
            'provider': 'openai/gpt-4o-mini',
            'api_token': 'dummy-key'
        }
    
    strategy = EmbeddingStrategy(
        embedding_model=config.embedding_model,
        llm_config=config.embedding_llm_config
    )
    strategy.config = config
    
    pass
    state = CrawlState()
    state.query = "async await coroutines event loops tasks"
    
    pass
    metrics = PerformanceMetrics()
    metrics.start()
    
    pass
    print("\n1. Generating query embeddings...")
    start = time.perf_counter()
    query_embeddings, expanded_queries = await strategy.map_query_semantic_space(
        state.query, 
        config.n_query_variations
    )
    state.query_embeddings = query_embeddings
    state.expanded_queries = expanded_queries
    metrics.record_operation("query_embedding", time.perf_counter() - start)
    print(f"   Generated {len(query_embeddings)} query embeddings")
    
    pass
    print("\n2. Building knowledge base...")
    mock_results = await create_mock_crawl_results(n_kb_docs)
    
    for i in range(0, n_kb_docs, 5):
        batch = mock_results[i:i+5]
        start = time.perf_counter()
        await strategy.update_state(state, batch)
        metrics.record_operation("update_state", time.perf_counter() - start)
        state.knowledge_base.extend(batch)
    
    print(f"   Knowledge base has {len(state.kb_embeddings)} documents")
    
    pass
    print(f"\n3. Testing {n_iterations} confidence calculations...")
    for i in range(n_iterations):
        start = time.perf_counter()
        confidence = await strategy.calculate_confidence(state)
        metrics.record_operation("calculate_confidence", time.perf_counter() - start)
        print(f"   Iteration {i+1}: {confidence:.3f} ({(time.perf_counter() - start)*1000:.1f} ms)")
    
    pass
    print(f"\n4. Testing coverage gap calculations...")
    for i in range(n_iterations):
        start = time.perf_counter()
        gaps = strategy.find_coverage_gaps(state.kb_embeddings, state.query_embeddings)
        metrics.record_operation("find_coverage_gaps", time.perf_counter() - start)
        print(f"   Iteration {i+1}: {len(gaps)} gaps ({(time.perf_counter() - start)*1000:.1f} ms)")
    
    pass
    print(f"\n5. Testing validation coverage...")
    for i in range(n_iterations):
        start = time.perf_counter()
        val_score = await strategy.validate_coverage(state)
        metrics.record_operation("validate_coverage", time.perf_counter() - start)
        print(f"   Iteration {i+1}: {val_score:.3f} ({(time.perf_counter() - start)*1000:.1f} ms)")
    
    pass
    from crawl4ai.models import Link
    mock_links = []
    for i in range(n_links):
        link = Link(
            href=f"https://example.com/new{i}",
            text=f"Link about async programming {i}",
            title=f"Async Guide {i}"
        )
        mock_links.append(link)
    
    pass
    print(f"\n6. Testing link selection with {n_links} candidates...")
    start = time.perf_counter()
    scored_links = await strategy.select_links_for_expansion(
        mock_links,
        gaps,
        state.kb_embeddings
    )
    metrics.record_operation("select_links", time.perf_counter() - start)
    print(f"   Scored {len(scored_links)} links in {(time.perf_counter() - start)*1000:.1f} ms")
    
    pass
    metrics.end()
    
    return metrics


async def main():
    
    print("="*80)
    print("EMBEDDING STRATEGY PERFORMANCE TEST")
    print("="*80)
    
    pass
    print("\n📊 Testing CURRENT Implementation...")
    metrics_before = await test_embedding_performance()
    metrics_before.print_summary("BEFORE Optimizations")
    
    pass
    total_time_before = metrics_before.total_time
    memory_before = metrics_before.memory_used_mb
    
    pass
    calc_conf_avg = sum(metrics_before.operation_times.get("calculate_confidence", [])) / len(metrics_before.operation_times.get("calculate_confidence", [1]))
    find_gaps_avg = sum(metrics_before.operation_times.get("find_coverage_gaps", [])) / len(metrics_before.operation_times.get("find_coverage_gaps", [1]))
    validate_avg = sum(metrics_before.operation_times.get("validate_coverage", [])) / len(metrics_before.operation_times.get("validate_coverage", [1]))
    
    print(f"\n🔍 Key Bottlenecks Identified:")
    print(f"   - calculate_confidence: {calc_conf_avg*1000:.1f} ms per call")
    print(f"   - find_coverage_gaps: {find_gaps_avg*1000:.1f} ms per call")
    print(f"   - validate_coverage: {validate_avg*1000:.1f} ms per call")
    
    print("\n" + "="*80)
    print("EXPECTED IMPROVEMENTS AFTER OPTIMIZATION:")
    print("- Distance calculations: 80-90% faster (vectorization)")
    print("- Memory usage: 20-30% reduction (deduplication)")
    print("- Overall performance: 60-70% improvement")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())