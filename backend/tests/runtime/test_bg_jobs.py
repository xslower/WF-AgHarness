from __future__ import annotations

import asyncio

from app.agent.bg_jobs import JobRegistry


def test_start_returns_immediately_and_result_drains_once():
    reg = JobRegistry()

    async def slow():
        await asyncio.sleep(0.05)
        return 0, "hello"

    async def go():
        job = reg.start("s1", "pytest -q", slow)
        pass
        assert job.job_id == "bg1"
        assert reg.drain_done("s1") == []
        await job.task
        done = reg.drain_done("s1")
        assert len(done) == 1 and done[0].exit == 0 and done[0].output == "hello"
        pass
        assert reg.drain_done("s1") == []

    asyncio.run(go())


def test_two_jobs_do_not_mix():

    async def make(out: str, delay: float):
        async def run():
            await asyncio.sleep(delay)
            return 0, out
        return run

    async def go():
        reg = JobRegistry()
        j1 = reg.start("s1", "pytest tests/a", await make("AAA", 0.01))
        j2 = reg.start("s1", "npm run build", await make("BBB", 0.02))
        await asyncio.gather(j1.task, j2.task)
        done = reg.drain_done("s1")
        assert [j.job_id for j in done] == ["bg1", "bg2"]
        text1, text2 = [j.result_text() for j in done]
        assert "job=bg1" in text1 and "pytest tests/a" in text1 and "AAA" in text1
        assert "job=bg2" in text2 and "npm run build" in text2 and "BBB" in text2
        assert "BBB" not in text1 and "AAA" not in text2

    asyncio.run(go())


def test_sessions_are_isolated():
    async def run():
        return 0, "x"

    async def go():
        reg = JobRegistry()
        a = reg.start("sess-a", "cmd-a", run)
        b = reg.start("sess-b", "cmd-b", run)
        await asyncio.gather(a.task, b.task)
        got_a = reg.drain_done("sess-a")
        assert [j.command for j in got_a] == ["cmd-a"]
        assert [j.job_id for j in reg.drain_done("sess-b")] == ["bg1"]

    asyncio.run(go())


def test_output_truncated_in_message():
    async def run():
        return 0, "x" * 20_000

    async def go():
        reg = JobRegistry()
        job = reg.start("s", "big", run)
        await job.task
        text = reg.drain_done("s")[0].result_text(limit=100)
        assert "已截断" in text and "20000" in text

    asyncio.run(go())


def test_timeout_and_error_status():
    async def boom():
        raise asyncio.TimeoutError()

    async def bad():
        raise RuntimeError("炸了")

    async def go():
        reg = JobRegistry()
        j1 = reg.start("s", "slow", boom)
        j2 = reg.start("s", "bad", bad)
        await asyncio.gather(j1.task, j2.task, return_exceptions=True)
        done = {j.job_id: j for j in reg.drain_done("s")}
        assert done["bg1"].status == "timeout"
        assert done["bg2"].status == "error" and "炸了" in done["bg2"].output

    asyncio.run(go())


def test_cancel_running_job():
    async def hang():
        await asyncio.sleep(10)
        return 0, "never"

    async def go():
        reg = JobRegistry()
        job = reg.start("s", "sleep 10", hang)
        assert reg.cancel("s", job.job_id) == 1
        await asyncio.gather(job.task, return_exceptions=True)
        done = reg.drain_done("s")
        assert done and done[0].status == "cancelled"

    asyncio.run(go())
