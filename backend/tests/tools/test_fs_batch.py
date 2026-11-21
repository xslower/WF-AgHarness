from __future__ import annotations

import asyncio

from app.tools.builtin.fs.schemas import SCHEMAS
from app.tools.builtin.fs.write import f_replace, f_write


async def _noop_snapshot(*_a, **_k):
    return None


class _Ctx:
    def __init__(self, cwd):
        self.cwd = str(cwd)
        self.session_id = "batch-test"
        self.path_check = None
        self.auto_snapshot = _noop_snapshot
        self.request_file_approval = None
        self.report_file = None

    def emit_stream(self, *_a, **_k):
        return None


def _run(coro):
    return asyncio.run(coro)


def _seed(tmp_path, text="A1\nA2\nA3\nA4\nA5\n"):
    p = tmp_path / "x.py"
    p.write_text(text, encoding="utf-8")
    return p, _Ctx(tmp_path)


pass
def test_write_batch_two_edits(tmp_path):
    p, ctx = _seed(tmp_path)
    out = _run(f_write("x.py", ctx=ctx, edits=[
        {"before": 1, "content": "HEAD\n"},
        {"append": True, "content": "TAIL\n"},
    ]))
    assert "2 处改动 → 2 成功 / 0 失败" in out
    assert p.read_text(encoding="utf-8") == "HEAD\nA1\nA2\nA3\nA4\nA5\nTAIL\n"


def test_write_batch_mode_outside_array(tmp_path):
    p, ctx = _seed(tmp_path, "L1\nL2\nL3\n")
    out = _run(f_write("x.py", ctx=ctx, edits=[
        {"before": 1, "content": "N1\n"},
        {"append": True, "content": "N2\n", "mode": 0}]))
    assert "2 处改动 → 2 成功" in out
    assert p.read_text(encoding="utf-8") == "N1\nL1\nL2\nL3\nN2\n"


def test_write_batch_one_edit_fails_others_still_apply(tmp_path):
    p, ctx = _seed(tmp_path)
    out = _run(f_write("x.py", ctx=ctx, edits=[
        {"before": 1, "content": "HEAD\n"},
        {"before": 3, "expect": "这段锚点不存在", "content": "BAD\n"},
        {"append": True, "content": "TAIL\n"},
    ]))
    assert "3 处改动 → 2 成功 / 1 失败" in out
    assert "#2 ✗" in out
    body = p.read_text(encoding="utf-8")
    assert body.startswith("HEAD\n") and body.endswith("TAIL\n")


def test_write_batch_revert_is_transactional(tmp_path):
    p, ctx = _seed(tmp_path, "ORIGINAL\n")
    _run(f_write("x.py", ctx=ctx, edits=[
        {"before": 1, "content": "V1\n"}, {"append": True, "content": "V2\n"}]))
    assert p.read_text(encoding="utf-8") != "ORIGINAL\n"
    _run(f_write("x.py", ctx=ctx, content="", mode=2))
    assert p.read_text(encoding="utf-8") == "ORIGINAL\n"


def test_write_batch_rejects_empty_and_non_object(tmp_path):
    _p, ctx = _seed(tmp_path)
    assert "为空" in _run(f_write("x.py", ctx=ctx, edits=[]))
    assert "不是对象" in _run(f_write("x.py", ctx=ctx, edits=["oops"]))


def test_single_write_still_works(tmp_path):
    p, ctx = _seed(tmp_path)
    out = _run(f_write("x.py", ctx=ctx, content="NEW\n"))
    assert "已写入" in out and p.read_text(encoding="utf-8") == "NEW\n"


pass
def test_replace_batch_two_edits(tmp_path):
    p, ctx = _seed(tmp_path, "foo\nbar\nbaz\n")
    out = _run(f_replace("x.py", ctx=ctx, edits=[
        {"old": "foo", "new": "FOO"},
        {"old": "bar", "new": "BAR"},
    ]))
    assert "2 处改动 → 2 成功 / 0 失败" in out
    assert p.read_text(encoding="utf-8") == "FOO\nBAR\nbaz\n"


def test_replace_count_limits_hits(tmp_path):
    p, ctx = _seed(tmp_path, "foo\nfoo\nfoo\n")
    out = _run(f_replace("x.py", ctx=ctx, old="foo", new="X",
                         replace_count=2))
    assert "已修改" in out
    assert p.read_text(encoding="utf-8") == "X\nX\nfoo\n"


def test_replace_batch_with_replace_count(tmp_path):
    p, ctx = _seed(tmp_path, "foo\nfoo\nfoo\n")
    _run(f_replace("x.py", ctx=ctx, edits=[
        {"old": "foo", "new": "X", "replace_count": 1},
        {"old": "foo", "new": "Y", "replace_count": 1},
    ]))
    assert p.read_text(encoding="utf-8") == "X\nY\nfoo\n"


def test_replace_batch_revert_is_transactional(tmp_path):
    p, ctx = _seed(tmp_path, "alpha\nbeta\n")
    _run(f_replace("x.py", ctx=ctx, edits=[
        {"old": "alpha", "new": "A"}, {"old": "beta", "new": "B"}]))
    _run(f_replace("x.py", ctx=ctx, mode=2))
    assert p.read_text(encoding="utf-8") == "alpha\nbeta\n"


def test_single_replace_still_works(tmp_path):
    p, ctx = _seed(tmp_path, "a\nb\n")
    out = _run(f_replace("x.py", ctx=ctx, old="a", new="z"))
    assert "已修改" in out and p.read_text(encoding="utf-8") == "z\nb\n"


pass
def test_schema_declares_batch_edits():
    w = SCHEMAS["f_write"]
    r = SCHEMAS["f_replace"]
    assert w["params"]["edits"]["type"] == "array"
    assert r["params"]["edits"]["type"] == "array"
    assert "mode" not in w["params"]["edits"].get("items", {}).get("properties", {})
    assert "edits" in w["required"] and "edits" in r["required"]


pass
def test_grep_default_context_uses_rg_with_C(tmp_path, monkeypatch):
    import subprocess
    from app.tools.builtin.fs import read as _r

    (tmp_path / "a.py").write_text("l1\nl2\nl3\nNEEDLE\nl5\nl6\nl7\n",
                                   encoding="utf-8")
    seen = {}

    class _R:
        stdout = "a.py:3-l2\na.py:4:NEEDLE\na.py:5-l5\n"
        stderr = ""
        returncode = 0


    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        return _R()

    monkeypatch.setattr(_r.shutil, "which", lambda _n: "/usr/bin/rg")
    monkeypatch.setattr(_r.subprocess, "run", fake_run)
    out = _r.grep_sync(["NEEDLE"], _Ctx(tmp_path), path=".")
    assert "-C" in seen["cmd"] and "3" in seen["cmd"]
    assert "NEEDLE" in out and "l2" in out


def test_grep_key_array_matches_any(tmp_path, monkeypatch):
    from app.tools.builtin.fs import read as _r

    (tmp_path / "a.py").write_text("foo\nbar\nbaz\n", encoding="utf-8")
    monkeypatch.setattr(_r.shutil, "which", lambda _n: None)
    out = _r.grep_sync(["foo", "baz"], _Ctx(tmp_path), path=".", context=0)
    assert "foo" in out and "baz" in out


def test_grep_schema_declares_key_array_and_regex_switch():
    g = SCHEMAS["grep"]
    assert g["params"]["key"]["type"] == "array"
    assert g["params"]["key"]["items"]["type"] == "string"
    assert g["params"]["regex"]["type"] == "boolean"
    assert "key" in g["required"]


def test_grep_literal_by_default_escapes_metachars(tmp_path, monkeypatch):
    from app.tools.builtin.fs import read as _r

    (tmp_path / "a.py").write_text('''a.c
abc
''', encoding="utf-8")
    monkeypatch.setattr(_r.shutil, "which", lambda _n: None)
    out = _r.grep_sync(["a.c"], _Ctx(tmp_path), path=".", context=0)
    assert "a.c" in out and "abc" not in out


def test_grep_regex_switch_matches_pattern(tmp_path, monkeypatch):
    from app.tools.builtin.fs import read as _r

    (tmp_path / "a.py").write_text('''def foo():
plain
''', encoding="utf-8")
    monkeypatch.setattr(_r.shutil, "which", lambda _n: None)
    rx = "def [a-z]+"
    assert "def foo():" in _r.grep_sync([rx], _Ctx(tmp_path), path=".", context=0, regex=True)
    assert "def foo():" not in _r.grep_sync([rx], _Ctx(tmp_path), path=".", context=0)


def test_grep_invalid_regex_reports_error(tmp_path, monkeypatch):
    from app.tools.builtin.fs import read as _r

    monkeypatch.setattr(_r.shutil, "which", lambda _n: None)
    assert "正则表达式无效" in _r.grep_sync(["("], _Ctx(tmp_path), path=".", regex=True)


def test_grep_empty_keys_reports_error(tmp_path):
    from app.tools.builtin.fs import read as _r

    assert "key 不能为空" in _r.grep_sync([], _Ctx(tmp_path), path=".")


def test_grep_single_string_still_works(tmp_path, monkeypatch):
    from app.tools.builtin.fs import read as _r

    (tmp_path / "a.py").write_text("NEEDLE" + chr(10), encoding="utf-8")
    monkeypatch.setattr(_r.shutil, "which", lambda _n: None)
    assert "NEEDLE" in _r.grep_sync("NEEDLE", _Ctx(tmp_path), path=".", context=0)


def test_grep_rg_uses_e_for_expression(tmp_path, monkeypatch):
    from app.tools.builtin.fs import read as _r

    (tmp_path / "a.py").write_text("-dash" + chr(10), encoding="utf-8")
    seen = {}

    class _R:
        stdout = "a.py:1:-dash"
        stderr = ""
        returncode = 0

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        return _R()

    monkeypatch.setattr(_r.shutil, "which", lambda _n: "/usr/bin/rg")
    monkeypatch.setattr(_r.subprocess, "run", fake_run)
    out = _r.grep_sync(["-dash"], _Ctx(tmp_path), path=".", context=0)
    assert "-e" in seen["cmd"] and "-dash" in out
    assert seen["cmd"].index("-e") < seen["cmd"].index("--")


pass
def test_write_batch_reverse_order_uses_original_line_numbers(tmp_path):
    p, ctx = _seed(tmp_path, "L1\nL2\nL3\nL4\nL5\n")
    out = _run(f_write("x.py", ctx=ctx, edits=[
        {"before": 2, "content": "AT2\n"},
        {"before": 4, "content": "AT4\n"},
    ]))
    assert "2 处改动 → 2 成功 / 0 失败" in out
    assert p.read_text(encoding="utf-8") == "L1\nAT2\nL2\nL3\nAT4\nL4\nL5\n"


def test_write_batch_conflicting_ranges_rejected_whole_batch(tmp_path):
    p, ctx = _seed(tmp_path, "L1\nL2\nL3\nL4\nL5\n")
    before = p.read_text(encoding="utf-8")
    out = _run(f_write("x.py", ctx=ctx, edits=[
        {"replace": "2,4", "content": "A\n"},
        {"replace": "3,5", "content": "B\n"},
    ]))
    assert "重叠" in out and "整批拒绝" in out
    assert p.read_text(encoding="utf-8") == before


def test_write_batch_overwrite_mixed_with_edit_rejected(tmp_path):
    p, ctx = _seed(tmp_path, "L1\nL2\n")
    before = p.read_text(encoding="utf-8")
    out = _run(f_write("x.py", ctx=ctx, edits=[
        {"content": "WHOLE\n"},
        {"append": True, "content": "TAIL\n"},
    ]))
    assert "整篇覆盖" in out and "整批拒绝" in out
    assert p.read_text(encoding="utf-8") == before


def test_write_batch_insert_inside_replace_range_rejected(tmp_path):
    p, ctx = _seed(tmp_path, "L1\nL2\nL3\nL4\n")
    before = p.read_text(encoding="utf-8")
    out = _run(f_write("x.py", ctx=ctx, edits=[
        {"replace": "1,4", "content": "NEW\n"},
        {"before": 3, "content": "IN\n"},
    ]))
    assert "插入点落在" in out and "整批拒绝" in out
    assert p.read_text(encoding="utf-8") == before


def test_write_batch_result_keeps_original_edit_index(tmp_path):
    _p, ctx = _seed(tmp_path, "L1\nL2\nL3\nL4\nL5\n")
    out = _run(f_write("x.py", ctx=ctx, edits=[
        {"before": 2, "content": "A\n"},
        {"before": 5, "content": "B\n"},
    ]))
    assert out.find("#1 ✓") < out.find("#2 ✓")


pass
pass
pass
pass


def test_batch_line_count_matches_read_side_on_formfeed(tmp_path):
    p, ctx = _seed(tmp_path, "A1\nA2\fB\nA3\vC\nA4\n")
    out = _run(f_write(p.name, ctx, edits=[{
        "replace": "5,5", "content": "X"}]))
    assert "error" in out.lower() or "错误" in out, out
    assert p.read_text("utf-8") == "A1\nA2\fB\nA3\vC\nA4\n"


def test_batch_replaces_by_read_side_line_numbers(tmp_path):
    p, ctx = _seed(tmp_path, "A1\nA2\fB\nA3\vC\nA4\n")
    out = _run(f_write(p.name, ctx, edits=[{
        "replace": "3,3", "content": "A3-new", "expect": "A3"}]))
    assert "error" not in out.lower(), out
    assert p.read_text("utf-8") == "A1\nA2\fB\nA3-new\nA4\n"
