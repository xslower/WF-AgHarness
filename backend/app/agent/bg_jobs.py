from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

import app.util.status as st

from typing import Awaitable, Callable, Optional

logger = logging.getLogger("harness.bg_jobs")

pass
BG_TIMEOUT = 30 * 60
pass
OUTPUT_KEEP = 40_000


@dataclass
class BgJob:
    job_id: str
    command: str
    started: float = field(default_factory=time.time)
    status: str = st.RUNNING
    exit: Optional[int] = None
    output: str = ""
    finished: float = 0.0
    task: Optional[asyncio.Task] = None

    def result_text(self, limit: int = 8000) -> str:
        head = f"[后台命令完成] job={self.job_id} | {self.status}"
        if self.exit is not None:
            head += f" | exit={self.exit}"
        head += f" | 耗时 {self.finished - self.started:.1f}s\n命令: {self.command}"
        body = self.output or "(无输出)"
        if len(body) > limit:
            body = body[:limit] + f"\n…[输出共 {len(self.output)} 字符，已截断]"
        return f"{head}\n---\n{body}"


class JobRegistry:

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, BgJob]] = {}
        self._seq: dict[str, int] = {}

    def _bucket(self, sid: str) -> dict[str, BgJob]:
        return self._jobs.setdefault(sid or "", {})

    def start(self, sid: str, command: str,
              runner: Callable[[], Awaitable[tuple[Optional[int], str]]],
              on_done: Optional[Callable[[BgJob], None]] = None) -> BgJob:
        bucket = self._bucket(sid)
        n = self._seq.get(sid, 0) + 1
        self._seq[sid] = n
        job = BgJob(job_id=f"bg{n}", command=command)
        bucket[job.job_id] = job

        async def _wrap() -> None:
            try:
                exit_code, output = await runner()
                job.exit = exit_code
                job.output = (output or "")[:OUTPUT_KEEP]
                job.status = st.DONE
            except asyncio.TimeoutError:
                job.status = st.TIMEOUT
                job.output = f"命令超时({BG_TIMEOUT}s)后被终止"
            except asyncio.CancelledError:
                job.status = st.CANCELLED
                job.output = "任务被取消"
                raise
            except Exception as e:
                job.status = st.ERROR
                job.output = f"{type(e).__name__}: {e}"
            finally:
                job.finished = time.time()
                if on_done is not None:
                    try:
                        on_done(job)
                    except Exception:
                        logger.debug("bg job on_done 回调失败: %s", job.job_id, exc_info=True)

        job.task = asyncio.create_task(_wrap())
        return job

    def drain_done(self, sid: str) -> list[BgJob]:
        bucket = self._bucket(sid)
        done = [j for j in bucket.values() if not st.is_active(j.status)]
        for j in done:
            bucket.pop(j.job_id, None)
        return sorted(done, key=lambda j: j.finished)

    def snapshot(self, sid: str) -> list[BgJob]:
        return sorted(self._bucket(sid).values(), key=lambda j: j.started)

    def cancel(self, sid: str, job_id: str = "") -> int:
        n = 0
        for j in list(self._bucket(sid).values()):
            if job_id and j.job_id != job_id:
                continue
            if j.task is not None and not j.task.done():
                pass
                pass
                if st.is_active(j.status):
                    j.status = "cancelled"
                    j.finished = time.time()
                j.task.cancel()
                n += 1
        return n

    def clear(self, sid: str) -> None:
        self._jobs.pop(sid, None)
        self._seq.pop(sid, None)



