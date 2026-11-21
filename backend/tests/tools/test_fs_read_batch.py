from __future__ import annotations

from app.tools.builtin.fs.read import MAX_BATCH_READ, f_read
from app.tools.builtin.fs.schemas import SCHEMAS


class _Ctx:
    def __init__(self, cwd):
        self.cwd = str(cwd)


def _seed(tmp_path):
    (tmp_path / "a.txt").write_text("A1\nA2\nA3\nA4\nA5\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("B1\nB2\nB3\n", encoding="utf-8")
    return _Ctx(tmp_path)


def test_single_string_path_unchanged(tmp_path):
    ctx = _seed(tmp_path)
    out = f_read("a.txt", ctx=ctx, lines="2,3")
    assert out == "A2\nA3"
    assert f_read("a.txt", ctx=ctx, lines="2,3", linenos=True) == "2\tA2\n3\tA3"


def test_batch_with_per_file_ranges(tmp_path):
    ctx = _seed(tmp_path)
    out = f_read(["a.txt", {"path": "b.txt", "lines": "-2,"}], ctx=ctx, linenos=True)
    assert "===== a.txt =====" in out
    assert "1\tA1" in out
    assert "===== b.txt [-2,] =====" in out
    assert "2\tB2" in out and "3\tB3" in out
    assert "1\tB1" not in out


def test_batch_top_level_lines_is_default(tmp_path):
    ctx = _seed(tmp_path)
    out = f_read(["a.txt", "b.txt"], ctx=ctx, lines="1,1", linenos=True)
    assert "1\tA1" in out and "1\tB1" in out
    assert "2\tA2" not in out


def test_batch_one_missing_does_not_abort_others(tmp_path):
    ctx = _seed(tmp_path)
    out = f_read(["a.txt", "nope.txt"], ctx=ctx)
    assert "A1\nA2" in out
    assert "路径不存在" in out


def test_batch_empty_tells_how_to_fix(tmp_path):
    ctx = _seed(tmp_path)
    out = f_read([], ctx=ctx)
    assert "为空" in out and "一次可给 8 个" in out


def test_over_cap_reads_first_n_and_lists_rest(tmp_path):
    ctx = _seed(tmp_path)
    for i in range(10):
        (tmp_path / f"f{i}.txt").write_text(f"CONTENT{i}\n", encoding="utf-8")
    paths = [f"f{i}.txt" for i in range(10)]
    out = f_read(paths, ctx=ctx)
    assert "一次最多读" not in out
    assert "CONTENT0" in out and "CONTENT7" in out
    assert "CONTENT8" not in out and "CONTENT9" not in out
    assert "未读 2 个" in out and "共 10 个" in out
    assert "f8.txt" in out and "f9.txt" in out
    assert "再发一次" in out


def test_cap_is_8(tmp_path):
    assert MAX_BATCH_READ == 8
    ctx = _seed(tmp_path)
    assert "===== a.txt =====" in f_read(["a.txt"] * 8, ctx=ctx)


def test_batch_per_file_budget_keeps_middle_file(tmp_path):
    ctx = _seed(tmp_path)
    (tmp_path / "big.txt").write_text(
        "HEAD_MARK\n" + "X" * 40000 + "\nTAIL_MARK\n", encoding="utf-8")
    (tmp_path / "mid.txt").write_text("MIDDLE_UNIQUE_CONTENT\n", encoding="utf-8")
    (tmp_path / "last.txt").write_text("LAST_UNIQUE_CONTENT\n", encoding="utf-8")
    out = f_read(["big.txt", "mid.txt", "last.txt"], ctx=ctx)
    assert "HEAD_MARK" in out and "TAIL_MARK" in out
    assert "MIDDLE_UNIQUE_CONTENT" in out
    assert "LAST_UNIQUE_CONTENT" in out
    assert "本段过长已收紧" in out


def test_schema_declares_array_path():
    p = SCHEMAS["f_read"]["params"]["path"]
    assert "array" in (p["type"] if isinstance(p["type"], list) else [p["type"]])
    assert "数组" in p["description"] or "多个" in p["description"]


def test_range_end_overflow_truncates_with_note(tmp_path):
    (tmp_path / "big.txt").write_text(
        "".join(f"l{i}\n" for i in range(1, 101)), encoding="utf-8")
    ctx = _Ctx(tmp_path)
    out = f_read("big.txt", ctx=ctx, lines="90,110")
    assert out.startswith("l90")
    assert "l100" in out and "l101" not in out
    assert "文件最长就是 100 行" in out and "终点 110 已截到末尾" in out


def test_range_start_overflow_still_errors(tmp_path):
    (tmp_path / "small.txt").write_text("a\nb\n", encoding="utf-8")
    ctx = _Ctx(tmp_path)
    out = f_read("small.txt", ctx=ctx, lines="90,110")
    assert "超出了范围" in out


def test_batch_mode3_rollback_then_write(tmp_path):
    import asyncio

    from app.tools.builtin.fs.batch import write_batch
    from app.tools import ToolContext

    p = tmp_path / "m.txt"
    p.write_text("L1\nL2\nL3\n", encoding="utf-8")
    ctx = ToolContext(str(tmp_path))
    asyncio.run(write_batch(str(p), ctx, [{"before": 1, "content": "BAD"}], mode=1))
    assert p.read_text("utf-8") == "BAD\nL1\nL2\nL3\n"
    out = asyncio.run(write_batch(str(p), ctx, [{"append": True, "content": "N2"}],
                                 mode=3))
    assert "已回退" in out and "成功" in out
    assert p.read_text("utf-8") == "L1\nL2\nL3\nN2\n"
