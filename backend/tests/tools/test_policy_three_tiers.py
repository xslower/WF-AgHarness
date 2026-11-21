from __future__ import annotations

import pytest

from app.security.engine import Decision, PolicyEngine


@pytest.fixture()
def proj(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    return p


def check(pe, cmd, proj, mode):
    return pe.check(cmd, str(proj), mode).decision


pass
def test_yolo_allows_everything_normal(proj):
    pe = PolicyEngine()
    for cmd in ["ls -la", "git add -A", "python3 main.py", "make build"]:
        assert check(pe, cmd, proj, "yolo") == Decision.ALLOW, cmd


def test_yolo_allows_outside_paths(proj):
    pe = PolicyEngine()
    assert check(pe, "cat /tmp/other/x.txt", proj, "yolo") == Decision.ALLOW


def test_yolo_still_blocks_critical_paths(proj):
    pe = PolicyEngine()
    for target in ("/etc/passwd", "/etc/hosts", "/usr/bin/env"):
        assert check(pe, f"cat {target}", proj, "yolo") == Decision.DENY, target


def test_yolo_still_blocks_static_danger(proj):
    pe = PolicyEngine()
    for cmd in ["sudo ls", "mkfs.ext4 /dev/sdb", "git push --force"]:
        assert check(pe, cmd, proj, "yolo") == Decision.DENY, cmd


pass
def test_workspace_allows_inside_including_mutations(proj):
    pe = PolicyEngine()
    for cmd in ["ls -la", "rm -rf build/", "mv a.txt b.txt", "cp x y",
                "touch new.txt", "python3 job.py"]:
        assert check(pe, cmd, proj, "workspace") == Decision.ALLOW, cmd


def test_workspace_outside_needs_review(proj):
    pe = PolicyEngine()
    v = pe.check("cat /var/data/elsewhere/x.txt", str(proj), "workspace")
    assert v.decision == Decision.REVIEW
    assert "工作目录之外" in v.risks[0].description


def test_workspace_outside_relative_path_needs_review(proj, monkeypatch):
    from app.security import core as policy_core
    monkeypatch.setattr(policy_core, "temp_roots", lambda extra=None: [])
    pe = PolicyEngine()
    assert check(pe, "rm -rf ../other/", proj, "workspace") == Decision.REVIEW


def test_workspace_blocks_critical(proj):
    pe = PolicyEngine()
    assert check(pe, "cat /etc/passwd", proj, "workspace") == Decision.DENY


def test_workspace_script_touching_outside_needs_review(proj):
    (proj / "clean.py").write_text(
        "import shutil\nshutil.rmtree('/home/someone/important')\n")
    pe = PolicyEngine()
    v = pe.check("python3 clean.py", str(proj), "workspace")
    assert v.decision == Decision.REVIEW
    assert "工作目录之外" in v.risks[0].description


def test_workspace_script_staying_inside_is_allowed(proj):
    (proj / "job.py").write_text("open('out.txt','w').write('x')\n")
    pe = PolicyEngine()
    assert check(pe, "python3 job.py", proj, "workspace") == Decision.ALLOW


pass
def test_review_allows_readonly_prefixes(proj):
    pe = PolicyEngine()
    for cmd in ["ls -la", "git status", "cat README.md", "grep -r x ."]:
        assert check(pe, cmd, proj, "review") == Decision.ALLOW, cmd


def test_review_mutations_need_review(proj):
    pe = PolicyEngine()
    for cmd in ["rm -rf build/", "mv a.txt b.txt", "python3 job.py"]:
        assert check(pe, cmd, proj, "review") == Decision.REVIEW, cmd


def test_review_blocks_critical(proj):
    pe = PolicyEngine()
    assert check(pe, "cat /etc/passwd", proj, "review") == Decision.DENY


pass
@pytest.mark.parametrize("mode", ["yolo", "workspace", "review"])
def test_install_needs_manual_in_all_modes(proj, mode):
    pe = PolicyEngine()
    for cmd in ["pip install requests", "npm install lodash",
                "apt-get install curl", "cargo install ripgrep"]:
        v = pe.check(cmd, str(proj), mode)
        assert v.decision == Decision.REVIEW, (mode, cmd)
        assert v.manual is True, (mode, cmd)


@pytest.mark.parametrize("mode", ["yolo", "workspace", "review"])
def test_critical_paths_denied_in_all_modes(proj, mode):
    pe = PolicyEngine()
    for target in ("/etc/shadow", "/etc/sudoers", "/usr/bin/python3"):
        assert check(pe, f"cat {target}", proj, mode) == Decision.DENY, target


def test_unknown_mode_falls_back_to_workspace(proj):
    pe = PolicyEngine()
    assert check(pe, "cat /var/data/elsewhere/x", proj, "typo-mode") == Decision.REVIEW


def test_ai_unavailable_in_review_mode_goes_to_human(proj):
    pe = PolicyEngine(gateway=None)
    assert check(pe, "python3 job.py", proj, "review") == Decision.REVIEW
