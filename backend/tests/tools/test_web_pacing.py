from __future__ import annotations

import asyncio
import time

import pytest

import app.tools.builtin.web.channels as ch
from app.tools.builtin.web import pacing as P
from app.tools.builtin.web.engines import BAIDU, SO360, SOGOU


class _Engine:
    def __init__(self, eid, pace=False):
        self.id = eid
        self.pace = pace


def test_only_rate_limited_engines_are_paced():
    assert SOGOU.pace and SO360.pace
    assert not BAIDU.pace


def test_skip_within_window_and_go_after(monkeypatch):
    now = time.time()
    monkeypatch.setattr(P.time, "time", lambda: now)
    P.mark("sogou", now=now)
    assert P.remaining("sogou", now=now) == pytest.approx(P.COOLDOWN_SEC)
    assert asyncio.run(P.gate(SOGOU, now=now)) == "skip"
    assert asyncio.run(P.gate(SOGOU, now=now + P.COOLDOWN_SEC)) == "go"


def test_near_end_waits_instead_of_skipping(monkeypatch):
    now = time.time()
    monkeypatch.setattr(P.time, "time", lambda: now)
    P.mark("so360", now=now)
    left = P.COOLDOWN_SEC - 1.0
    slept = []
    monkeypatch.setattr(P.asyncio, "sleep",
                        lambda s: _record(slept, s))
    assert asyncio.run(P.gate(SO360, now=now + left)) == "wait"
    assert slept and slept[0] <= P.WAIT_IF_NEAR_SEC


async def _record(out, s):
    out.append(s)


def test_unpaced_engine_always_goes_even_if_marked():
    P.mark("baidu")
    assert asyncio.run(P.gate(BAIDU)) == "go"


@pytest.mark.asyncio
async def test_search_one_engine_skips_paced_engine_on_second_call(monkeypatch):
    calls = []

    async def fake_page(engine, query, page, use_browser, timeout=8.0, crawler=None):
        calls.append((engine.id, page))
        return [{"title": f"结果{page}", "url": f"https://x.test/{page}",
                 "snippet": "摘要"}]

    monkeypatch.setattr(ch, "search_one_page", fake_page)
    items, err = await ch.search_one_engine(SOGOU, "q", 2, False)
    assert len(items) == 2 and not err and len(calls) == 2
    calls.clear()
    items2, err2 = await ch.search_one_engine(SOGOU, "q", 1, False)
    assert items2 == [] and err2 == "" and calls == []


@pytest.mark.asyncio
async def test_paging_within_one_search_is_not_skipped(monkeypatch):
    calls = []

    async def fake_page(engine, query, page, use_browser, timeout=8.0, crawler=None):
        calls.append(page)
        return [{"title": f"结果{page}", "url": f"https://x.test/{page}",
                 "snippet": "摘要"}]

    monkeypatch.setattr(ch, "search_one_page", fake_page)
    await ch.search_one_engine(SO360, "q", 3, False)
    assert calls == [1, 2, 3]


def test_lazy_browser_never_starts_until_acquired(monkeypatch):
    started = []

    async def fake_session():
        started.append(1)

        class _Inst:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False
        return _Inst()

    monkeypatch.setattr(ch, "browser_session", fake_session)
    lazy = ch.LazyBrowser(True)
    asyncio.run(lazy.close())
    assert started == []
    assert asyncio.run(lazy.acquire()) is not None
    asyncio.run(lazy.close())
    assert started == [1]
    assert ch.LazyBrowser(False).enabled is False
