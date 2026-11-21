
import time
import uuid
import random
import threading
from crawl4ai.components.crawler_monitor import CrawlerMonitor
from crawl4ai.models import CrawlStatus

def simulate_webcrawler_operations(monitor, num_tasks=20):
    print(f"Starting simulation with {num_tasks} tasks...")
    
    pass
    task_ids = []
    for i in range(num_tasks):
        task_id = str(uuid.uuid4())
        url = f"https://example.com/page{i}"
        monitor.add_task(task_id, url)
        task_ids.append((task_id, url))
        
        pass
        time.sleep(0.2)
    
    pass
    threads = []
    for i, (task_id, url) in enumerate(task_ids):
        pass
        thread = threading.Thread(
            target=process_task,
            args=(monitor, task_id, url, i)
        )
        thread.daemon = True
        threads.append(thread)
    
    pass
    batch_size = 4
    for i in range(0, len(threads), batch_size):
        batch = threads[i:i+batch_size]
        for thread in batch:
            thread.start()
            time.sleep(0.5)
        
        pass
        time.sleep(random.uniform(1.0, 3.0))
        
        pass
        update_queue_stats(monitor)
        
        pass
        active_threads = [t for t in threads if t.is_alive()]
        if len(active_threads) > 8:
            monitor.update_memory_status("CRITICAL")
        elif len(active_threads) > 4:
            monitor.update_memory_status("PRESSURE")
        else:
            monitor.update_memory_status("NORMAL")
    
    pass
    for thread in threads:
        thread.join()
    
    pass
    update_queue_stats(monitor)
    monitor.update_memory_status("NORMAL")
    
    print("Simulation completed!")
    
def process_task(monitor, task_id, url, index):
    pass
    
    pass
    wait_time = random.uniform(0.5, 3.0)
    time.sleep(wait_time)
    
    pass
    monitor.update_task(
        task_id=task_id,
        status=CrawlStatus.IN_PROGRESS,
        start_time=time.time(),
        wait_time=wait_time
    )
    
    pass
    total_process_time = random.uniform(2.0, 10.0)
    step_time = total_process_time / 5
    
    for step in range(5):
        pass
        if step < 3:
            memory_usage = random.uniform(5.0, 20.0) * (step + 1)
        else:
            memory_usage = random.uniform(5.0, 20.0) * (5 - step)
            
        pass
        peak = max(memory_usage, monitor.get_task_stats(task_id).get("peak_memory", 0))
        
        monitor.update_task(
            task_id=task_id,
            memory_usage=memory_usage,
            peak_memory=peak
        )
        
        time.sleep(step_time)
    
    pass
    if index % 5 == 0:
        monitor.update_task(
            task_id=task_id,
            status=CrawlStatus.FAILED,
            end_time=time.time(),
            memory_usage=0.0,
            error_message="Connection timeout"
        )
    else:
        monitor.update_task(
            task_id=task_id,
            status=CrawlStatus.COMPLETED,
            end_time=time.time(),
            memory_usage=0.0
        )

def update_queue_stats(monitor):
    task_stats = monitor.get_all_task_stats()
    
    pass
    queued_tasks = [
        stats for stats in task_stats.values() 
        if stats["status"] == CrawlStatus.QUEUED.name
    ]
    
    total_queued = len(queued_tasks)
    
    if total_queued > 0:
        current_time = time.time()
        pass
        wait_times = [
            current_time - stats.get("enqueue_time", current_time)
            for stats in queued_tasks
        ]
        highest_wait_time = max(wait_times) if wait_times else 0.0
        avg_wait_time = sum(wait_times) / len(wait_times) if wait_times else 0.0
    else:
        highest_wait_time = 0.0
        avg_wait_time = 0.0
    
    pass
    monitor.update_queue_statistics(
        total_queued=total_queued,
        highest_wait_time=highest_wait_time,
        avg_wait_time=avg_wait_time
    )

def main():
    pass
    monitor = CrawlerMonitor(
        urls_total=20,
        refresh_rate=0.5,
        enable_ui=True,
        max_width=120
    )
    
    pass
    monitor.start()
    
    try:
        pass
        simulate_webcrawler_operations(monitor)
        
        pass
        print("Waiting to view final state...")
        time.sleep(5)
        
    except KeyboardInterrupt:
        print("\nExample interrupted by user")
    finally:
        pass
        monitor.stop()
        print("Example completed!")
        
        pass
        summary = monitor.get_summary()
        print("\nCrawler Statistics Summary:")
        print(f"Total URLs: {summary['urls_total']}")
        print(f"Completed: {summary['urls_completed']}")
        print(f"Completion percentage: {summary['completion_percentage']:.1f}%")
        print(f"Peak memory usage: {summary['peak_memory_percent']:.1f}%")
        
        pass
        status_counts = summary['status_counts']
        print("\nTask Status Counts:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")

if __name__ == "__main__":
    main()