from __future__ import annotations

from app.agent.plan import is_likely_write_command


pass
def test_inline_python_write_detected():
    assert is_likely_write_command('''python3 -c "open('x.py','w').write('hi')"''') is True


def test_inline_python_read_not_blocked():
    assert is_likely_write_command('python3 -c "print(1)"') is False
    assert is_likely_write_command('python3 -c "import json; print(json.dumps({}))"') is False


def test_inline_node_write_detected():
    assert is_likely_write_command(
        'node -e "require(\'fs\').writeFileSync(\'x\',\'y\')"') is True


def test_inline_python_os_remove_detected():
    assert is_likely_write_command('python -c "import os; os.remove(\'f\')"') is True


def test_inline_bash_c_write_detected():
    assert is_likely_write_command('bash -c "rm -rf build"') is True


pass
def test_script_file_with_write_is_blocked(tmp_path):
    s = tmp_path / "tmp_edit.py"
    s.write_text("with open('out.txt', 'w') as f:\n    f.write('x')\n", "utf-8")
    assert is_likely_write_command(f"python {s.name}", str(tmp_path)) is True


def test_script_file_readonly_is_allowed(tmp_path):
    s = tmp_path / "scan.py"
    s.write_text("import json\nprint(json.dumps({'a': 1}))\n", "utf-8")
    assert is_likely_write_command(f"python {s.name}", str(tmp_path)) is False


def test_script_comment_mentioning_write_is_ignored(tmp_path):
    s = tmp_path / "scan2.py"
    s.write_text("# 这里以前用 open('x','w') 写过\nprint('ok')\n", "utf-8")
    assert is_likely_write_command(f"python {s.name}", str(tmp_path)) is False


def test_script_missing_file_not_blocked(tmp_path):
    assert is_likely_write_command("python not_exist_zz.py", str(tmp_path)) is False


def test_script_pathlib_write_text_detected(tmp_path):
    s = tmp_path / "p.py"
    s.write_text("from pathlib import Path\nPath('a.txt').write_text('x')\n", "utf-8")
    assert is_likely_write_command(f"python {s.name}", str(tmp_path)) is True


def test_script_shutil_detected(tmp_path):
    s = tmp_path / "c.py"
    s.write_text("import shutil\nshutil.rmtree('build')\n", "utf-8")
    assert is_likely_write_command(f"python {s.name}", str(tmp_path)) is True


pass
def test_tool_invoke_is_treated_as_write_tool():
    from app.agent.plan import READONLY_TOOL_ACTIONS, WRITE_TOOL_NAMES
    assert "tool" in WRITE_TOOL_NAMES
    assert READONLY_TOOL_ACTIONS["tool"] == {"search", "use"}


def test_subagent_spawn_allowed_in_readonly_mode():
    from app.agent.plan import READONLY_TOOL_ACTIONS, WRITE_TOOL_NAMES
    assert "subagent" in WRITE_TOOL_NAMES
    assert "spawn" in READONLY_TOOL_ACTIONS["subagent"]
    pass
    for act in ("message", "stop", "extend"):
        assert act not in READONLY_TOOL_ACTIONS["subagent"]


pass
def test_tool_cannot_invoke_tool():
    import asyncio
    import app.tools.builtin.meta as meta

    class _Ctx:
        mcp = None

    out = asyncio.run(meta._invoke("tool", {}, _Ctx()))
    assert "不允许调用 tool" in out
