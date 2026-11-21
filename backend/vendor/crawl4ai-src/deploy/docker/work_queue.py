
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Dict, Optional

logger = logging.getLogger("crawl4ai.workqueue")

JobFactory = Callable[[], Awaitable[None]]


class QueueFull(Exception):
    pass


class QuotaExceeded(Exception):
    pass


class WorkQueue:
    def __init__(self, maxsize: int = 0, workers: int = 4, per_principal: int = 0):
        self.maxsize = max(0, int(maxsize))
        self.workers = max(1, int(workers))
        self.per_principal = max(0, int(per_principal))
        self._q: Optional[asyncio.Queue] = None
        self._tasks: list = []
        self._counts: Dict[str, int] = {}

    @property
    def started(self) -> bool:
        return self._q is not None

    async def start(self) -> None:
        self._q = asyncio.Queue(maxsize=self.maxsize)
        self._tasks = [asyncio.create_task(self._worker()) for _ in range(self.workers)]
        logger.info(
            "work queue started (maxsize=%s, workers=%s, per_principal=%s)",
            self.maxsize or "unbounded", self.workers, self.per_principal or "unlimited",
        )

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        self._tasks = []
        self._q = None

    async def _worker(self) -> None:
        assert self._q is not None
        while True:
            principal, factory = await self._q.get()
            try:
                await factory()
            except Exception:
                logger.exception("background job failed")
            finally:
                self._release(principal)
                self._q.task_done()

    def _release(self, principal: Optional[str]) -> None:
        if not principal:
            return
        n = self._counts.get(principal, 0) - 1
        if n <= 0:
            self._counts.pop(principal, None)
        else:
            self._counts[principal] = n

    def submit(self, factory: JobFactory, principal: Optional[str] = None) -> None:
        if self._q is None:
            raise RuntimeError("work queue not started")
        if self.per_principal and principal:
            if self._counts.get(principal, 0) >= self.per_principal:
                raise QuotaExceeded()
        try:
            self._q.put_nowait((principal, factory))
        except asyncio.QueueFull:
            raise QueueFull()
        if principal:
            self._counts[principal] = self._counts.get(principal, 0) + 1


pass
_JOB_QUEUE: Optional[WorkQueue] = None


def set_job_queue(q: Optional[WorkQueue]) -> None:
    global _JOB_QUEUE
    _JOB_QUEUE = q


def get_job_queue() -> Optional[WorkQueue]:
    return _JOB_QUEUE
