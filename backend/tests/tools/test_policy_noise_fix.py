from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.security import core as policy_core
from app.security.audit.boundary import classify_path
from app.security.engine import Decision, PolicyEngine
from app.security.wiring import wire_policy
from app.tools import ToolContext

ROOT = "/home/swf/share/harness"


pass
def test_interpreter_is_not_an_operation_target():
    cmd = "cd backend && ../.venv/bin/python -m pytest -q"
    paths = policy_core.extract_paths(cmd)
    assert not any("venv/bin/python" in p for p in paths), paths


def test_cd_rebases_relative_paths():
    cmd = "cd backend && ../.venv/bin/python -m pytest -q"
    g = policy_core.grade_paths(policy_core.extract_paths(cmd), ROOT)
    assert not g.outside, g.outside


def test_heredoc_body_is_not_command_line():
    cmd = ("python - <<'PY'\n"
           '# note about "/tmp/cache/a.log"\n'
           "x = 1\n"
           "PY")
    assert policy_core.extract_paths(cmd) == []


def test_critical_paths_still_detected():
    g = policy_core.grade_paths(policy_core.extract_paths("cat /etc/passwd"), ROOT)
    assert g.critical, g
    assert PolicyEngine().check("cat /etc/passwd", ROOT, "yolo").decision == Decision.DENY


def test_quoted_inline_code_still_detected():
    paths = policy_core.extract_paths('python -c "open(\'/etc/passwd\')"')
    assert any("etc/passwd" in p for p in paths), paths


pass
def test_dev_shm_is_scratch_not_critical():
    assert classify_path("/dev/shm/x", ROOT).value == "project_outside"
    g = policy_core.grade_paths(["/dev/shm/x"], ROOT)
    assert g.scratch and not g.critical, g


@pytest.mark.parametrize("mode", ["yolo", "workspace", "review"])
def test_dev_shm_write_allowed_in_all_modes(mode):
    v = PolicyEngine().check_paths("write", ["/dev/shm/x"], ROOT, mode)
    assert v.decision == Decision.ALLOW


def test_dev_sda_still_critical():
    g = policy_core.grade_paths(["/dev/sda"], ROOT)
    assert g.critical, g


pass
def test_temp_exemption_not_broken_by_mixed_inside_path():
    pe = PolicyEngine()
    v = pe.check_paths("write", ["backend/a.py", "/tmp/b.log"], ROOT, "review")
    assert v.decision == Decision.ALLOW


def test_windows_temp_var_expanded(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("TEMP", str(tmp_path))
    assert policy_core.is_temp_path("%TEMP%\\x.log") is True


pass
class _Appr:
    def __init__(self):
        self.created = []

    def create(self, *a, **kw):
        self.created.append(a)
        return type("PA", (), {"id": "p0", "approved_hunks": None})()

    async def wait(self, pa, stop=None):
        return True


def _gateway_down():
    gw = AsyncMock()
    gw.call_utility = AsyncMock(side_effect=RuntimeError("model down"))
    cfg = type("C", (), {})()
    cfg.settings = type("S", (), {
        "commandDenyPatterns": [], "commandAllowPatterns": [],
        "policyExtraSafePaths": []})()
    gw.config = cfg
    return gw


def _gateway_disabled():
    gw = AsyncMock()
    gw.call_utility = AsyncMock(return_value="")
    cfg = type("C", (), {})()
    cfg.settings = type("S", (), {
        "commandDenyPatterns": [], "commandAllowPatterns": [],
        "policyExtraSafePaths": []})()
    gw.config = cfg
    return gw


async def _wired(tmp_path, mode="workspace", gw=None):
    gw = gw or _gateway_down()
    approvals = _Appr()
    ctx = ToolContext(str(tmp_path))

    async def emit(_e):
        return None

    wire_policy(ctx, str(tmp_path), emit, [], PolicyEngine(gateway=gw),
                approvals, gw, mode=mode)
    return ctx, approvals


@pytest.mark.asyncio
async def test_ai_failure_does_not_popup_for_inside_command(tmp_path):
    ctx, approvals = await _wired(tmp_path)
    v = await ctx.policy_check("ls -la")
    assert v.decision == Decision.ALLOW
    assert approvals.created == []


pass
@pytest.mark.asyncio
@pytest.mark.parametrize("mode,cmd,expected", [
    # 项目内：静态规则本来就该放行，禁用 AI 不应该把弹窗引回来
    ("workspace", "ls -la", Decision.ALLOW),
    # 真出目录：AI 评审禁用后仍按不变式转人工，绝不变成裸奔
    ("workspace", "cat /var/data/elsewhere/x.txt", Decision.REVIEW),
    # 静态高危：跟 AI 无关，三档永拦
    ("yolo", "sudo ls", Decision.DENY),
])
async def test_review_disabled_keeps_static_policy(tmp_path, mode, cmd, expected):
    gw = _gateway_disabled()
    ctx, approvals = await _wired(tmp_path, mode=mode, gw=gw)
    verdict = await ctx.policy_check(cmd)
    assert verdict.decision == expected, (cmd, verdict.reason)
    pass
    pass
    pass
    assert gw.call_utility.return_value == ""
    assert approvals.created == []


@pytest.mark.asyncio
async def test_ai_failure_still_goes_human_for_outside_command(tmp_path):
    ctx, _ = await _wired(tmp_path)
    v = await ctx.policy_check("cat /var/data/elsewhere/x.txt")
    assert v.decision == Decision.REVIEW


@pytest.mark.asyncio
async def test_install_skips_ai_goes_straight_to_human(tmp_path):
    ctx, approvals = await _wired(tmp_path, mode="yolo")
    v = await ctx.policy_check("pip install requests")
    assert v.decision == Decision.REVIEW and v.manual is True
    assert approvals.created == []


pass
def test_wire_policy_uses_session_mode_not_project_kv(tmp_path, monkeypatch):
    import app.security.project_mode as pp

    calls = []

    def fake(cwd):
        calls.append(cwd)
        return "review"

    monkeypatch.setattr(pp, "mode_for_cwd", fake)
    ctx = ToolContext(str(tmp_path))

    async def emit(_e):
        return None

    cfg = type("C", (), {})()
    cfg.settings = type("S", (), {
        "commandDenyPatterns": [], "commandAllowPatterns": [],
        "policyExtraSafePaths": []})()
    gw = type("G", (), {"config": cfg})()

    wire_policy(ctx, str(tmp_path), emit, [], PolicyEngine(), None, gw,
                mode="yolo")
    assert calls == [], "显式会话档位不应触发项目 kv 查询"

    pass
    wire_policy(ctx, str(tmp_path), emit, [], PolicyEngine(), None, gw)
    assert calls, "没传档位时应回落到项目默认档"


pass
pass
pass
pass
_READ_WORKFLOW_CMD = (
    "cd /home/swf/agent/inv-buddy && "
    "PY=/home/swf/miniconda3/envs/313/bin/python3; $PY -c \"\n"
    "import json\n"
    "d=json.load(open('.agent/workflows/x.json'))\n\"\n"
)


def test_interpreter_var_assignment_is_not_target():
    paths = policy_core.extract_paths(_READ_WORKFLOW_CMD)
    assert not any("miniconda3" in p for p in paths), paths
    g = policy_core.grade_paths(paths, "/home/swf/agent/inv-buddy")
    assert not g.outside, g.outside


def test_read_workflow_json_needs_no_popup():
    e = PolicyEngine()
    v = e.check(_READ_WORKFLOW_CMD, "/home/swf/agent/inv-buddy", "workspace")
    assert v.decision is Decision.ALLOW, (v.decision, v.reason)


def test_exec_var_whitelist_does_not_open_backdoor():
    paths = policy_core.extract_paths("X=/etc/shadow; rm $X")
    assert "/etc/shadow" in paths, paths
    g = policy_core.grade_paths(paths, "/home/swf/agent/inv-buddy")
    assert g.has_critical, g.critical

    outside = policy_core.extract_paths("OUT=/home/other/x.txt && echo hi > $OUT")
    g2 = policy_core.grade_paths(outside, "/home/swf/agent/inv-buddy")
    assert g2.outside, g2.outside


def test_env_var_expanded_so_danger_is_visible():
    paths = policy_core.extract_paths("rm -rf $HOME/docs")
    assert any(p.startswith("/") and p.endswith("/docs") for p in paths), paths


def test_inline_code_is_not_a_file_path():
    cmd = 'python3 -c "import json; json.load(open(\'.agent/x.json\'))"'
    paths = policy_core.extract_paths(cmd)
    assert not any("import json" in p for p in paths), paths


def test_inline_heredoc_critical_still_denied():
    e = PolicyEngine()
    heredoc = "python3 - <<'PY'\nimport os\nos.remove('/etc/hosts')\nPY\n"
    v = e.check(heredoc, "/home/swf/agent/inv-buddy", "workspace")
    assert v.decision is Decision.DENY, (v.decision, v.reason)
    inline = 'python3 -c "import os; os.remove(\'/etc/hosts\')"'
    v2 = e.check(inline, "/home/swf/agent/inv-buddy", "workspace")
    assert v2.decision is Decision.DENY, (v2.decision, v2.reason)


def test_segment_env_prefix_does_not_hide_interpreter():
    cmd = (
        'PY=/home/swf/miniconda3/envs/313/bin/python3 && PYTHONPATH=. '
        '$PY -c "import sqlite3"'
    )
    paths = policy_core.extract_paths(cmd)
    assert not any("miniconda" in p for p in paths), paths
    v = PolicyEngine().check(cmd, "/home/swf/share/agent/inv-buddy", "workspace")
    assert v.decision is Decision.ALLOW, (v.decision, v.reason)


def test_segment_env_prefix_still_catches_danger_after_it():
    g = policy_core.grade_paths(
        policy_core.extract_paths("A=1 && rm -rf /etc"),
        "/home/swf/share/agent/inv-buddy")
    assert g.has_critical, g.critical
    pass
    sub = policy_core.extract_paths("A=$(cat /etc/hosts) echo $A")
    assert "/etc/hosts" in sub, sub


pass
pass
pass
pass
_ROLE_CASES = [
    # (命令, cwd, 期望, 说明)
    ('PY=/x/bin/python3 && PYTHONPATH=. $PY -c "import sqlite3"', None, "allow",
     "conda 解释器在命令词位"),
    ('env PYTHONPATH=. /opt/conda/bin/python3 -c "print(1)"', None, "allow",
     "env 介词后的解释器"),
    ("X=/etc/shadow; rm $X", None, "deny",
     "同一变量的值出现在参数位就是数据"),
    ("OUT=/home/other/x.txt && echo hi > $OUT", None, "review",
     "重定向位的数据变量照判"),
    ("A=1 && rm -rf /etc", None, "deny", "跳过声明位不影响后面的真命令"),
    ("A=$(cat /etc/hosts) && echo $A", None, "deny", "$(...) 子命令也要看"),
    ("python3 - <<'P'\nimport os\nos.remove('/etc/hosts')\nP", None, "deny",
     "heredoc 正文交静态审查"),
    ('python3 -c "import os; os.remove(\'/etc/hosts\')"', None, "deny",
     "内联代码交静态审查"),
    ("cat kb/db/knowledge.db", None, "allow", "项目内裸相对文件名"),
    ("cd ../other && ls", None, "allow", "cd 目标本身不产生操作"),
]


@pytest.mark.parametrize("cmd,_cwd,expect,_why", _ROLE_CASES)
def test_role_model_decides_by_syntax_not_by_name(cmd, _cwd, expect, _why):
    root = "/home/swf/share/agent/inv-buddy"
    v = PolicyEngine().check(cmd, root, "workspace")
    assert v.decision.value == expect, (cmd, v.decision.value, v.reason)


def test_no_runtime_name_whitelist_left():
    from app.security import path_scan

    for gone in ("_EXEC_NAMES", "_looks_executable", "_SEG_PREFIX_RE",
                 "_exec_vars", "_bare_file_args", "_FILE_ARG_CMDS"):
        assert not hasattr(path_scan, gone), f"path_scan 又出现名字特例 {gone}"


def test_shell_role_model_user_commandlines():
    from app.security.engine import PolicyEngine
    from app.security.path_scan import extract_paths

    p = "/home/swf/miniconda3/envs/313/bin/python3"
    heredoc = (
        f"PY={p}; cd /home/swf/agent/inv-buddy && timeout 90 $PY - <<'PY'\n"
        "import os,sys\nsys.path.insert(0,'.')\nprint(1)\nPY"
    )
    inline = (
        f"cd /home/swf/share/agent/inv-buddy && PY={p} && "
        'PYTHONPATH=. $PY -c "print(1)"'
    )
    e = PolicyEngine()
    for cmd in (heredoc, inline):
        assert extract_paths(cmd) == [], cmd
        assert e.check(cmd, "/home/swf/code/harness", "workspace").decision.value == "allow"

    pass
    assert extract_paths("X=/etc/shadow; rm $X") == ["/etc/shadow"]
    assert e.check("X=/etc/shadow; rm $X", "/home/swf/code/harness", "workspace").decision.value == "deny"
    assert extract_paths("OUT=/home/other/x.txt; echo hi > $OUT") == ["/home/other/x.txt"]
    assert extract_paths("rm -rf /etc") == ["/etc"]
    assert extract_paths("A=$(cat /etc/hosts); echo $A") == ["/etc/hosts"]


def test_bare_words_and_numbers_are_not_paths():
    from app.security.path_scan import extract_paths

    assert extract_paths("echo hi") == []
    assert extract_paths("timeout 90 ls") == []
    assert extract_paths("for k in range(3): print(k)") == []
    pass
    import os
    name = next(n for n in os.listdir(".") if os.path.isfile(n))
    assert extract_paths(f"cat {name}") == [name]
