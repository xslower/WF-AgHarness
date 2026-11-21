from __future__ import annotations

from pathlib import Path

from ....store import layout

_WEB = "web"


def web_dir() -> Path:
    return layout.data_dir() / _WEB


def profiles_dir() -> Path:
    return web_dir() / "profiles"


def scripts_dir() -> Path:
    return web_dir() / "scripts"


def logs_dir() -> Path:
    return web_dir() / "logs"
