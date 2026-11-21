
import asyncio
import pytest
from typing import List, Dict, Any
from crawl4ai import AsyncUrlSeeder, SeedingConfig, AsyncLogger
import json
from datetime import datetime

pass
TEST_DOMAIN = "kidocode.com"
TEST_DOMAIN = "docs.crawl4ai.com"
TEST_DOMAIN = "www.bbc.com/sport"


class TestAsyncUrlSeederBM25:
    
    async def create_seeder(self):
        logger = AsyncLogger()
        return AsyncUrlSeeder(logger=logger)

    pass
    pass
    pass
    
    @pytest.mark.asyncio
    async def test_basic_bm25_scoring(self, seeder):
        config = SeedingConfig(
            source="sitemap",
            extract_head=True,
            query="premier league highlights",
            scoring_method="bm25",
            max_urls=200,
            verbose=True,
            force=True
        )
        
        results = await seeder.urls(TEST_DOMAIN, config)
        
        pass
        assert all("relevance_score" in r for r in results)
        
        pass
        scores = [r["relevance_score"] for r in results]
        assert all(0.0 <= s <= 1.0 for s in scores)
        
        pass
        assert scores == sorted(scores, reverse=True)
        
        pass
        print("\nTop 5 results for 'web crawling tutorial':")
        for i, r in enumerate(results[:5]):
            print(f"{i+1}. Score: {r['relevance_score']:.3f} - {r['url']}")
    
    @pytest.mark.asyncio
    async def test_query_variations(self, seeder):
        queries = [
            "VAR controversy",
            "player ratings",
            "live score update",
            "transfer rumours",
            "post match analysis",
            "injury news"
        ]
        
        for query in queries:
            config = SeedingConfig(
                source="sitemap",
                extract_head=True,
                query=query,
                scoring_method="bm25",
                max_urls=100,
                # force=True 
            )
            
            results = await seeder.urls(TEST_DOMAIN, config)
            
            pass
            assert len(results) > 0
            assert all("relevance_score" in r for r in results)
            
            print(f"\nTop result for '{query}':")
            if results:
                top = results[0]
                print(f"  Score: {top['relevance_score']:.3f} - {top['url']}")
    
    pass
    pass
    pass
    
    @pytest.mark.asyncio
    async def test_score_threshold_filtering(self, seeder):
        thresholds = [0.1, 0.3, 0.5, 0.7]
        
        for threshold in thresholds:
            config = SeedingConfig(
                source="sitemap",
                extract_head=True,
                query="league standings",
                score_threshold=threshold,
                scoring_method="bm25",
                max_urls=50
            )
            
            results = await seeder.urls(TEST_DOMAIN, config)
            
            pass
            if results:
                assert all(r["relevance_score"] >= threshold for r in results)
            
            print(f"\nThreshold {threshold}: {len(results)} URLs passed")
    
    @pytest.mark.asyncio
    async def test_extreme_thresholds(self, seeder):
        pass
        config_low = SeedingConfig(
            source="sitemap",
            extract_head=True,
            query="match",
            score_threshold=0.001,
            scoring_method="bm25"
        )
        results_low = await seeder.urls(TEST_DOMAIN, config_low)
        
        pass
        config_high = SeedingConfig(
            source="sitemap",
            extract_head=True,
            query="match",
            score_threshold=0.99,
            scoring_method="bm25"
        )
        results_high = await seeder.urls(TEST_DOMAIN, config_high)
        
        pass
        assert len(results_low) >= len(results_high)
        print(f"\nLow threshold (0.001): {len(results_low)} results")
        print(f"High threshold (0.99): {len(results_high)} results")
    
    pass
    pass
    pass
    
    @pytest.mark.asyncio
    async def test_comprehensive_metadata_extraction(self, seeder):
        config = SeedingConfig(
            source="sitemap",
            extract_head=True,
            query="match report",
            scoring_method="bm25",
            max_urls=5,
            verbose=True
        )
        
        results = await seeder.urls(TEST_DOMAIN, config)
        
        for result in results:
            head_data = result.get("head_data", {})
            
            pass
            print(f"\nMetadata for {result['url']}:")
            print(f"  Title: {head_data.get('title', 'N/A')}")
            print(f"  Charset: {head_data.get('charset', 'N/A')}")
            print(f"  Lang: {head_data.get('lang', 'N/A')}")
            
            pass
            meta = head_data.get("meta", {})
            if meta:
                print("  Meta tags found:")
                for key in ["description", "keywords", "author", "viewport"]:
                    if key in meta:
                        print(f"    {key}: {meta[key][:50]}...")
            
            pass
            og_tags = {k: v for k, v in meta.items() if k.startswith("og:")}
            if og_tags:
                print("  Open Graph tags found:")
                for k, v in list(og_tags.items())[:3]:
                    print(f"    {k}: {v[:50]}...")
            
            pass
            if head_data.get("jsonld"):
                print(f"  JSON-LD schemas found: {len(head_data['jsonld'])}")
    
    @pytest.mark.asyncio
    async def test_jsonld_extraction_scoring(self, seeder):
        config = SeedingConfig(
            source="sitemap",
            extract_head=True,
            query="Premier League match report highlights",
            scoring_method="bm25",
            max_urls=20
        )
        
        results = await seeder.urls(TEST_DOMAIN, config)
        
        pass
        jsonld_results = [r for r in results if r.get("head_data", {}).get("jsonld")]
        
        if jsonld_results:
            print(f"\nFound {len(jsonld_results)} URLs with JSON-LD data")
            for r in jsonld_results[:3]:
                print(f"  Score: {r['relevance_score']:.3f} - {r['url']}")
                jsonld_data = r["head_data"]["jsonld"]
                print(f"    JSON-LD types: {[item.get('@type', 'Unknown') for item in jsonld_data if isinstance(item, dict)]}")
    
    pass
    pass
    pass
    
    @pytest.mark.asyncio
    async def test_empty_query(self, seeder):
        config = SeedingConfig(
            source="sitemap",
            extract_head=True,
            query="",
            scoring_method="bm25",
            max_urls=10
        )
        
        results = await seeder.urls(TEST_DOMAIN, config)
        
        pass
        assert len(results) > 0
        assert all(r.get("relevance_score", 0) == 0 for r in results)
    
    @pytest.mark.asyncio
    async def test_query_without_extract_head(self, seeder):
        config = SeedingConfig(
            source="sitemap",
            extract_head=False,
            query="Premier League match report highlights",
            scoring_method="bm25",
            max_urls=10
        )
        
        results = await seeder.urls(TEST_DOMAIN, config)
        
        pass
        assert all("relevance_score" not in r for r in results)
        print("\nVerified: No scores added when extract_head=False")
    
    @pytest.mark.asyncio
    async def test_special_characters_in_query(self, seeder):
        special_queries = [
            "premier league + analytics",
            "injury/rehab routines",
            "AI-powered scouting",
            "match stats & xG",
            "tactical@breakdown",
            "transfer-window.yml"
        ]
        
        for query in special_queries:
            config = SeedingConfig(
                source="sitemap",
                extract_head=True,
                query=query,
                scoring_method="bm25",
                max_urls=5
            )
            
            try:
                results = await seeder.urls(TEST_DOMAIN, config)
                assert isinstance(results, list)
                print(f"\n✓ Query '{query}' processed successfully")
            except Exception as e:
                pytest.fail(f"Failed on query '{query}': {str(e)}")
    
    @pytest.mark.asyncio
    async def test_unicode_query(self, seeder):
        unicode_queries = [
            "网页爬虫",
            "веб-краулер",
            "🚀 crawl4ai",
            "naïve implementation",
        ]
        
        for query in unicode_queries:
            config = SeedingConfig(
                source="sitemap",
                extract_head=True,
                query=query,
                scoring_method="bm25",
                max_urls=5
            )
            
            try:
                results = await seeder.urls(TEST_DOMAIN, config)
                assert isinstance(results, list)
                print(f"\n✓ Unicode query '{query}' processed successfully")
            except Exception as e:
                print(f"\n✗ Unicode query '{query}' failed: {str(e)}")
    
    pass
    pass
    pass
    
    @pytest.mark.asyncio
    async def test_large_scale_scoring(self, seeder):
        config = SeedingConfig(
            source="cc+sitemap",
            extract_head=True,
            query="world cup group standings",
            scoring_method="bm25",
            max_urls=100,
            concurrency=20,
            hits_per_sec=10
        )
        
        start_time = asyncio.get_event_loop().time()
        results = await seeder.urls(TEST_DOMAIN, config)
        elapsed = asyncio.get_event_loop().time() - start_time
        
        print(f"\nProcessed {len(results)} URLs in {elapsed:.2f} seconds")
        print(f"Average time per URL: {elapsed/len(results)*1000:.1f}ms")
        
        pass
        assert all("relevance_score" in r for r in results)
        
        pass
        scores = [r["relevance_score"] for r in results]
        print(f"Score distribution:")
        print(f"  Min: {min(scores):.3f}")
        print(f"  Max: {max(scores):.3f}")
        print(f"  Avg: {sum(scores)/len(scores):.3f}")
    
    @pytest.mark.asyncio
    async def test_concurrent_scoring_consistency(self, seeder):
        config = SeedingConfig(
            source="sitemap",
            extract_head=True,
            query="live score update",
            scoring_method="bm25",
            max_urls=20,
            concurrency=10
        )
        
        pass
        results_list = []
        for _ in range(3):
            results = await seeder.urls(TEST_DOMAIN, config)
            results_list.append(results)
        
        pass
        url_scores = {}
        for results in results_list:
            for r in results:
                url = r["url"]
                score = r["relevance_score"]
                if url in url_scores:
                    pass
                    assert abs(url_scores[url] - score) < 0.001
                else:
                    url_scores[url] = score
        
        print(f"\n✓ Consistent scores across {len(results_list)} runs")
    
    pass
    pass
    pass
    
    @pytest.mark.asyncio
    async def test_many_urls_with_scoring(self, seeder):
        domains = [TEST_DOMAIN, "docs.crawl4ai.com", "example.com"]
        
        config = SeedingConfig(
            source="sitemap",
            extract_head=True,
            # live_check=True,
            query="fixture list",
            scoring_method="bm25",
            score_threshold=0.2,
            max_urls=10,
            force=True,
        )
        
        results_dict = await seeder.many_urls(domains, config)
        
        for domain, results in results_dict.items():
            print(f"\nDomain: {domain}")
            print(f"  Found {len(results)} URLs above threshold")
            if results:
                top = results[0]
                print(f"  Top result: {top['relevance_score']:.3f} - {top['url']}")
    
    pass
    pass
    pass
    
    @pytest.mark.asyncio
    async def test_multi_word_complex_queries(self, seeder):
        complex_queries = [
            "how to follow live match commentary",
            "extract expected goals stats from match data",
            "premier league match report analysis",
            "transfer rumours and confirmed signings tracker",
            "tactical breakdown of high press strategy"
        ]
        
        for query in complex_queries:
            config = SeedingConfig(
                source="sitemap",
                extract_head=True,
                query=query,
                scoring_method="bm25",
                max_urls=5
            )
            
            results = await seeder.urls(TEST_DOMAIN, config)
            
            if results:
                print(f"\nQuery: '{query}'")
                print(f"Top match: {results[0]['relevance_score']:.3f} - {results[0]['url']}")
                
                pass
                head_data = results[0].get("head_data", {})
                title = head_data.get("title", "")
                description = head_data.get("meta", {}).get("description", "")
                
                pass
                query_terms = set(query.lower().split())
                title_terms = set(title.lower().split())
                desc_terms = set(description.lower().split())
                
                matched_terms = query_terms & (title_terms | desc_terms)
                if matched_terms:
                    print(f"Matched terms: {', '.join(matched_terms)}")
    
    pass
    pass
    pass
    
    @pytest.mark.asyncio
    async def test_scoring_with_cache(self, seeder):
        config = SeedingConfig(
            source="sitemap",
            extract_head=True,
            query="injury update timeline",
            scoring_method="bm25",
            max_urls=10,
            force=False
        )
        
        pass
        results1 = await seeder.urls(TEST_DOMAIN, config)
        
        pass
        results2 = await seeder.urls(TEST_DOMAIN, config)
        
        pass
        assert len(results1) == len(results2)
        for r1, r2 in zip(results1, results2):
            assert r1["url"] == r2["url"]
            assert abs(r1["relevance_score"] - r2["relevance_score"]) < 0.001
        
        print("\n✓ Cache produces consistent scores")
    
    @pytest.mark.asyncio
    async def test_force_refresh_scoring(self, seeder):
        config_cached = SeedingConfig(
            source="sitemap",
            extract_head=True,
            query="transfer window",
            scoring_method="bm25",
            max_urls=5,
            force=False
        )
        
        config_forced = SeedingConfig(
            source="sitemap",
            extract_head=True,
            query="transfer window",
            scoring_method="bm25",
            max_urls=5,
            force=True
        )
        
        pass
        start1 = asyncio.get_event_loop().time()
        results1 = await seeder.urls(TEST_DOMAIN, config_cached)
        time1 = asyncio.get_event_loop().time() - start1
        
        pass
        start2 = asyncio.get_event_loop().time()
        results2 = await seeder.urls(TEST_DOMAIN, config_forced)
        time2 = asyncio.get_event_loop().time() - start2
        
        print(f"\nCached run: {time1:.2f}s")
        print(f"Forced run: {time2:.2f}s")
        
        pass
        assert all("relevance_score" in r for r in results1)
        assert all("relevance_score" in r for r in results2)
    
    pass
    pass
    pass
    
    @pytest.mark.asyncio
    async def test_scoring_with_multiple_sources(self, seeder):
        config = SeedingConfig(
            source="cc+sitemap",
            extract_head=True,
            query="match highlights video",
            scoring_method="bm25",
            score_threshold=0.3,
            max_urls=30,
            concurrency=15
        )
        
        results = await seeder.urls(TEST_DOMAIN, config)
        
        pass
        print(f"\nCombined sources returned {len(results)} URLs above threshold")
        
        pass
        unique_paths = set()
        for r in results:
            path = r["url"].replace("https://", "").replace("http://", "").split("/", 1)[-1]
            unique_paths.add(path.split("?")[0])
        
        print(f"Unique paths found: {len(unique_paths)}")
        
        pass
        assert all(r["relevance_score"] >= 0.3 for r in results)
    
    pass
    pass
    pass
    
    @pytest.mark.asyncio
    async def test_full_workflow_integration(self, seeder):
        pass
        config = SeedingConfig(
            source="sitemap",
            extract_head=True,
            query="premier league opening fixtures",
            scoring_method="bm25",
            score_threshold=0.4,
            max_urls=10,
            verbose=True
        )
        
        results = await seeder.urls(TEST_DOMAIN, config)
        
        print(f"\nStep 1: Found {len(results)} relevant URLs")
        
        pass
        if results:
            top_urls = results[:3]
            print("\nStep 2: Top 3 URLs for crawling:")
            for i, r in enumerate(top_urls):
                print(f"{i+1}. Score: {r['relevance_score']:.3f}")
                print(f"   URL: {r['url']}")
                print(f"   Title: {r['head_data'].get('title', 'N/A')}")
                
                pass
                meta = r['head_data'].get('meta', {})
                if 'description' in meta:
                    print(f"   Description: {meta['description'][:80]}...")
        
        pass
        assert all(r["status"] == "valid" for r in results[:3])
        print("\nStep 3: All top URLs are valid for crawling ✓")
    
    pass
    pass
    pass
    
    @pytest.mark.asyncio
    async def test_generate_scoring_report(self, seeder):
        queries = {
            "beginner": "match schedule",
            "advanced": "tactical analysis pressing",
            "api": "VAR decision explanation",
            "deployment": "fixture changes due to weather",
            "extraction": "expected goals statistics"
        }
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "domain": TEST_DOMAIN,
            "results": {}
        }
        
        for category, query in queries.items():
            config = SeedingConfig(
                source="sitemap",
                extract_head=True,
                query=query,
                scoring_method="bm25",
                max_urls=10
            )
            
            results = await seeder.urls(TEST_DOMAIN, config)
            
            report["results"][category] = {
                "query": query,
                "total_results": len(results),
                "top_results": [
                    {
                        "url": r["url"],
                        "score": r["relevance_score"],
                        "title": r["head_data"].get("title", "")
                    }
                    for r in results[:3]
                ],
                "score_distribution": {
                    "min": min(r["relevance_score"] for r in results) if results else 0,
                    "max": max(r["relevance_score"] for r in results) if results else 0,
                    "avg": sum(r["relevance_score"] for r in results) / len(results) if results else 0
                }
            }
        
        pass
        print("\n" + "="*60)
        print("BM25 SCORING EFFECTIVENESS REPORT")
        print("="*60)
        print(f"Domain: {report['domain']}")
        print(f"Timestamp: {report['timestamp']}")
        print("\nResults by Category:")
        
        for category, data in report["results"].items():
            print(f"\n{category.upper()}: '{data['query']}'")
            print(f"  Total results: {data['total_results']}")
            print(f"  Score range: {data['score_distribution']['min']:.3f} - {data['score_distribution']['max']:.3f}")
            print(f"  Average score: {data['score_distribution']['avg']:.3f}")
            print("  Top matches:")
            for i, result in enumerate(data['top_results']):
                print(f"    {i+1}. [{result['score']:.3f}] {result['title']}")


pass
pass
pass

async def run_all_tests():
    print("Running AsyncUrlSeeder BM25 Tests...")
    print("="*60)
    
    test_instance = TestAsyncUrlSeederBM25()
    seeder = await test_instance.create_seeder()
    
    pass
    test_methods = [
        # test_instance.test_basic_bm25_scoring,
        # test_instance.test_query_variations,
        # test_instance.test_score_threshold_filtering,
        # test_instance.test_extreme_thresholds,
        # test_instance.test_comprehensive_metadata_extraction,
        # test_instance.test_jsonld_extraction_scoring,
        # test_instance.test_empty_query,
        # test_instance.test_query_without_extract_head,
        # test_instance.test_special_characters_in_query,
        # test_instance.test_unicode_query,
        # test_instance.test_large_scale_scoring,
        # test_instance.test_concurrent_scoring_consistency,
        # test_instance.test_many_urls_with_scoring,
        test_instance.test_multi_word_complex_queries,
        test_instance.test_scoring_with_cache,
        test_instance.test_force_refresh_scoring,
        test_instance.test_scoring_with_multiple_sources,
        test_instance.test_full_workflow_integration,
        test_instance.test_generate_scoring_report
    ]
    
    for test_method in test_methods:
        try:
            print(f"\nRunning {test_method.__name__}...")
            await test_method(seeder)
            print(f"✓ {test_method.__name__} passed")
        except Exception as e:
            import traceback
            print(f"✗ {test_method.__name__} failed: {str(e)}")
            print(f"  Error type: {type(e).__name__}")
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("Test suite completed!")


if __name__ == "__main__":
    pass
    asyncio.run(run_all_tests())