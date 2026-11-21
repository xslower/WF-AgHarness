from __future__ import annotations

import pytest

from app.tools.builtin.fs.write import f_replace, f_write
from app.tools.builtin.fs.read import f_read
from app.tools import ToolContext


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(str(tmp_path))


def write_file(tmp_path, name, text, newline="\n"):
    p = tmp_path / name
    p.write_bytes(text.replace("\n", newline).encode("utf-8"))
    return p


pass

async def test_write_overwrite_when_no_lines(ctx, tmp_path):
    f = write_file(tmp_path, "a.txt", "hello\nworld")
    r = await f_write(str(f), ctx, content="new\ntext")
    assert "已写入" in r
    assert f.read_text("utf-8") == "new\ntext"


async def test_write_insert_before_line(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l1\nl2\nl3\n")
    r = await f_write(str(f), ctx, content="NEW", before=2)
    assert "插入" in r
    assert f.read_text("utf-8") == "l1\nNEW\nl2\nl3\n"


async def test_write_insert_after_line(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l1\nl2\nl3\n")
    await f_write(str(f), ctx, content="NEW", after=1)
    assert f.read_text("utf-8") == "l1\nNEW\nl2\nl3\n"
    f = write_file(tmp_path, "n.txt", "l1\nl2\nl3\n")
    await f_write(str(f), ctx, content="NEW", after=2)
    assert f.read_text("utf-8") == "l1\nl2\nNEW\nl3\n"


async def test_write_after_last_line_is_append(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l1\nl2\n")
    await f_write(str(f), ctx, content="TAIL", after=2)
    assert f.read_text("utf-8") == "l1\nl2\nTAIL\n"


async def test_write_negative_is_line_number_not_insert_point(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l1\nl2\nl3\nl4\nl5\n")
    await f_write(str(f), ctx, content="X", after=-2)
    assert f.read_text("utf-8") == "l1\nl2\nl3\nl4\nX\nl5\n"
    f = write_file(tmp_path, "n.txt", "l1\nl2\nl3\nl4\nl5\n")
    await f_write(str(f), ctx, content="X", before=-2)
    assert f.read_text("utf-8") == "l1\nl2\nl3\nX\nl4\nl5\n"
    f = write_file(tmp_path, "n.txt", "l1\nl2\nl3\n")
    await f_write(str(f), ctx, content="X", after=-1)
    assert f.read_text("utf-8") == "l1\nl2\nl3\nX\n"
    f = write_file(tmp_path, "n.txt", "l1\nl2\nl3\n")
    await f_write(str(f), ctx, content="X", before=-1)
    assert f.read_text("utf-8") == "l1\nl2\nX\nl3\n"


async def test_write_after_out_of_range_errors(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l1\nl2\n")
    r = await f_write(str(f), ctx, content="X", after=99)
    assert "不存在" in r
    r = await f_write(str(f), ctx, content="X", after=-99)
    assert "超出范围" in r
    assert f.read_text("utf-8") == "l1\nl2\n"


async def test_write_only_one_anchor_param(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l1\n")
    r = await f_write(str(f), ctx, content="X", before=1, after=1)
    assert "只能给一个" in r
    assert f.read_text("utf-8") == "l1\n"


async def test_write_insert_at_zero_is_head(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l1\nl2\n")
    await f_write(str(f), ctx, content="HEAD", before=0)
    assert f.read_text("utf-8") == "HEAD\nl1\nl2\n"


async def test_write_insert_negative_appends(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l1\nl2\n")
    await f_write(str(f), ctx, content="TAIL", append=True)
    assert f.read_text("utf-8") == "l1\nl2\nTAIL\n"


async def test_write_insert_negative_second_last(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l1\nl2\nl3\n")
    await f_write(str(f), ctx, content="X", before=-2)
    assert f.read_text("utf-8") == "l1\nX\nl2\nl3\n"


async def test_write_replace_line_range(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l0\nl1\nl2\nl3\n")
    r = await f_write(str(f), ctx, content="X\nY", replace="2,3")
    assert "原第 2~3 行" in r
    assert f.read_text("utf-8") == "l0\nX\nY\nl3\n"


async def test_write_replace_to_end(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l0\nl1\nl2\n")
    await f_write(str(f), ctx, content="X", replace="2,")
    assert f.read_text("utf-8") == "l0\nX\n"


async def test_write_line_out_of_range_errors(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l0\nl1\n")
    r = await f_write(str(f), ctx, content="X", before=99)
    assert "不存在" in r or "越界" in r
    assert f.read_text("utf-8") == "l0\nl1\n"


async def test_write_bad_lines_syntax_errors(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l0\n")
    r = await f_write(str(f), ctx, content="X", before="abc")
    assert "整数" in r


pass
pass

async def test_mode_zero_is_gone(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l0\nl1\n")
    r = await f_write(str(f), ctx, content="X", before=1, mode=0)
    assert "mode 只能是" in r
    assert f.read_text("utf-8") == "l0\nl1\n"


async def test_write_revert_restores_previous(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l0\nl1\n")
    await f_write(str(f), ctx, content="X", before=2)
    assert f.read_text("utf-8") == "l0\nX\nl1\n"
    r = await f_write(str(f), ctx, content="", mode=2)
    assert "已回退" in r
    assert f.read_text("utf-8") == "l0\nl1\n"


async def test_revert_without_history_errors(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l0\n")
    r = await f_write(str(f), ctx, content="", mode=2)
    assert "没有可回退" in r


async def test_truncate_guard_blocks_short_overwrite(ctx, tmp_path):
    body = "".join(f"line{i}\n" for i in range(30))
    f = write_file(tmp_path, "big.txt", body)
    r = await f_write(str(f), ctx, content="x")
    assert "误覆盖" in r
    assert f.read_text("utf-8") == body
    pass
    r = await f_write(str(f), ctx, content="x", truncate_ok=True)
    assert "已写入" in r


pass

async def test_replace_single(ctx, tmp_path):
    f = write_file(tmp_path, "a.txt", "hello\nworld\n")
    r = await f_replace(str(f), ctx, old="hello", new="hi")
    assert "已修改" in r
    assert f.read_text("utf-8") == "hi\nworld\n"


async def test_replace_multiline_block(ctx, tmp_path):
    f = write_file(tmp_path, "a.txt", "a\nb\nc\nd\n")
    await f_replace(str(f), ctx, old="b\nc", new="X")
    assert f.read_text("utf-8") == "a\nX\nd\n"


async def test_replace_delete_with_empty_new(ctx, tmp_path):
    f = write_file(tmp_path, "a.txt", "a\nb\nc\n")
    await f_replace(str(f), ctx, old="b\n", new="")
    assert f.read_text("utf-8") == "a\nc\n"


async def test_replace_missing_errors_with_nearby(ctx, tmp_path):
    f = write_file(tmp_path, "a.txt", "alpha\nbeta\n")
    r = await f_replace(str(f), ctx, old="gamma", new="x")
    assert "没找到" in r
    assert f.read_text("utf-8") == "alpha\nbeta\n"


async def test_replace_multiple_hits_errors(ctx, tmp_path):
    f = write_file(tmp_path, "a.txt", "x\nx\n")
    r = await f_replace(str(f), ctx, old="x", new="y")
    assert "出现 2 次" in r
    assert f.read_text("utf-8") == "x\nx\n"


async def test_replace_all(ctx, tmp_path):
    f = write_file(tmp_path, "a.txt", "x\nx\n")
    r = await f_replace(str(f), ctx, old="x", new="y", replace_all=True)
    assert "已修改" in r
    assert f.read_text("utf-8") == "y\ny\n"


async def test_replace_fuzzy_indent(ctx, tmp_path):
    f = write_file(tmp_path, "a.txt", "def f():\n    return 1\n")
    r = await f_replace(str(f), ctx, old="return 1 ", new="return 2")
    assert "忽略缩进/空行" in r
    pass
    assert f.read_text("utf-8") == "def f():\n    return 2\n"


async def test_replace_keeps_indent_on_frag(ctx, tmp_path):
    f = write_file(tmp_path, "a.txt", "x = foo(bar)\n")
    await f_replace(str(f), ctx, old="foo", new="baz")
    assert f.read_text("utf-8") == "x = baz(bar)\n"


async def test_replace_mode_zero_rejected(ctx, tmp_path):
    f = write_file(tmp_path, "a.txt", "hello\n")
    r = await f_replace(str(f), ctx, old="hello", new="hi", mode=0)
    assert "mode 只能是" in r
    assert f.read_text("utf-8") == "hello\n"


async def test_replace_revert(ctx, tmp_path):
    f = write_file(tmp_path, "a.txt", "hello\n")
    await f_replace(str(f), ctx, old="hello", new="hi")
    await f_replace(str(f), ctx, old="", new="", mode=2)
    assert f.read_text("utf-8") == "hello\n"


async def test_replace_missing_new_errors(ctx, tmp_path):
    f = write_file(tmp_path, "a.txt", "hello\n")
    r = await f_replace(str(f), ctx, old="hello", new=None)
    assert "new" in r
    assert f.read_text("utf-8") == "hello\n"


async def test_replace_on_missing_file_errors(ctx, tmp_path):
    r = await f_replace(str(tmp_path / "nope.txt"), ctx, old="a", new="b")
    assert "不存在" in r


pass

MULTI_SRC = ("def a():\n"
             "    x = 1\n"
             "\n"
             "    y = 2\n"
             "    return x\n")


async def test_replace_old_with_blank_line_inside(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", MULTI_SRC)
    r = await f_replace(str(f), ctx, old="x = 1\ny = 2", new="z = 9")
    assert "已修改" in r
    assert f.read_text("utf-8") == (
        "def a():\n    z = 9\n    return x\n")


async def test_replace_old_with_leading_trailing_blank_lines(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", MULTI_SRC)
    r = await f_replace(str(f), ctx, old="\n    x = 1\n    y = 2\n\n",
                        new="    q = 0")
    assert "已修改" in r
    assert "q = 0" in f.read_text("utf-8")
    assert "x = 1" not in f.read_text("utf-8")


async def test_replace_fuzzy_block_keeps_indent_on_last_line(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", "def f():\n    if a:\n        return 1\n")
    r = await f_replace(str(f), ctx, old="if a:\nreturn 1",
                        new="if b:\nreturn 2")
    assert "已修改" in r
    assert f.read_text("utf-8") == ("def f():\n    if b:\n        return 2\n")


async def test_replace_block_no_double_indent(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", "def f():\n    a = 1\n    b = 2\n")
    r = await f_replace(str(f), ctx, old="    a = 1\n    b = 2",
                        new="    a = 9\n    b = 8")
    assert "已修改" in r
    assert f.read_text("utf-8") == "def f():\n    a = 9\n    b = 8\n"


async def test_expect_multiline_hits(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", MULTI_SRC)
    r = await f_write(str(f), ctx, content="    q = 0", before=5,
                      expect="x = 1\n\ny = 2")
    pass
    assert "已写入" in r and "命中第 2 行" in r
    assert "    q = 0" in f.read_text("utf-8")


async def test_expect_multiline_off_by_one(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", MULTI_SRC)
    r = await f_write(str(f), ctx, content="    q = 0", before=5,
                      expect="y = 2\n    return x")
    assert "已写入" in r and "命中第 4 行" in r
    assert "    q = 0\ndef" not in f.read_text("utf-8")


async def test_expect_multiline_used_by_replace(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", MULTI_SRC)
    pass
    r = await f_write(str(f), ctx, content="    q = 0", replace="2,3",
                      expect="x = 1\ny = 2")
    assert "已写入" in r
    assert f.read_text("utf-8") == (
        "def a():\n    q = 0\n    y = 2\n    return x\n")
    pass
    f = write_file(tmp_path, "a.py", MULTI_SRC)
    r = await f_write(str(f), ctx, content="    q = 0", replace="3,4",
                      expect="x = 1\ny = 2")
    assert "已写入" in r and "命中第 2 行" in r


pass

async def test_crlf_preserved_on_replace(ctx, tmp_path):
    f = write_file(tmp_path, "c.txt", "a\nb\n", newline="\r\n")
    await f_replace(str(f), ctx, old="b", new="B")
    raw = f.read_bytes()
    assert raw == b"a\r\nB\r\n"


async def test_crlf_preserved_on_line_edit(ctx, tmp_path):
    f = write_file(tmp_path, "c.txt", "a\nb\nc\n", newline="\r\n")
    await f_write(str(f), ctx, content="X", before=2)
    assert f.read_bytes() == b"a\r\nX\r\nb\r\nc\r\n"


async def test_crlf_preserved_on_range_replace(ctx, tmp_path):
    f = write_file(tmp_path, "c.txt", "a\nb\nc\n", newline="\r\n")
    await f_write(str(f), ctx, content="X", replace="2,3")
    assert f.read_bytes() == b"a\r\nX\r\n"


pass

async def test_read_lines_forms(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "".join(f"l{i}\n" for i in range(1, 21)))
    r = f_read(str(f), ctx, lines="3,5", linenos=True)
    assert "3\tl3" in r and "5\tl5" in r and "6\tl6" not in r
    r = f_read(str(f), ctx, lines="1,10", linenos=True)
    assert "1\tl1" in r and "11\tl11" not in r
    r = f_read(str(f), ctx, lines="-3,", linenos=True)
    assert "18\tl18" in r and "20\tl20" in r and "17\tl17" not in r
    r = f_read(str(f), ctx, lines="-2,-1", linenos=True)
    assert "19\tl19" in r and "20\tl20" in r and "18\tl18" not in r
    r = f_read(str(f), ctx, lines="18,", linenos=True)
    assert "20\tl20" in r
    r = f_read(str(f), ctx, lines="7", linenos=True)
    assert "7\tl7" in r and "8\tl8" not in r


@pytest.mark.parametrize("spec", [
    "3-5", "3~5", "3:5", "3..5", "3到5", "3至5", " 3 , 5 ", "3，5",
])
async def test_read_lines_lenient_range_forms(ctx, tmp_path, spec):
    f = write_file(tmp_path, "n.txt", "".join(f"l{i}\n" for i in range(1, 21)))
    r = f_read(str(f), ctx, lines=spec, linenos=True)
    assert "3\tl3" in r and "5\tl5" in r and "6\tl6" not in r


@pytest.mark.parametrize("spec", ["18-", "18~", "18:", "18.."])
async def test_read_lines_lenient_open_end(ctx, tmp_path, spec):
    f = write_file(tmp_path, "n.txt", "".join(f"l{i}\n" for i in range(1, 21)))
    r = f_read(str(f), ctx, lines=spec, linenos=True)
    assert "18\tl18" in r and "20\tl20" in r and "17\tl17" not in r


async def test_read_lines_lenient_keeps_negative_single(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "".join(f"l{i}\n" for i in range(1, 21)))
    r = f_read(str(f), ctx, lines="-3", linenos=True)
    assert r == "18\tl18"


async def test_read_lines_garbage_still_errors(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "a\nb\n")
    r = f_read(str(f), ctx, lines="range(1,10)")
    assert "行号必须是整数" in r


async def test_write_replace_lenient_range(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l1\nl2\nl3\nl4\n")
    r = await f_write(str(f), ctx, content="X", replace="2-3")
    assert "原第 2~3 行" in r
    assert f.read_text("utf-8") == "l1\nX\nl4\n"
    f = write_file(tmp_path, "m.txt", "a\nb\nc\n")
    await f_write(str(f), ctx, content="Y", replace="2，")
    assert f.read_text("utf-8") == "a\nY\n"


async def test_read_without_lines_returns_all(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "a\nb\n")
    r = f_read(str(f), ctx)
    assert r == "a\nb"
    assert f_read(str(f), ctx, linenos=True) == "1\ta\n2\tb"


async def test_read_linenos_false_is_clean(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "a\nb\n")
    r = f_read(str(f), ctx, linenos=False)
    assert r == "a\nb"


pass

async def test_py_dangling_insert_repaired(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", "def f():\n    return 1\n")
    r = await f_write(str(f), ctx, content="x = 1\ny = 2", before=-1)
    assert "已自动修正缩进" in r
    assert f.read_text("utf-8") == "def f():\n    x = 1\n    y = 2\n    return 1\n"


async def test_py_if_body_missing_indent_repaired(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", "def f():\n    pass\n")
    r = await f_write(str(f), ctx,
                      content="if x:\nreturn 1", before=-1)
    assert "已自动修正缩进" in r
    assert f.read_text("utf-8") == "def f():\n    if x:\n        return 1\n    pass\n"


async def test_py_correct_write_untouched(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", "def f():\n    return 1\n")
    r = await f_write(str(f), ctx, content="x = 1\n", append=True)
    assert "已写入" in r and "自动修正" not in r
    assert f.read_text("utf-8") == "def f():\n    return 1\nx = 1\n"


async def test_py_intentional_reindent_untouched(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", "def f():\n    x = 1\n    y = 2\n")
    r = await f_replace(str(f), ctx, old="    x = 1", new="    if x:\n        x = 2")
    assert "已修改" in r
    assert f.read_text("utf-8") == "def f():\n    if x:\n        x = 2\n    y = 2\n"


async def test_py_unrepairable_reports_original(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", "def f():\n    return 1\n")
    r = await f_write(str(f), ctx, content="def broken(:\n    pass\n", append=True)
    assert "语法错误" in r
    assert f.read_text("utf-8") == "def f():\n    return 1\n"


async def test_py_broken_file_passes_with_note(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", "def f(:\n    return 1\n")
    r = await f_write(str(f), ctx, content="x = 1\n", append=True)
    assert "不是合法 Python" in r
    assert f.read_text("utf-8").endswith("x = 1\n")


async def test_non_py_not_checked(ctx, tmp_path):
    f = write_file(tmp_path, "a.txt", "def f(:\n")
    r = await f_write(str(f), ctx, content="x = 1\n", append=True)
    assert "已写入" in r


async def test_py_repair_note_in_success_echo(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", "def f():\n    return 1\n")
    r = await f_write(str(f), ctx, content="x = 1\n", before=-1)
    assert "已写入" in r and "已自动修正缩进" in r
    assert f.read_text("utf-8") == "def f():\n    x = 1\n    return 1\n"

async def test_py_replace_block_repaired(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", "def f():\n    x = 1\n    y = 2\n")
    r = await f_replace(str(f), ctx, old="    x = 1", new="z = 1")
    assert "已修改" in r
    assert f.read_text("utf-8") == "def f():\n    z = 1\n    y = 2\n"


pass

async def test_replace_expect_match(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l1\nl2\nl3\n")
    r = await f_write(str(f), ctx, content="X", replace="2,2", expect="l2")
    assert "已写入" in r
    assert f.read_text("utf-8") == "l1\nX\nl3\n"


async def test_replace_expect_mismatch_rejects(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l1\nl2\nl3\n")
    r = await f_write(str(f), ctx, content="X", replace="2,2", expect="nope")
    assert "找不到" in r and "l2" in r
    assert f.read_text("utf-8") == "l1\nl2\nl3\n"


pass

pass
pass
pass

async def test_rename_function_allowed(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", "def old():\n    return 1\n")
    r = await f_write(str(f), ctx, content="def new():\n    return 1", replace="1,2")
    assert "已写入" in r
    assert f.read_text("utf-8") == "def new():\n    return 1\n"


async def test_change_signature_allowed(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", "def f(a):\n    return a\n")
    r = await f_write(str(f), ctx, content="def f(a, b=0):\n    return a", replace="1,2")
    assert "已写入" in r
    assert "def f(a, b=0)" in f.read_text("utf-8")


async def test_delete_function_allowed(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", "def a():\n    pass\n\n\ndef b():\n    pass\n")
    r = await f_write(str(f), ctx, content="", replace="4,5")
    assert "已写入" in r
    assert "def b" not in f.read_text("utf-8")
    assert "def a" in f.read_text("utf-8")


async def test_whole_file_rewrite_allowed(ctx, tmp_path):
    f = write_file(tmp_path, "a.py",
                   "def foo(a, b):\n    return a\n\n\ndef bar():\n    return 1\n")
    r = await f_write(str(f), ctx, content="def bar():\n    return 1\n",
                      truncate_ok=True)
    assert "已写入" in r
    assert f.read_text("utf-8") == "def bar():\n    return 1\n"


pass

async def test_small_broken_write_rejected(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", "def foo():\n    return 1\n")
    r = await f_write(str(f), ctx, content="def foo(:\n    pass", replace="1,2")
    assert "语法错误" in r
    assert "f_read" in r
    assert f.read_text("utf-8") == "def foo():\n    return 1\n"


async def test_big_broken_write_lands_with_warning(ctx, tmp_path):
    f = write_file(tmp_path, "a.py",
                   "def foo():\n    a = 1\n    b = 2\n    return a\n")
    bad = "def foo(:\n    a = 1\n    b = 2\n    return a"
    r = await f_write(str(f), ctx, content=bad, replace="1,4")
    assert "已写入" in r
    assert "语法错误" in r
    assert "mode=3" in r
    assert f.read_text("utf-8").startswith("def foo(:")


async def test_frontend_unbalanced_small_rejected(ctx, tmp_path):
    src = "export function f() {\n  return 1;\n}\n"
    f = write_file(tmp_path, "a.js", src)
    r = await f_write(str(f), ctx, content="export function f() {", replace="1,3")
    assert "括号不配平" in r
    assert f.read_text("utf-8") == src


async def test_frontend_unbalanced_big_lands_with_warning(ctx, tmp_path):
    src = "export function f() {\n  const a = 1;\n  const b = 2;\n  return a;\n}\n"
    f = write_file(tmp_path, "a.js", src)
    body = "export function f() {\n  const a = 1;\n  const b = 2;\n  return a;"
    r = await f_write(str(f), ctx, content=body, replace="1,5")
    assert "已写入" in r and "括号不配平" in r
    assert f.read_text("utf-8").endswith("return a;\n")


async def test_broken_syntax_still_rejected(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", "def foo():\n    pass\n")
    r = await f_write(str(f), ctx, content="def foo(:\n    pass", replace="1,2")
    assert "语法错误" in r
    assert f.read_text("utf-8") == "def foo():\n    pass\n"


async def test_broken_syntax_whole_overwrite_rejected(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", "def foo():\n    pass\n")
    r = await f_write(str(f), ctx, content="x = (\n")
    assert "语法错误" in r
    assert f.read_text("utf-8") == "def foo():\n    pass\n"


async def test_ast_broken_old_file_allows_any_edit(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", "def foo(:\n    return 1\n")
    r = await f_write(str(f), ctx, content="x = 1\n", append=True)
    assert "已写入" in r


pass

pass
PY_SRC = "def a():\n    pass\n\ndef b():\n    pass\n"


async def test_expect_exact_hit(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", PY_SRC)
    r = await f_write(str(f), ctx, content="    # hi", before=4, expect="def b")
    assert "已写入" in r and "命中" not in r
    assert f.read_text("utf-8") == "def a():\n    pass\n\n    # hi\ndef b():\n    pass\n"


async def test_expect_off_by_one_is_corrected(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", PY_SRC)
    r = await f_write(str(f), ctx, content="    # hi", before=3, expect="def b")
    assert "已写入" in r
    assert "命中第 4 行" in r and "你给的是第 3 行" in r
    pass
    assert f.read_text("utf-8") == "def a():\n    pass\n\n    # hi\ndef b():\n    pass\n"


async def test_expect_off_by_one_after(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", PY_SRC)
    r = await f_write(str(f), ctx, content="    # hi", after=3, expect="def b")
    assert "已写入" in r and "命中第 4 行" in r
    assert f.read_text("utf-8") == "def a():\n    pass\n\ndef b():\n    # hi\n    pass\n"


async def test_expect_off_by_four_is_rejected(ctx, tmp_path):
    src = "".join(f"l{i}\n" for i in range(1, 11))
    f = write_file(tmp_path, "a.py", src)
    r = await f_write(str(f), ctx, content="    # hi", before=1, expect="l10")
    assert "差了" in r and "容差 3 行" in r
    assert f.read_text("utf-8") == src


async def test_expect_not_found_is_rejected(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", PY_SRC)
    r = await f_write(str(f), ctx, content="    # hi", before=4, expect="zzz不存在")
    assert "找不到" in r
    assert "def b" in r or "pass" in r
    assert f.read_text("utf-8") == PY_SRC


async def test_expect_ambiguous_within_tolerance_is_rejected(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "a\nX\nb\nX\nc\n")
    r = await f_write(str(f), ctx, content="Y", before=3, expect="X")
    assert "多处" in r and "第 2 行" in r and "第 4 行" in r
    assert f.read_text("utf-8") == "a\nX\nb\nX\nc\n"


async def test_expect_on_replace_shifts_range(ctx, tmp_path):
    f = write_file(tmp_path, "a.py", PY_SRC)
    pass
    r = await f_write(str(f), ctx, content="def b():\n    return 1",
                      replace="3,4", expect="def b")
    assert "已写入" in r and "命中第 4 行" in r
    assert f.read_text("utf-8") == "def a():\n    pass\n\ndef b():\n    return 1\n"


async def test_expect_without_anchor_param_is_ignored(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l1\nl2\n")
    r = await f_write(str(f), ctx, content="X\n", expect="l1", truncate_ok=True)
    assert "已写入" in r
    assert f.read_text("utf-8") == "X\n"


pass
pass


async def test_success_echo_has_no_diff_body(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l1\nl2\nl3\n")
    ok = await f_write(str(f), ctx, content="A\nB", before=3)
    assert "已写入" in ok
    assert "| A" not in ok and "| B" not in ok
    assert "3| l3" not in ok
    assert "f_read" in ok
    assert "mode=2" in ok


async def test_overflow_range_echoes_context(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "".join(f"l{i}\n" for i in range(1, 101)))
    r = await f_write(str(f), ctx, content="NEW", replace="90,110")
    assert "已写入" in r
    assert "最长就是 100 行" in r
    assert "NEW" in r and "l89" in r
    lines = f.read_text("utf-8").splitlines()
    assert lines[89] == "NEW" and len(lines) == 90

pass

async def test_partial_hunk_approval_still_goes_through_syntax_gate(tmp_path):
    f = write_file(tmp_path, "m.py", "a = 1\nb = 2\nc = 3\n")

    class _Ctx:
        def __init__(self):
            self.project_dir = lambda: str(tmp_path)

        async def auto_snapshot(self, *_a, **_k):
            return None

        async def request_file_approval(self, *_a, **_k):
            return True, [0]

    r = await f_write(str(f), _Ctx(), content="a = 1\nb = (2\n     + 3)\nc = 3\n")
    assert "error" in r, "部分批准拼出非法 Python 却回了成功"
    assert "合法 Python" in r
    pass
    assert f.read_text("utf-8") == "a = 1\nb = 2\nc = 3\n"


async def test_partial_hunk_approval_summary_reflects_written_file(tmp_path):
    f = write_file(tmp_path, "m.py", "a = 1\nb = 2\nc = 3\nd = 4\ne = 5\nf = 6\n")

    class _Ctx:
        def __init__(self):
            self.project_dir = lambda: str(tmp_path)

        async def auto_snapshot(self, *_a, **_k):
            return None

        async def request_file_approval(self, *_a, **_k):
            return True, [0]

    pass
    new = "a = 1\nb = 22\nc = 3\nd = 4\ne = 55\nf = 6\n"
    r = await f_write(str(f), _Ctx(), content=new)
    assert "error" not in r.lower(), r
    assert "仅批准部分 hunk" in r
    on_disk = f.read_text("utf-8")
    assert on_disk != new, "应当只写入部分 hunk"
    pass
    assert f"新 {len(on_disk.splitlines())} 行" in r, r


pass

async def test_mode3_rollback_then_rewrite(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l1\nl2\nl3\n")
    await f_write(str(f), ctx, content="BAD\nBAD2", replace="1,3")
    assert f.read_text("utf-8") == "BAD\nBAD2\n"
    r = await f_write(str(f), ctx, content="l2", replace="1,1", mode=3)
    assert "已写入" in r
    assert f.read_text("utf-8") == "l2\nl2\nl3\n"


async def test_mode3_without_history_errors(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l1\n")
    r = await f_write(str(f), ctx, content="X", append=True, mode=3)
    assert "没有可回退" in r
    assert f.read_text("utf-8") == "l1\n"


async def test_mode3_keeps_revert_point(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l0\nl1\n")
    await f_write(str(f), ctx, content="X\n", append=True)
    await f_write(str(f), ctx, content="Y\n", append=True)
    r = await f_write(str(f), ctx, content="Z\n", append=True, mode=3)
    assert "已写入" in r
    pass
    assert f.read_text("utf-8") == "l0\nl1\nX\nZ\n"
    back = await f_write(str(f), ctx, content="", mode=2)
    assert "已回退" in back
    assert f.read_text("utf-8") == "l0\nl1\nX\n"


async def test_replace_mode3_rollback_then_rewrite(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l1\nl2\n")
    await f_replace(str(f), ctx, old="l1", new="BAD")
    assert f.read_text("utf-8") == "BAD\nl2\n"
    r = await f_replace(str(f), ctx, old="l1", new="NEW", mode=3)
    assert "已修改" in r
    assert f.read_text("utf-8") == "NEW\nl2\n"



pass

async def test_write_with_old_new_routes_to_replace(ctx, tmp_path):
    f = write_file(tmp_path, "a.txt", "aaa\nbbb\n")
    from app.tools.builtin.fs.compat import f_write_entry
    r = await f_write_entry(path="a.txt", ctx=ctx, old="bbb", new="XXX")
    assert "猜你想调用 f_replace" in r
    assert f.read_text("utf-8") == "aaa\nXXX\n"


async def test_write_edits_with_old_new_routes_to_replace(ctx, tmp_path):
    f = write_file(tmp_path, "a.txt", "aaa\nbbb\n")
    from app.tools.builtin.fs.compat import f_write_entry
    r = await f_write_entry(path="a.txt", ctx=ctx,
                            edits=[{"old": "aaa", "new": "A"},
                                   {"old": "bbb", "new": "B"}])
    assert "猜你想调用 f_replace" in r
    assert f.read_text("utf-8") == "A\nB\n"


async def test_replace_with_content_routes_to_write(ctx, tmp_path):
    f = write_file(tmp_path, "a.txt", "aaa\nbbb\n")
    from app.tools.builtin.fs.compat import f_replace_entry
    r = await f_replace_entry(path="a.txt", ctx=ctx,
                              content="ZZZ", replace="1,1")
    assert "猜你想调用 f_write" in r
    assert f.read_text("utf-8") == "ZZZ\nbbb\n"


async def test_replace_multi_files_with_matching_edits(ctx, tmp_path):
    a = write_file(tmp_path, "a.txt", "x\n")
    b = write_file(tmp_path, "b.txt", "y\n")
    from app.tools.builtin.fs.compat import f_replace_entry
    r = await f_replace_entry(path=["a.txt", "b.txt"], ctx=ctx,
        edits=[{"old": "x", "new": "x1"}, {"old": "y", "new": "y1"}])
    assert r.count("已修改") == 2
    assert a.read_text("utf-8") == "x1\n"
    assert b.read_text("utf-8") == "y1\n"


async def test_replace_multi_files_mismatch_errors(ctx, tmp_path):
    a = write_file(tmp_path, "a.txt", "x\n")
    b = write_file(tmp_path, "b.txt", "y\n")
    from app.tools.builtin.fs.compat import f_replace_entry
    r = await f_replace_entry(path=["a.txt", "b.txt"], ctx=ctx,
                              edits=[{"old": "x", "new": "x1"}])
    assert "必须同数量" in r and "error" in r
    assert a.read_text("utf-8") == "x\n" and b.read_text("utf-8") == "y\n"


async def test_replace_single_element_array_is_single_file(ctx, tmp_path):
    a = write_file(tmp_path, "a.txt", "x\n")
    from app.tools.builtin.fs.compat import f_replace_entry
    r = await f_replace_entry(path=["a.txt"], ctx=ctx, old="x", new="x1")
    assert "已修改" in r and "猜你想调用" not in r
    assert a.read_text("utf-8") == "x1\n"


async def test_expect_unique_hit_tolerance_three(ctx, tmp_path):
    f = write_file(tmp_path, "a.txt", "".join(f"l{i}\n" for i in range(1, 11)))
    r = await f_write(str(f), ctx, content="MARK", replace="7,7", expect="l10")
    assert "已写入" in r and "命中第 10 行" in r
    assert "MARK" in f.read_text("utf-8")


async def test_expect_multiple_hits_tolerance_still_one(ctx, tmp_path):
    from app.tools.builtin.fs.lines import LinesError
    from app.tools.builtin.fs.text import split_rows
    from app.tools.builtin.fs.lines import find_anchor
    rows = split_rows("target\nx\ny\nzzz\ntarget\n")
    try:
        find_anchor(rows, 3, "target")
        assert False, "多处命中应被拒绝"
    except LinesError:
        pass


pass
pass
pass

async def test_write_replace_single_line_number_only_one_line(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l0\nl1\nl2\nl3\n")
    await f_write(str(f), ctx, content="X", replace="2")
    assert f.read_text("utf-8") == "l0\nX\nl2\nl3\n"


async def test_write_replace_single_line_negative(ctx, tmp_path):
    f = write_file(tmp_path, "n.txt", "l0\nl1\nl2\n")
    await f_write(str(f), ctx, content="Z", replace="-1")
    assert f.read_text("utf-8") == "l0\nl1\nZ\n"


def test_write_replace_single_line_matches_read_range():
    from app.tools.builtin.fs.lines import parse_read_range, parse_write_target
    total = 300
    for spec in ("1", "10", "-1", "-3", "10,10", "90,110", "10,", "-3,",
                 "2-3", "1-220", "2，", "-2,", "1-"):
        w = parse_write_target(None, None, spec, False, total)
        r = parse_read_range(spec, total)
        assert (w["start"], w["end"]) == (r[0], r[1]), spec


def test_read_lines_json_string_array(tmp_path):
    import json as _json
    from app.tools.registry import ToolContext
    from app.tools.builtin.fs.read_file import f_read

    (tmp_path / "a.txt").write_text("a\nb\nc\n", "utf-8")
    (tmp_path / "b.txt").write_text("d\ne\n", "utf-8")
    ctx = ToolContext(cwd=str(tmp_path), project=str(tmp_path))
    out = f_read(path=["a.txt", "b.txt"], lines=_json.dumps(["1,2", "2,"]),
                 ctx=ctx)
    assert "a\nb" in out and "行号必须是整数" not in out
    pass
    assert f_read(path="a.txt", lines="1,2", ctx=ctx).startswith("a\nb")
