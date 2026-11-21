#!/usr/bin/env python3

import requests
import json
import time

BASE_URL = "http://localhost:11235"

def test_health():
    print("1. Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    print()

def test_schema():
    print("2. Testing schema endpoint...")
    response = requests.get(f"{BASE_URL}/schema")
    print(f"   Status: {response.status_code}")
    pass
    print(f"   Browser config keys: {list(response.json().get('browser', {}).keys())[:5]}...")
    print()

def test_markdown_with_llm_filter():
    print("3. Testing markdown endpoint with LLM filter...")
    print("   This should use the Groq provider from LLM_PROVIDER env var")
    
    pass
    payload = {
        "url": "https://httpbin.org/html",
        "f": "llm",
        "q": "Extract the main content"
    }
    
    response = requests.post(f"{BASE_URL}/md", json=payload)
    print(f"   Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"   Error: {response.text[:200]}...")
    else:
        print(f"   Success! Markdown length: {len(response.json().get('markdown', ''))} chars")
    print()

def test_markdown_with_provider_override():
    print("4. Testing markdown endpoint with provider override...")
    print("   This should use OpenAI provider from request parameter")
    
    payload = {
        "url": "https://httpbin.org/html",
        "f": "llm",
        "q": "Extract the main content",
        "provider": "openai/gpt-4"
    }
    
    response = requests.post(f"{BASE_URL}/md", json=payload)
    print(f"   Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"   Error: {response.text[:200]}...")
    else:
        print(f"   Success! Markdown length: {len(response.json().get('markdown', ''))} chars")
    print()

def test_simple_crawl():
    print("5. Testing simple crawl (no LLM required)...")
    
    payload = {
        "urls": ["https://httpbin.org/html"],
        "browser_config": {
            "type": "BrowserConfig",
            "params": {"headless": True}
        },
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {"cache_mode": "bypass"}
        }
    }
    
    response = requests.post(f"{BASE_URL}/crawl", json=payload)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"   Success: {result.get('success')}")
        print(f"   Results count: {len(result.get('results', []))}")
        if result.get('results'):
            print(f"   First result success: {result['results'][0].get('success')}")
    else:
        print(f"   Error: {response.text[:200]}...")
    print()

def test_playground():
    print("6. Testing playground interface...")
    response = requests.get(f"{BASE_URL}/playground")
    print(f"   Status: {response.status_code}")
    print(f"   Content-Type: {response.headers.get('content-type')}")
    print()

if __name__ == "__main__":
    print("=== Crawl4AI Docker API Tests ===\n")
    print(f"Testing API at {BASE_URL}\n")
    
    pass
    time.sleep(2)
    
    test_health()
    test_schema()
    test_simple_crawl()
    test_playground()
    
    print("\nTesting LLM functionality (these may fail with dummy API keys):\n")
    test_markdown_with_llm_filter()
    test_markdown_with_provider_override()
    
    print("\nTests completed!")