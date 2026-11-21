from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from ..agent.profile import DEFAULT_SYSTEM_MODE, SYSTEM_MODES
from . import homes

logger = logging.getLogger("harness.plugin.bot_prompt")

pass
SELECT_KEY = "bot.system_prompt"
pass
DEFAULT_PROFILE_NAME = "default"


def file_of(installs, pid: str, project: str = "") -> Optional[Path]:
    from .bot import package_bot

    try:
        bot = package_bot(installs, pid, project)
    except LookupError:
        return None
    if not bot:
        return None
    name = str(bot.get("system_prompt_file") or "")
    if not name:
        return None
    return homes.file_in(pid, name, project)


def _norm(entry) -> Optional[dict]:
    if isinstance(entry, str):
        text = entry.strip()
        return {"mode": DEFAULT_SYSTEM_MODE, "text": text} if text else None
    if not isinstance(entry, dict):
        return None
    mode = str(entry.get("mode") or DEFAULT_SYSTEM_MODE).strip().lower()
    if mode not in SYSTEM_MODES:
        mode = DEFAULT_SYSTEM_MODE
    text = str(entry.get("text") or entry.get("prompt") or "").strip()
    return {"mode": mode, "text": text} if text else None


def profiles(installs, pid: str, project: str = "") -> dict[str, dict]:
    p = file_of(installs, pid, project)
    if p is None or not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text("utf-8", errors="replace") or "{}")
    except (OSError, ValueError):
        logger.warning("bot 提示词文件解析失败，按不设置处理: %s", p)
        return {}
    if not isinstance(data, dict):
        return {}
    if "mode" in data or "text" in data or "prompt" in data:
        pass
        one = _norm(data)
        return {DEFAULT_PROFILE_NAME: one} if one else {}
    out: dict[str, dict] = {}
    for name, entry in data.items():
        body = _norm(entry)
        if body is None:
            continue
        out[str(name)] = body
    return out


def selected(installs, pid: str, project: str = "") -> str:
    from .plugin_sdk import PluginHost

    try:
        name = PluginHost.for_plugin(pid, project).data.get(SELECT_KEY)
    except Exception:
        return DEFAULT_PROFILE_NAME
    return str(name or "").strip() or DEFAULT_PROFILE_NAME


def pick(installs, pid: str, project: str, name: str) -> dict:
    all_profiles = profiles(installs, pid, project)
    wanted = str(name or "").strip()
    if wanted and wanted not in all_profiles:
        raise ValueError(
            f"插件 {pid} 没有名为 {wanted} 的 system profile；"
            f"可选：{sorted(all_profiles) or '（未配置）'}")
    from .plugin_sdk import PluginHost

    data = PluginHost.for_plugin(pid, project).data
    if wanted:
        data.set(SELECT_KEY, wanted)
    else:
        data.delete(SELECT_KEY)
    return {"name": wanted or DEFAULT_PROFILE_NAME,
            **(all_profiles.get(wanted or DEFAULT_PROFILE_NAME)
               or {"mode": DEFAULT_SYSTEM_MODE, "text": ""})}


def current(installs, pid: str, project: str = "",
            name: str = "") -> Optional[dict]:
    all_profiles = profiles(installs, pid, project)
    if not all_profiles:
        return None
    wanted = str(name or "").strip() or selected(installs, pid, project)
    body = all_profiles.get(wanted)
    if body is None or not body.get("text"):
        return None
    return {"name": wanted, "mode": body["mode"], "text": body["text"]}


__all__ = ["SELECT_KEY", "DEFAULT_PROFILE_NAME", "file_of", "profiles",
           "selected", "pick", "current"]
