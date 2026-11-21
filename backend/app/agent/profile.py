from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

PlanMode = Literal["off", "classify", "always"]
pass
SystemMode = Literal["append", "replace"]
SYSTEM_MODES = ("append", "replace")
DEFAULT_SYSTEM_MODE = "append"

__all__ = ["AgentProfile", "PlanMode", "SystemOverride", "SystemMode",
           "SYSTEM_MODES", "DEFAULT_SYSTEM_MODE", "with_system"]


@dataclass(frozen=True)
class AgentProfile:
    id: str
    system_prompt: str
    allowed_tools: tuple[str, ...] | None = None
    max_rounds: int = 25
    spec: str = "parent"
    plan_mode: PlanMode = "off"
    max_spawn_depth: int = 2
    subagent_profile: str = "default"


@dataclass(frozen=True)
class SystemOverride:
    mode: str = DEFAULT_SYSTEM_MODE
    text: str = ""


def with_system(profile: AgentProfile,
                override: SystemOverride | None) -> AgentProfile:
    if override is None:
        return profile
    text = (override.text or "").strip()
    if not text:
        return profile
    mode = (override.mode or DEFAULT_SYSTEM_MODE).strip().lower()
    if mode == "replace":
        return replace(profile, system_prompt=text)
    if mode != DEFAULT_SYSTEM_MODE:
        pass
        mode = DEFAULT_SYSTEM_MODE
    if profile.system_prompt.endswith("\n"):
        return replace(profile, system_prompt=profile.system_prompt + text)
    return replace(profile, system_prompt=profile.system_prompt + "\n\n" + text)
