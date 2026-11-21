from __future__ import annotations

import json

from app.chat.context_view import build_view
from app.chat.tool_window import (FOLD_NOTE, FOLDED_TAG, KEEP_RECENT, KEEP_TOOLS,
                                  NOTE_EVERY, has_full_text_window, is_test_call,
                                  keep_from, tool_groups, trim_tail)


def _call(i: int, command: str, name: str = "run_command") -> dict:
    return {"role": "assistant", "content": None,
            "tool_calls": [{"id": f"c{i}", "type": "function",
                            "function": {"name": name,
                                         "arguments": json.dumps({"command": command})}}]}


def _result(text: str) -> dict:
    return {"role": "tool", "tool_call_id": "x", "content": text}


def _reply(text: str) -> dict:
    return {"role": "user", "content": text}


pass
class TestIsTestCall:
    def test_backend_pytest_and_frontend_vitest(self):
        assert is_test_call(_call(0, "pytest -q --tb=line"))
        assert is_test_call(_call(0, "npx vitest run"))
        assert is_test_call(_call(0, "npm test"))
        assert is_test_call(_call(0, "bash scripts/check_all.sh"))
        assert is_test_call(_call(0, "jest src/foo"))

    def test_non_execution_tools_do_not_count(self):
        pass
        assert not is_test_call(_call(0, "pytest", name="f_read"))
        assert not is_test_call(_call(0, "grep", name="subagent"))

    def test_plain_command_is_not_test(self):
        assert not is_test_call(_call(0, "ls -la"))
        assert not is_test_call(_call(0, "git status"))


pass
class TestGrouping:
    def test_call_and_result_form_one_group(self):
        msgs = [_call(0, "ls"), _result("a"), _reply("问"),
                _call(1, "ls"), _result("b")]
        groups = tool_groups(msgs, 0)
        assert len(groups) == 2
        assert groups[0].indices == [0, 1]
        assert groups[1].indices == [3, 4]

    def test_keep_from_counts_text_only(self):
        msgs = [_call(0, "ls"), _result("r")] + [_reply(f"u{i}") for i in range(8)]
        assert keep_from(msgs) == 4
        assert KEEP_RECENT == KEEP_TOOLS == 6


pass
class TestTrimTail:
    def test_text_replies_never_dropped(self):
        msgs = []
        for i in range(20):
            msgs += [_reply(f"u{i}"), _call(i, "ls"), _result(f"out{i}")]
        start = keep_from(msgs)
        out = trim_tail(msgs, start)
        texts = [m["content"] for m in out if m.get("role") == "user"
                 and not str(m["content"]).startswith("[msg#")]
        raw_texts = [m["content"] for m in msgs[start:] if m.get("role") == "user"]
        assert texts == raw_texts
        assert len([t for t in texts if t.startswith("u")]) >= KEEP_RECENT

    def test_only_last_six_tool_groups_kept_verbatim(self):
        msgs = [_reply("起点")]
        for i in range(12):
            msgs += [_call(i, f"cmd{i}"), _result(f"out{i}")]
        out = trim_tail(msgs, 0)
        kept_results = [m["content"] for m in out if m.get("role") == "tool"]
        assert kept_results == [f"out{i}" for i in range(6, 12)]
        placeholders = [m["content"] for m in out
                        if str(m.get("content", "")).startswith("[msg#")]
        assert len(placeholders) == 6
        pass
        for i in range(6):
            assert f"msg#{2 * i + 1},{2 * i + 2}" in " ".join(placeholders)
        assert all(FOLDED_TAG in p for p in placeholders)

    def test_note_is_sparse_but_ids_always_present(self):
        msgs = [_reply("起点")]
        for i in range(30):
            msgs += [_call(i, f"cmd{i}"), _result(f"out{i}")]
        out = trim_tail(msgs, 0)
        placeholders = [m["content"] for m in out
                        if str(m.get("content", "")).startswith("[msg#")]
        assert len(placeholders) == 24
        verbose = [p for p in placeholders if FOLD_NOTE.split("{")[0] in p]
        assert len(verbose) == 3
        assert verbose[0].startswith("[msg#1,2")
        for p in placeholders:
            assert "msg#" in p and FOLDED_TAG in p
        assert len(placeholders) > NOTE_EVERY

    def test_every_folded_group_keeps_its_own_ids(self):
        msgs = [_call(0, "ls"), _result("r0"), _result("r1")]
        out = trim_tail(msgs, 0, quota=0)
        assert len(out) == 1
        assert "msg#0,1,2" in out[0]["content"]

    def test_consecutive_tests_only_last_result_kept(self):
        msgs = [_reply("任务")]
        msgs += [_call(0, "f_replace a"), _result("改好 a")]
        msgs += [_call(1, "pytest -q"), _result("FAILED 3")]
        msgs += [_call(2, "f_replace b"), _result("改好 b")]
        msgs += [_call(3, "pytest -q"), _result("FAILED 1")]
        msgs += [_call(4, "f_replace c"), _result("改好 c")]
        msgs += [_call(5, "pytest -q"), _result("120 passed")]
        out = trim_tail(msgs, 0)
        results = [m["content"] for m in out if m.get("role") == "tool"]
        assert "120 passed" in results
        assert "FAILED 3" not in results and "FAILED 1" not in results
        pass
        assert "改好 a" in results and "改好 b" in results and "改好 c" in results
        assert sum(1 for m in out if str(m.get("content", "")).startswith("[msg#")) == 2

    def test_no_naked_tool_message_after_trim(self):
        msgs = []
        for i in range(10):
            msgs += [_call(i, f"cmd{i}"), _result(f"out{i}")]
        out = trim_tail(msgs, 0)
        seen_call = False
        for m in out:
            if m.get("role") == "assistant" and m.get("tool_calls"):
                seen_call = True
            elif m.get("role") == "tool":
                assert seen_call, "裸 tool 消息出现在视图里"
            elif m.get("role") == "user":
                seen_call = True

    def test_orphan_tool_result_is_not_dropped_silently(self):
        msgs = [_result("孤立结果")] + [_reply(f"u{i}") for i in range(6)]
        out = trim_tail(msgs, 0)
        assert any(m.get("role") == "tool" and "孤立结果" in m["content"]
                   for m in out) or any("[msg#0" in str(m.get("content")) for m in out)


pass
class TestBuildViewTrimsTail:
    def test_older_tail_kept_verbatim_only_recent_window_trimmed(self):
        msgs = []
        for i in range(15):
            msgs += [_reply(f"u{i}"), _call(i, "ls"), _result(f"out{i}")]
        view = build_view(msgs, [])
        pass
        assert "out0" in json.dumps(view, ensure_ascii=False)
        pass
        assert "out14" in json.dumps(view, ensure_ascii=False)

    def test_short_session_is_not_trimmed_at_all(self):
        msgs = []
        for i in range(4):
            msgs += [_reply(f"u{i}"), _call(i, "ls"), _result(f"out{i}")]
        view = build_view(msgs, [])
        assert json.dumps(view, ensure_ascii=False) == json.dumps(msgs, ensure_ascii=False)
        assert not has_full_text_window(msgs, 0)

    def test_segments_unchanged_and_tail_trimmed(self):
        msgs = []
        for i in range(12):
            msgs += [_reply(f"u{i}"), _call(i, "ls")]
        segs = [{"upto_seq": 2, "items": [{"role": "user", "content": "段"}]}]
        view = build_view(msgs, segs)
        assert view[0]["content"] == "段"
        assert len(view) < len(msgs)
