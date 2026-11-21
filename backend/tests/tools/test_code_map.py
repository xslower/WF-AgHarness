from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.agent import code_map
from app.agent.code_map import (MAX_MAP_CHARS, build_index, query_index,
                                render_for_spawn)
from app.tools.builtin.fs.read import grep_sync
from app.tools.builtin.fs.schemas import SCHEMAS


class _Ctx:
    cwd = ""


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / ".agent").mkdir()
    (tmp_path / "svc").mkdir()
    (tmp_path / "svc" / "orders.py").write_text(
        'class OrderService:\n'
        '    """处理订单"""\n'
        '    def create_order(self, x):\n'
        '        return x\n'
        '    def cancel_order(self):\n'
        '        pass\n'
        '\n'
        'def send_mail(to):\n'
        '    return to\n', encoding="utf-8")
    (tmp_path / "svc" / "misc.py").write_text(
        'def ping():\n    return "pong"\n', encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.py").write_text(
        'def should_not_be_indexed():\n    pass\n', encoding="utf-8")
    return tmp_path


def test_index_only_scans_own_project(project):
    files, _ = build_index(str(project / "svc"))
    paths = {f["path"] for f in files}
    assert paths == {"svc/orders.py", "svc/misc.py"}
    assert (project / ".agent" / "code_map.json").exists()


def test_index_path_is_relative_and_has_line_ranges(project):
    files, _ = build_index(str(project / "svc"))
    rows = next(f["rows"] for f in files if f["path"] == "svc/orders.py")
    assert any("create_order" in r and r.startswith("L") for r in rows)
    assert any("OrderService" in r for r in rows)
    pass
    assert any("-" in r.split()[0] for r in rows)


def test_index_is_incremental_by_mtime(project, monkeypatch):
    build_index(str(project / "svc"))
    calls = []
    orig = code_map.rows_for

    def spy(text, lines):
        calls.append(1)
        return orig(text, lines)

    monkeypatch.setattr(code_map, "rows_for", spy)
    build_index(str(project / "svc"))
    assert calls == [], "mtime 未变时不应重新 ast.parse"


def test_rebuild_after_file_change(project, monkeypatch):
    build_index(str(project / "svc"))
    pass
    p = project / "svc" / "misc.py"
    p.write_text('def ping():\n    return "pong"\n\ndef refund():\n    pass\n',
                 encoding="utf-8")
    import os
    os.utime(p, (p.stat().st_mtime + 10, p.stat().st_mtime + 10))
    files, _ = build_index(str(project / "svc"))
    rows = next(f["rows"] for f in files if f["path"] == "svc/misc.py")
    assert any("refund" in r for r in rows)


def test_query_by_key_returns_index_not_fulltext(project):
    out = query_index(str(project / "svc"), ["order"])
    assert "svc/orders.py" in out and "create_order" in out
    assert "return x" not in out, "地图不能塞函数体"
    assert "svc/misc.py" not in out


def test_query_empty_key_gives_overview(project):
    out = query_index(str(project / "svc"), [])
    assert "个源文件" in out
    assert "svc/orders.py" in out
    assert "create_order" not in out, "概览不该列全量签名"


def test_query_no_match(project):
    assert "无匹配" in query_index(str(project / "svc"), ["zzz_no_such"])


def test_non_project_cwd_is_empty(tmp_path):
    pass
    assert query_index(str(tmp_path), []) .startswith("(代码地图为空")
    assert render_for_spawn(str(tmp_path), ["x"]) == ""


def test_render_for_spawn_is_bounded_and_index_only(project):
    s = render_for_spawn(str(project / "svc"), ["order"])
    assert "项目代码地图" in s and "OrderService" in s
    assert "return x" not in s
    assert len(s) <= MAX_MAP_CHARS
    pass
    assert "svc/orders.py" in render_for_spawn(str(project / "svc"), [])


def test_render_hints_no_match_falls_back_to_filelist(project):
    s = render_for_spawn(str(project / "svc"), ["zzz_no_such"])
    assert "无命中" in s and "svc/orders.py" in s


def test_grep_outline_schema_and_entry(project):
    assert "outline" in SCHEMAS["grep"]["params"]
    ctx = _Ctx()
    ctx.cwd = str(project / "svc")
    out = grep_sync(["order"], ctx, outline=True)
    assert "svc/orders.py" in out and "create_order" in out
    assert "return x" not in out


def test_grep_outline_empty_key_allowed(project):
    ctx = _Ctx()
    ctx.cwd = str(project / "svc")
    out = grep_sync([], ctx, outline=True)
    assert "个源文件" in out


def test_grep_normal_still_requires_key(project):
    ctx = _Ctx()
    ctx.cwd = str(project / "svc")
    assert "key 不能为空" in grep_sync([], ctx)


def test_index_file_is_json_and_reloadable(project):
    build_index(str(project / "svc"))
    data = json.loads((project / ".agent" / "code_map.json").read_text(
        encoding="utf-8"))
    assert "files" in data and len(data["files"]) == 2
    assert all("path" in f and "rows" in f and "mtime" in f
               for f in data["files"])


def test_subagent_schema_has_hints():
    from app.tools.builtin.subagent_tool import subagent
    import inspect
    assert "hints" in inspect.signature(subagent).parameters


def test_grep_outline_respects_path_scope(tmp_path):
    (tmp_path / ".agent").mkdir()
    for d, name, fn in (("a", "one", "alpha"), ("b", "two", "beta")):
        (tmp_path / d).mkdir()
        (tmp_path / d / f"{name}.py").write_text(
            f"def {fn}():\n    pass\n", encoding="utf-8")
    ctx = _Ctx()
    ctx.cwd = str(tmp_path)
    scoped = grep_sync(["alpha", "beta"], ctx, path="a", outline=True)
    assert "a/one.py" in scoped
    assert "b/two.py" not in scoped, "path=a 时不该返回兄弟目录"
    whole = grep_sync(["alpha", "beta"], ctx, outline=True)
    assert "a/one.py" in whole and "b/two.py" in whole


def test_grep_outline_ts_dir_gives_clear_hint(tmp_path):
    (tmp_path / ".agent").mkdir()
    (tmp_path / "frontend" / "src").mkdir(parents=True)
    (tmp_path / "frontend" / "src" / "x.ts").write_text(
        "export const a = 1;\n", encoding="utf-8")
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "b.py").write_text(
        "def foo():\n    pass\n", encoding="utf-8")
    ctx = _Ctx()
    ctx.cwd = str(tmp_path)
    out = grep_sync(["foo"], ctx, path="frontend/src", outline=True)
    assert "backend/b.py" not in out
    assert "没有可索引的源码文件" in out


def test_grep_outline_path_outside_project_errors(tmp_path):
    proj = tmp_path / "proj"
    (proj / ".agent").mkdir(parents=True)
    (proj / "m.py").write_text("def foo():\n    pass\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    ctx = _Ctx()
    ctx.cwd = str(proj)
    out = grep_sync(["foo"], ctx, path=str(outside), outline=True)
    assert "不在当前项目内" in out
