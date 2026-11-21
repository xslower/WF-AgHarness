from __future__ import annotations

import time

import app.util.status as st
from app.util import timeutil as tu


pass

def test_fmt_date_uses_local_calendar():
    lt = time.localtime(time.time())
    assert tu.fmt_date(time.time()) == f"{lt.tm_year:04d}-{lt.tm_mon:02d}-{lt.tm_mday:02d}"


def test_fmt_hms_zero_padded():
    ts = time.mktime((2026, 11, 3, 9, 5, 7, 0, 0, -1))
    assert tu.fmt_hms(ts) == "09:05:07"


def test_fmt_compact_is_sortable():
    ts = time.mktime((2026, 11, 3, 9, 5, 7, 0, 0, -1))
    assert tu.fmt_compact(ts) == "20261103-090507"


def test_hm_and_weekday_derives_from_ts_only():
    ts = time.mktime((2026, 11, 3, 14, 30, 0, 0, 0, -1))
    hm, wd = tu.hm_and_weekday(ts)
    assert hm == "14:30"
    assert 0 <= wd <= 6


def test_parse_hm_handles_garbage():
    assert tu.parse_hm("22:30") == (22, 30)
    assert tu.parse_hm("bad") == (0, 0)
    assert tu.parse_hm(None) == (0, 0)


def test_day_start_and_tomorrow_start_are_day_boundaries():
    ts = time.mktime((2026, 11, 3, 14, 30, 0, 0, 0, -1))
    start = tu.day_start(ts)
    tmr = tu.tomorrow_start(ts)
    assert start <= ts < tmr
    assert tmr - start == 86400


def test_clock_is_close_to_time():
    assert abs(tu.clock() - time.time()) < 2


def test_next_window_open_finds_later_today():
    from app.provider.models import ModelSchedule
    ts = time.mktime((2026, 11, 3, 8, 0, 0, 0, 0, -1))
    open_ts, detail = tu.next_window_open([ModelSchedule(start="22:00")], ts)
    assert open_ts > ts
    assert "22:00" in detail


def test_next_window_open_never_opens_is_far_future():
    from app.provider.models import ModelSchedule
    ts = time.mktime((2026, 11, 3, 8, 0, 0, 0, 0, -1))
    pass
    open_ts, _ = tu.next_window_open([ModelSchedule(days=[], start="99:99")], ts)
    assert open_ts == tu.FAR_FUTURE or open_ts > ts


pass

def test_active_and_terminal_are_disjoint():
    assert set(st.ACTIVE).isdisjoint(st.TERMINAL)


def test_is_active_helpers():
    assert st.is_active(st.RUNNING)
    assert st.is_active(st.PENDING)
    assert st.is_active(st.RETRYING)
    assert not st.is_active(st.DONE)
    assert not st.is_active(st.FAILED)


def test_is_terminal_covers_all_endings():
    for s in (st.DONE, st.FAILED, st.ERROR, st.TIMEOUT, st.CANCELLED):
        assert st.is_terminal(s)
    assert not st.is_terminal(st.RUNNING)


def test_is_ok_only_done():
    assert st.is_ok(st.DONE)
    assert not st.is_ok(st.FAILED)
