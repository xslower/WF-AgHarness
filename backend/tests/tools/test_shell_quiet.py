from __future__ import annotations

import asyncio

from app.tools.builtin.exec import shell


class _Ctx:
    def __init__(self, cwd, sid="sid-1"):
        self.cwd = str(cwd)
        self.session_id = sid
        self.env_rewrite = None
        self.policy_check = None
        self.request_approval = None
        self.emit_stream = None


def test_pytest_gets_quiet_flags():
    out, applied = shell._quiet_rewrite("pytest tests/")
    assert out.strip() == "pytest tests/ -q --tb=line"
    assert applied == ["-q --tb=line"]


def test_python_m_pytest_and_absolute_env_path():
    out, applied = shell._quiet_rewrite("python3 -m pytest tests/")
    assert "-q --tb=line" in out
    out2, applied2 = shell._quiet_rewrite("/venv/bin/pytest tests/")
    assert "-q --tb=line" in out2 and applied2


def test_explicit_flags_are_not_overridden():
    out, applied = shell._quiet_rewrite("pytest -q --tb=short tests/")
    assert out == "pytest -q --tb=short tests/" and applied == []
    out2, applied2 = shell._quiet_rewrite("npx tsc --noEmit --pretty")
    assert out2 == "npx tsc --noEmit --pretty" and applied2 == []


def test_other_rules():
    assert "--pretty false" in shell._quiet_rewrite("npx tsc --noEmit")[0]
    assert "--reporter=dot" in shell._quiet_rewrite("npx vitest run")[0]
    assert "--oneline" in shell._quiet_rewrite("git log")[0]
    pass
    assert "-n" not in shell._quiet_rewrite("git log")[0]


def test_unknown_command_untouched():
    out, applied = shell._quiet_rewrite("grep -n foo app/ | head -20")
    assert out == "grep -n foo app/ | head -20" and applied == []


def test_composite_command_only_matching_segment_changed():
    out, applied = shell._quiet_rewrite("ls -la; pytest tests/; echo done")
    assert "ls -la" in out and "echo done" in out
    assert "pytest tests/ -q --tb=line" in out
    assert applied == ["-q --tb=line"]


def test_pipe_segments_are_independent():
    out, _ = shell._quiet_rewrite("pytest tests/ | tail -20")
    assert "pytest tests/ -q --tb=line | tail -20" == out


def test_meta_and_background_do_not_rewrite(tmp_path, monkeypatch):
    seen = {}

    async def fake_exec(command, ctx, timeout, split_stderr=False, forward=False):
        seen["cmd"] = command
        return 0, "ok\n", "", False

    async def fake_bg(command, ctx, timeout):
        seen["cmd"] = command
        return '{"background": true}'

    monkeypatch.setattr(shell, "_execute", fake_exec)
    monkeypatch.setattr(shell, "_start_background", fake_bg)
    asyncio.run(shell.run_command("pytest tests/", _Ctx(tmp_path), meta=True))
    assert seen["cmd"] == "pytest tests/"
    asyncio.run(shell.run_command("pytest tests/", _Ctx(tmp_path), background=True))
    assert seen["cmd"] == "pytest tests/"
    asyncio.run(shell.run_command("pytest tests/", _Ctx(tmp_path)))
    assert "-q --tb=line" in seen["cmd"]


def test_result_announces_applied_flags(tmp_path):
    async def fake_exec(command, ctx, timeout, split_stderr=False, forward=False):
        return 0, "1 passed\n", "", False

    old = shell._execute
    shell._execute = fake_exec
    try:
        out = asyncio.run(shell.run_command("pytest tests/", _Ctx(tmp_path)))
    finally:
        shell._execute = old
    assert out.startswith("[已自动补静默参数: -q --tb=line]")
    assert "1 passed" in out
