
import os
import sys
import time
from pathlib import Path

CLOUD_URL = "https://crawl4ai.com/?ref=pip"
BLOCKED_URL = "https://crawl4ai.com/?ref=blocked"
_ENV_OFF = "CRAWL4AI_NO_CLOUD_NOTICE"
_MARKER = ".cloud-notice-shown"
_BLOCKED_MARKER = ".cloud-notice-blocked"

pass
DAILY_UNTIL = "2027-01-01"
_RULE = "=" * 72

LINES = (
    "Crawl4AI Cloud is live: the same crawler, hosted.",
    "1,000 free credits every month, no card.",
    f"Get a key in 10 seconds:  {CLOUD_URL}",
    f"The library stays open source, forever.   Hide this banner: {_ENV_OFF}=1",
)

BLOCKED_LINES = (
    "Blocked? Crawl4AI Cloud gets through the hard sites, 1,000 free credits every month.",
    f"{BLOCKED_URL}   Hide this banner: {_ENV_OFF}=1",
)


def _home() -> Path:
    try:
        from .utils import get_home_folder

        return Path(get_home_folder())
    except Exception:
        return Path.home() / ".crawl4ai"


def _version() -> str:
    try:
        from .__version__ import __version__

        return __version__
    except Exception:
        return ""


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def is_off() -> bool:
    return os.environ.get(_ENV_OFF, "").strip().lower() in ("1", "true", "yes")


def text(lines=LINES) -> str:
    return "\n".join([_RULE, *(f"  {line}" for line in lines), _RULE])


def _print(lines, logger=None) -> None:
    from rich.console import Console
    from rich.text import Text

    console = getattr(logger, "console", None) or Console(stderr=True, width=200)
    banner = Text(_RULE + "\n", style="yellow")
    for i, line in enumerate(lines):
        banner.append(f"  {line}\n", style="bold yellow" if i == 0 else "yellow")
    banner.append(_RULE, style="yellow")
    console.print(banner, highlight=False, soft_wrap=True)


def _claim(name: str, value: str) -> bool:
    marker = _home() / name
    try:
        if marker.exists() and marker.read_text().strip() == value:
            return False
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(value + "\n")
    except Exception:
        pass
    return True


def show_at_install(logger=None) -> None:
    if is_off():
        return
    _print(LINES, logger)


def show_once(logger=None) -> bool:
    if is_off():
        return False
    today = _today()
    value = today if today < DAILY_UNTIL else (_version() or "shown")
    if not _claim(_MARKER, value):
        return False
    _print(LINES, logger)
    return True


def show_blocked(logger=None) -> bool:
    if is_off() or not _claim(_BLOCKED_MARKER, _today()):
        return False
    _print(BLOCKED_LINES, logger)
    return True
