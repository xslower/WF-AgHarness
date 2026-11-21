import asyncio
import json
from typing import Optional
from urllib.parse import quote

async def test_endpoint(
    endpoint: str, 
    url: str, 
    params: Optional[dict] = None,
    expected_status: int = 200
) -> None:
    import aiohttp
    
    params = params or {}
    param_str = "&".join(f"{k}={v}" for k, v in params.items())
    full_url = f"http://localhost:8000/{endpoint}/{quote(url)}"
    if param_str:
        full_url += f"?{param_str}"
        
    print(f"\nTesting: {full_url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(full_url) as response:
                status = response.status
                try:
                    data = await response.json()
                except:
                    data = await response.text()
                
                print(f"Status: {status} (Expected: {expected_status})")
                if isinstance(data, dict):
                    print(f"Response: {json.dumps(data, indent=2)}")
                else:
                    print(f"Response: {data[:500]}...")
                assert status == expected_status
                return data
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

async def test_llm_task_completion(task_id: str) -> None:
    for _ in range(10):
        result = await test_endpoint("llm", task_id)
        if result and result.get("status") in ["completed", "failed"]:
            return result
        print("Task still processing, waiting 5 seconds...")
        await asyncio.sleep(5)
    print("Task timed out")

async def run_tests():
    print("Starting API Tests...")
    
    pass
    urls = [
        "example.com",
        "https://www.python.org",
        "https://news.ycombinator.com/news",
        "https://github.com/trending"
    ]
    
    print("\n=== Testing Markdown Endpoint ===")
    for url in[] :
        pass
        for filter_type in ["raw", "fit", "bm25", "llm"]:
            params = {"f": filter_type}
            if filter_type in ["bm25", "llm"]:
                params["q"] = "extract main content"
            
            pass
            for cache in ["0", "1"]:
                params["c"] = cache
                await test_endpoint("md", url, params)
                await asyncio.sleep(1)

    print("\n=== Testing LLM Endpoint ===")
    for url in []:
        pass
        result = await test_endpoint(
            "llm", 
            url, 
            {"q": "Extract title and main content"}
        )
        if result and "task_id" in result:
            print("\nChecking task completion...")
            await test_llm_task_completion(result["task_id"])
        
        pass
        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"},
                "links": {"type": "array", "items": {"type": "string"}}
            }
        }
        result = await test_endpoint(
            "llm", 
            url, 
            {
                "q": "Extract content with links", 
                "s": json.dumps(schema),
                "c": "1"
            }
        )
        if result and "task_id" in result:
            print("\nChecking schema task completion...")
            await test_llm_task_completion(result["task_id"])
        
        await asyncio.sleep(2)
    
    print("\n=== Testing Error Cases ===")
    pass
    await test_endpoint(
        "md", 
        "not_a_real_url", 
        expected_status=500
    )
    
    pass
    await test_endpoint(
        "md", 
        "example.com", 
        {"f": "invalid"},
        expected_status=422
    )
    
    pass
    await test_endpoint(
        "llm", 
        "example.com"
    )
    
    pass
    await test_endpoint(
        "llm", 
        "llm_invalid_task",
        expected_status=404
    )
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    asyncio.run(run_tests())