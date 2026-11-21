from __future__ import annotations

import pytest

from app.security.engine import Decision, PolicyEngine
from app.security.core import BENIGN_PATHS, extract_paths, grade_paths, is_benign_path

DEVNULL = "/dev/" + "null"


@pytest.fixture()
def proj(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    return p


pass
def test_benign_set_covers_common_devices():
    for p in (DEVNULL, "/dev/stdout", "/dev/stderr"):
        assert is_benign_path(p), p


def test_benign_set_does_not_cover_block_devices():
    for p in ("/dev/sda", "/dev/sda1", "/dev/nvme0n1", "/dev/mem", "/dev/kmsg"):
        assert not is_benign_path(p), p


def test_grade_skips_benign_paths(proj):
    g = grade_paths([DEVNULL], str(proj))
    assert g.critical == []
    assert g.outside == [] and g.inside == []


def test_grade_still_flags_block_device(proj):
    g = grade_paths(["/dev/sda"], str(proj))
    assert g.critical == ["/dev/sda"]


pass
@pytest.mark.parametrize("mode", ["yolo", "workspace"])
@pytest.mark.parametrize("cmd", [
    f"curl -s -o {DEVNULL} http://x",
    f"cmd > {DEVNULL} 2>&1",
    f"echo hi > {DEVNULL}",
    f"ls 2>{DEVNULL}",
    f"make > {DEVNULL} &",
])
def test_devnull_redirect_allowed_in_permissive_modes(proj, mode, cmd):
    v = PolicyEngine().check(cmd, str(proj), mode)
    assert v.decision == Decision.ALLOW, f"{mode}: {cmd}"


@pytest.mark.parametrize("cmd", [
    f"cat x > {DEVNULL}",
    f"ls 2>{DEVNULL}",
])
def test_devnull_not_treated_as_escape_in_review_mode(proj, cmd):
    assert PolicyEngine().check(cmd, str(proj), "review").decision == Decision.ALLOW


pass
@pytest.mark.parametrize("cmd", [
    "curl -s https://api.example.com/v1/chat",
    "git clone https://github.com/a/b.git",
    "wget http://example.com/x.tar.gz",
])
def test_urls_are_not_mistaken_for_paths(proj, cmd):
    assert extract_paths(cmd) == []
    assert PolicyEngine().check(cmd, str(proj), "workspace").decision == Decision.ALLOW


pass
def test_extract_strips_shell_syntax_tails(proj):
    got = extract_paths(f'cmd > {DEVNULL}" 2>&1')
    assert DEVNULL in got
    assert all(not g.startswith(DEVNULL + '"') for g in got)


def test_extract_drops_fd_redirect_noise(proj):
    got = extract_paths(f"cmd > {DEVNULL} 2>&1; ls")
    assert got == [DEVNULL]


def test_extract_drops_option_flags(proj):
    assert all(not p.startswith("-") for p in extract_paths("rm -rf /tmp/x"))


def test_benign_set_is_a_frozenset():
    assert isinstance(BENIGN_PATHS, frozenset)
