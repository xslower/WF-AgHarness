from __future__ import annotations

import pytest

from app.security.engine import Decision, PolicyEngine
from app.security.core import is_root_delete

PROJ = "/some/project"


pass
@pytest.mark.parametrize("cmd", [
    "rm -rf /",
    "rm -rf /*",
    "rm -rf ~",
    "rm -rf ~/",
    "rm -rf ~/*",
    "rm -rf $HOME",
    "rm -rf --recursive /",
    "rm -fr /",
    "rm -r -f /",
    "rm -Rf ~",
    'rm -rf "/"',
    "rm -rf --no-preserve-root /",
    "rm -rf / && echo done",
    "sudo rm -rf /",
    "cd /tmp && rm -rf /",
])
def test_root_delete_true(cmd):
    assert is_root_delete(cmd) is True, cmd


@pytest.mark.parametrize("cmd", [
    "rm -rf /var/data/old",
    "rm -rf /tmp/build",
    "rm -rf /home/swf/x",
    "rm -rf ~/Documents",
    "rm -rf ./dist",
    "rm -rf build",
    "rm -rf build/ dist/",
    "rm -rf dist node_modules",
    "rm -f /var/data/a.txt",
    "rm -rf /media/swf/disk/proj/dist",
    "rm a.txt",
    "ls -la",
    "git add -A",
    "rm -rf /var/data/old /tmp/x",
])
def test_root_delete_false_for_normal_deletes(cmd):
    assert is_root_delete(cmd) is False, cmd


pass
@pytest.mark.parametrize("cmd", ["rm -rf /", "rm -rf ~", "sudo rm -rf /"])
def test_policy_denies_root_delete_in_all_modes(cmd):
    pe = PolicyEngine()
    for mode in ("yolo", "workspace", "review"):
        assert pe.check(cmd, PROJ, mode).decision == Decision.DENY, (cmd, mode)


@pytest.mark.parametrize("cmd", [
    "rm -rf /var/data/old",
    "rm -rf /tmp/build",
    "rm -rf build/",
    "rm -rf ./dist",
])
def test_policy_allows_normal_delete_in_yolo(cmd):
    pe = PolicyEngine()
    assert pe.check(cmd, PROJ, "yolo").decision == Decision.ALLOW, cmd
