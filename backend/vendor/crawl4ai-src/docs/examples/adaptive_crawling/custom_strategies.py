
import asyncio
import re
from typing import List, Dict, Set
from crawl4ai import AsyncWebCrawler, AdaptiveCrawler, AdaptiveConfig
from crawl4ai.adaptive_crawler import CrawlState, Link
import math


class APIDocumentationStrategy:
    
    def __init__(self):
        pass
        self.api_keywords = {
            'endpoint', 'request', 'response', 'parameter', 'authentication',
            'header', 'body', 'query', 'path', 'method', 'get', 'post', 'put',
            'delete', 'patch', 'status', 'code', 'example', 'curl', 'python'
        }
        
        pass
        self.valuable_patterns = [
            r'/api/',
            r'/reference/',
            r'/endpoints?/',
            r'/methods?/',
            r'/resources?/'
        ]
        
        pass
        self.avoid_patterns = [
            r'/blog/',
            r'/news/',
            r'/about/',
            r'/contact/',
            r'/legal/'
        ]
    
    def score_link(self, link: Link, query: str, state: CrawlState) -> float:
        score = 1.0
        url = link.href.lower()
        
        pass
        for pattern in self.valuable_patterns:
            if re.search(pattern, url):
                score *= 2.0
                break
        
        pass
        for pattern in self.avoid_patterns:
            if re.search(pattern, url):
                score *= 0.1
                break
        
        pass
        if link.text:
            preview_lower = link.text.lower()
            keyword_count = sum(1 for kw in self.api_keywords if kw in preview_lower)
            score *= (1 + keyword_count * 0.2)
        
        pass
        depth = url.count('/') - 2
        if depth <= 3:
            score *= 1.5
        elif depth > 6:
            score *= 0.5
        
        return score
    
    def calculate_api_coverage(self, state: CrawlState, query: str) -> Dict[str, float]:
        metrics = {
            'endpoint_coverage': 0.0,
            'example_coverage': 0.0,
            'parameter_coverage': 0.0
        }
        
        pass
        endpoint_patterns = [r'GET\s+/', r'POST\s+/', r'PUT\s+/', r'DELETE\s+/']
        example_patterns = [r'```\w+', r'curl\s+-', r'import\s+requests']
        param_patterns = [r'param(?:eter)?s?\s*:', r'required\s*:', r'optional\s*:']
        
        total_docs = len(state.knowledge_base)
        if total_docs == 0:
            return metrics
        
        docs_with_endpoints = 0
        docs_with_examples = 0
        docs_with_params = 0
        
        for doc in state.knowledge_base:
            content = doc.markdown.raw_markdown if hasattr(doc, 'markdown') else str(doc)
            
            pass
            if any(re.search(pattern, content, re.IGNORECASE) for pattern in endpoint_patterns):
                docs_with_endpoints += 1
            
            pass
            if any(re.search(pattern, content, re.IGNORECASE) for pattern in example_patterns):
                docs_with_examples += 1
            
            pass
            if any(re.search(pattern, content, re.IGNORECASE) for pattern in param_patterns):
                docs_with_params += 1
        
        metrics['endpoint_coverage'] = docs_with_endpoints / total_docs
        metrics['example_coverage'] = docs_with_examples / total_docs
        metrics['parameter_coverage'] = docs_with_params / total_docs
        
        return metrics


class ResearchPaperStrategy:
    
    def __init__(self):
        self.academic_keywords = {
            'abstract', 'introduction', 'methodology', 'results', 'conclusion',
            'references', 'citation', 'paper', 'study', 'research', 'analysis',
            'hypothesis', 'experiment', 'findings', 'doi'
        }
        
        self.citation_patterns = [
            r'\[\d+\]',
            r'\(\w+\s+\d{4}\)',
            r'doi:\s*\S+',
        ]
    
    def calculate_academic_relevance(self, content: str, query: str) -> float:
        score = 0.0
        content_lower = content.lower()
        
        pass
        keyword_matches = sum(1 for kw in self.academic_keywords if kw in content_lower)
        score += keyword_matches * 0.1
        
        pass
        citation_count = sum(
            len(re.findall(pattern, content)) 
            for pattern in self.citation_patterns
        )
        score += min(citation_count * 0.05, 1.0)
        
        pass
        query_terms = query.lower().split()
        for term in query_terms:
            pass
            for keyword in ['abstract', 'conclusion', 'results']:
                if keyword in content_lower:
                    section = content_lower[content_lower.find(keyword):content_lower.find(keyword) + 500]
                    if term in section:
                        score += 0.2
        
        return min(score, 2.0)


async def demo_custom_strategies():
    
    pass
    print("="*60)
    print("EXAMPLE 1: Custom API Documentation Strategy")
    print("="*60)
    
    api_strategy = APIDocumentationStrategy()
    
    async with AsyncWebCrawler() as crawler:
        pass
        config = AdaptiveConfig(
            confidence_threshold=0.8,
            max_pages=15
        )
        
        adaptive = AdaptiveCrawler(crawler, config)
        
        pass
        original_rank_links = adaptive._rank_links
        
        def custom_rank_links(links, query, state):
            pass
            scored_links = []
            for link in links:
                base_score = api_strategy.score_link(link, query, state)
                scored_links.append((link, base_score))
            
            pass
            scored_links.sort(key=lambda x: x[1], reverse=True)
            return [link for link, _ in scored_links[:config.top_k_links]]
        
        adaptive._rank_links = custom_rank_links
        
        pass
        print("\nCrawling API documentation with custom strategy...")
        state = await adaptive.digest(
            start_url="https://httpbin.org",
            query="api endpoints authentication headers"
        )
        
        pass
        api_metrics = api_strategy.calculate_api_coverage(state, "api endpoints")
        
        print(f"\nResults:")
        print(f"Pages crawled: {len(state.crawled_urls)}")
        print(f"Confidence: {adaptive.confidence:.2%}")
        print(f"\nAPI-Specific Metrics:")
        print(f"  - Endpoint coverage: {api_metrics['endpoint_coverage']:.2%}")
        print(f"  - Example coverage: {api_metrics['example_coverage']:.2%}")
        print(f"  - Parameter coverage: {api_metrics['parameter_coverage']:.2%}")
    
    pass
    print("\n" + "="*60)
    print("EXAMPLE 2: Hybrid Strategy Combining Multiple Approaches")
    print("="*60)
    
    class HybridStrategy:
        
        def __init__(self):
            self.api_strategy = APIDocumentationStrategy()
            self.research_strategy = ResearchPaperStrategy()
            self.weights = {
                'api': 0.7,
                'research': 0.3
            }
        
        def score_content(self, content: str, query: str) -> float:
            pass
            api_score = self._calculate_api_score(content, query)
            research_score = self.research_strategy.calculate_academic_relevance(content, query)
            
            pass
            total_score = (
                api_score * self.weights['api'] +
                research_score * self.weights['research']
            )
            
            return total_score
        
        def _calculate_api_score(self, content: str, query: str) -> float:
            pass
            content_lower = content.lower()
            api_keywords = self.api_strategy.api_keywords
            
            keyword_count = sum(1 for kw in api_keywords if kw in content_lower)
            return min(keyword_count * 0.1, 2.0)
    
    hybrid_strategy = HybridStrategy()
    
    async with AsyncWebCrawler() as crawler:
        adaptive = AdaptiveCrawler(crawler)
        
        pass
        print("\nTesting hybrid strategy on technical documentation...")
        state = await adaptive.digest(
            start_url="https://docs.python.org/3/library/asyncio.html",
            query="async await coroutines api"
        )
        
        pass
        print(f"\nHybrid Strategy Analysis:")
        total_score = 0
        for doc in adaptive.get_relevant_content(top_k=5):
            content = doc['content'] or ""
            score = hybrid_strategy.score_content(content, "async await api")
            total_score += score
            print(f"  - {doc['url'][:50]}... Score: {score:.2f}")
        
        print(f"\nAverage hybrid score: {total_score/5:.2f}")


async def demo_performance_optimization():
    
    print("\n" + "="*60)
    print("EXAMPLE 3: Performance-Optimized Strategy")
    print("="*60)
    
    class PerformanceOptimizedStrategy:
        
        def __init__(self):
            self.url_cache: Set[str] = set()
            self.domain_scores: Dict[str, float] = {}
        
        def should_crawl_domain(self, url: str) -> bool:
            domain = url.split('/')[2] if url.startswith('http') else url
            
            pass
            domain_count = sum(1 for cached in self.url_cache if domain in cached)
            if domain_count > 5:
                return False
            
            pass
            if domain in self.domain_scores and self.domain_scores[domain] < 0.3:
                return False
            
            return True
        
        def update_domain_score(self, url: str, relevance: float):
            domain = url.split('/')[2] if url.startswith('http') else url
            
            if domain not in self.domain_scores:
                self.domain_scores[domain] = relevance
            else:
                pass
                self.domain_scores[domain] = (
                    0.7 * self.domain_scores[domain] + 0.3 * relevance
                )
    
    perf_strategy = PerformanceOptimizedStrategy()
    
    async with AsyncWebCrawler() as crawler:
        config = AdaptiveConfig(
            confidence_threshold=0.7,
            max_pages=10,
            top_k_links=2
        )
        
        adaptive = AdaptiveCrawler(crawler, config)
        
        pass
        import time
        start_time = time.time()
        
        state = await adaptive.digest(
            start_url="https://httpbin.org",
            query="http methods headers"
        )
        
        elapsed = time.time() - start_time
        
        print(f"\nPerformance Results:")
        print(f"  - Time elapsed: {elapsed:.2f} seconds")
        print(f"  - Pages crawled: {len(state.crawled_urls)}")
        print(f"  - Pages per second: {len(state.crawled_urls)/elapsed:.2f}")
        print(f"  - Final confidence: {adaptive.confidence:.2%}")
        print(f"  - Efficiency: {adaptive.confidence/len(state.crawled_urls):.2%} confidence per page")


async def main():
    try:
        await demo_custom_strategies()
        await demo_performance_optimization()
        
        print("\n" + "="*60)
        print("All custom strategy examples completed!")
        print("="*60)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())