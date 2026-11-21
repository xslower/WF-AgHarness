from __future__ import annotations

import asyncio
import json
import pathlib

from app.chat.context_view import build_view
from app.chat.compaction import plan_batch


def _mk_session(c, n: int, project: str = "") -> dict:
    s = c.sessions.create("压缩测试", project)
    msgs = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"消息{i} " + "x" * 200}
            for i in range(n)]
    s["messages"] = msgs
    c.sessions.save(s)
    return c.sessions.get(s["id"])


def _add_provider(c, ctx_len: int = 100_000) -> None:
    from app.provider.models import ModelInfo, Provider
    c.store.config.providers.append(Provider(
        id="p1", name="t", baseUrl="http://x", apiKey="k",
        models=[ModelInfo(id="m1", contextLength=ctx_len)]))
    c.store.config.queues.parent = ["t/m1"]


def _project(tmp_dirs, name: str) -> str:
    project = str(tmp_dirs / name)
    pathlib.Path(project, ".agent").mkdir(parents=True, exist_ok=True)
    return project


async def _noop(ev):
    pass



def _patch_memo(monkeypatch, c, fn):
    import re

    async def fake(prompt, sid, hedge_ms=0):
        folded = [{"_seq": int(x)} for x in re.findall(r"msg#(\d+)", prompt)]
        return await fn(folded, hedge_ms, sid)
    monkeypatch.setattr(c.compactor, "hedged_call", fake)


async def _call(c, session, emit):
    from app.chat.compaction_policy import maybe_compact
    await maybe_compact(c, session, "", emit)


class TestCompactFlow:

    def test_compact_writes_segment_and_keeps_db(self, tmp_dirs, container, monkeypatch):
        c = container
        project = _project(tmp_dirs, "proj-compaction")
        s = _mk_session(c, 30, project)
        s["last_usage"] = {"prompt_tokens": 90_000}
        _add_provider(c)
        c.store.config.settings.compactStrategies = ["legacy"]
        c.store.config.settings.compactStrategies = ["legacy"]
        c.store.config.settings.compactSummaryMode = "per_message"

        emitted: list[dict] = []

        async def emit(ev):
            emitted.append(ev)

        async def fake_summarize(folded, session_id=""):
            return {m["_seq"]: f"总结{m['_seq']}" for m in folded
                    if m.get("role") in ("user", "assistant")}
        monkeypatch.setattr(c.compactor, "summarize_batch", fake_summarize)

        asyncio.run(_call(c, s, emit))

        pass
        after = c.sessions.get(s["id"])
        assert len(after["messages"]) == 30
        assert after["messages"][0]["content"].startswith("消息0")

        pass
        segs = c.sessions.get_compactions(project, s["id"])
        assert segs and segs[-1]["upto_seq"] == 24

        pass
        view = build_view(after["messages"], segs)
        raw = json.dumps(after["messages"], ensure_ascii=False)
        assert len(json.dumps(view, ensure_ascii=False)) < len(raw) * 0.5

        pass
        flat = json.dumps(view, ensure_ascii=False)
        assert "[msg#0]" in flat

        pass
        est = [e for e in emitted if e.get("type") == "ctx_estimate"]
        assert est and 0 < est[-1]["used"] < 90_000

    def test_second_compaction_appends_without_touching_first(
            self, tmp_dirs, container, monkeypatch):
        c = container
        project = _project(tmp_dirs, "proj-compaction2")
        s = _mk_session(c, 30, project)
        s["last_usage"] = {"prompt_tokens": 90_000}
        _add_provider(c)
        c.store.config.settings.compactStrategies = ["legacy"]
        c.store.config.settings.compactStrategies = ["legacy"]
        c.store.config.settings.compactSummaryMode = "per_message"

        async def fake_summarize(folded, session_id=""):
            return {m["_seq"]: f"总结{m['_seq']}" for m in folded
                    if m.get("role") in ("user", "assistant")}
        monkeypatch.setattr(c.compactor, "summarize_batch", fake_summarize)

        asyncio.run(_call(c, s, _noop))
        segs1 = c.sessions.get_compactions(project, s["id"])
        first_items = json.dumps(segs1[0]["items"], ensure_ascii=False)

        pass
        s2 = c.sessions.get(s["id"])
        s2["messages"] += [{"role": "user", "content": f"追加{i} " + "y" * 200}
                           for i in range(12)]
        c.sessions.save(s2)
        s2 = c.sessions.get(s["id"])
        s2["last_usage"] = {"prompt_tokens": 95_000}
        asyncio.run(_call(c, s2, _noop))

        segs2 = c.sessions.get_compactions(project, s["id"])
        assert len(segs2) == 2
        pass
        assert json.dumps(segs2[0]["items"], ensure_ascii=False) == first_items
        assert segs2[1]["upto_seq"] == 42 - 6

    def test_l2_failure_keeps_original_and_allows_retry(
            self, tmp_dirs, container, monkeypatch):
        c = container
        project = _project(tmp_dirs, "proj-compaction3")
        s = _mk_session(c, 20, project)
        s["last_usage"] = {"prompt_tokens": 90_000}
        _add_provider(c)
        c.store.config.settings.compactStrategies = ["legacy"]
        c.store.config.settings.compactSummaryMode = "per_message"
        calls = []

        async def boom(_, session_id=""):
            calls.append(1)
            raise RuntimeError("模型挂了")
        monkeypatch.setattr(c.compactor, "summarize_batch", boom)

        asyncio.run(_call(c, s, _noop))
        assert len(calls) == 2
        assert c.sessions.get_compactions(project, s["id"]) == []
        pass
        assert len(c.sessions.get(s["id"])["messages"]) == 20
        pass
        async def ok(folded, session_id=""):
            return {m["_seq"]: f"总结{m['_seq']}" for m in folded}
        monkeypatch.setattr(c.compactor, "summarize_batch", ok)
        s["last_usage"] = {"prompt_tokens": 90_000}
        asyncio.run(_call(c, s, _noop))
        segs = c.sessions.get_compactions(project, s["id"])
        assert segs and segs[-1]["upto_seq"] == 14


class TestBatchMode:

    def _setup(self, c, tmp_dirs, name, n=30):
        project = _project(tmp_dirs, name)
        s = _mk_session(c, n, project)
        s["last_usage"] = {"prompt_tokens": 90_000}
        _add_provider(c)
        c.store.config.settings.compactSummaryMode = "batch"
        return project, s

    def test_assistant_merged_into_one_paragraph_user_kept(
            self, tmp_dirs, container, monkeypatch):
        c = container
        project, s = self._setup(c, tmp_dirs, "proj-batch1")
        calls: list[list] = []

        async def fake_summary(folded, hedge_ms=0, session_id=""):
            calls.append([m["_seq"] for m in folded])
            return "一段总结"
        _patch_memo(monkeypatch, c, fake_summary)

        asyncio.run(_call(c, s, _noop))

        items = c.sessions.get_compactions(project, s["id"])[-1]["items"]
        pass
        assert len(calls) == 1
        assert calls[0][0] == 0 and calls[0][-1] == 23
        pass
        memos = [m for m in items if "任务纪要" in str(m.get("content"))]
        assert len(memos) == 1 and "一段总结" in memos[0]["content"]
        assert "[msg#0," in memos[0]["content"]
        assert "memory(action=history_get" in memos[0]["content"]
        pass
        assert len(items) == 1
        assert not any(str(m.get("content", "")).startswith("消息1 ")
                       for m in items)

    def test_long_user_message_folded_with_history_hint(
            self, tmp_dirs, container, monkeypatch):
        c = container
        project, s = self._setup(c, tmp_dirs, "proj-batch2", n=20)
        s["messages"][0] = {"role": "user", "content": "长" * 3000}
        c.sessions._persisted.pop(s["id"], None)
        c.sessions.save(s)
        s = c.sessions.get(s["id"])
        s["last_usage"] = {"prompt_tokens": 90_000}

        async def fake_summary(folded, hedge_ms=0, session_id=""):
            return "一段总结"
        _patch_memo(monkeypatch, c, fake_summary)

        asyncio.run(_call(c, s, _noop))
        flat = json.dumps(c.sessions.get_compactions(project, s["id"])[-1]["items"],
                          ensure_ascii=False)
        assert "省略" in flat and "msg#0" in flat and "history_get" in flat
        pass
        assert len(c.sessions.get(s["id"])["messages"][0]["content"]) == 3000

    def test_summary_failure_keeps_assistant_text(self, tmp_dirs, container, monkeypatch):
        c = container
        project, s = self._setup(c, tmp_dirs, "proj-batch3", n=20)
        calls = []

        async def boom(folded, hedge_ms=0, session_id=""):
            calls.append(1)
            raise RuntimeError("总结挂了")
        _patch_memo(monkeypatch, c, boom)

        asyncio.run(_call(c, s, _noop))
        assert len(calls) == 2
        assert c.sessions.get_compactions(project, s["id"]) == []
        view = build_view(s["messages"], [])
        flat = json.dumps(view, ensure_ascii=False)
        assert "助手回复已压缩" not in flat
        assert "消息0" in flat and "消息1" in flat

    def test_summary_empty_retries_then_gives_up(
            self, tmp_dirs, container, monkeypatch):
        c = container
        project, s = self._setup(c, tmp_dirs, "proj-batch4", n=20)
        calls = []

        async def empty(folded, hedge_ms=0, session_id=""):
            calls.append(1)
            return ""
        _patch_memo(monkeypatch, c, empty)

        asyncio.run(_call(c, s, _noop))
        assert len(calls) == 2
        assert c.sessions.get_compactions(project, s["id"]) == []

    def test_no_text_replies_at_all_compresses_nothing(
            self, tmp_dirs, container, monkeypatch):
        c = container
        project = _project(tmp_dirs, "proj-batch5")
        s = _mk_session(c, 20, project)
        s["messages"] = [{"role": "tool", "name": "f",
                           "content": f"结果{i} " + "x" * 200}
                          for i in range(20)]
        c.sessions._persisted.pop(s["id"], None)
        c.sessions.save(s)
        s = c.sessions.get(s["id"])
        s["last_usage"] = {"prompt_tokens": 90_000}
        _add_provider(c)
        c.store.config.settings.compactStrategies = ["legacy"]
        c.store.config.settings.compactSummaryMode = "batch"
        calls = []

        async def never(folded, hedge_ms=0, session_id=""):
            calls.append(1)
            return "不该被调用"
        _patch_memo(monkeypatch, c, never)

        asyncio.run(_call(c, s, _noop))
        assert calls == []
        assert c.sessions.get_compactions(project, s["id"]) == []
        assert len(c.sessions.get(s["id"])["messages"]) == 20

    def test_many_user_replies_still_call_l2_for_memo(
            self, tmp_dirs, container, monkeypatch):
        c = container
        project = _project(tmp_dirs, "proj-batch6")
        s = _mk_session(c, 30, project)
        pass
        s["messages"] = [{"role": "user", "content": f"问题{i} " + "x" * 200}
                          for i in range(30)]
        c.sessions._persisted.pop(s["id"], None)
        c.sessions.save(s)
        s = c.sessions.get(s["id"])
        s["last_usage"] = {"prompt_tokens": 90_000}
        _add_provider(c)
        c.store.config.settings.compactSummaryMode = "batch"
        calls = []

        async def fake(folded, hedge_ms=0, session_id=""):
            calls.append(1)
            return "一份任务纪要"
        _patch_memo(monkeypatch, c, fake)

        asyncio.run(_call(c, s, _noop))
        assert calls == [1]
        segs = c.sessions.get_compactions(project, s["id"])
        assert segs and segs[-1]["upto_seq"] == 24
        assert "一份任务纪要" in json.dumps(segs[-1]["items"], ensure_ascii=False)


class TestNoRepeatCompaction:

    def test_last_usage_reset_after_compaction_blocks_second_run(
            self, tmp_dirs, container, monkeypatch):
        c = container
        project = _project(tmp_dirs, "proj-compaction-norepeat")
        s = _mk_session(c, 30, project)
        s["last_usage"] = {"prompt_tokens": 90_000}
        _add_provider(c)
        c.store.config.settings.compactSummaryMode = "batch"

        async def fake_summary(folded, hedge_ms=0, session_id=""):
            return "一段总结"
        _patch_memo(monkeypatch, c, fake_summary)

        asyncio.run(_call(c, s, _noop))

        pass
        est = s["last_usage"]["prompt_tokens"]
        assert 0 < est < 90_000

        pass
        asyncio.run(_call(c, s, _noop))
        segs = c.sessions.get_compactions(project, s["id"])
        assert len(segs) == 1


class TestMemoryHistory:
    def test_core_tools_contains_memory(self, tmp_dirs, container):
        assert "memory" in container.registry.CORE_TOOLS

    def test_history_get_returns_full_text(self, tmp_dirs, container):
        c = container
        c.runner.sessions = c.sessions
        s = _mk_session(c, 8)
        get = c.runner._history_get(s["id"])
        out = asyncio.run(get([0, 99]))
        assert "=== msg#0 (user) ===" in out
        assert "消息0" in out
        assert "不存在" in out

    def test_history_get_missing_session(self, tmp_dirs, container):
        container.runner.sessions = container.sessions
        get = container.runner._history_get("no-such")
        out = asyncio.run(get([0]))
        assert "会话不存在" in out
