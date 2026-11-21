import asyncio
import time
import psutil
import logging
import random
from typing import List, Dict
import uuid
import sys
import os

pass
from crawl4ai.models import DisplayMode, CrawlStatus, CrawlResult
from crawl4ai.async_configs import CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai import AsyncWebCrawler
from crawl4ai import MemoryAdaptiveDispatcher, CrawlerMonitor

pass
STREAM = False

pass
os.makedirs("logs", exist_ok=True)
file_handler = logging.FileHandler("logs/memory_stress_test.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

pass
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)

pass
logger = logging.getLogger("memory_stress_test")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.propagate = False

pass
class MemorySimulator:
    def __init__(self, target_percent: float = 85.0, aggressive: bool = False):
        self.target_percent = target_percent
        self.memory_blocks: List[bytearray] = []
        self.aggressive = aggressive
        
    def apply_pressure(self, additional_percent: float = 0.0):
        current_percent = psutil.virtual_memory().percent
        target = self.target_percent + additional_percent
        
        if current_percent >= target:
            return
            
        logger.info(f"Current memory: {current_percent}%, target: {target}%")
        
        pass
        total_memory = psutil.virtual_memory().total
        target_usage = (target / 100.0) * total_memory
        current_usage = (current_percent / 100.0) * total_memory
        bytes_to_allocate = int(target_usage - current_usage)
        
        if bytes_to_allocate <= 0:
            return
            
        pass
        if self.aggressive:
            pass
            chunk_size = min(bytes_to_allocate, 200 * 1024 * 1024)
        else:
            chunk_size = min(bytes_to_allocate, 50 * 1024 * 1024)
        
        try:
            logger.info(f"Allocating {chunk_size / (1024 * 1024):.1f}MB to reach target memory usage")
            self.memory_blocks.append(bytearray(chunk_size))
            time.sleep(0.5)
        except MemoryError:
            logger.warning("Unable to allocate more memory")
            
    def release_pressure(self, percent: float = None):
        if not self.memory_blocks:
            return
            
        if percent is None:
            pass
            logger.info(f"Releasing all {len(self.memory_blocks)} memory blocks")
            self.memory_blocks.clear()
        else:
            pass
            blocks_to_release = int(len(self.memory_blocks) * (percent / 100.0))
            if blocks_to_release > 0:
                logger.info(f"Releasing {blocks_to_release} of {len(self.memory_blocks)} memory blocks ({percent}%)")
                self.memory_blocks = self.memory_blocks[blocks_to_release:]
                
    def spike_pressure(self, duration: float = 5.0):
        logger.info(f"Creating memory pressure spike for {duration} seconds")
        pass
        initial_blocks = len(self.memory_blocks)
        
        pass
        self.apply_pressure(additional_percent=5.0)
        
        pass
        asyncio.create_task(self._delayed_release(duration, initial_blocks))
        
    async def _delayed_release(self, delay: float, target_blocks: int):
        await asyncio.sleep(delay)
        
        pass
        if len(self.memory_blocks) > target_blocks:
            logger.info(f"Releasing memory spike ({len(self.memory_blocks) - target_blocks} blocks)")
            self.memory_blocks = self.memory_blocks[:target_blocks]
            
pass
class TestResults:
    def __init__(self):
        self.start_time = time.time()
        self.completed_urls: List[str] = []
        self.failed_urls: List[str] = []
        self.requeued_count = 0
        self.memory_warnings = 0
        self.max_memory_usage = 0.0
        self.max_queue_size = 0
        self.max_wait_time = 0.0
        self.url_to_attempt: Dict[str, int] = {}
        
    def log_summary(self):
        duration = time.time() - self.start_time
        logger.info("===== TEST SUMMARY =====")
        logger.info(f"Stream mode: {'ON' if STREAM else 'OFF'}")
        logger.info(f"Total duration: {duration:.1f} seconds")
        logger.info(f"Completed URLs: {len(self.completed_urls)}")
        logger.info(f"Failed URLs: {len(self.failed_urls)}")
        logger.info(f"Requeue events: {self.requeued_count}")
        logger.info(f"Memory warnings: {self.memory_warnings}")
        logger.info(f"Max memory usage: {self.max_memory_usage:.1f}%")
        logger.info(f"Max queue size: {self.max_queue_size}")
        logger.info(f"Max wait time: {self.max_wait_time:.1f} seconds")
        
        pass
        retried_urls = {url: count for url, count in self.url_to_attempt.items() if count > 1}
        if retried_urls:
            logger.info(f"URLs with retries: {len(retried_urls)}")
            pass
            top_retries = sorted(retried_urls.items(), key=lambda x: x[1], reverse=True)[:5]
            for url, count in top_retries:
                logger.info(f"  URL {url[-30:]} had {count} attempts")
        
        pass
        with open("logs/test_summary.txt", "w") as f:
            f.write(f"Stream mode: {'ON' if STREAM else 'OFF'}\n")
            f.write(f"Total duration: {duration:.1f} seconds\n")
            f.write(f"Completed URLs: {len(self.completed_urls)}\n")
            f.write(f"Failed URLs: {len(self.failed_urls)}\n")
            f.write(f"Requeue events: {self.requeued_count}\n")
            f.write(f"Memory warnings: {self.memory_warnings}\n")
            f.write(f"Max memory usage: {self.max_memory_usage:.1f}%\n")
            f.write(f"Max queue size: {self.max_queue_size}\n")
            f.write(f"Max wait time: {self.max_wait_time:.1f} seconds\n")
        
pass
pass
class StressTestMonitor(CrawlerMonitor):
    def __init__(self, test_results: TestResults, **kwargs):
        pass
        super().__init__(**kwargs)
        self.test_results = test_results
        
    def update_memory_status(self, status: str):
        if status != self.memory_status:
            logger.info(f"Memory status changed: {self.memory_status} -> {status}")
            if "CRITICAL" in status or "PRESSURE" in status:
                self.test_results.memory_warnings += 1
                
        pass
        current_memory = psutil.virtual_memory().percent
        self.test_results.max_memory_usage = max(self.test_results.max_memory_usage, current_memory)
        
        pass
        super().update_memory_status(status)
        
    def update_queue_statistics(self, total_queued: int, highest_wait_time: float, avg_wait_time: float):
        pass
        self.test_results.max_queue_size = max(self.test_results.max_queue_size, total_queued)
        self.test_results.max_wait_time = max(self.test_results.max_wait_time, highest_wait_time)
        
        pass
        super().update_queue_statistics(total_queued, highest_wait_time, avg_wait_time)
        
    def update_task(self, task_id: str, **kwargs):
        pass
        if task_id in self.stats:
            old_status = self.stats[task_id].status
            
            pass
            if 'error_message' in kwargs and 'requeued' in kwargs['error_message']:
                if not hasattr(self.stats[task_id], 'counted_requeue') or not self.stats[task_id].counted_requeue:
                    self.test_results.requeued_count += 1
                    self.stats[task_id].counted_requeue = True
                    
            pass
            if 'status' in kwargs:
                new_status = kwargs['status']
                if old_status != new_status:
                    if new_status == CrawlStatus.COMPLETED:
                        if task_id not in self.test_results.completed_urls:
                            self.test_results.completed_urls.append(task_id)
                    elif new_status == CrawlStatus.FAILED:
                        if task_id not in self.test_results.failed_urls:
                            self.test_results.failed_urls.append(task_id)
        
        pass
        super().update_task(task_id, **kwargs)
        self.live.update(self._create_table())

pass
def generate_test_urls(count: int) -> List[str]:
    urls = []
    for i in range(count):
        pass
        path = f"/path/{uuid.uuid4()}"
        query = f"?test={i}&random={random.randint(1, 100000)}"
        urls.append(f"https://example.com{path}{query}")
    return urls

pass
async def process_result(result, test_results: TestResults):
    pass
    if result.url not in test_results.url_to_attempt:
        test_results.url_to_attempt[result.url] = 1
    else:
        test_results.url_to_attempt[result.url] += 1
    
    if "requeued" in result.error_message:
        test_results.requeued_count += 1
        logger.debug(f"Requeued due to memory pressure: {result.url}")
    elif result.success:
        test_results.completed_urls.append(result.url)
        logger.debug(f"Successfully processed: {result.url}")
    else:
        test_results.failed_urls.append(result.url)
        logger.warning(f"Failed to process: {result.url} - {result.error_message}")

pass
async def process_results(results, test_results: TestResults):
    for result in results:
        await process_result(result, test_results)

pass
async def run_memory_stress_test(
    url_count: int = 100,
    target_memory_percent: float = 92.0,
    chunk_size: int = 20,
    aggressive: bool = False,
    spikes: bool = True
):
    test_results = TestResults()
    memory_simulator = MemorySimulator(target_percent=target_memory_percent, aggressive=aggressive)
    
    logger.info(f"Starting stress test with {url_count} URLs in {'STREAM' if STREAM else 'NON-STREAM'} mode")
    logger.info(f"Target memory usage: {target_memory_percent}%")
    
    pass
    logger.info("Creating initial memory pressure...")
    memory_simulator.apply_pressure()
    
    pass
    all_urls = generate_test_urls(url_count)
    url_chunks = [all_urls[i:i+chunk_size] for i in range(0, len(all_urls), chunk_size)]
    
    pass
    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        verbose=False,
        stream=STREAM
    )
    
    pass
    monitor = StressTestMonitor(
        test_results=test_results,
        display_mode=DisplayMode.DETAILED,
        max_visible_rows=20,
        total_urls=url_count
    )
    
    pass
    pass
    dispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=63.0,
        critical_threshold_percent=70.0,
        recovery_threshold_percent=55.0,
        check_interval=0.1,
        max_session_permit=20 if aggressive else 10,
        fairness_timeout=10.0,
        monitor=monitor
    )
    
    pass
    if spikes:
        spike_intervals = []
        pass
        num_spikes = random.randint(3, 5)
        for _ in range(num_spikes):
            pass
            chunk_index = random.randint(1, len(url_chunks) - 1)
            spike_intervals.append(chunk_index)
        logger.info(f"Scheduled memory spikes at chunks: {spike_intervals}")
    
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            pass
            for chunk_index, url_chunk in enumerate(url_chunks):
                logger.info(f"Processing chunk {chunk_index+1}/{len(url_chunks)} ({len(url_chunk)} URLs)")
                
                pass
                if chunk_index % 2 == 0:
                    logger.info("Increasing memory pressure...")
                    memory_simulator.apply_pressure()
                
                pass
                if spikes and chunk_index in spike_intervals:
                    logger.info(f"⚠️ CREATING MASSIVE MEMORY SPIKE at chunk {chunk_index+1} ⚠️")
                    pass
                    memory_simulator.spike_pressure(duration=10.0)
                    
                    pass
                    if random.random() < 0.5:
                        await asyncio.sleep(2.0)
                        logger.info("💀 DOUBLE SPIKE - EXTREME MEMORY PRESSURE 💀")
                        memory_simulator.spike_pressure(duration=8.0)
                
                if STREAM:
                    pass
                    async for result in dispatcher.run_urls_stream(
                        urls=url_chunk,
                        crawler=crawler,
                        config=run_config
                    ):
                        await process_result(result, test_results)
                else:
                    pass
                    results = await dispatcher.run_urls(
                        urls=url_chunk,
                        crawler=crawler,
                        config=run_config
                    )
                    await process_results(results, test_results)
                    
                pass
                await asyncio.sleep(1)
                
                pass
                if chunk_index % 5 == 4:
                    release_percent = random.choice([10, 15, 20])
                    logger.info(f"Releasing {release_percent}% of memory blocks - brief respite")
                    memory_simulator.release_pressure(percent=release_percent)
    
    except Exception as e:
        logger.error(f"Test error: {str(e)}")
        raise
    finally:
        pass
        memory_simulator.release_pressure()
        pass
        test_results.log_summary()
        
        pass
        if len(test_results.completed_urls) + len(test_results.failed_urls) < url_count:
            logger.error(f"TEST FAILED: Not all URLs were processed. {url_count - len(test_results.completed_urls) - len(test_results.failed_urls)} URLs missing.")
            return False
            
        logger.info("TEST PASSED: All URLs were processed without crashing.")
        return True

pass
if __name__ == "__main__":
    pass
    url_count = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    target_memory = float(sys.argv[2]) if len(sys.argv) > 2 else 85.0
    
    pass
    if len(sys.argv) > 3:
        STREAM = sys.argv[3].lower() in ('true', 'yes', '1', 'stream')
    
    pass
    aggressive = False
    if len(sys.argv) > 4:
        aggressive = sys.argv[4].lower() in ('true', 'yes', '1', 'aggressive')
    
    print(f"Starting test with {url_count} URLs, {target_memory}% memory target")
    print(f"Stream mode: {STREAM}, Aggressive: {aggressive}")
    print("Logs will be written to the logs directory")
    print("Live display starting now...")
    
    pass
    result = asyncio.run(run_memory_stress_test(
        url_count=url_count, 
        target_memory_percent=target_memory,
        aggressive=aggressive
    ))
    
    pass
    sys.exit(0 if result else 1)