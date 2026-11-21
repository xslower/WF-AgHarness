from __future__ import annotations

import asyncio
import time

import pytest

from app.security.engine import ApprovalManager, Risk


def _manager() -> ApprovalManager:
    return ApprovalManager()


pass
def test_pending_carries_session_id():
    am = _manager()
    pa = am.create("rm x", [Risk(target="x")], "要确认", session_id="s1")
    assert pa.session_id == "s1"
    assert am._pending[pa.id].session_id == "s1"


def test_list_filters_by_session():
    am = _manager()
    am.create("a", [], "r", session_id="s1")
    am.create("b", [], "r", session_id="s2")
    assert len(am.list(session_id="s1")) == 1
    assert len(am.list(session_id="s2")) == 1


def test_list_without_session_returns_all():
    am = _manager()
    am.create("a", [], "r", session_id="s1")
    am.create("b", [], "r", session_id="s2")
    assert len(am.list()) == 2


def test_list_with_unknown_session_is_empty():
    am = _manager()
    am.create("a", [], "r", session_id="s1")
    assert am.list(session_id="nope") == []


pass
@pytest.mark.asyncio
async def test_cancel_session_releases_waiting_tool():
    am = _manager()
    pa = am.create("rm x", [], "要确认", session_id="s1")
    task = asyncio.create_task(am.wait(pa))
    await asyncio.sleep(0.01)
    assert not task.done()

    assert am.cancel_session("s1") == 1
    ok = await asyncio.wait_for(task, timeout=2)
    assert ok is False
    assert am._pending == {}


def test_cancel_session_only_affects_that_session():
    am = _manager()
    am.create("a", [], "r", session_id="s1")
    am.create("b", [], "r", session_id="s2")
    assert am.cancel_session("s1") == 1
    left = am.list(session_id="s2")
    assert len(left) == 1


def test_cancel_empty_session_is_noop():
    am = _manager()
    am.create("a", [], "r", session_id="s1")
    assert am.cancel_session("") == 0
    assert len(am._pending) == 1


def test_cancel_unknown_session_is_noop():
    am = _manager()
    assert am.cancel_session("nope") == 0


pass
@pytest.mark.asyncio
async def test_wait_gives_up_when_stopped():
    am = _manager()
    pa = am.create("rm x", [], "要确认", session_id="s1")
    flag = {"stop": False}

    async def stopper():
        await asyncio.sleep(0.1)
        flag["stop"] = True

    asyncio.create_task(stopper())
    t0 = time.monotonic()
    ok = await asyncio.wait_for(am.wait(pa, stop_check=lambda: flag["stop"]),
                                timeout=5)
    elapsed = time.monotonic() - t0
    assert ok is False
    assert elapsed < 2, f"应该很快放弃，实际 {elapsed:.2f}s"
    assert pa.id not in am._pending


@pytest.mark.asyncio
async def test_wait_returns_true_when_approved_midway():
    am = _manager()
    pa = am.create("rm x", [], "要确认", session_id="s1")

    async def approver():
        await asyncio.sleep(0.1)
        am.decide(pa.id, True)

    asyncio.create_task(approver())
    assert await asyncio.wait_for(am.wait(pa, stop_check=lambda: False),
                                  timeout=5) is True


@pytest.mark.asyncio
async def test_broken_stop_check_does_not_break_waiting():
    am = _manager()
    pa = am.create("rm x", [], "要确认", session_id="s1")

    def boom():
        raise RuntimeError("stop_check 坏了")

    async def approver():
        await asyncio.sleep(0.1)
        am.decide(pa.id, True)

    asyncio.create_task(approver())
    assert await asyncio.wait_for(am.wait(pa, stop_check=boom), timeout=5) is True


@pytest.mark.asyncio
async def test_decide_after_cancel_does_not_crash():
    am = _manager()
    pa = am.create("rm x", [], "要确认", session_id="s1")
    am.cancel_session("s1")
    assert am.decide(pa.id, True) is False
