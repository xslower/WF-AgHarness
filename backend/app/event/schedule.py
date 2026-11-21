from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import datetime
from typing import Any, Awaitable, Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ..store import layout
from ..store.timer_db import TimerDb

logger = logging.getLogger("harness.timers")

pass
Handler = Callable[[dict], Awaitable[None]]

pass
TOLERANCE = 0.001
pass
MAX_MISSED = 10_000


def make_trigger(kind: str, spec: str):
    if kind == "every":
        try:
            seconds = float(spec)
        except (TypeError, ValueError):
            raise ValueError(f"周期任务间隔必须是秒数：{spec!r}") from None
        if seconds <= 0:
            raise ValueError(f"周期任务间隔必须 > 0 秒：{spec!r}")
        return IntervalTrigger(seconds=seconds)
    if kind == "cron":
        return CronTrigger.from_crontab(str(spec).strip())
    raise ValueError(f"未知的定时任务类型：{kind!r}")


def next_fire(kind: str, spec: str, base: Optional[float] = None) -> Optional[float]:
    trigger = make_trigger(kind, spec)
    now = datetime.now(trigger.timezone) if base is None else \
        datetime.fromtimestamp(base, trigger.timezone)
    nxt = trigger.get_next_fire_time(None, now)
    return None if nxt is None else nxt.timestamp()


class Timers:

    def __init__(self, db: TimerDb | None = None, owner: str = "backend") -> None:
        self._db = db
        self._db_path: str = ""
        self._owner = owner
        self._lock = threading.RLock()
        self._rules: dict[str, dict[str, Any]] = {}
        self._subs: dict[str, dict[str, Handler]] = {}
        self._actions: dict[str, Handler] = {}

        self._sched: Optional[AsyncIOScheduler] = None
        self._running: dict[str, bool] = {}

    pass
    @property
    def db(self) -> TimerDb:
        if self._db is not None:
            return self._db
        path = str(layout.timers_db())
        if self._db_path != path:
            self._db = TimerDb()
            self._db_path = path
        return self._db

    pass
    def on(self, name: str, fn: Handler, key: str = "") -> Callable[[], None]:
        k = key or getattr(fn, "__name__", "") or repr(id(fn))
        with self._lock:
            self._subs.setdefault(name, {})[k] = fn
        return lambda: self.off(name, key=k)

    def off(self, name: str, key: str = "") -> None:
        with self._lock:
            subs = self._subs.get(name)
            if subs is None:
                return
            if key:
                subs.pop(key, None)
            else:
                subs.clear()
            if not subs:
                self._subs.pop(name, None)

    def subscribers(self, name: str) -> list[Handler]:
        with self._lock:
            return self._subscribers_locked(name)

    def _subscribers_locked(self, name: str) -> list[Handler]:
        subs = list(self._subs.get(name, {}).values())
        if subs:
            return subs
        rule = self._rules.get(name) or {}
        fn = self._actions.get(str(rule.get("action") or ""))
        return [fn] if fn is not None else []


    def set_action_handler(self, action: str, fn: Handler) -> None:
        with self._lock:
            self._actions[action] = fn

    pass
    def register(self, name: str, kind: str, spec: str,
                 payload: dict | None = None, action: str = "session") -> None:
        _check_name(name)
        trigger = make_trigger(kind, spec)
        with self._lock:
            self._rules[name] = {
                "trigger": trigger, "kind": kind, "spec": str(spec),
                "action": action, "payload": dict(payload or {}),
                "next": trigger.get_next_fire_time(None,
                                                   _now_in(trigger.timezone)),
            }
            sched = self._sched
            if sched is not None:
                self._schedule(sched, name)
        try:
            self.db.upsert(name, kind=kind, spec=str(spec), payload=payload or {},
                           owner=self._owner, action=action)
        except Exception:
            logger.warning("定时任务落库失败：%s", name, exc_info=True)

    def remove(self, name: str) -> bool:
        gone = self.detach(name)
        try:
            self.db.delete(name)
        except Exception:
            logger.warning("定时任务删除落库失败：%s", name, exc_info=True)
        return gone

    def detach(self, name: str) -> bool:
        with self._lock:
            gone = self._rules.pop(name, None) is not None
            self._subs.pop(name, None)
            sched = self._sched
        if sched is not None:
            try:
                sched.remove_job(name)
            except Exception:
                logger.debug("remove job 失败（可能尚未调度）: %s", name)
        return gone

    def jobs(self) -> list[dict]:
        with self._lock:
            sched = self._sched
            out: list[dict] = []
            for name in sorted(self._rules):
                rule = self._rules[name]
                nxt = None
                if sched is not None:
                    try:
                        job = sched.get_job(name)
                    except Exception:
                        job = None
                    if job is not None and job.next_run_time is not None:
                        nxt = job.next_run_time.isoformat(timespec="seconds")
                out.append({"name": name, "kind": rule["kind"],
                            "spec": rule["spec"], "action": rule["action"],
                            "subscribers": len(self._subs.get(name, {})),
                            "nextRun": nxt})
            return out

    def _schedule(self, sched: AsyncIOScheduler, name: str) -> None:
        sched.add_job(self._fire, trigger=self._rules[name]["trigger"],
                      args=[name], id=name, name=name, replace_existing=True)

    pass
    async def _fire(self, name: str) -> None:
        with self._lock:
            rule = self._rules.get(name)
            if rule is None:
                return
            trigger = rule["trigger"]
            now = _now_in(trigger.timezone)
            first = rule["next"] or trigger.get_next_fire_time(None, now)
            due, missed = first, 0
            while due is not None and (missed == 0
                                       or due.timestamp() <= now.timestamp() + TOLERANCE):
                missed += 1
                due = trigger.get_next_fire_time(due, due)
                if missed > MAX_MISSED:
                    logger.warning("定时任务 %s 单轮漏跑超过 %s 次，后续不再折算",
                                   name, MAX_MISSED)
                    break
            rule["next"] = due
            subs = self._subscribers_locked(name)

            if self._running.get(name, 0):
                logger.info("定时任务 %s 上一轮仍在执行，本轮跳过", name)
                return
            if first is None or not subs:
                logger.debug("定时任务 %s 到点但无订阅者，不执行", name)
                return
            pass
            self._running[name] = len(subs)

        task = {
            "name": name,
            "action": rule.get("action") or "",
            "payload": dict(rule.get("payload") or {}),
            "scheduledAt": first.timestamp(),
            "firedAt": time.time(),
            "lateMs": round((now.timestamp() - first.timestamp()) * 1000, 1),
            "missed": missed,
        }
        for fn in subs:
            pass
            pass
            asyncio.create_task(self._run(name, fn, task))

    async def _run(self, name: str, fn: Handler, task: dict) -> None:
        try:
            await fn(dict(task))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("定时任务订阅者失败：%s", name, exc_info=True)
        finally:
            with self._lock:
                left = max(0, self._running.get(name, 1) - 1)
                if left:
                    self._running[name] = left
                else:
                    self._running.pop(name, None)


    pass
    def start(self, owner: str = "") -> None:
        self._owner = owner or self._owner
        with self._lock:
            if self._sched is not None:
                return
            self._load_db()
            sched = AsyncIOScheduler(
                job_defaults={"coalesce": True, "max_instances": 1,
                              "misfire_grace_time": None})
            for name, rule in self._rules.items():
                pass
                rule["next"] = rule["trigger"].get_next_fire_time(
                    None, _now_in(rule["trigger"].timezone))
                self._schedule(sched, name)
            self._sched = sched
        sched.start()

    def refresh(self) -> None:
        with self._lock:
            self._rules.clear()
            self._load_db()
            sched = self._sched
            if sched is None:
                return
            for job in sched.get_jobs():
                if job.id not in self._rules:
                    try:
                        sched.remove_job(job.id)
                    except Exception:
                        logger.debug("refresh 移除 job 失败: %s", job.id)
            for name in self._rules:
                self._schedule(sched, name)

    def _load_db(self) -> None:
        try:
            rows = self.db.load_all(owner=self._owner, enabled_only=True)
        except Exception:
            logger.warning("定时任务库读取失败，按空表启动", exc_info=True)
            return
        for row in rows:
            try:
                trigger = make_trigger(row["kind"], row["spec"])
            except ValueError:
                logger.warning("定时任务定义非法，跳过：%s %s=%s",
                               row["name"], row["kind"], row["spec"])
                continue
            self._rules[row["name"]] = {
                "trigger": trigger, "kind": row["kind"], "spec": row["spec"],
                "action": row["action"], "payload": row["payload"],
                "next": trigger.get_next_fire_time(None, _now_in(trigger.timezone)),
            }

    def stop(self) -> None:
        with self._lock:
            sched, self._sched = self._sched, None
            pass
            self._db, self._db_path = None, ""
        if sched is not None:
            try:
                sched.shutdown(wait=False)
            except Exception:
                logger.debug("调度器关停失败", exc_info=True)


def _now_in(tz) -> datetime:
    return datetime.now(tz)


def _check_name(name: str) -> None:
    if not name or "." in name or "*" in name or "/" in name:
        raise ValueError(
            f"定时任务名不能为空、不能含 '.' / '*' / '/'：{name!r}")


pass
TIMERS = Timers()
