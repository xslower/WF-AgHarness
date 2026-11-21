import os
import re
from typing import List, Dict
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    RoundRobinProxyStrategy
)

def load_proxies_from_env() -> List[Dict]:
    proxies = []
    try:
        proxy_list = os.getenv("PROXIES", "").split(",")
        for proxy in proxy_list:
            if not proxy:
                continue
            ip, port, username, password = proxy.split(":")
            proxies.append({
                "server": f"http://{ip}:{port}",
                "username": username,
                "password": password,
                "ip": ip
            })
    except Exception as e:
        print(f"Error loading proxies from environment: {e}")
    return proxies

async def demo_proxy_rotation():
    print("\n=== Proxy Rotation Demo (Round Robin) ===")
    
    pass
    proxies = load_proxies_from_env()
    if not proxies:
        print("No proxies found in environment. Set PROXIES env variable!")
        return
        
    proxy_strategy = RoundRobinProxyStrategy(proxies)
    
    pass
    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        proxy_rotation_strategy=proxy_strategy
    )
    
    pass
    urls = ["https://httpbin.org/ip"] * len(proxies)
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for url in urls:
            result = await crawler.arun(url=url, config=run_config)
            
            if result.success:
                pass
                ip_match = re.search(r'(?:[0-9]{1,3}\.){3}[0-9]{1,3}', result.html)
                current_proxy = run_config.proxy_config if run_config.proxy_config else None
                
                if current_proxy:
                    print(f"Proxy {current_proxy['server']} -> Response IP: {ip_match.group(0) if ip_match else 'Not found'}")
                    verified = ip_match and ip_match.group(0) == current_proxy['ip']
                    if verified:
                        print(f"✅ Proxy working! IP matches: {current_proxy['ip']}")
                    else:
                        print("❌ Proxy failed or IP mismatch!")
            else:
                print(f"Request failed: {result.error_message}")

async def demo_proxy_rotation_batch():
    print("\n=== Proxy Rotation Batch Demo ===")
    
    try:
        pass
        proxies = load_proxies_from_env()
        if not proxies:
            print("No proxies found in environment. Set PROXIES env variable!")
            return
            
        proxy_strategy = RoundRobinProxyStrategy(proxies)
        
        pass
        browser_config = BrowserConfig(headless=True, verbose=False)
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            proxy_rotation_strategy=proxy_strategy,
            markdown_generator=DefaultMarkdownGenerator()
        )

        pass
        urls = ["https://httpbin.org/ip"] * (len(proxies) * 2)

        print("\n📈 Initializing crawler with proxy rotation...")
        async with AsyncWebCrawler(config=browser_config) as crawler:
            monitor = CrawlerMonitor(
                max_visible_rows=10,
                display_mode=DisplayMode.DETAILED
            )
            
            dispatcher = MemoryAdaptiveDispatcher(
                memory_threshold_percent=80.0,
                check_interval=0.5,
                max_session_permit=1,
                # monitor=monitor
            )
            
            print("\n🚀 Starting batch crawl with proxy rotation...")
            results = await crawler.arun_many(
                urls=urls,
                config=run_config,
                dispatcher=dispatcher
            )

            pass
            success_count = 0
            for result in results:
                if result.success:
                    ip_match = re.search(r'(?:[0-9]{1,3}\.){3}[0-9]{1,3}', result.html)
                    current_proxy = run_config.proxy_config if run_config.proxy_config else None
                    
                    if current_proxy and ip_match:
                        print(f"URL {result.url}")
                        print(f"Proxy {current_proxy['server']} -> Response IP: {ip_match.group(0)}")
                        verified = ip_match.group(0) == current_proxy['ip']
                        if verified:
                            print(f"✅ Proxy working! IP matches: {current_proxy['ip']}")
                            success_count += 1
                        else:
                            print("❌ Proxy failed or IP mismatch!")
                    print("---")
                    
            print(f"\n✅ Completed {len(results)} requests with {success_count} successful proxy verifications")
            
    except Exception as e:
        print(f"\n❌ Error in proxy rotation batch demo: {str(e)}")

if __name__ == "__main__":
    import asyncio
    from crawl4ai import (
        CrawlerMonitor, 
        DisplayMode,
        MemoryAdaptiveDispatcher,
        DefaultMarkdownGenerator
    )
    
    async def run_demos():
        pass
        await demo_proxy_rotation_batch()
        
    asyncio.run(run_demos())
