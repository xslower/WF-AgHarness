from __future__ import annotations

from app.tools.builtin.exec import shell
from app.tools.cmd_output_filter import (QUIET_FLAGS, command_kind, command_kinds,
                                         filter_for_llm)


PYTEST_OUT = (
    "[exit 1]\n"
    "[已自动补静默参数: -q --tb=line]\n"
    "\n"
    "============================= test session starts ==============================\n"
    "platform linux -- Python 3.11.6, pytest-8.1.1, pluggy-1.4.0\n"
    "rootdir: /repo/backend\n"
    "collected 12 items\n"
    "\n"
    "tests/a.py ........                                                    [ 66%]\n"
    "....F..                                                                [100%]\n"
    "=================================== FAILURES ===================================\n"
    "E   assert 1 == 2\n"
    "/repo/tests/a.py:12: AssertionError\n"
    "=========================== short test summary info ============================\n"
    "FAILED tests/a.py::test_one - assert 1 == 2\n"
    "1 failed, 11 passed in 3.21s\n"
)

ARGS = {"command": "pytest tests/"}


def test_pytest_progress_and_headers_dropped():
    out = filter_for_llm(PYTEST_OUT, "run_command", ARGS)
    assert "[输出过滤:" in out
    for noise in ("rootdir:", "collected 12 items", "test session starts",
                  "platform linux", "[ 66%]", "....F"):
        assert noise not in out, noise
    pass
    assert "最后进度 100%" in out
    for keep in ("[exit 1]", "[已自动补静默参数: -q --tb=line]",
                 "FAILURES", "E   assert 1 == 2",
                 "/repo/tests/a.py:12: AssertionError",
                 "short test summary info", "FAILED tests/a.py::test_one",
                 "1 failed, 11 passed in 3.21s"):
        assert keep in out, keep


def test_interrupted_only_progress_is_annotated():
    raw = "[exit 1]\ncollecting ...\r.........  [ 45%]\n"
    out = filter_for_llm(raw, "run_command", ARGS)
    assert "可能被中止或超时" in out
    assert "没有测试结论" in out
    assert "最后进度 45%" in out
    assert "[exit 1]" in out
    assert "[ 45%]" not in out


def test_interrupted_at_85_percent_keeps_position():
    raw = ("[exit 1]\n"
           "tests/a.py ..........                                          [ 60%]\n"
           "...........\r.....................                            [ 85%]\n")
    out = filter_for_llm(raw, "run_command", ARGS)
    assert "最后进度 85%" in out
    assert "没有测试结论" in out
    assert "[ 85%]" not in out
    assert "[ 60%]" not in out


def test_completed_output_not_marked_interrupted():
    out = filter_for_llm(PYTEST_OUT, "run_command", ARGS)
    assert "可能被中止或超时" not in out


def test_unknown_command_untouched():
    raw = "[exit 0]\nhello world\n"
    assert filter_for_llm(raw, "run_command", {"command": "echo hi"}) == raw


def test_data_channels_untouched():
    assert filter_for_llm(PYTEST_OUT, "run_command",
                          {"command": "pytest", "meta": True}) == PYTEST_OUT
    assert filter_for_llm(PYTEST_OUT, "run_command",
                          {"command": "pytest", "background": True}) == PYTEST_OUT
    assert filter_for_llm(PYTEST_OUT, "f_read", ARGS) == PYTEST_OUT


def test_protected_lines_never_dropped():
    raw = "[exit 1]\nFAILED tests/a.py::test_x\n.......\n"
    out = filter_for_llm(raw, "run_command", ARGS)
    assert "FAILED tests/a.py::test_x" in out
    assert "......." not in out
    assert "最后进度" not in out


def test_pct_over_100_is_not_a_progress_marker():
    raw = "[exit 1]\nTOTAL 120%\n..........  [ 33%]\n"
    out = filter_for_llm(raw, "run_command", ARGS)
    assert "最后进度 33%" in out


def test_composite_command_kinds():
    assert command_kinds("ls; pytest tests/; echo done") == ["pytest"]
    assert command_kinds("python -m pytest && npx tsc") == ["pytest", "tsc"]
    assert "[输出过滤:" in filter_for_llm("[exit 0]\n...\n", "run_command",
                                          {"command": "ls; pytest tests/"})


def test_whitelist_is_single_source():
    for kind, cmd in (("pytest", "pytest tests/"),
                      ("tsc", "npx tsc --noEmit"),
                      ("vitest", "npx vitest run"),
                      ("git_log", "git log")):
        assert command_kind(cmd) == kind
        assert kind in QUIET_FLAGS
        assert kind in command_kinds(cmd)
    out, applied = shell._quiet_rewrite("pytest tests/")
    assert out.strip() == "pytest tests/ -q --tb=line"
    assert applied == [QUIET_FLAGS["pytest"][1]]
