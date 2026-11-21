from __future__ import annotations

from typing import Iterable

from ...agent.profile import AgentProfile
from .default import DEFAULT_PROFILE
from .researcher import RESEARCHER_PROFILE
from .reviewer import REVIEWER_PROFILE

BUILTIN_PROFILES: tuple[AgentProfile, ...] = (
    DEFAULT_PROFILE, REVIEWER_PROFILE, RESEARCHER_PROFILE)


class ProfileRegistry:

    def __init__(self) -> None:
        self._items: dict[str, AgentProfile] = {}

    def register(self, profile: AgentProfile) -> AgentProfile:
        if not profile.id:
            raise ValueError("AgentProfile 缺少 id")
        if profile.id in self._items:
            raise ValueError(f"AgentProfile 重复注册: {profile.id}")
        self._items[profile.id] = profile
        return profile

    def get(self, profile_id: str) -> AgentProfile | None:
        return self._items.get(profile_id)

    def all(self) -> list[AgentProfile]:
        return list(self._items.values())


def build_profile_registry(extra: Iterable[AgentProfile] | None = None) -> ProfileRegistry:
    reg = ProfileRegistry()
    for profile in BUILTIN_PROFILES:
        reg.register(profile)
    for profile in extra or ():
        try:
            reg.register(profile)
        except ValueError:
            continue
    return reg
