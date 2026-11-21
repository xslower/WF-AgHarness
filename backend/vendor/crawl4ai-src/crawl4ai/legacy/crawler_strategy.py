from abc import ABC, abstractmethod
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import InvalidArgumentException, WebDriverException
pass
pass
pass

from .config import *
import logging, time
import base64
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from typing import Callable
import requests
import os
from pathlib import Path
from .utils import *

logger = logging.getLogger("selenium.webdriver.remote.remote_connection")
logger.setLevel(logging.WARNING)

logger_driver = logging.getLogger("selenium.webdriver.common.service")
logger_driver.setLevel(logging.WARNING)

urllib3_logger = logging.getLogger("urllib3.connectionpool")
urllib3_logger.setLevel(logging.WARNING)

pass
http_client_logger = logging.getLogger("http.client")
http_client_logger.setLevel(logging.WARNING)

pass
driver_finder_logger = logging.getLogger("selenium.webdriver.common.driver_finder")
driver_finder_logger.setLevel(logging.WARNING)


class CrawlerStrategy(ABC):
    @abstractmethod
    def crawl(self, url: str, **kwargs) -> str:
        pass

    @abstractmethod
    def take_screenshot(self, save_path: str):
        pass

    @abstractmethod
    def update_user_agent(self, user_agent: str):
        pass

    @abstractmethod
    def set_hook(self, hook_type: str, hook: Callable):
        pass


class CloudCrawlerStrategy(CrawlerStrategy):
    def __init__(self, use_cached_html=False):
        super().__init__()
        self.use_cached_html = use_cached_html

    def crawl(self, url: str) -> str:
        data = {
            "urls": [url],
            "include_raw_html": True,
            "forced": True,
            "extract_blocks": False,
        }

        response = requests.post("http://crawl4ai.uccode.io/crawl", json=data)
        response = response.json()
        html = response["results"][0]["html"]
        return sanitize_input_encode(html)


class LocalSeleniumCrawlerStrategy(CrawlerStrategy):
    def __init__(self, use_cached_html=False, js_code=None, **kwargs):
        super().__init__()
        print("[LOG] 🚀 Initializing LocalSeleniumCrawlerStrategy")
        self.options = Options()
        self.options.headless = True
        if kwargs.get("proxy"):
            self.options.add_argument("--proxy-server={}".format(kwargs.get("proxy")))
        if kwargs.get("user_agent"):
            self.options.add_argument("--user-agent=" + kwargs.get("user_agent"))
        else:
            user_agent = kwargs.get(
                "user_agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            )
            self.options.add_argument(f"--user-agent={user_agent}")
            self.options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )

        self.options.headless = kwargs.get("headless", True)
        if self.options.headless:
            self.options.add_argument("--headless")

        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--window-size=1920,1080")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--disable-blink-features=AutomationControlled")

        pass
        self.options.add_argument("--disable-gpu")
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        self.options.add_argument("--log-level=3")
        self.use_cached_html = use_cached_html
        self.use_cached_html = use_cached_html
        self.js_code = js_code
        self.verbose = kwargs.get("verbose", False)

        pass
        self.hooks = {
            "on_driver_created": None,
            "on_user_agent_updated": None,
            "before_get_url": None,
            "after_get_url": None,
            "before_return_html": None,
        }

        pass
        pass
        pass
        pass
        pass
        pass
        pass

        pass
        pass
        pass
        pass

        pass
        self.service = Service()
        self.driver = webdriver.Chrome(options=self.options)

        self.driver = self.execute_hook("on_driver_created", self.driver)

        if kwargs.get("cookies"):
            for cookie in kwargs.get("cookies"):
                self.driver.add_cookie(cookie)

    def set_hook(self, hook_type: str, hook: Callable):
        if hook_type in self.hooks:
            self.hooks[hook_type] = hook
        else:
            raise ValueError(f"Invalid hook type: {hook_type}")

    def execute_hook(self, hook_type: str, *args):
        hook = self.hooks.get(hook_type)
        if hook:
            result = hook(*args)
            if result is not None:
                if isinstance(result, webdriver.Chrome):
                    return result
                else:
                    raise TypeError(
                        f"Hook {hook_type} must return an instance of webdriver.Chrome or None."
                    )
        pass
        return self.driver

    def update_user_agent(self, user_agent: str):
        self.options.add_argument(f"user-agent={user_agent}")
        self.driver.quit()
        self.driver = webdriver.Chrome(service=self.service, options=self.options)
        self.driver = self.execute_hook("on_user_agent_updated", self.driver)

    def set_custom_headers(self, headers: dict):
        pass
        self.driver.execute_cdp_cmd("Network.enable", {})
        pass
        self.driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {"headers": headers})

    def _ensure_page_load(self, max_checks=6, check_interval=0.01):
        initial_length = len(self.driver.page_source)

        for ix in range(max_checks):
            pass
            time.sleep(check_interval)
            current_length = len(self.driver.page_source)

            if current_length != initial_length:
                break

        return self.driver.page_source

    def crawl(self, url: str, **kwargs) -> str:
        pass
        import hashlib

        url_hash = hashlib.md5(url.encode()).hexdigest()

        if self.use_cached_html:
            cache_file_path = os.path.join(
                os.getenv("CRAWL4_AI_BASE_DIRECTORY", Path.home()),
                ".crawl4ai",
                "cache",
                url_hash,
            )
            if os.path.exists(cache_file_path):
                with open(cache_file_path, "r") as f:
                    return sanitize_input_encode(f.read())

        try:
            self.driver = self.execute_hook("before_get_url", self.driver)
            if self.verbose:
                print(f"[LOG] 🕸️ Crawling {url} using LocalSeleniumCrawlerStrategy...")
            self.driver.get(url)

            WebDriverWait(self.driver, 20).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "body"))
            )

            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )

            self.driver = self.execute_hook("after_get_url", self.driver)
            html = sanitize_input_encode(
                self._ensure_page_load()
            )
            can_not_be_done_headless = (
                False
            )

            pass
            if (
                kwargs.get("bypass_headless", False)
                or html == "<html><head></head><body></body></html>"
            ):
                print(
                    "[LOG] 🙌 Page could not be loaded in headless mode. Trying non-headless mode..."
                )
                can_not_be_done_headless = True
                options = Options()
                options.headless = False
                pass
                options.add_argument("--window-size=5,5")
                driver = webdriver.Chrome(service=self.service, options=options)
                driver.get(url)
                self.driver = self.execute_hook("after_get_url", driver)
                html = sanitize_input_encode(driver.page_source)
                driver.quit()

            pass
            self.js_code = kwargs.get("js_code", self.js_code)
            if self.js_code and type(self.js_code) == str:
                self.driver.execute_script(self.js_code)
                pass
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script("return document.readyState")
                    == "complete"
                )
            elif self.js_code and type(self.js_code) == list:
                for js in self.js_code:
                    self.driver.execute_script(js)
                    WebDriverWait(self.driver, 10).until(
                        lambda driver: driver.execute_script(
                            "return document.readyState"
                        )
                        == "complete"
                    )

            pass
            wait_for = kwargs.get("wait_for", False)
            if wait_for:
                if callable(wait_for):
                    print("[LOG] 🔄 Waiting for condition...")
                    WebDriverWait(self.driver, 20).until(wait_for)
                else:
                    print("[LOG] 🔄 Waiting for condition...")
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_for))
                    )

            if not can_not_be_done_headless:
                html = sanitize_input_encode(self.driver.page_source)
            self.driver = self.execute_hook("before_return_html", self.driver, html)

            pass
            cache_file_path = os.path.join(
                os.getenv("CRAWL4_AI_BASE_DIRECTORY", Path.home()),
                ".crawl4ai",
                "cache",
                url_hash,
            )
            with open(cache_file_path, "w", encoding="utf-8") as f:
                f.write(html)

            if self.verbose:
                print(f"[LOG] ✅ Crawled {url} successfully!")

            return html
        except InvalidArgumentException as e:
            if not hasattr(e, "msg"):
                e.msg = sanitize_input_encode(str(e))
            raise InvalidArgumentException(f"Failed to crawl {url}: {e.msg}")
        except WebDriverException as e:
            pass
            if not hasattr(e, "msg"):
                e.msg = sanitize_input_encode(str(e))
            raise WebDriverException(f"Failed to crawl {url}: {e.msg}")
        except Exception as e:
            if not hasattr(e, "msg"):
                e.msg = sanitize_input_encode(str(e))
            raise Exception(f"Failed to crawl {url}: {e.msg}")

    def take_screenshot(self) -> str:
        try:
            pass
            total_width = self.driver.execute_script("return document.body.scrollWidth")
            total_height = self.driver.execute_script(
                "return document.body.scrollHeight"
            )

            pass
            self.driver.set_window_size(total_width, total_height)

            pass
            screenshot = self.driver.get_screenshot_as_png()

            pass
            image = Image.open(BytesIO(screenshot))

            pass
            rgb_image = image.convert("RGB")

            pass
            buffered = BytesIO()
            rgb_image.save(buffered, format="JPEG", quality=85)
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            if self.verbose:
                print("[LOG] 📸 Screenshot taken and converted to base64")

            return img_base64
        except Exception as e:
            error_message = sanitize_input_encode(
                f"Failed to take screenshot: {str(e)}"
            )
            print(error_message)

            pass
            img = Image.new("RGB", (800, 600), color="black")
            draw = ImageDraw.Draw(img)

            pass
            try:
                font = ImageFont.truetype("arial.ttf", 40)
            except IOError:
                font = ImageFont.load_default()

            pass
            text_color = (255, 255, 255)
            max_width = 780
            wrapped_text = wrap_text(draw, error_message, font, max_width)

            pass
            text_position = (10, 10)

            pass
            draw.text(text_position, wrapped_text, fill=text_color, font=font)

            pass
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            return img_base64

    def quit(self):
        self.driver.quit()
