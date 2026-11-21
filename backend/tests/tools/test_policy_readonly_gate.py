from __future__ import annotations

import pytest

from app.security.core import is_readonly_command
from app.security.engine import Decision, PolicyEngine

DEVNULL = "/dev/" + "null"


@pytest.mark.parametrize("cmd", [
    "env rm -rf ~/docs",
    "pwd; rm -rf ~/x",
    "environment_backup x",
    "cat x > y",
    "ls && rm -rf y",
    "echo `rm -rf /tmp/x`",
    "sed -i s/a/b/ f",
    "sort -o out a",
    "git stash",
])
def test_substring_and_write_variants_are_not_readonly(cmd):
    assert is_readonly_command(cmd) is False, cmd


@pytest.mark.parametrize("cmd", [
    "ls -la",
    "cat README.md",
    "grep -rn foo .",
    "git status",
    "git stash list",
    "sed -n 1,5p f",
    f"cat x > {DEVNULL}",
    f"echo hi > {DEVNULL} 2>&1",
])
def test_genuinely_readonly_commands_pass(cmd):
    assert is_readonly_command(cmd) is True, cmd


def test_review_mode_does_not_allow_wrapped_delete(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    v = PolicyEngine().check("env rm -rf ~/docs", str(proj), "review")
    assert v.decision is not Decision.ALLOW
