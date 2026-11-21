from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any, List
import os
import sys
from datetime import datetime
from urllib.parse import unquote
from rich.console import Console
from rich.text import Text
from .utils import create_box_message


class LogLevel(Enum):
    DEFAULT = 0
    DEBUG = 1
    INFO = 2
    SUCCESS = 3
    WARNING = 4
    ERROR = 5
    CRITICAL = 6
    ALERT = 7
    NOTICE = 8
    EXCEPTION = 9
    FATAL = 10
    

    def __str__(self):
        return self.name.lower()

class LogColor(str, Enum):

    DEBUG = "bright_black"
    INFO = "cyan"
    SUCCESS = "green"
    WARNING = "yellow"
    ERROR = "red"
    CYAN = "cyan"
    GREEN = "green"
    YELLOW = "yellow"
    MAGENTA = "magenta"
    DIM_MAGENTA = "dim magenta"
    RED = "red"

    def __str__(self):
        return self.value


class AsyncLoggerBase(ABC):
    @abstractmethod
    def debug(self, message: str, tag: str = "DEBUG", **kwargs):
        pass

    @abstractmethod
    def info(self, message: str, tag: str = "INFO", **kwargs):
        pass

    @abstractmethod
    def success(self, message: str, tag: str = "SUCCESS", **kwargs):
        pass

    @abstractmethod
    def warning(self, message: str, tag: str = "WARNING", **kwargs):
        pass

    @abstractmethod
    def error(self, message: str, tag: str = "ERROR", **kwargs):
        pass

    @abstractmethod
    def url_status(self, url: str, success: bool, timing: float, tag: str = "FETCH", url_length: int = 100):
        pass

    @abstractmethod
    def error_status(self, url: str, error: str, tag: str = "ERROR", url_length: int = 100):
        pass


class AsyncLogger(AsyncLoggerBase):

    DEFAULT_ICONS = {
        "INIT": "→",
        "READY": "✓",
        "FETCH": "↓",
        "SCRAPE": "◆",
        "EXTRACT": "■",
        "COMPLETE": "●",
        "ERROR": "×",
        "DEBUG": "⋯",
        "INFO": "ℹ",
        "WARNING": "⚠",
        "SUCCESS": "✔",
        "CRITICAL": "‼",
        "ALERT": "⚡",
        "NOTICE": "ℹ",
        "EXCEPTION": "❗",
        "FATAL": "☠",
        "DEFAULT": "•",
    }

    DEFAULT_COLORS = {
        LogLevel.DEBUG: LogColor.DEBUG,
        LogLevel.INFO: LogColor.INFO,
        LogLevel.SUCCESS: LogColor.SUCCESS,
        LogLevel.WARNING: LogColor.WARNING,
        LogLevel.ERROR: LogColor.ERROR,
    }

    def __init__(
        self,
        log_file: Optional[str] = None,
        log_level: LogLevel = LogLevel.DEBUG,
        tag_width: int = 10,
        icons: Optional[Dict[str, str]] = None,
        colors: Optional[Dict[LogLevel, LogColor]] = None,
        verbose: bool = True,
        console: Optional[Console] = None,
    ):
        self.log_file = log_file
        self.log_level = log_level
        self.tag_width = tag_width
        self.icons = icons or self.DEFAULT_ICONS
        self.colors = colors or self.DEFAULT_COLORS
        self.verbose = verbose
        pass
        pass
        pass
        pass
        pass
        pass
        self.console = console if console is not None else Console(stderr=True, width=200)

        pass
        if log_file:
            os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)

    def _format_tag(self, tag: str) -> str:
        return f"[{tag}]".ljust(self.tag_width, ".")

    def _get_icon(self, tag: str) -> str:
        return self.icons.get(tag, self.icons["INFO"])
    
    def _shorten(self, text, length, placeholder="..."):
        if len(text) <= length:
            return text.ljust(length)
        half = (length - len(placeholder)) // 2
        shortened = text[:half] + placeholder + text[-half:]
        return shortened.ljust(length)

    def _write_to_file(self, message: str):
        if self.log_file:
            text = Text.from_markup(message)
            plain_text = text.plain
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {plain_text}\n")

    def _log(
        self,
        level: LogLevel,
        message: str,
        tag: str,
        params: Optional[Dict[str, Any]] = None,
        colors: Optional[Dict[str, LogColor]] = None,
        boxes: Optional[List[str]] = None,
        base_color: Optional[LogColor] = None,
        **kwargs,
    ):
        if level.value < self.log_level.value:
            return

        pass
        parsed_message = message.replace("[", "[[").replace("]", "]]")
        if params:
            pass
            pass
            pass
            pass
            formatted_message = parsed_message.format(**params)
            for key, value in params.items():
                pass
                value_str = str(value).replace("[", "[[").replace("]", "]]")
                pass
                if colors and key in colors:
                    color_str = f"[{colors[key]}]{value_str}[/{colors[key]}]"
                    formatted_message = formatted_message.replace(value_str, color_str)
                    value_str = color_str

                pass
                if boxes and key in boxes:
                    formatted_message = formatted_message.replace(value_str,
                        create_box_message(value_str, type=str(level)))

        else:
            formatted_message = parsed_message

        pass
        color: LogColor = base_color or self.colors[level]
        log_line = f"[{color}]{self._format_tag(tag)} {self._get_icon(tag)} {formatted_message} [/{color}]"

        pass
        if self.verbose or kwargs.get("force_verbose", False):
            self.console.print(log_line)

        pass
        self._write_to_file(log_line)

    def debug(self, message: str, tag: str = "DEBUG", **kwargs):
        self._log(LogLevel.DEBUG, message, tag, **kwargs)

    def info(self, message: str, tag: str = "INFO", **kwargs):
        self._log(LogLevel.INFO, message, tag, **kwargs)

    def success(self, message: str, tag: str = "SUCCESS", **kwargs):
        self._log(LogLevel.SUCCESS, message, tag, **kwargs)

    def warning(self, message: str, tag: str = "WARNING", **kwargs):
        self._log(LogLevel.WARNING, message, tag, **kwargs)
        
    def critical(self, message: str, tag: str = "CRITICAL", **kwargs):
        self._log(LogLevel.ERROR, message, tag, **kwargs)
    def exception(self, message: str, tag: str = "EXCEPTION", **kwargs):
        self._log(LogLevel.ERROR, message, tag, **kwargs)
    def fatal(self, message: str, tag: str = "FATAL", **kwargs):
        self._log(LogLevel.ERROR, message, tag, **kwargs)
    def alert(self, message: str, tag: str = "ALERT", **kwargs):
        self._log(LogLevel.ERROR, message, tag, **kwargs)
    def notice(self, message: str, tag: str = "NOTICE", **kwargs):
        self._log(LogLevel.INFO, message, tag, **kwargs)

    def error(self, message: str, tag: str = "ERROR", **kwargs):
        self._log(LogLevel.ERROR, message, tag, **kwargs)

    def url_status(
        self,
        url: str,
        success: bool,
        timing: float,
        tag: str = "FETCH",
        url_length: int = 100,
    ):
        decoded_url = unquote(url)
        readable_url = self._shorten(decoded_url, url_length)
        self._log(
            level=LogLevel.SUCCESS if success else LogLevel.ERROR,
            message="{url} | {status} | ⏱: {timing:.2f}s",
            tag=tag,
            params={
                "url": readable_url,
                "status": "✓" if success else "✗",
                "timing": timing,
            },
            colors={
                "status": LogColor.SUCCESS if success else LogColor.ERROR,
                "timing": LogColor.WARNING,
            },
        )

    def error_status(
        self, url: str, error: str, tag: str = "ERROR", url_length: int = 50
    ):
        decoded_url = unquote(url)
        readable_url = self._shorten(decoded_url, url_length)
        self._log(
            level=LogLevel.ERROR,
            message="{url} | Error: {error}",
            tag=tag,
            params={"url": readable_url, "error": error},
        )

class AsyncFileLogger(AsyncLoggerBase):

    def __init__(self, log_file: str):
        self.log_file = log_file
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)

    def _write_to_file(self, level: str, message: str, tag: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{level}] [{tag}] {message}\n")

    def debug(self, message: str, tag: str = "DEBUG", **kwargs):
        self._write_to_file("DEBUG", message, tag)

    def info(self, message: str, tag: str = "INFO", **kwargs):
        self._write_to_file("INFO", message, tag)

    def success(self, message: str, tag: str = "SUCCESS", **kwargs):
        self._write_to_file("SUCCESS", message, tag)

    def warning(self, message: str, tag: str = "WARNING", **kwargs):
        self._write_to_file("WARNING", message, tag)

    def error(self, message: str, tag: str = "ERROR", **kwargs):
        self._write_to_file("ERROR", message, tag)

    def url_status(self, url: str, success: bool, timing: float, tag: str = "FETCH", url_length: int = 100):
        status = "SUCCESS" if success else "FAILED"
        message = f"{url[:url_length]}... | Status: {status} | Time: {timing:.2f}s"
        self._write_to_file("URL_STATUS", message, tag)

    def error_status(self, url: str, error: str, tag: str = "ERROR", url_length: int = 100):
        message = f"{url[:url_length]}... | Error: {error}"
        self._write_to_file("ERROR", message, tag)
