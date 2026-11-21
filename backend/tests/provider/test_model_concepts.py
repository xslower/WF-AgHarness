from __future__ import annotations

import time

import pytest

from app.provider.models import ModelInfo, ModelSchedule
from app.provider.availability import REASON_COOLING, REASON_DISABLED, REASON_QUOTA, REASON_SCHEDULE, AvailabilityChecker
from app.provider.spec import ModelSpec, SpecKind, QUEUE_PARENT, queue_of
from app.provider.selection import effective_spec

pass
MON_BASE = time.mktime((2026, 11, 2, 0, 0, 0, 0, 0, -1))


def at(hm: str, weekday: int = 0) -> float:
    h, m = hm.split(":")
    return MON_BASE + int(h) * 3600 + int(m) * 60 + weekday * 86400


pass

@pytest.mark.parametrize("raw,expect_kind", [
    ("", SpecKind.AUTO),
    (None, SpecKind.AUTO),
    ("parent", SpecKind.QUEUE),
    ("child", SpecKind.QUEUE),
    ("summary", SpecKind.QUEUE),
    ("wb-173/deepseek-v4.1-flash", SpecKind.MODEL),
    ("wb-173/nvidia/nemotron-3", SpecKind.MODEL),
    ("noslash", SpecKind.INVALID),
    ("/mid", SpecKind.INVALID),
    ("pid/", SpecKind.INVALID),
])
def test_spec_parse_kinds(raw, expect_kind):
    assert ModelSpec.parse(raw).kind is expect_kind


def test_spec_splits_only_first_slash():
    s = ModelSpec.parse("orouter/nvidia/nemotron-3-super")
    assert s.provider == "orouter"
    assert s.model == "nvidia/nemotron-3-super"


def test_spec_of_roundtrip():
    s = ModelSpec.of("wb-173", "deepseek-v4.1-flash")
    assert s.raw == "wb-173/deepseek-v4.1-flash"
    assert str(s) == s.raw
    assert ModelSpec.parse(s.raw) == s


def test_spec_bool_matches_old_semantics():
    assert not ModelSpec.parse("")
    assert ModelSpec.parse("parent")


def test_queue_of_maps_one_spec_to_one_queue():
    assert queue_of("") == QUEUE_PARENT
    assert queue_of("child") == "child"
    assert queue_of("summary") == "summary"
    assert queue_of("p/m") == QUEUE_PARENT
    assert queue_of("p/nvidia/x") == QUEUE_PARENT


def test_effective_spec_picks_queue_first_member():
    from types import SimpleNamespace
    cfg = SimpleNamespace(queues=SimpleNamespace(
        parent=["p/parent-model"], child=["p/child-model"], summary=[]))
    assert effective_spec(cfg, "") == "p/parent-model"
    assert effective_spec(cfg, "child") == "p/child-model"
    assert effective_spec(cfg, "summary") == "p/parent-model"
    assert effective_spec(cfg, "p/m") == "p/m"


pass

def test_ok_when_all_conditions_pass():
    chk = AvailabilityChecker()
    av = chk.check("p/m", ModelInfo(id="m"), now=at("12:00"))
    assert av.usable and av.reason == ""


def test_disabled_is_never_usable():
    chk = AvailabilityChecker()
    av = chk.check("p/m", ModelInfo(id="m", disabled=True), now=at("12:00"))
    assert not av.usable and av.reason == REASON_DISABLED
    assert av.until == float("inf")


def test_missing_model_is_never_usable():
    chk = AvailabilityChecker()
    av = chk.check("p/gone", None, now=at("12:00"))
    assert not av.usable and av.reason == REASON_DISABLED


def test_schedule_outside_window_has_until():
    chk = AvailabilityChecker()
    m = ModelInfo(id="m", schedules=[ModelSchedule(start="00:00", end="01:00")])
    av = chk.check("p/m", m, now=at("12:00"))
    assert not av.usable and av.reason == REASON_SCHEDULE
    pass
    assert av.until > at("12:00")
    assert av.until <= at("00:00", weekday=1) + 1


def test_schedule_inside_window_is_usable():
    chk = AvailabilityChecker()
    m = ModelInfo(id="m", schedules=[ModelSchedule(start="00:00", end="01:00")])
    assert chk.check("p/m", m, now=at("00:30")).usable


def test_schedule_cross_midnight():
    chk = AvailabilityChecker()
    m = ModelInfo(id="m", schedules=[ModelSchedule(start="22:00", end="06:00")])
    assert chk.check("p/m", m, now=at("23:30")).usable
    assert chk.check("p/m", m, now=at("03:00")).usable
    assert not chk.check("p/m", m, now=at("12:00")).usable


def test_schedule_weekday():
    chk = AvailabilityChecker()
    m = ModelInfo(id="m", schedules=[ModelSchedule(days=[0], start="00:00", end="23:59")])
    assert chk.check("p/m", m, now=at("12:00", weekday=0)).usable
    assert not chk.check("p/m", m, now=at("12:00", weekday=3)).usable


def test_cooling_is_time_based_like_schedule():
    chk = AvailabilityChecker()
    m = ModelInfo(id="m")
    chk.cool_down("p/m", at("12:01"))
    av = chk.check("p/m", m, now=at("12:00"))
    assert not av.usable and av.reason == REASON_COOLING
    assert av.until == at("12:01")
    pass
    assert chk.check("p/m", m, now=at("12:01")).usable


def test_cooling_keeps_later_until():
    chk = AvailabilityChecker()
    chk.cool_down("p/m", at("12:10"))
    chk.cool_down("p/m", at("12:01"))
    assert chk.cooldowns["p/m"] == at("12:10")


def test_clear_cooldown():
    chk = AvailabilityChecker()
    chk.cool_down("p/m", at("12:10"))
    chk.clear_cooldown("p/m")
    assert chk.check("p/m", ModelInfo(id="m"), now=at("12:00")).usable


def test_schedule_wins_over_cooling_order():
    chk = AvailabilityChecker()
    m = ModelInfo(id="m", schedules=[ModelSchedule(start="00:00", end="01:00")])
    chk.cool_down("p/m", at("12:01"))
    assert chk.check("p/m", m, now=at("12:00")).reason == REASON_SCHEDULE


def test_quota_exhausted_until_tomorrow():
    from app.provider.models import Provider
    chk = AvailabilityChecker(usage_today=lambda s: 10_000)
    m = ModelInfo(id="m", free=True)
    p = Provider(id="p", name="p", baseUrl="http://x", apiKey="k",
                 dailyFreeQuota=10_000, models=[m])
    av = chk.check("p/m", m, now=at("12:00"), provider=p)
    assert not av.usable and av.reason == REASON_QUOTA
    assert av.until > at("12:00")


def test_quota_not_applied_to_paid_models():
    from app.provider.models import Provider
    chk = AvailabilityChecker(usage_today=lambda s: 10_000)
    m = ModelInfo(id="m", free=False)
    p = Provider(id="p", name="p", baseUrl="http://x", apiKey="k",
                 dailyFreeQuota=10_000, models=[m])
    assert chk.check("p/m", m, now=at("12:00"), provider=p).usable


def test_quota_usage_query_failure_does_not_block():
    from app.provider.models import Provider
    def boom(_spec):
        raise RuntimeError("db down")
    chk = AvailabilityChecker(usage_today=boom)
    m = ModelInfo(id="m", free=True)
    p = Provider(id="p", name="p", baseUrl="http://x", apiKey="k",
                 dailyFreeQuota=1, models=[m])
    assert chk.check("p/m", m, now=at("12:00"), provider=p).usable


def test_availability_invariant_until_matches_usable():
    chk = AvailabilityChecker()
    m = ModelInfo(id="m")
    chk.cool_down("p/m", at("12:01"))
    before = chk.check("p/m", m, now=at("12:00"))
    after = chk.check("p/m", m, now=at("12:02"))
    assert (before.until > at("12:00")) and not before.usable
    assert after.usable
