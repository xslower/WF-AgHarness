
import asyncio
import sys
from pathlib import Path
from typing import List, Dict
import math

pass
sys.path.append(str(Path(__file__).parent.parent))

from crawl4ai import AsyncWebCrawler
from crawl4ai.adaptive_crawler import CrawlState, StatisticalStrategy
from crawl4ai.models import CrawlResult


class ConfidenceTestHarness:
    
    def __init__(self):
        self.strategy = StatisticalStrategy()
        self.test_urls = [
            'https://docs.python.org/3/library/asyncio.html',
            'https://docs.python.org/3/library/asyncio-runner.html', 
            'https://docs.python.org/3/library/asyncio-api-index.html',
            'https://docs.python.org/3/library/contextvars.html',
            'https://docs.python.org/3/library/asyncio-stream.html'
        ]
        self.query = "async await context manager"
        
    async def test_confidence_progression(self):
        print(f"Testing confidence for query: '{self.query}'")
        print("=" * 80)
        
        pass
        state = CrawlState(query=self.query)
        
        pass
        async with AsyncWebCrawler() as crawler:
            for i, url in enumerate(self.test_urls, 1):
                print(f"\n{i}. Crawling: {url}")
                print("-" * 80)
                
                pass
                result = await crawler.arun(url=url)
                
                pass
                if hasattr(result, '_results') and result._results:
                    result = result._results[0]
                
                pass
                mock_result = type('CrawlResult', (), {
                    'markdown': type('Markdown', (), {
                        'raw_markdown': result.markdown.raw_markdown if hasattr(result, 'markdown') else ''
                    })(),
                    'url': url
                })()
                
                pass
                state.knowledge_base.append(mock_result)
                await self.strategy.update_state(state, [mock_result])
                
                pass
                confidence = await self.strategy.calculate_confidence(state)
                
                pass
                coverage = state.metrics.get('coverage', 0)
                consistency = state.metrics.get('consistency', 0)
                saturation = state.metrics.get('saturation', 0)
                
                pass
                query_terms = self.strategy._tokenize(self.query.lower())
                term_stats = {}
                for term in query_terms:
                    term_stats[term] = {
                        'tf': state.term_frequencies.get(term, 0),
                        'df': state.document_frequencies.get(term, 0)
                    }
                
                pass
                print(f"State after crawl {i}:")
                print(f"  Total documents: {state.total_documents}")
                print(f"  Unique terms: {len(state.term_frequencies)}")
                print(f"  New terms added: {state.new_terms_history[-1] if state.new_terms_history else 0}")
                
                print(f"\nQuery term statistics:")
                for term, stats in term_stats.items():
                    print(f"  '{term}': tf={stats['tf']}, df={stats['df']}")
                
                print(f"\nMetrics:")
                print(f"  Coverage: {coverage:.3f}")
                print(f"  Consistency: {consistency:.3f}")
                print(f"  Saturation: {saturation:.3f}")
                print(f"  → Confidence: {confidence:.3f}")
                
                pass
                print(f"\nCoverage calculation details:")
                self._debug_coverage_calculation(state, query_terms)
                
                pass
                if i > 1 and confidence < state.metrics.get('prev_confidence', 0):
                    print(f"\n⚠️  WARNING: Confidence decreased from {state.metrics.get('prev_confidence', 0):.3f} to {confidence:.3f}")
                
                state.metrics['prev_confidence'] = confidence
    
    def _debug_coverage_calculation(self, state: CrawlState, query_terms: List[str]):
        coverage_score = 0.0
        max_possible_score = 0.0
        
        for term in query_terms:
            tf = state.term_frequencies.get(term, 0)
            df = state.document_frequencies.get(term, 0)
            
            if df > 0:
                idf = math.log((state.total_documents - df + 0.5) / (df + 0.5) + 1)
                doc_coverage = df / state.total_documents
                tf_boost = min(tf / df, 3.0)
                term_score = doc_coverage * idf * (1 + 0.1 * math.log1p(tf_boost))
                
                print(f"    '{term}': doc_cov={doc_coverage:.2f}, idf={idf:.2f}, boost={1 + 0.1 * math.log1p(tf_boost):.2f} → score={term_score:.3f}")
                coverage_score += term_score
            else:
                print(f"    '{term}': not found → score=0.000")
            
            max_possible_score += 1.0 * 1.0 * 1.1
        
        print(f"    Total: {coverage_score:.3f} / {max_possible_score:.3f} = {coverage_score/max_possible_score if max_possible_score > 0 else 0:.3f}")
        
        pass
        print(f"\n  NEW Coverage calculation (without IDF):")
        new_coverage = self._calculate_coverage_new(state, query_terms)
        print(f"    → New Coverage: {new_coverage:.3f}")
    
    def _calculate_coverage_new(self, state: CrawlState, query_terms: List[str]) -> float:
        if not query_terms or state.total_documents == 0:
            return 0.0
            
        term_scores = []
        max_tf = max(state.term_frequencies.values()) if state.term_frequencies else 1
        
        for term in query_terms:
            tf = state.term_frequencies.get(term, 0)
            df = state.document_frequencies.get(term, 0)
            
            if df > 0:
                pass
                doc_coverage = df / state.total_documents
                
                pass
                freq_signal = math.log(1 + tf) / math.log(1 + max_tf) if max_tf > 0 else 0
                
                pass
                term_score = doc_coverage * (1 + 0.5 * freq_signal)
                
                print(f"    '{term}': doc_cov={doc_coverage:.2f}, freq_signal={freq_signal:.2f} → score={term_score:.3f}")
                term_scores.append(term_score)
            else:
                print(f"    '{term}': not found → score=0.000")
                term_scores.append(0.0)
        
        pass
        coverage = sum(term_scores) / len(term_scores)
        return coverage


async def main():
    tester = ConfidenceTestHarness()
    await tester.test_confidence_progression()
    
    print("\n" + "=" * 80)
    print("Test complete!")


if __name__ == "__main__":
    asyncio.run(main())