from __future__ import annotations

import asyncio
import json
import pathlib
import uuid

import pytest

from app.chat.compaction_kit import save_state as _save_state
from app.chat.compaction_secondary import (RECOMPACT_LADDER as COMPACT_LADDER,
                                           condense_items, decide as _decide,
                                           plan_secondary)
from app.chat.context_view import build_view, context_used


def _rung(i: int) -> int:
    return int(COMPACT_LADDER[i] * 1000)


def _below_first() -> int:
    return max(0, _rung(0) - 10)


def _over_last() -> int:
    return min(1000, _rung(-1) + 200)


def _all_rungs() -> list[int]:
    return [_rung(i) for i in range(len(COMPACT_LADDER))]


def _new_sid() -> str:
    return "ladder-" + uuid.uuid4().hex


def _project(tmp_dirs, name: str) -> str:
    project = str(tmp_dirs / name)
    pathlib.Path(project, ".agent").mkdir(parents=True, exist_ok=True)
    return project


def _provider(c, name: str = "t", ctx_len: int = 1_000) -> str:
    from app.provider.models import ModelInfo, Provider
    c.store.config.providers.append(Provider(
        id=name, name=name, baseUrl="http://x", apiKey="k",
        models=[ModelInfo(id="m1", contextLength=ctx_len)]))
    c.store.config.queues.parent = [f"{name}/m1"]
    return f"{name}/m1"


def _msg(i: int) -> dict:
    return {"role": "user" if i % 2 == 0 else "assistant",
            "content": f"消息{i} " + "字" * 300}


@pytest.fixture
def env(tmp_dirs, container, monkeypatch):
    c = container
    project = _project(tmp_dirs, "proj-ladder")
    spec = _provider(c)
    async def fake_memo(prompt, sid, hedge_ms=0):
        return "[任务] 测试\n[线索] 保留\n[已完成] 完成"

    monkeypatch.setattr(c.compactor, "hedged_call", fake_memo)
    s = c.sessions.create("触发策略", project)
    s["messages"] = [_msg(i) for i in range(30)]
    c.sessions.save(s)
    return {"c": c, "s": c.sessions.get(s["id"]), "spec": spec,
            "project": project, "emitted": [], "n": 30}


def _grow(env, n: int = 12) -> None:
    s = env["s"]
    s["messages"] += [_msg(env["n"] + i) for i in range(n)]
    env["n"] += n
    env["c"].sessions.save(s)


def _run(env, used: int, spec: str | None = None, grow: int = 0) -> None:
    if grow:
        _grow(env, grow)
    s, c = env["s"], env["c"]

    async def emit(ev):
        env["emitted"].append(ev)

    s["last_usage"] = {"prompt_tokens": used}
    asyncio.run(_call(c, s, spec or env["spec"], emit))


async def _noop_emit(ev):
    pass


async def _call(c, s, spec, emit):
    from app.chat.compaction_policy import maybe_compact
    await maybe_compact(c, s, spec, emit)


def _segs(env):
    return env["c"].sessions.get_compactions(env["project"], env["s"]["id"])


def _nags(env) -> list[dict]:
    return [n for n in env["emitted"]
            if n.get("type") == "notice" and "建议开启新会话" in n.get("text", "")]


pass
class TestSecondaryRungs:

    def test_ladder_thresholds_follow_single_source(self):
        assert len(COMPACT_LADDER) >= 2
        assert all(0 < x < 1 for x in COMPACT_LADDER)
        assert list(COMPACT_LADDER) == sorted(COMPACT_LADDER)

    def test_below_first_threshold_is_idle(self):
        assert _decide(_new_sid(), _below_first(), 1000)[1] == "idle"

    def test_second_rung_needs_higher_usage(self):
        sid = _new_sid()
        state, action = _decide(sid, _rung(0), 1000)
        assert action == "recompact"
        state["steps"] = 1
        _save_state(sid, state)
        between = (_rung(0) + _rung(1)) // 2
        assert _decide(sid, between, 1000)[1] == "idle"
        assert _decide(sid, _rung(1), 1000)[1] == "recompact"

    def test_each_rung_triggers_once(self):
        sid = _new_sid()
        for i, used in enumerate(_all_rungs()):
            state, action = _decide(sid, used, 1000)
            assert action == "recompact", f"第 {i} 档该触发"
            state["steps"] = i + 1
            _save_state(sid, state)
        assert _decide(sid, _over_last(), 1000)[1] == "nag"

    def test_after_ladder_exhausted_only_nags(self):
        sid = _new_sid()
        _save_state(sid, {"steps": len(COMPACT_LADDER)})
        assert _decide(sid, _over_last(), 1000)[1] == "nag"
        assert _decide(sid, _over_last(), 1000)[1] == "idle"

    def test_exhausted_but_low_usage_is_silent(self):
        sid = _new_sid()
        _save_state(sid, {"steps": len(COMPACT_LADDER)})
        assert _decide(sid, 100, 1000)[1] == "idle"

    def test_zero_limit_never_recompacts(self):
        assert _decide(_new_sid(), _over_last(), 0)[1] == "idle"


pass
class TestOncePerTurn:

    def test_compacts_even_when_usage_tiny(self, env):
        _run(env, 1)
        assert len(_segs(env)) == 1

    def test_does_not_recompact_same_batch(self, env):
        _run(env, 1)
        before = len(_segs(env))
        asyncio.run(_call(env["c"], env["s"], env["spec"], _noop_emit))
        assert len(_segs(env)) == before

    def test_switch_model_has_no_special_trigger(self, env):
        new_spec = _provider(env["c"], name="t2")
        _run(env, 1, spec=new_spec)
        assert len(_segs(env)) == 1
        assert not any("已切换" in n.get("text", "") for n in env["emitted"])

    def test_l2_failure_keeps_original_and_allows_retry(self, env, monkeypatch):
        c = env["c"]
        calls = []

        async def boom(prompt, sid, hedge_ms=0):
            calls.append(1)
            raise RuntimeError("模型挂了")
        monkeypatch.setattr(c.compactor, "hedged_call", boom)
        _run(env, 900)
        assert len(calls) == 2
        assert _segs(env) == []

        async def ok(prompt, sid, hedge_ms=0):
            return "[任务] 测试\n[已完成] 完成"
        monkeypatch.setattr(c.compactor, "hedged_call", ok)
        _run(env, 900)
        assert len(_segs(env)) == 1

    def test_short_history_compresses_nothing(self, env):
        env["s"]["messages"] = [_msg(i) for i in range(6)]
        _run(env, 900)
        assert _segs(env) == []


pass
def _memo() -> str:
    return ("[任务] 修 A 模块空指针\n"
            "[线索] a.py:12 抛 NoneType，b.py:44 是调用方\n"
            "[已完成] 改 a.py:12 与 b.py:44，" + "过程细节" * 100 + "\n"
            "[决定] 用方案 B，因方案 A 会破坏缓存前缀\n"
            "[进行中] 方案 C 待评估，" + "评估过程" * 100 + "\n"
            "[未完成] 补文档\n"
            "[建议] 建议开新会话")


def _seg_seq(upto: int, text: str) -> dict:
    return {"upto_seq": upto, "items": [{"role": "user", "content": text}]}


class TestSecondaryLayering:

    def test_too_few_segments_is_noop(self):
        assert plan_secondary([_seg_seq(10, "a"), _seg_seq(20, "b")]) == ([], 0)

    def test_recent_two_untouched(self):
        segs = [_seg_seq(i * 10, _memo()) for i in range(1, 4)]
        updates, delete_before = plan_secondary(segs)
        assert delete_before == 0
        assert [u for u, _ in updates] == [10]
        assert segs[-1]["items"][0]["content"] == _memo()

    def test_old_segments_deleted_and_middle_condensed(self):
        segs = [_seg_seq(i * 10, _memo()) for i in range(1, 9)]
        updates, delete_before = plan_secondary(segs)
        assert delete_before == 40
        assert [u for u, _ in updates] == [40, 50, 60]
        assert 70 not in [u for u, _ in updates]

    def test_condense_keeps_clues_drops_advice(self):
        items = condense_items([{"role": "user", "content": _memo()}])
        text = items[0]["content"]
        assert "[任务]" in text and "[线索]" in text and "[决定]" in text
        assert "[建议]" not in text
        assert len(text) < len(_memo()) // 2

    def test_legacy_segment_without_sections_is_shortened(self):
        long = "旧总结 " * 300
        out = condense_items([{"role": "user", "content": long}])
        assert len(out[0]["content"]) <= 401


pass
class TestSecondaryIntegration:
    def test_recompact_writes_updates_and_deletes(self, env, monkeypatch):
        c, project, sid = env["c"], env["project"], env["s"]["id"]
        memo = _memo()
        for i in range(1, 9):
            c.sessions.add_compaction(project, sid, i * 3,
                                      [{"role": "user", "content": memo}])
        calls = {"set": [], "del": []}
        orig_set = c.sessions.set_compaction_items
        orig_del = c.sessions.delete_compactions_before

        def _set(p, s, upto, items):
            calls["set"].append(upto)
            return orig_set(p, s, upto, items)

        def _del(p, s, upto):
            calls["del"].append(upto)
            return orig_del(p, s, upto)

        monkeypatch.setattr(c.sessions, "set_compaction_items", _set)
        monkeypatch.setattr(c.sessions, "delete_compactions_before", _del)
        _run(env, 900)
        assert len(calls["set"]) == 3
        assert calls["del"] == [12]
        segs = _segs(env)
        assert len(segs) == 5
        assert "[建议]" not in json.dumps(segs[0]["items"], ensure_ascii=False)
        assert segs[-1]["items"][0]["content"] == memo


pass
class TestCtxEstimateAfterCompaction:
    def test_emits_ctx_estimate_smaller_than_before(self, env):
        pre = context_used(env["s"]["messages"], [])["used"]
        _run(env, 900)
        est = [e for e in env["emitted"] if e.get("type") == "ctx_estimate"]
        assert est, "压缩后必须发 ctx_estimate，否则用户以为没压"
        assert est[-1]["used"] < pre

    def test_estimate_is_calibrated(self, env):
        c, s, spec = env["c"], env["s"], env["spec"]
        pass
        for _ in range(5):
            c.usage.record(spec, "s", prompt_tokens=300, completion_tokens=0,
                           est=100)
        assert c.usage.calibration(spec) == pytest.approx(3.0)

        _run(env, 900)
        est = [e for e in env["emitted"] if e.get("type") == "ctx_estimate"][-1]["used"]
        segs = _segs(env)
        raw = sum(__import__("app.util.tokens", fromlist=["x"]).estimate_obj(m)
                  for m in build_view(s["messages"], segs))
        assert est == pytest.approx(raw * 3.0, rel=0.02)

    def test_last_usage_marked_estimated(self, env):
        _run(env, 900)
        assert env["s"]["last_usage"]["estimated"] is True
