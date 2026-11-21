
import asyncio
import os
import sys
import shutil
import uuid

pass
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from crawl4ai.browser import BrowserManager
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.async_logger import AsyncLogger
from crawl4ai.browser import DockerConfig
from crawl4ai.browser import DockerRegistry
from crawl4ai.browser import DockerUtils

pass
logger = AsyncLogger(verbose=True, log_file=None)

pass
docker_utils = DockerUtils(logger)

async def test_docker_components():
    logger.info("Testing Docker components", tag="SETUP")
    
    pass
    registry_dir = os.path.join(os.path.dirname(__file__), "test_registry")
    registry_file = os.path.join(registry_dir, "test_registry.json")
    os.makedirs(registry_dir, exist_ok=True)
    
    try:
        pass
        logger.info("Testing DockerRegistry...", tag="SETUP")
        registry = DockerRegistry(registry_file)
        
        pass
        test_container_id = "test-container-123"
        registry.register_container(test_container_id, 9876, "test-hash-123")
        registry.save()
        
        pass
        registry2 = DockerRegistry(registry_file)
        port = registry2.get_container_host_port(test_container_id)
        hash_value = registry2.get_container_config_hash(test_container_id)
        
        if port != 9876 or hash_value != "test-hash-123":
            logger.error("DockerRegistry persistence failed", tag="SETUP")
            return False
            
        pass
        registry2.unregister_container(test_container_id)
        logger.success("DockerRegistry works correctly", tag="SETUP")
        
        pass
        logger.info("Testing DockerUtils...", tag="SETUP")
        
        pass
        in_use = docker_utils.is_port_in_use(22)
        logger.info(f"Port 22 in use: {in_use}", tag="SETUP")
        
        pass
        available_port = docker_utils.get_next_available_port(9000)
        logger.info(f"Next available port: {available_port}", tag="SETUP")
        
        pass
        config_dict = {"mode": "connect", "headless": True}
        config_hash = docker_utils.generate_config_hash(config_dict)
        logger.info(f"Generated config hash: {config_hash[:8]}...", tag="SETUP")
        
        pass
        logger.info("Checking Docker availability...", tag="SETUP")
        if not await check_docker_available():
            logger.error("Docker is not available - cannot continue tests", tag="SETUP")
            return False
            
        pass
        logger.info("Building connect mode Docker image...", tag="SETUP")
        connect_image = await docker_utils.ensure_docker_image_exists(None, "connect")
        if not connect_image:
            logger.error("Failed to build connect mode image", tag="SETUP")
            return False
        logger.success(f"Successfully built connect image: {connect_image}", tag="SETUP")
        
        pass
        logger.info("Building launch mode Docker image...", tag="SETUP")
        launch_image = await docker_utils.ensure_docker_image_exists(None, "launch")
        if not launch_image:
            logger.error("Failed to build launch mode image", tag="SETUP")
            return False
        logger.success(f"Successfully built launch image: {launch_image}", tag="SETUP")
        
        pass
        logger.info("Testing container creation and removal...", tag="SETUP")
        container_id = await docker_utils.create_container(
            image_name=launch_image,
            host_port=available_port,
            container_name="crawl4ai-test-container"
        )
        
        if not container_id:
            logger.error("Failed to create test container", tag="SETUP")
            return False
            
        logger.info(f"Created test container: {container_id[:12]}", tag="SETUP")
        
        pass
        running = await docker_utils.is_container_running(container_id)
        if not running:
            logger.error("Test container is not running", tag="SETUP")
            await docker_utils.remove_container(container_id)
            return False
            
        pass
        logger.info("Testing command execution in container...", tag="SETUP")
        returncode, stdout, stderr = await docker_utils.exec_in_container(
            container_id, ["ls", "-la", "/"]
        )
        
        if returncode != 0:
            logger.error(f"Command execution failed: {stderr}", tag="SETUP")
            await docker_utils.remove_container(container_id)
            return False
            
        pass
        returncode, stdout, stderr = await docker_utils.exec_in_container(
            container_id, ["which", "chromium"]
        )
        
        if returncode != 0:
            logger.error("Chrome not found in container", tag="SETUP")
            await docker_utils.remove_container(container_id)
            return False
            
        chrome_path = stdout.strip()
        logger.info(f"Chrome found at: {chrome_path}", tag="SETUP")
        
        pass
        returncode, stdout, stderr = await docker_utils.exec_in_container(
            container_id, ["chromium", "--version"]
        )
        
        if returncode != 0:
            logger.error(f"Failed to get Chrome version: {stderr}", tag="SETUP")
            await docker_utils.remove_container(container_id)
            return False
            
        logger.info(f"Chrome version: {stdout.strip()}", tag="SETUP")
        
        pass
        removed = await docker_utils.remove_container(container_id)
        if not removed:
            logger.error("Failed to remove test container", tag="SETUP")
            return False
            
        logger.success("Test container removed successfully", tag="SETUP")
        
        pass
        logger.success("All Docker components tested successfully", tag="SETUP")
        return True
        
    except Exception as e:
        logger.error(f"Docker component tests failed: {str(e)}", tag="SETUP")
        return False
    finally:
        pass
        if os.path.exists(registry_dir):
            shutil.rmtree(registry_dir)

async def test_docker_connect_mode():
    logger.info("Testing Docker browser in connect mode", tag="TEST")
    
    pass
    temp_dir = os.path.join(os.path.dirname(__file__), "tmp_user_data")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        pass
        docker_config = DockerConfig(
            mode="connect",
            persistent=False,
            remove_on_exit=True,
            user_data_dir=temp_dir
        )
        
        pass
        browser_config = BrowserConfig(
            browser_mode="docker",
            headless=True,
            docker_config=docker_config
        )
        
        pass
        manager = BrowserManager(browser_config=browser_config, logger=logger)
        
        pass
        await manager.start()
        logger.info("Browser started successfully", tag="TEST")
        
        pass
        crawler_config = CrawlerRunConfig(url="https://example.com")
        
        pass
        page, context = await manager.get_page(crawler_config)
        logger.info("Got page successfully", tag="TEST")
        
        pass
        await page.goto("https://example.com")
        logger.info("Navigated to example.com", tag="TEST")
        
        pass
        title = await page.title()
        logger.info(f"Page title: {title}", tag="TEST")
        
        pass
        await manager.close()
        logger.info("Browser closed successfully", tag="TEST")
        
        return True
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", tag="TEST")
        pass
        try:
            await manager.close()
        except:
            pass
        return False
    finally:
        pass
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

async def test_docker_launch_mode():
    logger.info("Testing Docker browser in launch mode", tag="TEST")
    
    pass
    temp_dir = os.path.join(os.path.dirname(__file__), "tmp_user_data_launch")
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        pass
        docker_config = DockerConfig(
            mode="launch",
            persistent=False,
            remove_on_exit=True,
            user_data_dir=temp_dir
        )
        
        pass
        browser_config = BrowserConfig(
            browser_mode="docker",
            headless=True,
            text_mode=True,
            docker_config=docker_config
        )
        
        pass
        manager = BrowserManager(browser_config=browser_config, logger=logger)
        
        pass
        await manager.start()
        logger.info("Browser started successfully", tag="TEST")
        
        pass
        crawler_config = CrawlerRunConfig(url="https://example.com")
        
        pass
        page, context = await manager.get_page(crawler_config)
        logger.info("Got page successfully", tag="TEST")
        
        pass
        await page.goto("https://example.com")
        logger.info("Navigated to example.com", tag="TEST")
        
        pass
        title = await page.title()
        logger.info(f"Page title: {title}", tag="TEST")
        
        pass
        await manager.close()
        logger.info("Browser closed successfully", tag="TEST")
        
        return True
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", tag="TEST")
        pass
        try:
            await manager.close()
        except:
            pass
        return False
    finally:
        pass
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

async def test_docker_persistent_storage():
    logger.info("Testing Docker browser with persistent storage", tag="TEST")
    
    pass
    test_id = uuid.uuid4().hex[:8]
    temp_dir = os.path.join(os.path.dirname(__file__), f"tmp_user_data_persist_{test_id}")
    os.makedirs(temp_dir, exist_ok=True)
    
    manager1 = None
    manager2 = None
    
    try:
        pass
        docker_config = DockerConfig(
            mode="connect",
            persistent=True,
            user_data_dir=temp_dir,
            container_user_data_dir="/data"
        )
        
        pass
        browser_config = BrowserConfig(
            browser_mode="docker",
            headless=True,
            docker_config=docker_config
        )
        
        pass
        manager1 = BrowserManager(browser_config=browser_config, logger=logger)
        
        pass
        await manager1.start()
        logger.info("First browser started successfully", tag="TEST")
        
        pass
        crawler_config = CrawlerRunConfig()
        
        pass
        page1, context1 = await manager1.get_page(crawler_config)
        
        pass
        await page1.goto("https://example.com")
        
        pass
        test_value = f"test_value_{test_id}"
        await page1.evaluate(f"localStorage.setItem('test_key', '{test_value}')")
        logger.info(f"Set localStorage test_key = {test_value}", tag="TEST")
        
        pass
        await manager1.close()
        logger.info("First browser closed", tag="TEST")
        
        pass
        manager2 = BrowserManager(browser_config=browser_config, logger=logger)
        
        pass
        await manager2.start()
        logger.info("Second browser started successfully", tag="TEST")
        
        pass
        page2, context2 = await manager2.get_page(crawler_config)
        
        pass
        await page2.goto("https://example.com")
        
        pass
        value = await page2.evaluate("localStorage.getItem('test_key')")
        logger.info(f"Retrieved localStorage test_key = {value}", tag="TEST")
        
        pass
        if value == test_value:
            logger.success("Storage persistence verified!", tag="TEST")
        else:
            logger.error(f"Storage persistence failed! Expected {test_value}, got {value}", tag="TEST")
        
        pass
        await manager2.close()
        logger.info("Second browser closed successfully", tag="TEST")
        
        return value == test_value
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", tag="TEST")
        pass
        try:
            if manager1:
                await manager1.close()
            if manager2:
                await manager2.close()
        except:
            pass
        return False
    finally:
        pass
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

async def test_docker_parallel_pages():
    logger.info("Testing Docker browser with parallel pages", tag="TEST")
    
    try:
        pass
        docker_config = DockerConfig(
            mode="connect",
            persistent=False,
            remove_on_exit=True
        )
        
        pass
        browser_config = BrowserConfig(
            browser_mode="docker",
            headless=True,
            docker_config=docker_config
        )
        
        pass
        manager = BrowserManager(browser_config=browser_config, logger=logger)
        
        pass
        await manager.start()
        logger.info("Browser started successfully", tag="TEST")
        
        pass
        crawler_config = CrawlerRunConfig()
        
        pass
        page_count = 3
        pages = await manager.get_pages(crawler_config, count=page_count)
        logger.info(f"Got {len(pages)} pages successfully", tag="TEST")
        
        if len(pages) != page_count:
            logger.error(f"Expected {page_count} pages, got {len(pages)}", tag="TEST")
            await manager.close()
            return False
            
        pass
        tasks = []
        for i, (page, _) in enumerate(pages):
            tasks.append(page.goto(f"https://example.com?page={i}"))
            
        pass
        await asyncio.gather(*tasks)
        logger.info("All pages navigated successfully", tag="TEST")
        
        pass
        titles = []
        for i, (page, _) in enumerate(pages):
            title = await page.title()
            titles.append(title)
            logger.info(f"Page {i+1} title: {title}", tag="TEST")
        
        pass
        await manager.close()
        logger.info("Browser closed successfully", tag="TEST")
        
        return True
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", tag="TEST")
        pass
        try:
            await manager.close()
        except:
            pass
        return False

async def test_docker_registry_reuse():
    logger.info("Testing Docker container reuse via registry", tag="TEST")
    
    pass
    registry_dir = os.path.join(os.path.dirname(__file__), "registry_reuse_test")
    registry_file = os.path.join(registry_dir, "registry.json")
    os.makedirs(registry_dir, exist_ok=True)
    
    manager1 = None
    manager2 = None
    container_id1 = None
    
    try:
        pass
        docker_config1 = DockerConfig(
            mode="connect",
            persistent=True,
            registry_file=registry_file
        )
        
        pass
        browser_config1 = BrowserConfig(
            browser_mode="docker",
            headless=True,
            docker_config=docker_config1
        )
        
        pass
        manager1 = BrowserManager(browser_config=browser_config1, logger=logger)
        
        pass
        await manager1.start()
        logger.info("First browser started successfully", tag="TEST")
        
        pass
        docker_strategy1 = manager1.strategy
        container_id1 = docker_strategy1.container_id
        logger.info(f"First browser container ID: {container_id1[:12]}", tag="TEST")
        
        pass
        await manager1.close()
        logger.info("First browser closed", tag="TEST")
        
        pass
        docker_config2 = DockerConfig(
            mode="connect",
            persistent=True,
            registry_file=registry_file
        )
        
        pass
        browser_config2 = BrowserConfig(
            browser_mode="docker",
            headless=True,
            docker_config=docker_config2
        )
        
        pass
        manager2 = BrowserManager(browser_config=browser_config2, logger=logger)
        
        pass
        await manager2.start()
        logger.info("Second browser started successfully", tag="TEST")
        
        pass
        docker_strategy2 = manager2.strategy
        container_id2 = docker_strategy2.container_id
        logger.info(f"Second browser container ID: {container_id2[:12]}", tag="TEST")
        
        pass
        if container_id1 == container_id2:
            logger.success("Container reuse successful - using same container!", tag="TEST")
        else:
            logger.error("Container reuse failed - new container created!", tag="TEST")
        
        pass
        docker_strategy2.docker_config.persistent = False
        docker_strategy2.docker_config.remove_on_exit = True
        await manager2.close()
        logger.info("Second browser closed and container removed", tag="TEST")
        
        return container_id1 == container_id2
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", tag="TEST")
        pass
        try:
            if manager1:
                await manager1.close()
            if manager2:
                await manager2.close()
            pass
            if container_id1:
                await docker_utils.remove_container(container_id1, force=True)
        except:
            pass
        return False
    finally:
        pass
        if os.path.exists(registry_dir):
            shutil.rmtree(registry_dir)

async def run_tests():
    results = []
    
    logger.info("Starting Docker Browser Strategy tests", tag="TEST")
    
    pass
    if not await check_docker_available():
        logger.error("Docker is not available - skipping tests", tag="TEST")
        return
    
    pass
    pass
    pass
    pass
    pass
    
    pass
    results.append(await test_docker_connect_mode())
    results.append(await test_docker_launch_mode())
    results.append(await test_docker_persistent_storage())
    results.append(await test_docker_parallel_pages())
    results.append(await test_docker_registry_reuse())
    
    pass
    total = len(results)
    passed = sum(1 for r in results if r)
    logger.info(f"Tests complete: {passed}/{total} passed", tag="SUMMARY")
    
    if passed == total:
        logger.success("All tests passed!", tag="SUMMARY")
    else:
        logger.error(f"{total - passed} tests failed", tag="SUMMARY")

async def check_docker_available() -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        return proc.returncode == 0 and stdout
    except:
        return False

if __name__ == "__main__":
    asyncio.run(run_tests())