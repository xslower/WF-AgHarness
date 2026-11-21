from __future__ import annotations

import asyncio
import sys

from app.chat.compaction_kit import (STRATEGIES, get_strategy, session_data,
                                     plan_batch_scope, fold_batch)
from app.chat.compaction_kit import (FALLBACK_UNFINISHED_TURNS,
                                     is_complete_assistant, unfinished_turns)
from app.chat.compaction_policy import maybe_compact, turn_interrupted


class _Sessions:
    def __init__(self, msgs: list) -> None:
        self._msgs = msgs
        self.get_calls = 0

    def get(self, sid):
        self.get_calls += 1
        return {"id": sid, "project": "", "messages": self._msgs}

    def get_compactions(self, project, sid):
        return []


class _Cfg:
    def __init__(self, names) -> None:
        self.settings = type("S", (), {
            "compactStrategies": names, "compactSummaryMode": "batch",
            "compactUserMsgLimit": 1000, "summaryHedgeMs": 0})()
        self.providers = []
        self.queues = type("Q", (), {"parent": [], "child": [], "summary": []})()


class _Store:
    def __init__(self, names) -> None:
        self.config = _Cfg(names)


class _Compactor:
    async def hedged_call(self, prompt, sid, hedge_ms=0):
        return "[任务] 契约测试\n[已完成] 完成"


class _C:
    def __init__(self, names, msgs) -> None:
        self.store = _Store(names)
        self.sessions = _Sessions(msgs)
        self.usage = None
        self.gateway = None
        self.compactor = _Compactor()


def _emit_sink():
    events: list[dict] = []

    async def emit(ev):
        events.append(ev)
    return emit, events


class TestDispatcher:
    def test_outer_only_dispatches_by_config(self, monkeypatch):
        calls: list[str] = []

        class S:
            def __init__(self, name):
                self.name = name

            async def compact(self, c, sid, emit, *, session=None, model=""):
                calls.append((self.name, sid))

        monkeypatch.setattr("app.chat.compaction_policy.get_strategy",
                            lambda n: S(n))
        c = _C(["memo", "secondary"], [{"role": "user", "content": "x"}] * 12)
        emit, _ = _emit_sink()
        s = {"id": "sid-1", "messages": c.sessions._msgs}
        asyncio.run(maybe_compact(c, s, "", emit))
        assert calls == [("memo", "sid-1"), ("secondary", "sid-1")]
        assert c.sessions.get_calls == 0

    def test_default_names_when_config_missing(self, monkeypatch):
        calls: list[str] = []

        class S:
            async def compact(self, c, sid, emit, *, session=None, model=""):
                calls.append("x")

        monkeypatch.setattr("app.chat.compaction_policy.get_strategy",
                            lambda n: S())
        c = _C([], [])
        emit, _ = _emit_sink()
        asyncio.run(maybe_compact(c, {"id": "s"}, "", emit))
        assert len(calls) == 2


class TestRegistry:
    def test_three_independent_strategies(self):
        assert STRATEGIES == ("memo", "secondary", "legacy")
        names = {get_strategy(n).name for n in STRATEGIES}
        assert names == {"memo", "secondary", "legacy"}

    def test_legacy_is_dead_code_until_selected(self, monkeypatch):
        monkeypatch.delitem(sys.modules, "app.chat.compaction_legacy", raising=False)
        for sub in ("memo", "secondary"):
            get_strategy(sub)
        assert "app.chat.compaction_legacy" not in sys.modules
        get_strategy("legacy")
        assert "app.chat.compaction_legacy" in sys.modules


class TestStrategyOwnsData:
    def test_session_data_reads_by_sid_and_folds_inside_strategy(self):
        msgs = [{"role": "user", "content": f"问题{i}"} for i in range(12)]
        c = _C(["memo"], msgs)
        ctx = session_data(c, "sid-2")
        assert ctx is not None and len(ctx.msgs) == 12
        assert c.sessions.get_calls == 1
        start, end = plan_batch_scope(ctx.msgs, ctx.segments)
        assert start == 0 and end > 0
        assert len(fold_batch(ctx.msgs, start, end)) == end - start


class TestInterruptedTurnSkipsCompaction:

    @staticmethod
    def _msgs(*tail: dict) -> list:
        pass
        pass
        base: list = []
        for _ in range(6):
            base += [{"role": "user", "content": "问题"},
                     {"role": "assistant", "content": "答",
                      "turn_complete": True}]
        return base + list(tail)

    def test_turn_interrupted_reads_last_assistant_only(self):
        user = {"role": "user", "content": "本轮问题"}
        half = {"role": "assistant", "content": "半截", "interrupted": True}
        full = {"role": "assistant", "content": "完整回复",
                "turn_complete": True}
        assert turn_interrupted({"messages": self._msgs(user, half)})
        assert not turn_interrupted({"messages": self._msgs(user, full)})
        pass
        msgs = self._msgs(user, full)
        msgs[3]["interrupted"] = True
        assert not turn_interrupted({"messages": msgs})
        pass
        msgs = self._msgs(user, half, {"role": "tool", "content": "结果"})
        assert turn_interrupted({"messages": msgs})
        pass
        assert not turn_interrupted({"messages": []})

    def test_dispatcher_skips_all_strategies_when_interrupted(self, monkeypatch):
        calls: list[str] = []

        class S:
            def __init__(self, name):
                self.name = name

            async def compact(self, c, sid, emit, *, session=None, model=""):
                calls.append(self.name)

        monkeypatch.setattr("app.chat.compaction_policy.get_strategy",
                            lambda n: S(n))
        c = _C(["memo", "secondary"], [])
        emit, events = _emit_sink()
        s = {"id": "s", "messages": self._msgs(
            {"role": "user", "content": "本轮问题"},
            {"role": "assistant", "content": "半截", "interrupted": True})}
        assert unfinished_turns(s["messages"]) < FALLBACK_UNFINISHED_TURNS
        asyncio.run(maybe_compact(c, s, "", emit))
        assert calls == []
        assert events == []
        assert c.sessions.get_calls == 0

    def test_dispatcher_still_runs_for_normal_turn(self, monkeypatch):
        calls: list[str] = []

        class S:
            async def compact(self, c, sid, emit, *, session=None, model=""):
                calls.append(sid)

        monkeypatch.setattr("app.chat.compaction_policy.get_strategy",
                            lambda n: S())
        c = _C(["memo", "secondary"], [])
        emit, _ = _emit_sink()
        s = {"id": "s", "messages": self._msgs(
            {"role": "user", "content": "本轮问题"},
            {"role": "assistant", "content": "完整回复",
             "turn_complete": True})}
        asyncio.run(maybe_compact(c, s, "", emit))
        assert calls == ["s", "s"]


class TestCompleteTurnMarker:

    @staticmethod
    def _msgs(*tail):
        base: list = []
        for _ in range(6):
            base += [{"role": "user", "content": "问题"},
                     {"role": "assistant", "content": "答",
                      "turn_complete": True}]
        return base + list(tail)

    def test_marker_semantics(self):
        assert is_complete_assistant(
            {"role": "assistant", "content": "答", "turn_complete": True})
        pass
        pass
        pass
        assert not is_complete_assistant(
            {"role": "assistant", "content": "## 📋 实施计划",
             "turn_complete": False})
        assert not is_complete_assistant(
            {"role": "assistant", "content": "半截", "interrupted": True})
        assert not is_complete_assistant(
            {"role": "assistant", "tool_calls": [{"id": "1"}]})
        pass
        assert is_complete_assistant({"role": "assistant", "content": "老回复"})

    def test_restart_residue_does_not_pass_gate(self):
        pass
        msgs = self._msgs({"role": "user", "content": "重发的问题"},
                          {"role": "tool", "content": "半截结果"})
        assert turn_interrupted({"messages": msgs})
        assert unfinished_turns(msgs) == 1

    def test_plan_round_does_not_pass_gate(self):
        msgs = self._msgs({"role": "user", "content": "给个方案"},
                          {"role": "assistant",
                           "content": "## 📋 实施计划",
                           "turn_complete": False})
        assert turn_interrupted({"messages": msgs})

    def test_complete_turn_passes_gate(self):
        msgs = self._msgs({"role": "user", "content": "本轮问题"},
                          {"role": "assistant", "content": "答",
                           "turn_complete": True})
        assert not turn_interrupted({"messages": msgs})
        assert unfinished_turns(msgs) == 0

    def test_fallback_after_three_unfinished_rounds(self, monkeypatch):
        calls: list[str] = []

        class S:
            async def compact(self, c, sid, emit, *, session=None, model=""):
                calls.append(sid)

        monkeypatch.setattr("app.chat.compaction_policy.get_strategy",
                            lambda n: S())
        msgs: list = []
        for _ in range(FALLBACK_UNFINISHED_TURNS):
            msgs += [{"role": "user", "content": "问"},
                     {"role": "assistant", "content": "半截",
                      "interrupted": True}]
        c = _C(["memo"], msgs)
        emit, _ = _emit_sink()
        assert unfinished_turns(msgs) == FALLBACK_UNFINISHED_TURNS
        asyncio.run(maybe_compact(c, {"id": "s", "messages": msgs}, "", emit))
        assert calls == ["s"]

    def test_no_fallback_below_threshold(self, monkeypatch):
        calls: list[str] = []

        class S:
            async def compact(self, c, sid, emit, *, session=None, model=""):
                calls.append(sid)

        monkeypatch.setattr("app.chat.compaction_policy.get_strategy",
                            lambda n: S())
        msgs: list = []
        for _ in range(FALLBACK_UNFINISHED_TURNS - 1):
            msgs += [{"role": "user", "content": "问"},
                     {"role": "assistant", "content": "半截",
                      "interrupted": True}]
        c = _C(["memo"], msgs)
        emit, _ = _emit_sink()
        asyncio.run(maybe_compact(c, {"id": "s", "messages": msgs}, "", emit))
        assert calls == []

    def test_lines_merges_unfinished_fragment_into_one_turn(self):
        from app.chat.compaction_memo_strategy import MemoStrategy
        folded = [
            {"role": "user", "content": "任务A", "_seq": 0, "_complete": False},
            {"role": "assistant", "content": "半截", "_seq": 1,
             "_complete": False},
            {"role": "user", "content": "任务B", "_seq": 2, "_complete": False},
            {"role": "assistant", "content": "答完", "_seq": 3,
             "_complete": True},
        ]
        lines = MemoStrategy._lines(folded)
        assert sum(1 for ln in lines if ln.startswith("[回合")) == 1
        assert any("上一回合未完成" in ln for ln in lines)

    def test_normal_rounds_still_numbered_separately(self):
        from app.chat.compaction_memo_strategy import MemoStrategy
        folded = [
            {"role": "user", "content": "A", "_seq": 0, "_complete": False},
            {"role": "assistant", "content": "答A", "_seq": 1,
             "_complete": True},
            {"role": "user", "content": "B", "_seq": 2, "_complete": False},
            {"role": "assistant", "content": "答B", "_seq": 3,
             "_complete": True},
        ]
        lines = MemoStrategy._lines(folded)
        assert sum(1 for ln in lines if ln.startswith("[回合")) == 2

    def test_finish_text_round_marks_complete_but_not_plan_round(self):
        from app.agent import stream as agent_stream

        class FakeRunner:
            def __init__(self, plan):
                self._plan = plan

            async def _finish_plan_round(self, text, reason, emit):
                return self._plan

            def _last_model_spec(self):
                return "m"

            async def _emit_done(self, emit, model, usage, meta=None, **kw):
                pass

        async def emit(ev):
            pass

        normal = asyncio.run(agent_stream.finish_text_round(
            FakeRunner(False), 0, "答", "", {}, {}, emit))
        assert normal.get("turn_complete") is True
        plan = asyncio.run(agent_stream.finish_text_round(
            FakeRunner(True), 0, "## 📋 实施计划", "", {}, {}, emit))
        assert plan.get("turn_complete") is False
