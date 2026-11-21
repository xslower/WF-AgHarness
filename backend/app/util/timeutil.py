from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..provider.models import ModelSchedule

FMT_DATE = "%Y-%m-%d"
FMT_STAMP = "%Y-%m-%d %H:%M:%S"
FMT_COMPACT = "%Y%m%d-%H%M%S"

FAR_FUTURE = float("inf")


def clock() -> float:
    return time.time()


def fmt_date(ts: float) -> str:
    return time.strftime(FMT_DATE, time.localtime(ts))


def fmt_hms(ts: float) -> str:
    lt = time.localtime(ts)
    return f"{lt.tm_hour:02d}:{lt.tm_min:02d}:{lt.tm_sec:02d}"


def fmt_stamp(ts: float) -> str:
    return time.strftime(FMT_STAMP, time.localtime(ts))


def fmt_compact(ts: float) -> str:
    return time.strftime(FMT_COMPACT, time.localtime(ts))


def hm_and_weekday(ts: float) -> tuple[str, int]:
    lt = time.localtime(ts)
    return f"{lt.tm_hour:02d}:{lt.tm_min:02d}", lt.tm_wday


def parse_hm(text: str) -> tuple[int, int]:
    try:
        h, m = str(text).split(":")
        return int(h), int(m)
    except (ValueError, AttributeError):
        return 0, 0


def day_start(ts: float) -> float:
    lt = time.localtime(ts)
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday,
                        0, 0, 0, 0, 0, -1))


def tomorrow_start(ts: float) -> float:
    lt = time.localtime(ts)
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday + 1,
                        0, 0, 0, 0, 0, -1))


def next_window_open(schedules: "list[ModelSchedule]", ts: float,
                     days_ahead: int = 8) -> tuple[float, str]:
    lt = time.localtime(ts)
    base_day = day_start(ts)
    for day_offset in range(days_ahead + 1):
        base = base_day + day_offset * 86400
        wd = (lt.tm_wday + day_offset) % 7
        for s in schedules:
            if s.days and wd not in s.days:
                continue
            hh, mm = parse_hm(s.start or "00:00")
            cand = base + hh * 3600 + mm * 60
            if cand > ts:
                return cand, f"{fmt_hms(cand)} 开启"
    return FAR_FUTURE, "没有可用的时间窗"
