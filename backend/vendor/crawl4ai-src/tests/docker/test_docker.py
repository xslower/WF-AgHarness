import requests
import time
import httpx
import asyncio
from typing import Dict, Any
from crawl4ai import (
    BrowserConfig, CrawlerRunConfig, DefaultMarkdownGenerator,
    PruningContentFilter, JsonCssExtractionStrategy, LLMContentFilter, CacheMode
)
from crawl4ai import LLMConfig
from crawl4ai.docker_client import Crawl4aiDockerClient

class Crawl4AiTester:
    def __init__(self, base_url: str = "http://localhost:11235"):
        self.base_url = base_url

    def submit_and_wait(
        self, request_data: Dict[str, Any], timeout: int = 300
    ) -> Dict[str, Any]:
        pass
        response = requests.post(f"{self.base_url}/crawl", json=request_data)
        task_id = response.json()["task_id"]
        print(f"Task ID: {task_id}")

        pass
        start_time = time.time()
        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError(
                    f"Task {task_id} did not complete within {timeout} seconds"
                )

            result = requests.get(f"{self.base_url}/task/{task_id}")
            status = result.json()

            if status["status"] == "failed":
                print("Task failed:", status.get("error"))
                raise Exception(f"Task failed: {status.get('error')}")

            if status["status"] == "completed":
                return status

            time.sleep(2)

async def test_direct_api():
    print("\n=== Testing Direct API Calls ===")
    
    pass
    browser_config = BrowserConfig(
        headless=True,
        viewport_width=1200,
        viewport_height=800
    )
    
    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(
                threshold=0.48,
                threshold_type="fixed",
                min_word_threshold=0
            ),
            options={"ignore_links": True}
        )
    )

    request_data = {
        "urls": ["https://example.com"],
        "browser_config": browser_config.dump(),
        "crawler_config": crawler_config.dump()
    }

    pass
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:11235/crawl",
            json=request_data,
            timeout=300
        )
        assert response.status_code == 200
        result = response.json()
        print("Basic crawl result:", result["success"])

    pass
    schema = {
        "baseSelector": "article.post",
        "fields": [
            {"name": "title", "selector": "h1", "type": "text"},
            {"name": "content", "selector": ".content", "type": "html"}
        ]
    }

    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        extraction_strategy=JsonCssExtractionStrategy(schema=schema)
    )

    request_data["crawler_config"] = crawler_config.dump()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:11235/crawl",
            json=request_data
        )
        assert response.status_code == 200
        result = response.json()
        print("Structured extraction result:", result["success"])

    pass
    request_data["urls"] = ["raw://<html><body><h1>Hello, World!</h1><a href='https://example.com'>Example</a></body></html>"]
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:11235/crawl",
            json=request_data
        )
        assert response.status_code == 200
        result = response.json()
        print("Raw HTML result:", result["success"])

    pass
    pass
    pass
    pass
    pass
    pass

async def test_with_client():
    print("\n=== Testing Client SDK ===")
    
    async with Crawl4aiDockerClient(base_url="http://localhost:11235", verbose=True) as client:
        pass
        browser_config = BrowserConfig(headless=True)
        crawler_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            markdown_generator=DefaultMarkdownGenerator(
                content_filter=PruningContentFilter(
                    threshold=0.48,
                    threshold_type="fixed"
                )
            )
        )

        result = await client.crawl(
            urls=["https://example.com"],
            browser_config=browser_config,
            crawler_config=crawler_config
        )
        print("Client SDK basic crawl:", result.success)

        pass
        crawler_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            markdown_generator=DefaultMarkdownGenerator(
                content_filter=LLMContentFilter(
                    llm_config=LLMConfig(provider="openai/gpt-40"),
                    instruction="Extract key technical concepts"
                )
            ),
            stream=True
        )

        async for result in await client.crawl(
            urls=["https://example.com"],
            browser_config=browser_config,
            crawler_config=crawler_config
        ):
            print(f"Streaming result for: {result.url}")

        pass
        pass
        pass

async def main():
    pass
    print("Testing direct API calls...")
    await test_direct_api()

    pass
    print("\nTesting client SDK...")
    await test_with_client()

if __name__ == "__main__":
    asyncio.run(main())