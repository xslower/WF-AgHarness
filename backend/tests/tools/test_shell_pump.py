from __future__ import annotations

import asyncio

import pytest

import app.tools.builtin.exec.shell as shell


class _FakeStream:

    def __init__(self, chunks: list[bytes]):
        self._chunks = list(chunks)

    async def read(self, n: int) -> bytes:
        return self._chunks.pop(0) if self._chunks else b""


class _Ctx:
    def __init__(self, emit=None):
        self.emit_stream = emit
        self.pushed: list[dict] = []


class _Proc:
    def __init__(self):
        self.pid = 12345

    def kill(self):
        self.killed = True


def run_pump(chunks, *, push=False, emit=None, proc=None, state=None):
    ctx = _Ctx(emit)
    sink: list[str] = []
    st = state or shell._PumpState()
    pr = proc or _Proc()
    asyncio.run(shell._pump(_FakeStream(chunks), sink, st, pr,
                            ctx=ctx, push=push))
    return sink, st, pr, ctx


pass
def test_splits_lines_and_keeps_trailing_partial():
    sink, st, _, _ = run_pump([b"a\nb\nc"])
    assert sink == ["a\n", "b\n", "c"]
    assert st.total == 5


def test_line_split_across_chunks():
    sink, _, _, _ = run_pump([b"hel", b"lo\nwor", b"ld\n"])
    assert sink == ["hello\n", "world\n"]


def test_empty_stream_yields_nothing():
    sink, st, _, _ = run_pump([])
    assert sink == [] and st.total == 0


def test_invalid_utf8_is_replaced_not_raised():
    sink, _, _, _ = run_pump([b"\xff\xfe ok\n"])
    assert "\ufffd" in sink[0]


pass
def test_push_emits_each_line():
    async def emit(ev):
        pushed.append(ev)

    pushed: list[dict] = []
    ctx = _Ctx(emit)
    sink: list[str] = []
    asyncio.run(shell._pump(_FakeStream([b"x\ny\n"]), sink,
                            shell._PumpState(), _Proc(), ctx=ctx, push=True))
    assert [e["text"] for e in pushed] == ["x\n", "y\n"]
    assert all(e["type"] == "tool_output" for e in pushed)


def test_no_push_when_forward_false():
    pushed: list[dict] = []

    async def emit(ev):
        pushed.append(ev)

    sink: list[str] = []
    asyncio.run(shell._pump(_FakeStream([b"x\n"]), sink,
                            shell._PumpState(), _Proc(), ctx=_Ctx(emit),
                            push=False))
    assert pushed == [] and sink == ["x\n"]


def test_emit_failure_does_not_break_pump():
    async def emit(ev):
        raise RuntimeError("ws 断了")

    sink, _, _, _ = run_pump([b"x\ny\n"], push=True, emit=emit)
    assert sink == ["x\n", "y\n"]


def test_no_emit_when_ctx_has_no_stream():
    sink, _, _, _ = run_pump([b"x\n"], push=True, emit=None)
    assert sink == ["x\n"]


pass
def test_over_limit_kills_process_and_stops():
    big = b"x" * (shell.MAX_OUTPUT_HARD + 10)
    victim = _Proc()
    sink, st, proc, _ = run_pump([big], proc=victim)
    assert st.over is True
    assert getattr(proc, "killed", False) is True


def test_over_limit_still_keeps_what_was_read():
    big = b"y" * (shell.MAX_OUTPUT_HARD + 10)
    sink, st, _, _ = run_pump([big])
    assert "".join(sink) and st.over is True


def test_under_limit_does_not_kill():
    victim = _Proc()
    _, st, proc, _ = run_pump([b"ok\n"], proc=victim)
    assert st.over is False
    assert not getattr(proc, "killed", False)


def test_hard_limit_is_a_positive_budget():
    assert shell.MAX_OUTPUT_HARD > 0


pass
def test_two_streams_share_one_budget():
    async def main():
        half = shell.MAX_OUTPUT_HARD // 2 + 10
        out = _FakeStream([b"o" * half])
        err = _FakeStream([b"e" * half])
        st = shell._PumpState()
        ctx = _Ctx()
        await asyncio.gather(
            shell._pump(out, [], st, _Proc(), ctx=ctx, push=False),
            shell._pump(err, [], st, _Proc(), ctx=ctx, push=False),
        )
        return st

    st = asyncio.run(main())
    assert st.total > shell.MAX_OUTPUT_HARD, "合计必须累加，不能被后一条流覆盖"
    assert st.over is True, "合计超硬顶必须置 over"
