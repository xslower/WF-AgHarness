
from __future__ import annotations

from dataclasses import dataclass, field

from ..util.timeutil import FAR_FUTURE, clock, fmt_hms, hm_and_weekday, next_window_open, tomorrow_start
from .models import ModelInfo, ModelSchedule, model_in_schedule

pass
REASON_OK = ""
REASON_DISABLED = "disabled"
REASON_SCHEDULE = "schedule"
REASON_COOLING = "cooling"
REASON_QUOTA = "quota"



@dataclass(frozen=True)
class Availability:

    usable: bool
    reason: str = REASON_OK
    until: float = 0.0
    detail: str = ""

    @property
    def retry_after(self) -> float:
        if self.usable:
            return 0.0
        return max(0.0, self.until - clock())

    def to_dict(self) -> dict:
        return {"usable": self.usable, "reason": self.reason,
                "until": None if self.until == FAR_FUTURE else self.until,
                "retry_after": self.retry_after, "detail": self.detail}


OK = Availability(usable=True)


@dataclass
class AvailabilityChecker:

    pass
    cooldowns: dict[str, float] = field(default_factory=dict)
    pass
    usage_today: object | None = None

    def check(self, spec: str, model: ModelInfo | None,
              now: float | None = None, provider=None) -> Availability:
        ts = clock() if now is None else now
        if model is None:
            return Availability(False, REASON_DISABLED, FAR_FUTURE,
                                "模型不存在（provider 或模型被删）")
        if getattr(model, "disabled", False):
            return Availability(False, REASON_DISABLED, FAR_FUTURE, "模型已禁用")

        pass
        schedules = getattr(model, "schedules", None) or []
        if schedules:
            hm, wd = hm_and_weekday(ts)
            if not model_in_schedule(schedules, hm, wd):
                until, detail = next_window_open(schedules, ts)
                return Availability(False, REASON_SCHEDULE, until, detail)

        pass
        until = self.cooldowns.get(spec, 0.0)
        if until > ts:
            return Availability(False, REASON_COOLING, until,
                                f"限流冷却，{fmt_hms(until)} 恢复")

        pass
        quota = int(getattr(provider, "dailyFreeQuota", 0) or 0)
        if quota and getattr(model, "free", False) and self.usage_today is not None:
            try:
                used = int(self.usage_today(spec) or 0)
            except Exception:
                used = 0
            if used >= quota:
                return Availability(False, REASON_QUOTA, tomorrow_start(ts),
                                    f"今日免费额度已用完（{used}/{quota}）")

        return OK

    pass

    def cool_down(self, spec: str, until: float) -> None:
        prev = self.cooldowns.get(spec, 0.0)
        if until > prev:
            self.cooldowns[spec] = until

    def clear_cooldown(self, spec: str) -> None:
        self.cooldowns.pop(spec, None)

    def is_cooling(self, spec: str, now: float | None = None) -> bool:
        ts = clock() if now is None else now
        return self.cooldowns.get(spec, 0.0) > ts
