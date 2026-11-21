from __future__ import annotations

import json

from app.chat.context_view import KEEP_RECENT, build_view
from app.chat.compaction import (ContextCompactor, SUMMARY_CHARS, keep_from,
                                 l1_fold, plan_batch)


def _tool_msg(seq: int, name: str = "read_file", result: str = "line1\nline2") -> dict:
    return {"_seq": seq, "role": "tool", "name": name, "content": result}


def _assistant_calls(seq: int, text: str = "我来改文件") -> dict:
    return {"_seq": seq, "role": "assistant", "content": text,
            "tool_calls": [{"function": {"name": "f_write",
                                         "arguments": json.dumps({"path": "a.py", "content": "x" * 500})}}]}


pass
class TestL1Fold:
    def test_tool_result_becomes_name_and_first_line(self):
        out = l1_fold(_tool_msg(3, "read_file", "def main():\n" + "x" * 500))
        assert out["role"] == "tool"
        assert "[msg#3 read_file" in out["content"]
        assert "def main():" in out["content"]
        assert "x" * 500 not in out["content"]

    def test_assistant_tool_calls_keep_name_and_key_params(self):
        out = l1_fold(_assistant_calls(5))
        assert out["role"] == "assistant"
        assert "[msg#5 调用 f_write(path=a.py" in out["content"]
        assert "x" * 500 not in out["content"]

    def test_user_and_plain_assistant_pass_through(self):
        u = {"_seq": 1, "role": "user", "content": "帮我改 bug"}
        assert l1_fold(u) == {"role": "user", "content": "帮我改 bug"}
        a = {"_seq": 2, "role": "assistant", "content": "结论是 X"}
        assert l1_fold(a)["content"] == "结论是 X"

    def test_reasoning_stripped(self):
        a = {"_seq": 2, "role": "assistant", "content": "答案",
             "reasoning_content": "很长的思考" * 100}
        out = l1_fold(a)
        assert "reasoning_content" not in out
        assert "很长的思考" not in str(out)

    def test_list_content_flattened(self):
        m = {"_seq": 4, "role": "tool", "name": "web",
             "content": [{"type": "text", "text": "搜索结果第一行"}]}
        out = l1_fold(m)
        assert "搜索结果第一行" in out["content"]


pass
class TestPlanBatch:
    def test_nothing_to_compact(self):
        assert plan_batch(6, 0) == (-1, -1)
        assert plan_batch(7, 7) == (-1, -1)

    def test_first_batch(self):
        assert plan_batch(20, 0) == (0, 14)

    def test_second_batch_starts_at_boundary(self):
        assert plan_batch(30, 14) == (14, 24)

    def test_negative_upto_clamped(self):
        assert plan_batch(20, -5) == (0, 14)

    def test_explicit_end_overrides_legacy_tail(self):
        assert plan_batch(20, 0, end=8) == (0, 8)
        assert plan_batch(20, 14, end=15) == (14, 15)

    def test_explicit_end_at_or_before_boundary_is_noop(self):
        assert plan_batch(20, 14, end=14) == (-1, -1)
        assert plan_batch(20, 14, end=10) == (-1, -1)


pass
class TestKeepFrom:

    def test_counts_only_user_and_assistant_with_text(self):
        msgs = [{"role": "user", "content": f"u{i}"} for i in range(10)]
        pass
        assert keep_from(msgs) == 4

    def test_interleaved_tools_are_kept_too(self):
        msgs = []
        for i in range(10):
            msgs.append({"role": "user", "content": f"u{i}"})
            msgs.append({"role": "tool", "content": f"t{i}"})
        pass
        assert keep_from(msgs) == 8
        kept = msgs[8:]
        assert sum(1 for m in kept if m["role"] == "tool") == 6
        assert kept[0]["content"] == "u4"

    def test_fewer_than_six_replies_keeps_everything(self):
        msgs = [{"role": "user", "content": f"u{i}"} for i in range(3)]
        assert keep_from(msgs) == 0
        assert plan_batch(len(msgs), 0, end=keep_from(msgs)) == (-1, -1)

    def test_empty_assistant_text_not_counted(self):
        msgs = [{"role": "assistant", "content": ""} for _ in range(5)]
        msgs += [{"role": "user", "content": f"u{i}"} for i in range(6)]
        assert keep_from(msgs) == 5
        pass
        assert SUMMARY_CHARS == 3000


pass
def _mk_msgs(n: int) -> list[dict]:
    return [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"}
            for i in range(n)]


class TestBuildView:
    def test_no_segments_returns_all(self):
        msgs = _mk_msgs(10)
        view = build_view(msgs, [])
        assert len(view) == 10
        assert view[0]["content"] == "m0"

    def test_tail_kept_verbatim(self):
        msgs = _mk_msgs(20)
        segs = [{"upto_seq": 14, "items": [{"role": "user", "content": "[msg#0..13 已压缩]"}]}]
        view = build_view(msgs, segs)
        pass
        assert len(view) == 1 + 6
        assert view[-1]["content"] == "m19"
        assert view[-6]["content"] == "m14"

    def test_multi_segments_in_order(self):
        msgs = _mk_msgs(30)
        segs = [
            {"upto_seq": 10, "items": [{"role": "user", "content": "seg-A"}]},
            {"upto_seq": 20, "items": [{"role": "user", "content": "seg-B"}]},
        ]
        view = build_view(msgs, segs)
        assert [v["content"] for v in view[:2]] == ["seg-A", "seg-B"]
        assert len(view) == 2 + 10

    def test_stale_segment_falls_back_to_raw(self):
        msgs = _mk_msgs(10)
        segs = [{"upto_seq": 99, "items": [{"role": "user", "content": "过时段"}]}]
        view = build_view(msgs, segs)
        assert len(view) == 10
        assert all(v["content"].startswith("m") for v in view)

    def test_deterministic_bytes(self):
        msgs = _mk_msgs(20)
        segs = [{"upto_seq": 14, "items": [{"role": "user", "content": "seg"}]}]
        a = json.dumps(build_view(msgs, segs), ensure_ascii=False, sort_keys=True)
        b = json.dumps(build_view(msgs, segs), ensure_ascii=False, sort_keys=True)
        assert a == b

    def test_segments_do_not_mutate_source(self):
        msgs = _mk_msgs(20)
        segs = [{"upto_seq": 14, "items": [{"role": "user", "content": "seg"}]}]
        build_view(msgs, segs)
        assert msgs[0]["content"] == "m0"
        assert len(msgs) == 20


pass
class TestMerge:
    def test_summaries_replace_text_roles_only(self):
        folded = [
            {"_seq": 0, "role": "user", "content": "长问题" * 100},
            {"_seq": 1, "role": "tool", "name": "read_file", "content": "[msg#1 read_file → x]"},
        ]
        out = ContextCompactor.merge(folded, {0: "用户要求修 X bug"})
        assert out[0]["content"] == "[msg#0] 用户要求修 X bug"
        assert out[1]["content"].startswith("[msg#1")

    def test_missing_summary_keeps_folded(self):
        folded = [{"_seq": 2, "role": "assistant", "content": "长回复" * 100}]
        out = ContextCompactor.merge(folded, {})
        assert out[0]["content"] == "长回复" * 100


pass
class _FakeChunk:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _FakeGateway:
    def __init__(self, reply: str):
        self._reply = reply

    async def chat_stream(self, messages, tools=None, spec="", **kw):
        for part in self._reply.split("‖"):
            yield _FakeChunk(part)


class TestSummarizeBatch:
    def _mk(self, n=3):
        return [{"_seq": i, "role": "user" if i % 2 == 0 else "assistant",
                 "content": f"内容{i}"} for i in range(n)]

    def test_plain_json(self):
        import asyncio
        from app.chat.compaction import ContextCompactor
        c = ContextCompactor(_FakeGateway('[{"n":0,"s":"问 X"},{"n":1,"s":"答 Y"},{"n":2,"s":"续 Z"}]'))
        out = asyncio.run(c.summarize_batch(self._mk()))
        assert out == {0: "问 X", 1: "答 Y", 2: "续 Z"}

    def test_markdown_fenced_json(self):
        import asyncio
        from app.chat.compaction import ContextCompactor
        reply = '```json\n[{"n":0,"s":"A"},{"n":1,"s":"B"},{"n":2,"s":"C"}]\n```'
        c = ContextCompactor(_FakeGateway(reply))
        out = asyncio.run(c.summarize_batch(self._mk()))
        assert out == {0: "A", 1: "B", 2: "C"}

    def test_garbage_returns_empty_not_raise(self):
        import asyncio
        from app.chat.compaction import ContextCompactor
        c = ContextCompactor(_FakeGateway("我不会输出 JSON，抱歉……"))
        out = asyncio.run(c.summarize_batch(self._mk()))
        assert out == {}


class TestEstimateTokens:

    def test_cjk_counts_per_char(self):
        from app.chat.context_view import estimate_tokens
        pass
        assert estimate_tokens([{"role": "user", "content": "你好世界"}]) == 5

    def test_ascii_three_chars_per_token(self):
        from app.chat.context_view import estimate_tokens
        pass
        assert estimate_tokens([{"role": "user", "content": "a" * 40}]) == 14

    def test_bigger_view_estimates_bigger(self):
        from app.chat.context_view import estimate_tokens
        small = [{"role": "user", "content": "短"}]
        big = [{"role": "user", "content": "长" * 500}]
        assert estimate_tokens(small) < estimate_tokens(big)
