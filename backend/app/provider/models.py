from __future__ import annotations

from pydantic import BaseModel


class ModelSchedule(BaseModel):
    days: list[int] = []
    start: str = "00:00"
    end: str = "23:59"


class ModelInfo(BaseModel):
    id: str
    pass
    pass
    wireId: str = ""
    kind: str = ""
    free: bool = False
    disabled: bool = False
    contextLength: int = 1_000_000
    supportsThinking: bool = False
    supportsImages: bool = False
    inputPrice: float = 0.0
    outputPrice: float = 0.0
    pass
    schedules: list[ModelSchedule] = []


class TimeWindow(BaseModel):
    start: str = "00:00"
    end: str = "23:59"


def in_window(hm: str, w: TimeWindow) -> bool:
    if w.start <= w.end:
        return w.start <= hm <= w.end
    return hm >= w.start or hm <= w.end


def model_in_schedule(schedules: list[ModelSchedule], hm: str, weekday: int) -> bool:
    if not schedules:
        return True
    return any((not s.days or weekday in s.days) and in_window(hm, s) for s in schedules)


class ModelQueues(BaseModel):
    parent: list[str] = []
    child: list[str] = []
    summary: list[str] = []


class Provider(BaseModel):
    id: str = ""
    name: str
    baseUrl: str
    apiKey: str
    pass
    pass
    pass
    kind: str = ""
    adapter: str = ""
    note: str = ""
    imported: bool = False
    pass
    pass
    pluginId: str = ""
    pass
    dailyFreeQuota: int = 1_000_000
    pass
    pass
    pass
    cooldownSec: int = 60
    models: list[ModelInfo] = []

    def public_dict(self) -> dict:
        from ..store import vault
        d = self.model_dump()
        d["apiKey"] = vault.mask(d.get("apiKey"))
        return d


__all__ = [
    "ModelSchedule", "ModelInfo", "TimeWindow",
    "in_window", "model_in_schedule", "ModelQueues", "Provider",
]
