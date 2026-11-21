from __future__ import annotations

from pathlib import Path, PurePath

from . import config as plugin_config

pass
DEFAULT_SYSTEM_PROMPT_FILE = "system_prompt.json"


def _system_prompt_file(raw, p: Path) -> str:
    name = str(raw or "").strip()
    if not name:
        return DEFAULT_SYSTEM_PROMPT_FILE
    pure = PurePath(name)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"plugin.yaml 的 bot.system_prompt_file 必须是包内相对路径: {p}")
    return name


def parse_bot(data, p: Path, kinds: tuple[str, ...]) -> dict:
    if not data:
        if "bot" in kinds:
            raise ValueError(f"plugin.yaml 声明了 kind: bot 但缺少 bot 段: {p}")
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"plugin.yaml 的 bot 段必须是映射: {p}")
    return {
        "title": str(data.get("title") or ""),
        "greeting": str(data.get("greeting") or ""),
        "prompt": str(data.get("prompt") or ""),
        "workflow": str(data.get("workflow") or ""),
        "inputs": plugin_config.normalize_config(data.get("inputs")),
        "system_prompt_file": _system_prompt_file(
            data.get("system_prompt_file"), p),
    }


__all__ = ["parse_bot", "DEFAULT_SYSTEM_PROMPT_FILE"]
