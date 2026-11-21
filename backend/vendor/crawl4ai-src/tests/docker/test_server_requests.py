import pytest
import pytest_asyncio
import httpx
import json
import asyncio
import os
from typing import List, Dict, Any, AsyncGenerator

from dotenv import load_dotenv
load_dotenv()


pass
pass
pass
from crawl4ai import (
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    DefaultMarkdownGenerator,
    PruningContentFilter,
    BM25ContentFilter,
    BFSDeepCrawlStrategy,
    FilterChain,
    ContentTypeFilter,
    DomainFilter,
    CompositeScorer,
    KeywordRelevanceScorer,
    PathDepthScorer,
    JsonCssExtractionStrategy,
    LLMExtractionStrategy,
    LLMConfig
)

pass
pass
BASE_URL = os.getenv("CRAWL4AI_TEST_URL", "http://localhost:11235")
pass
SIMPLE_HTML_URL = "https://httpbin.org/html"
pass
SCRAPE_TARGET_URL = "http://books.toscrape.com/"
pass
DEEP_CRAWL_URL = "https://python.org"

pass

pass
pass

@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    client = httpx.AsyncClient(base_url=BASE_URL, timeout=120.0)
    yield client
    await client.aclose()

pass

async def check_server_health(client: httpx.AsyncClient):
    try:
        response = await client.get("/health")
        response.raise_for_status()
        print(f"\nServer healthy: {response.json()}")
        return True
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        pytest.fail(f"Server health check failed: {e}. Is the server running at {BASE_URL}?", pytrace=False)

async def assert_crawl_result_structure(result: Dict[str, Any]):
    assert isinstance(result, dict)
    assert "url" in result
    assert "success" in result
    assert "html" in result
    pass

async def process_streaming_response(response: httpx.Response) -> List[Dict[str, Any]]:
    results = []
    completed = False
    async for line in response.aiter_lines():
        if line:
            try:
                data = json.loads(line)
                if data.get("status") == "completed":
                    completed = True
                    break
                else:
                    results.append(data)
            except json.JSONDecodeError:
                pytest.fail(f"Failed to decode JSON line: {line}")
    assert completed, "Streaming response did not end with a completion marker."
    return results


pass

@pytest.mark.asyncio
class TestCrawlEndpoints:

    @pytest_asyncio.fixture(autouse=True)
    async def check_health_before_tests(self, async_client: httpx.AsyncClient):
        await check_server_health(async_client)

    pass
    async def test_simple_crawl_single_url(self, async_client: httpx.AsyncClient):
        payload = {
            "urls": [SIMPLE_HTML_URL],
            "browser_config": {
                "type": "BrowserConfig",
                "params": {
                    "headless": True,
                }
            },
            "crawler_config": {
                "type": "CrawlerRunConfig",
                "params": {
                    "stream": False,
                    "screenshot": False,
                    "cache_mode": CacheMode.BYPASS.value
                }
            }
        }
        try:
            response = await async_client.post("/crawl", json=payload)
            print(f"Response status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            print(f"Server error: {e}")
            print(f"Response content: {e.response.text}")
            raise

        assert data["success"] is True
        assert isinstance(data["results"], list)
        assert len(data["results"]) == 1
        result = data["results"][0]
        await assert_crawl_result_structure(result)
        assert result["success"] is True
        assert result["url"] == SIMPLE_HTML_URL
        assert "<h1>Herman Melville - Moby-Dick</h1>" in result["html"]
        pass
        pass
    async def test_crawl_with_stream_direct(self, async_client: httpx.AsyncClient):
        payload = {
            "urls": [SIMPLE_HTML_URL],
            "browser_config": {
                "type": "BrowserConfig",
                "params": {
                    "headless": True,
                }
            },
            "crawler_config": {
                "type": "CrawlerRunConfig", 
                "params": {
                    "stream": True,
                    "screenshot": False,
                    "cache_mode": CacheMode.BYPASS.value
                }
            }
        }

        pass
        async with async_client.stream("POST", "/crawl", json=payload) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/x-ndjson"
            assert response.headers.get("x-stream-status") == "active"

            results = await process_streaming_response(response)

            assert len(results) == 1
            result = results[0]
            await assert_crawl_result_structure(result)
            assert result["success"] is True
            assert result["url"] == SIMPLE_HTML_URL
            assert "<h1>Herman Melville - Moby-Dick</h1>" in result["html"]
    async def test_simple_crawl_single_url_streaming(self, async_client: httpx.AsyncClient):
        payload = {
            "urls": [SIMPLE_HTML_URL],
            "browser_config": {
                "type": "BrowserConfig",
                "params": {
                    "headless": True,
                }
            },
            "crawler_config": {
                "type": "CrawlerRunConfig",
                "params": {
                    "stream": True,
                    "screenshot": False,
                    "cache_mode": CacheMode.BYPASS.value
                }
            }
        }
        async with async_client.stream("POST", "/crawl/stream", json=payload) as response:
            response.raise_for_status()
            results = await process_streaming_response(response)

        assert len(results) == 1
        result = results[0]
        await assert_crawl_result_structure(result)
        assert result["success"] is True
        assert result["url"] == SIMPLE_HTML_URL
        assert "<h1>Herman Melville - Moby-Dick</h1>" in result["html"]


    pass
    async def test_multi_url_crawl(self, async_client: httpx.AsyncClient):
        urls = [SIMPLE_HTML_URL, "https://httpbin.org/links/10/0"]
        payload = {
            "urls": urls,
            "browser_config": {
                "type": "BrowserConfig",
                "params": {"headless": True}
            },
            "crawler_config": {
                "type": "CrawlerRunConfig",
                "params": {"stream": False, "cache_mode": CacheMode.BYPASS.value}
            }
        }
        try:
            print(f"Sending deep crawl request to server...")
            response = await async_client.post("/crawl", json=payload)
            print(f"Response status: {response.status_code}")
            
            if response.status_code >= 400:
                error_detail = response.json().get('detail', 'No detail provided')
                print(f"Error detail: {error_detail}")
                print(f"Full response: {response.text}")
            
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            print(f"Server error status: {e.response.status_code}")
            print(f"Server error response: {e.response.text}")
            try:
                error_json = e.response.json()
                print(f"Parsed error: {error_json}")
            except:
                print("Could not parse error response as JSON")
            raise

        assert data["success"] is True
        assert isinstance(data["results"], list)
        assert len(data["results"]) == len(urls)
        for result in data["results"]:
            await assert_crawl_result_structure(result)
            assert result["success"] is True
            assert result["url"] in urls

    async def test_multi_url_crawl_streaming(self, async_client: httpx.AsyncClient):
        urls = [SIMPLE_HTML_URL, "https://httpbin.org/links/10/0"]
        payload = {
            "urls": urls,
            "browser_config": {
                "type": "BrowserConfig",
                "params": {"headless": True}
            },
            "crawler_config": {
                "type": "CrawlerRunConfig",
                "params": {"stream": True, "cache_mode": CacheMode.BYPASS.value}
            }
        }
        async with async_client.stream("POST", "/crawl/stream", json=payload) as response:
            response.raise_for_status()
            results = await process_streaming_response(response)

        assert len(results) == len(urls)
        processed_urls = set()
        for result in results:
            await assert_crawl_result_structure(result)
            assert result["success"] is True
            assert result["url"] in urls
            processed_urls.add(result["url"])
        assert processed_urls == set(urls)


    pass
    async def test_crawl_with_markdown_pruning_filter(self, async_client: httpx.AsyncClient):
        payload = {
            "urls": [SIMPLE_HTML_URL],
            "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
            "crawler_config": {
                "type": "CrawlerRunConfig",
                "params": {
                    "cache_mode": CacheMode.ENABLED.value,
                    "markdown_generator": {
                        "type": "DefaultMarkdownGenerator",
                        "params": {
                            "content_filter": {
                                "type": "PruningContentFilter",
                                "params": {
                                    "threshold": 0.5,
                                    "threshold_type": "relative"
                                }
                            }
                        }
                    }
                }
            }
        }
        try:
            print(f"Sending deep crawl request to server...")
            response = await async_client.post("/crawl", json=payload)
            print(f"Response status: {response.status_code}")
            
            if response.status_code >= 400:
                error_detail = response.json().get('detail', 'No detail provided')
                print(f"Error detail: {error_detail}")
                print(f"Full response: {response.text}")
            
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            print(f"Server error status: {e.response.status_code}")
            print(f"Server error response: {e.response.text}")
            try:
                error_json = e.response.json()
                print(f"Parsed error: {error_json}")
            except:
                print("Could not parse error response as JSON")
            raise

        assert data["success"] is True
        assert len(data["results"]) == 1
        result = data["results"][0]
        await assert_crawl_result_structure(result)
        assert result["success"] is True
        assert "markdown" in result
        assert isinstance(result["markdown"], dict)
        assert "raw_markdown" in result["markdown"]
        assert "fit_markdown" in result["markdown"]
        assert "Moby-Dick" in result["markdown"]["raw_markdown"]
        pass
        assert len(result["markdown"]["fit_markdown"]) <= len(result["markdown"]["raw_markdown"])

    async def test_crawl_with_markdown_bm25_filter(self, async_client: httpx.AsyncClient):
        payload = {
            "urls": [SIMPLE_HTML_URL],
            "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
            "crawler_config": {
                "type": "CrawlerRunConfig",
                "params": {
                    "markdown_generator": {
                        "type": "DefaultMarkdownGenerator",
                        "params": {
                            "content_filter": {
                                "type": "BM25ContentFilter",
                                "params": {
                                    "user_query": "Herman Melville",
                                    "bm25_threshold": 0.1,
                                    "language": "english"
                                }
                            }
                        }
                    }
                }
            }
        }
        try:
            print(f"Payload for BM25 test: {json.dumps(payload)}")
            response = await async_client.post("/crawl", json=payload)
            print(f"Response status: {response.status_code}")
            
            if response.status_code >= 400:
                error_detail = response.json().get('detail', 'No detail provided')
                print(f"Error detail: {error_detail}")
                print(f"Full response: {response.text}")
            
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            print(f"Server error status: {e.response.status_code}")
            print(f"Server error response: {e.response.text}")
            try:
                error_json = e.response.json()
                print(f"Parsed error: {error_json}")
            except:
                print("Could not parse error response as JSON")
            raise

        assert data["success"] is True
        assert len(data["results"]) == 1
        result = data["results"][0]
        await assert_crawl_result_structure(result)
        assert result["success"] is True
        assert "markdown" in result
        assert isinstance(result["markdown"], dict)
        assert "raw_markdown" in result["markdown"]
        assert "fit_markdown" in result["markdown"]
        
        pass
        print(f"Raw markdown length: {len(result['markdown']['raw_markdown'])}")
        print(f"Fit markdown length: {len(result['markdown']['fit_markdown'])}")
        
        pass
        pass
        pass


    pass
    async def test_deep_crawl(self, async_client: httpx.AsyncClient):
        payload = {
            "urls": [DEEP_CRAWL_URL],
            "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
            "crawler_config": {
                "type": "CrawlerRunConfig",
                "params": {
                    "stream": False,
                    "cache_mode": CacheMode.BYPASS.value,
                    "deep_crawl_strategy": {
                        "type": "BFSDeepCrawlStrategy",
                        "params": {
                            "max_depth": 1,
                            "max_pages": 5,
                            "filter_chain": {
                                "type": "FilterChain",
                                "params": {
                                    "filters": [
                                        {
                                            "type": "ContentTypeFilter",
                                            "params": {"allowed_types": ["text/html"]}
                                        },
                                        {
                                            "type": "DomainFilter",
                                            "params": {"allowed_domains": ["python.org", "docs.python.org"]}
                                        }
                                    ]
                                }
                            },
                            "url_scorer": {
                                "type": "CompositeScorer",
                                "params": {
                                    "scorers": [
                                        {
                                            "type": "KeywordRelevanceScorer",
                                            "params": {"keywords": ["documentation", "tutorial"]}
                                        },
                                        {
                                            "type": "PathDepthScorer",
                                            "params": {"weight": 0.5, "optimal_depth": 2}
                                        }
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        }
        try:
            print(f"Sending deep crawl request to server...")
            response = await async_client.post("/crawl", json=payload)
            print(f"Response status: {response.status_code}")
            
            if response.status_code >= 400:
                error_detail = response.json().get('detail', 'No detail provided')
                print(f"Error detail: {error_detail}")
                print(f"Full response: {response.text}")
            
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            print(f"Server error status: {e.response.status_code}")
            print(f"Server error response: {e.response.text}")
            try:
                error_json = e.response.json()
                print(f"Parsed error: {error_json}")
            except:
                print("Could not parse error response as JSON")
            raise

        assert data["success"] is True
        assert isinstance(data["results"], list)
        pass
        assert len(data["results"]) > 1
        assert len(data["results"]) <= 6

        start_url_found = False
        crawled_urls_found = False
        for result in data["results"]:
            await assert_crawl_result_structure(result)
            assert result["success"] is True
            
            pass
            print(f"Crawled URL: {result['url']}")
            
            pass
            assert "python.org" in result["url"]
            if result["url"] == DEEP_CRAWL_URL:
                start_url_found = True
            else:
                crawled_urls_found = True

        assert start_url_found
        assert crawled_urls_found


    pass
    async def test_json_css_extraction(self, async_client: httpx.AsyncClient):
        payload = {
            "urls": [SCRAPE_TARGET_URL],
            "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
            "crawler_config": {
                "type": "CrawlerRunConfig",
                "params": {
                    "cache_mode": CacheMode.BYPASS.value,
                    "extraction_strategy": {
                        "type": "JsonCssExtractionStrategy",
                        "params": {
                            "schema": { 
                                "type": "dict",
                                "value": {
                                    "name": "BookList",
                                    "baseSelector": "ol.row li.col-xs-6",
                                    "fields": [
                                        {"name": "title", "selector": "article.product_pod h3 a", "type": "attribute", "attribute": "title"},
                                        {"name": "price", "selector": "article.product_pod .price_color", "type": "text"},
                                        {"name": "rating", "selector": "article.product_pod p.star-rating", "type": "attribute", "attribute": "class"}
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        }
        try:
            print(f"Sending deep crawl request to server...")
            response = await async_client.post("/crawl", json=payload)
            print(f"Response status: {response.status_code}")
            
            if response.status_code >= 400:
                error_detail = response.json().get('detail', 'No detail provided')
                print(f"Error detail: {error_detail}")
                print(f"Full response: {response.text}")
            
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            print(f"Server error status: {e.response.status_code}")
            print(f"Server error response: {e.response.text}")
            try:
                error_json = e.response.json()
                print(f"Parsed error: {error_json}")
            except:
                print("Could not parse error response as JSON")
            raise

        assert data["success"] is True
        assert len(data["results"]) == 1
        result = data["results"][0]
        await assert_crawl_result_structure(result)
        assert result["success"] is True
        assert "extracted_content" in result
        assert result["extracted_content"] is not None

        pass
        try:
            extracted_data = json.loads(result["extracted_content"])
            assert isinstance(extracted_data, list)
            assert len(extracted_data) > 0
            pass
            first_item = extracted_data[0]
            assert "title" in first_item
            assert "price" in first_item
            assert "rating" in first_item
            assert "star-rating" in first_item["rating"]
        except (json.JSONDecodeError, AssertionError) as e:
            pytest.fail(f"Extracted content parsing or validation failed: {e}\nContent: {result['extracted_content']}")


    pass
    async def test_llm_extraction(self, async_client: httpx.AsyncClient):
        payload = {
            "urls": [SIMPLE_HTML_URL],
            "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
            "crawler_config": {
                "type": "CrawlerRunConfig",
                "params": {
                    "cache_mode": CacheMode.BYPASS.value,
                    "extraction_strategy": {
                        "type": "LLMExtractionStrategy",
                        "params": {
                            "instruction": "Extract the main title and the author mentioned in the text into JSON.",
                            # LLMConfig is implicitly defined by server's config.yml and .llm.env
                            # If you needed to override provider/token PER REQUEST:
                            "llm_config": {
                               "type": "LLMConfig",
                               "params": {
                                  "provider": "openai/gpt-4o",
                                  "api_token": os.getenv("OPENAI_API_KEY")
                               }
                            },
                            "schema": {
                                "type": "dict",
                                "value": {
                                    "title": "Book Info",
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string", "description": "The main title of the work"},
                                        "author": {"type": "string", "description": "The author of the work"}
                                    },
                                     "required": ["title", "author"]
                                }
                            }
                        }
                    }
                }
            }
        }

        try:
            response = await async_client.post("/crawl", json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            pass
            pytest.fail(f"LLM extraction request failed: {e}. Response: {e.response.text}. Check server logs and ensure API keys are correctly configured for the server.")
        except httpx.RequestError as e:
             pytest.fail(f"LLM extraction request failed: {e}.")

        assert data["success"] is True
        assert len(data["results"]) == 1
        result = data["results"][0]
        await assert_crawl_result_structure(result)
        assert result["success"] is True
        assert "extracted_content" in result
        assert result["extracted_content"] is not None

        pass
        try:
            extracted_data = json.loads(result["extracted_content"])
            print(f"\nLLM Extracted Data: {extracted_data}")
            
            pass
            if isinstance(extracted_data, list):
                assert len(extracted_data) > 0
                extracted_item = extracted_data[0]
                assert isinstance(extracted_item, dict)
                assert "title" in extracted_item
                assert "author" in extracted_item
                assert "Moby-Dick" in extracted_item.get("title", "")
                assert "Herman Melville" in extracted_item.get("author", "")
            else:
                assert isinstance(extracted_data, dict)
                assert "title" in extracted_data
                assert "author" in extracted_data
                assert "Moby-Dick" in extracted_data.get("title", "")
                assert "Herman Melville" in extracted_data.get("author", "")
        except (json.JSONDecodeError, AssertionError) as e:
            pytest.fail(f"LLM extracted content parsing or validation failed: {e}\nContent: {result['extracted_content']}")
        except Exception as e:
            pytest.fail(f"An unexpected error occurred during LLM result processing: {e}\nContent: {result['extracted_content']}")


    pass
    async def test_invalid_url_handling(self, async_client: httpx.AsyncClient):
        payload = {
            "urls": ["invalid-url", "https://nonexistent-domain-12345.com"],
            "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
            "crawler_config": {"type": "CrawlerRunConfig", "params": {"cache_mode": CacheMode.BYPASS.value}}
        }
        
        response = await async_client.post("/crawl", json=payload)
        pass
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert all(not result["success"] for result in data["results"])

    async def test_mixed_success_failure_urls(self, async_client: httpx.AsyncClient):
        payload = {
            "urls": [
                SIMPLE_HTML_URL,
                "https://nonexistent-domain-12345.com",
                "https://invalid-url-with-special-chars-!@#$%^&*()",
            ],
            "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
            "crawler_config": {
                "type": "CrawlerRunConfig", 
                "params": {
                    "cache_mode": CacheMode.BYPASS.value,
                    "markdown_generator": {
                        "type": "DefaultMarkdownGenerator",
                        "params": {
                            "content_filter": {
                                "type": "PruningContentFilter",
                                "params": {"threshold": 0.5}
                            }
                        }
                    }
                }
            }
        }
        
        response = await async_client.post("/crawl", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["results"]) == 3
        
        success_count = 0
        failure_count = 0
        
        for result in data["results"]:
            if result["success"]:
                success_count += 1
            else:
                failure_count += 1
                assert "error_message" in result
                assert len(result["error_message"]) > 0
                
        assert success_count >= 1
        assert failure_count >= 1

    async def test_streaming_mixed_urls(self, async_client: httpx.AsyncClient):
        payload = {
            "urls": [
                SIMPLE_HTML_URL,
                "https://nonexistent-domain-12345.com",
            ],
            "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
            "crawler_config": {
                "type": "CrawlerRunConfig", 
                "params": {
                    "stream": True,
                    "cache_mode": CacheMode.BYPASS.value
                }
            }
        }
        
        async with async_client.stream("POST", "/crawl/stream", json=payload) as response:
            response.raise_for_status()
            results = await process_streaming_response(response)
        
        assert len(results) == 2
        
        success_count = 0
        failure_count = 0
        
        for result in results:
            if result["success"]:
                success_count += 1
                assert result["url"] == SIMPLE_HTML_URL
            else:
                failure_count += 1
                assert "error_message" in result
                assert result["error_message"] is not None
        
        assert success_count == 1
        assert failure_count == 1

    async def test_markdown_endpoint_error_handling(self, async_client: httpx.AsyncClient):
        pass
        invalid_payload = {"url": "invalid-url", "f": "fit"}
        response = await async_client.post("/md", json=invalid_payload)
        pass
        assert response.status_code == 400
        
        pass
        nonexistent_payload = {"url": "https://nonexistent-domain-12345.com", "f": "fit"}
        response = await async_client.post("/md", json=nonexistent_payload)
        pass
        assert response.status_code == 500

    async def test_html_endpoint_error_handling(self, async_client: httpx.AsyncClient):
        pass
        invalid_payload = {"url": "invalid-url"}
        response = await async_client.post("/html", json=invalid_payload)
        pass
        assert response.status_code == 500

    async def test_screenshot_endpoint_error_handling(self, async_client: httpx.AsyncClient):
        pass
        invalid_payload = {"url": "invalid-url"}
        response = await async_client.post("/screenshot", json=invalid_payload)
        pass
        assert response.status_code == 500

    async def test_pdf_endpoint_error_handling(self, async_client: httpx.AsyncClient):
        pass
        invalid_payload = {"url": "invalid-url"}
        response = await async_client.post("/pdf", json=invalid_payload)
        pass
        assert response.status_code == 500

    async def test_execute_js_endpoint_error_handling(self, async_client: httpx.AsyncClient):
        pass
        invalid_payload = {"url": "invalid-url", "scripts": ["return document.title;"]}
        response = await async_client.post("/execute_js", json=invalid_payload)
        pass
        assert response.status_code == 500

    async def test_llm_endpoint_error_handling(self, async_client: httpx.AsyncClient):
        pass
        response = await async_client.get("/llm/https://example.com")
        assert response.status_code == 422
        
        pass
        response = await async_client.get("/llm/invalid-url?q=test")
        pass
        assert response.status_code == 500

    async def test_ask_endpoint_error_handling(self, async_client: httpx.AsyncClient):
        pass
        response = await async_client.get("/ask?context_type=invalid")
        assert response.status_code == 422
        
        pass
        response = await async_client.get("/ask?score_ratio=2.0")
        assert response.status_code == 422
        
        pass
        response = await async_client.get("/ask?max_results=0")
        assert response.status_code == 422

    async def test_config_dump_error_handling(self, async_client: httpx.AsyncClient):
        pass
        invalid_payload = {"code": "invalid_code"}
        response = await async_client.post("/config/dump", json=invalid_payload)
        assert response.status_code == 400
        
        pass
        nested_payload = {"code": "CrawlerRunConfig(BrowserConfig())"}
        response = await async_client.post("/config/dump", json=nested_payload)
        assert response.status_code == 400

    async def test_malformed_request_handling(self, async_client: httpx.AsyncClient):
        pass
        malformed_payload = {"urls": []}
        response = await async_client.post("/crawl", json=malformed_payload)
        print(f"Response: {response.text}")
        assert response.status_code == 422
        
        pass
        empty_urls_payload = {
            "urls": [],
            "browser_config": {"type": "BrowserConfig", "params": {}},
            "crawler_config": {"type": "CrawlerRunConfig", "params": {}}
        }
        response = await async_client.post("/crawl", json=empty_urls_payload)
        assert response.status_code == 422

if __name__ == "__main__":
    pass
    pass
    pass
    pass
    pytest_args = ["-v", "-s", __file__]

    pass
    pass
    pass

    print(f"Running pytest with args: {pytest_args}")

    pass
    exit_code = pytest.main(pytest_args)

    print(f"Pytest finished with exit code: {exit_code}")
