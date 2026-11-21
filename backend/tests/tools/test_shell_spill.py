from __future__ import annotations

import asyncio

from app.store import layout
from app.tools.builtin.exec import shell


class _Ctx:
    def __init__(self, cwd, sid="sid-1"):
        self.cwd = str(cwd)
        self.session_id = sid
        self.env_rewrite = None
        self.policy_check = None
        self.request_approval = None
        self.emit_stream = None


def test_spill_returns_relative_path_and_writes_full_output(tmp_path):
    text = "HEAD\n" + "x\n" * 20_000 + "FAILED tests/a.py::test_x\n"
    rel = shell._spill_output(_Ctx(tmp_path), text, "pytest -q")
    assert rel and not rel.startswith("/")
    p = tmp_path / rel
    assert p.is_file()
    body = p.read_text(encoding="utf-8")
    assert body.startswith("$ pytest -q")
    assert body.endswith("FAILED tests/a.py::test_x\n")
    assert len(body) > 30_000


def test_spill_is_per_session(tmp_path):
    a = shell._spill_output(_Ctx(tmp_path, "A"), "x" * 40_000, "cmd")
    b = shell._spill_output(_Ctx(tmp_path, "B"), "y" * 40_000, "cmd")
    assert a and b and (tmp_path / a).parent != (tmp_path / b).parent


def test_spill_failure_is_silent(tmp_path, monkeypatch):
    monkeypatch.setattr(layout, "session_tool_output_dir",
                        lambda *_a, **_k: 1 / 0)
    assert shell._spill_output(_Ctx(tmp_path), "x" * 40_000, "cmd") is None


def test_long_command_result_mentions_spilled_path(tmp_path):
    async def fake_exec(command, ctx, timeout, split_stderr=False, forward=False):
        return 0, "HEAD\n" + "line\n" * 20_000 + "FAILED tests/a.py::test_x\n", "", False

    monkeypatch_exec = shell._execute
    shell._execute = fake_exec
    try:
        out = asyncio.run(shell.run_command("pytest", _Ctx(tmp_path)))
    finally:
        shell._execute = monkeypatch_exec
    assert "完整输出已落盘" in out and "f_read(path=" in out
    assert "[已自动补静默参数: -q --tb=line]" in out and out.startswith("[已自动补")
    assert "--lf" not in out
    assert out.rstrip().endswith("FAILED tests/a.py::test_x")
    assert "tool_output." in out


def test_short_command_does_not_spill(tmp_path, monkeypatch):
    called = []
    monkeypatch.setattr(shell, "_spill_output",
                        lambda *a, **k: called.append(1) or "fake.log")

    async def fake_exec(command, ctx, timeout, split_stderr=False, forward=False):
        return 0, "ok\n", "", False

    old = shell._execute
    shell._execute = fake_exec
    try:
        out = asyncio.run(shell.run_command("echo ok", _Ctx(tmp_path)))
    finally:
        shell._execute = old
    assert called == [] and "落盘" not in out and out.strip() == "[exit 0]\nok"


def test_layout_dir_is_per_session():
    a = layout.session_tool_output_dir("/tmp/proj", "A")
    b = layout.session_tool_output_dir("/tmp/proj", "B")
    assert a != b and "A" in str(a) and "B" in str(b)
