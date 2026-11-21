from __future__ import annotations

import asyncio
import time

import pytest

from app.event.schedule import Timers, make_trigger, next_fire
from app.store.timer_db import TimerDb


def _db(tmp_path) -> TimerDb:
    return TimerDb(tmp_path / "timers.db")


@pytest.fixture
def timers(tmp_path):
    t = Timers(db=_db(tmp_path))
    yield t
    t.stop()


async def _wait_async(pred, timeout: float = 3.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return True
        await asyncio.sleep(0.01)
    return False


def _run(coro_fn):
    return asyncio.run(coro_fn())


def test_every_calls_subscriber(tmp_path):
    t = Timers(db=_db(tmp_path))
    seen: list[dict] = []

    async def cb(task: dict) -> None:
        seen.append(task)

    async def go() -> None:
        t.register("tick", "every", "0.05")
        t.on("tick", cb)
        t.start()
        try:
            assert await _wait_async(lambda: len(seen) >= 2)
        finally:
            t.stop()

    try:
        _run(go)
    finally:
        t.stop()
    first = seen[0]
    assert first["name"] == "tick"
    assert first["missed"] >= 1
    assert first["lateMs"] >= 0
    assert first["firedAt"] >= first["scheduledAt"]


def test_stop_ends_triggering(tmp_path):
    t = Timers(db=_db(tmp_path))
    count = 0

    async def cb(_task: dict) -> None:
        nonlocal count
        count += 1

    async def go() -> None:
        t.register("tick", "every", "0.05")
        t.on("tick", cb)
        t.start()
        assert await _wait_async(lambda: count >= 2)
        t.stop()
        frozen = count
        await asyncio.sleep(0.3)
        assert count == frozen

    try:
        _run(go)
    finally:
        t.stop()


def test_remove_ends_triggering(tmp_path):
    t = Timers(db=_db(tmp_path))
    count = 0

    async def cb(_task: dict) -> None:
        nonlocal count
        count += 1

    async def go() -> None:
        t.register("tick", "every", "0.05")
        t.on("tick", cb)
        t.start()
        assert await _wait_async(lambda: count >= 1)
        assert t.remove("tick") is True
        frozen = count
        await asyncio.sleep(0.2)
        assert count == frozen
        assert t.jobs() == []
        assert t.remove("tick") is False

    try:
        _run(go)
    finally:
        t.stop()
    assert t.db.get("tick") is None


def test_same_name_replaces_job(tmp_path):
    t = Timers(db=_db(tmp_path))
    t.register("tick", "every", "0.05")
    t.register("tick", "every", "0.10")
    assert [j["name"] for j in t.jobs()] == ["tick"]
    assert [r["name"] for r in t.db.load_all()] == ["tick"]
    assert t.db.get("tick")["spec"] == "0.10"


def test_cron_registers_and_reports_next_run(tmp_path):
    t = Timers(db=_db(tmp_path))
    t.register("nightly", "cron", "0 3 * * *")
    jobs = t.jobs()
    assert len(jobs) == 1
    assert jobs[0]["kind"] == "cron"
    nxt = next_fire("cron", "0 3 * * *")
    assert nxt is not None
    assert "T03:00:00" in time.strftime("%Y-%m-%dT%H:%M:%S",
                                        time.localtime(nxt))


def test_bad_cron_expression_raises(timers):
    with pytest.raises(ValueError):
        timers.register("x", "cron", "not a cron")
    with pytest.raises(ValueError):
        timers.register("x", "cron", "0 3 * *")
    with pytest.raises(ValueError):
        make_trigger("nope", "1")
    assert timers.jobs() == []


def test_name_must_be_url_safe(timers):
    for bad in ("", "a.b", "a*", "a/b"):
        with pytest.raises(ValueError):
            timers.register(bad, "every", "1")


def test_every_rejects_non_positive(timers):
    with pytest.raises(ValueError):
        timers.register("tick", "every", "0")
    with pytest.raises(ValueError):
        timers.register("tick", "every", "abc")


def test_no_subscriber_means_no_run(tmp_path):
    t = Timers(db=_db(tmp_path))

    async def go() -> None:
        t.register("nobody", "every", "0.05")
        t.start()
        try:
            await asyncio.sleep(0.3)
        finally:
            t.stop()

    try:
        _run(go)
    finally:
        t.stop()
    assert t.jobs()[0]["subscribers"] == 0


def test_subscriber_error_does_not_kill_others(tmp_path):
    t = Timers(db=_db(tmp_path))
    good: list[int] = []

    async def bad(_task: dict) -> None:
        raise RuntimeError("boom")

    async def ok(_task: dict) -> None:
        good.append(1)

    async def go() -> None:
        t.register("tick", "every", "0.05")
        t.on("tick", bad, key="bad")
        t.on("tick", ok, key="ok")
        t.start()
        try:
            assert await _wait_async(lambda: len(good) >= 2)
        finally:
            t.stop()

    try:
        _run(go)
    finally:
        t.stop()


def test_slow_subscriber_does_not_block_schedule(tmp_path):
    t = Timers(db=_db(tmp_path))
    hits: list[int] = []

    async def slow(_task: dict) -> None:
        hits.append(1)
        await asyncio.sleep(5)

    async def go() -> None:
        t.register("long", "every", "0.05")
        t.on("long", slow)
        t.start()
        try:
            pass
            await asyncio.sleep(0.3)
            assert len(hits) == 1
        finally:
            t.stop()

    try:
        _run(go)
    finally:
        t.stop()


def test_action_handler_dispatches_without_on(tmp_path):
    t = Timers(db=_db(tmp_path))
    seen: list[dict] = []

    async def handler(task: dict) -> None:
        seen.append(task)

    async def go() -> None:
        t.set_action_handler("session", handler)
        t.register("daily", "every", "0.05", action="session",
                   payload={"project": "p", "prompt": "hi"})
        t.start()
        try:
            assert await _wait_async(lambda: len(seen) >= 1)
        finally:
            t.stop()

    try:
        _run(go)
    finally:
        t.stop()
    assert seen[0]["action"] == "session"
    assert seen[0]["payload"]["prompt"] == "hi"


def test_definitions_survive_restart(tmp_path):
    db = _db(tmp_path)

    async def go() -> list[dict]:
        first = Timers(db=db, owner="backend")
        first.register("daily", "cron", "0 9 * * mon", action="workflow",
                       payload={"project": "p", "workflow": "日报"})
        first.stop()
        second = Timers(db=_db(tmp_path), owner="backend")
        second.start()
        try:
            return second.jobs()
        finally:
            second.stop()

    jobs = asyncio.run(go())
    assert [j["name"] for j in jobs] == ["daily"]
    assert jobs[0]["action"] == "workflow"


def test_start_loads_only_own_owner(tmp_path):
    db = _db(tmp_path)
    db.upsert("be", kind="every", spec="3600", payload={},
              owner="backend", action="session")
    db.upsert("fe", kind="every", spec="3600", payload={},
              owner="frontend", action="session")

    async def go() -> list[str]:
        t = Timers(db=db, owner="backend")
        t.start()
        try:
            return [j["name"] for j in t.jobs()]
        finally:
            t.stop()

    assert asyncio.run(go()) == ["be"]


def test_global_singleton_is_a_timers_instance():
    from app.event.schedule import TIMERS
    assert isinstance(TIMERS, Timers)
