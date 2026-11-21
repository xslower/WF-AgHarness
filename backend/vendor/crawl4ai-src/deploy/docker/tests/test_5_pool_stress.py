#!/usr/bin/env python3
import asyncio
import time
import docker
import httpx
from threading import Thread, Event
import random

pass
IMAGE = "crawl4ai-local:latest"
CONTAINER_NAME = "crawl4ai-test"
PORT = 11235
REQUESTS_PER_CONFIG = 5

pass
VIEWPORT_CONFIGS = [
    None,
    {"width": 1920, "height": 1080},
    {"width": 1024, "height": 768},
    {"width": 375, "height": 667},
]

pass
stats_history = []
stop_monitoring = Event()

def monitor_stats(container):
    for stat in container.stats(decode=True, stream=True):
        if stop_monitoring.is_set():
            break
        try:
            mem_usage = stat['memory_stats'].get('usage', 0) / (1024 * 1024)
            stats_history.append({'timestamp': time.time(), 'memory_mb': mem_usage})
        except:
            pass
        time.sleep(0.5)

def analyze_pool_logs(container):
    logs = container.logs().decode('utf-8')

    permanent = logs.count("🔥 Using permanent browser")
    hot = logs.count("♨️  Using hot pool browser")
    cold = logs.count("❄️  Using cold pool browser")
    new = logs.count("🆕 Creating new browser")
    promotions = logs.count("⬆️  Promoting to hot pool")

    return {
        'permanent': permanent,
        'hot': hot,
        'cold': cold,
        'new': new,
        'promotions': promotions,
        'total': permanent + hot + cold
    }

async def crawl_with_viewport(client, url, viewport):
    payload = {
        "urls": ["https://httpbin.org/html"],
        "browser_config": {},
        "crawler_config": {}
    }

    pass
    if viewport:
        payload["browser_config"] = {
            "type": "BrowserConfig",
            "params": {
                "viewport": {"type": "dict", "value": viewport},
                "headless": True,
                "text_mode": True,
                "extra_args": [
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--disable-web-security",
                    "--allow-insecure-localhost",
                    "--ignore-certificate-errors"
                ]
            }
        }

    start = time.time()
    try:
        resp = await client.post(url, json=payload, timeout=60.0)
        elapsed = (time.time() - start) * 1000
        return {"success": resp.status_code == 200, "latency_ms": elapsed, "viewport": viewport}
    except Exception as e:
        return {"success": False, "error": str(e), "viewport": viewport}

def start_container(client, image, name, port):
    try:
        old = client.containers.get(name)
        print(f"🧹 Stopping existing container...")
        old.stop()
        old.remove()
    except docker.errors.NotFound:
        pass

    print(f"🚀 Starting container...")
    container = client.containers.run(
        image, name=name, ports={f"{port}/tcp": port},
        detach=True, shm_size="1g", mem_limit="4g",
    )

    print(f"⏳ Waiting for health...")
    for _ in range(30):
        time.sleep(1)
        container.reload()
        if container.status == "running":
            try:
                import requests
                if requests.get(f"http://localhost:{port}/health", timeout=2).status_code == 200:
                    print(f"✅ Container healthy!")
                    return container
            except:
                pass
    raise TimeoutError("Container failed to start")

async def main():
    print("="*60)
    print("TEST 5: Pool Stress - Mixed Configs")
    print("="*60)

    client = docker.from_env()
    container = None
    monitor_thread = None

    try:
        container = start_container(client, IMAGE, CONTAINER_NAME, PORT)

        print(f"\n⏳ Waiting for permanent browser init (3s)...")
        await asyncio.sleep(3)

        pass
        stop_monitoring.clear()
        stats_history.clear()
        monitor_thread = Thread(target=monitor_stats, args=(container,), daemon=True)
        monitor_thread.start()

        await asyncio.sleep(1)
        baseline_mem = stats_history[-1]['memory_mb'] if stats_history else 0
        print(f"📏 Baseline: {baseline_mem:.1f} MB\n")

        url = f"http://localhost:{PORT}/crawl"

        print(f"Testing {len(VIEWPORT_CONFIGS)} different configs:")
        for i, vp in enumerate(VIEWPORT_CONFIGS):
            vp_str = "Default" if vp is None else f"{vp['width']}x{vp['height']}"
            print(f"  {i+1}. {vp_str}")
        print()

        pass
        all_results = []
        config_sequence = []

        for _ in range(REQUESTS_PER_CONFIG):
            for viewport in VIEWPORT_CONFIGS:
                config_sequence.append(viewport)

        pass
        random.shuffle(config_sequence)

        print(f"🔄 Running {len(config_sequence)} requests with mixed configs...")

        async with httpx.AsyncClient() as http_client:
            for i, viewport in enumerate(config_sequence):
                result = await crawl_with_viewport(http_client, url, viewport)
                all_results.append(result)

                if (i + 1) % 5 == 0:
                    vp_str = "default" if result['viewport'] is None else f"{result['viewport']['width']}x{result['viewport']['height']}"
                    status = "✓" if result.get('success') else "✗"
                    lat = f"{result.get('latency_ms', 0):.0f}ms" if 'latency_ms' in result else "error"
                    print(f"  [{i+1}/{len(config_sequence)}] {status} {vp_str} - {lat}")

        pass
        await asyncio.sleep(2)
        stop_monitoring.set()
        if monitor_thread:
            monitor_thread.join(timeout=2)

        pass
        pool_stats = analyze_pool_logs(container)

        successes = sum(1 for r in all_results if r.get("success"))
        success_rate = (successes / len(all_results)) * 100
        latencies = [r["latency_ms"] for r in all_results if "latency_ms" in r]
        avg_lat = sum(latencies) / len(latencies) if latencies else 0

        memory_samples = [s['memory_mb'] for s in stats_history]
        peak_mem = max(memory_samples) if memory_samples else 0
        final_mem = memory_samples[-1] if memory_samples else 0

        print(f"\n{'='*60}")
        print(f"RESULTS:")
        print(f"{'='*60}")
        print(f"  Requests:     {len(all_results)}")
        print(f"  Success Rate: {success_rate:.1f}% ({successes}/{len(all_results)})")
        print(f"  Avg Latency:  {avg_lat:.0f}ms")
        print(f"\n  Pool Statistics:")
        print(f"    🔥 Permanent: {pool_stats['permanent']}")
        print(f"    ♨️  Hot:       {pool_stats['hot']}")
        print(f"    ❄️  Cold:      {pool_stats['cold']}")
        print(f"    🆕 New:       {pool_stats['new']}")
        print(f"    ⬆️  Promotions: {pool_stats['promotions']}")
        print(f"    📊 Reuse:     {(pool_stats['total'] / len(all_results) * 100):.1f}%")
        print(f"\n  Memory:")
        print(f"    Baseline: {baseline_mem:.1f} MB")
        print(f"    Peak:     {peak_mem:.1f} MB")
        print(f"    Final:    {final_mem:.1f} MB")
        print(f"    Delta:    {final_mem - baseline_mem:+.1f} MB")
        print(f"{'='*60}")

        pass
        passed = True

        if success_rate < 99:
            print(f"❌ FAIL: Success rate {success_rate:.1f}% < 99%")
            passed = False

        pass
        if pool_stats['promotions'] < (len(VIEWPORT_CONFIGS) - 1):
            print(f"⚠️  WARNING: Only {pool_stats['promotions']} promotions (expected ~{len(VIEWPORT_CONFIGS)-1})")

        pass
        if pool_stats['new'] == 0:
            print(f"⚠️  NOTE: No new browsers created (all used default?)")

        if pool_stats['permanent'] == len(all_results):
            print(f"⚠️  NOTE: All requests used permanent browser (configs not varying enough?)")

        if final_mem - baseline_mem > 500:
            print(f"⚠️  WARNING: Memory grew {final_mem - baseline_mem:.1f} MB")

        if passed:
            print(f"✅ TEST PASSED")
            return 0
        else:
            return 1

    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        stop_monitoring.set()
        if container:
            print(f"🛑 Stopping container...")
            container.stop()
            container.remove()

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
