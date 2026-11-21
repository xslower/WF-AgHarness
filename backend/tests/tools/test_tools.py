import json

import pytest

from app.tools import ToolContext, ToolRegistry

from app.tools.builtin import build_tools as build_registry


@pytest.fixture
def reg():
    return build_registry()


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(str(tmp_path))


async def run(reg, ctx, name, **args):
    return await reg.execute(name, args, ctx)


async def test_write_read_replace_flow(reg, ctx, tmp_path):
    r = await run(reg, ctx, "f_write", path="a/b.txt", content="hello\nworld")
    assert "已创建" in r and (tmp_path / "a" / "b.txt").read_text("utf-8") == "hello\nworld"

    r = await run(reg, ctx, "f_read", path="a/b.txt")
    assert r == "hello\nworld"
    r = await run(reg, ctx, "f_read", path="a/b.txt", linenos=True)
    assert "1\thello" in r and "2\tworld" in r

    r = await run(reg, ctx, "f_replace", path="a/b.txt", old="hello", new="hi")
    assert "已修改" in r
    assert (tmp_path / "a" / "b.txt").read_text("utf-8") == "hi\nworld"

    pass
    r = await run(reg, ctx, "f_replace", path="a/b.txt", old="nope", new="x")
    assert "没找到" in r

    pass
    await run(reg, ctx, "f_write", path="c.txt", content="a\na")
    r = await run(reg, ctx, "f_replace", path="c.txt", old="a", new="b")
    assert "出现 2 次" in r


async def test_write_lines_forms(reg, ctx, tmp_path):
    f = tmp_path / "n.txt"
    f.write_text("l1\nl2\nl3\n", "utf-8")
    pass
    r = await run(reg, ctx, "f_write", path="n.txt", content="X", before=2)
    assert "插入" in r and f.read_text("utf-8") == "l1\nX\nl2\nl3\n"
    pass
    await run(reg, ctx, "f_write", path="n.txt", content="TAIL", append=True)
    assert f.read_text("utf-8") == "l1\nX\nl2\nl3\nTAIL\n"
    pass
    await run(reg, ctx, "f_write", path="n.txt", content="Y", replace="2,3")
    assert f.read_text("utf-8") == "l1\nY\nl3\nTAIL\n"


async def test_read_lines_range(reg, ctx, tmp_path):
    f = tmp_path / "r.txt"
    f.write_text("a\nb\nc\nd\n", "utf-8")
    r = await run(reg, ctx, "f_read", path="r.txt", lines="2,3")
    assert r == "b\nc"
    r = await run(reg, ctx, "f_read", path="r.txt", lines="2,3", linenos=True)
    assert "2\tb" in r and "3\tc" in r and "4\td" not in r


async def test_write_truncate_guard(reg, ctx, tmp_path):
    f = tmp_path / "big.txt"
    f.write_text("".join(f"l{i}\n" for i in range(30)), "utf-8")
    before = f.read_text("utf-8")
    r = await run(reg, ctx, "f_write", path="big.txt", content="x")
    assert "误覆盖" in r and f.read_text("utf-8") == before
    r = await run(reg, ctx, "f_write", path="big.txt", content="x", truncate_ok=True)
    assert "已写入" in r


async def test_read_missing_file(reg, ctx):
    r = await run(reg, ctx, "f_read", path="ghost.txt")
    assert "不存在" in r


pass

async def test_read_binary_xlsx_routes_to_table(reg, ctx, tmp_path):
    p = tmp_path / "data.xlsx"
    p.write_bytes(b"PK\x03\x04")
    r = await run(reg, ctx, "f_read", path=str(p))
    assert "二进制表格文件" in r or "xlsx" in r
    assert "table" in r

async def test_read_binary_pptx_routes_to_ppt(reg, ctx, tmp_path):
    p = tmp_path / "slides.pptx"
    p.write_bytes(b"PK\x03\x04")
    r = await run(reg, ctx, "f_read", path=str(p))
    assert "二进制演示文稿" in r or "pptx" in r
    assert "ppt" in r

async def test_read_binary_pdf_routes_to_pdf_convert(reg, ctx, tmp_path):
    p = tmp_path / "doc.pdf"
    p.write_text("%PDF-1.4 fake", "utf-8")
    r = await run(reg, ctx, "f_read", path=str(p))
    assert "PDF" in r
    assert "pdf_convert" in r

async def test_read_binary_legacy_doc_rejected(reg, ctx, tmp_path):
    p = tmp_path / "old.doc"
    p.write_bytes(b"\xd0\xcf\x11\xe0")
    r = await run(reg, ctx, "f_read", path=str(p))
    assert "不支持" in r or "旧版" in r

async def test_read_binary_docx_reads_directly(reg, ctx, tmp_path):
    p = tmp_path / "notes.docx"
    p.write_bytes(b"PK\x03\x04")
    r = await run(reg, ctx, "f_read", path=str(p))
    pass
    assert "docx" not in r.lower() or "error" not in r.lower()


async def test_install_commands_blocked(reg, ctx):
    for cmd in ["pip install requests", "npm install left-pad",
                "python -m pip install x", "pnpm add x", "yarn add x",
                "uv pip install x", "conda install x"]:
        r = await run(reg, ctx, "run_command", command=cmd)
        assert "安装" in r, cmd


async def test_normal_command_allowed(reg, ctx):
    r = await run(reg, ctx, "run_command", command="echo hello-123")
    assert "hello-123" in r and "error" not in r


async def test_grep_and_glob(reg, ctx, tmp_path):
    (tmp_path / "x.py").write_text("def foo():\n    pass\n", "utf-8")
    (tmp_path / "y.txt").write_text("nothing here\n", "utf-8")
    r = await run(reg, ctx, "grep", key=["def foo"])
    assert "x.py" in r
    r = await run(reg, ctx, "search_files", pattern="*.txt")
    assert "y.txt" in r and "x.py" not in r


async def test_grep_with_context(reg, ctx, tmp_path):
    (tmp_path / "c.py").write_text("a\nb\nTARGET\nd\ne\n", "utf-8")
    r = await run(reg, ctx, "grep", key=["TARGET"], context=1)
    assert "b" in r and "d" in r


async def test_list_dir(reg, ctx, tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "f.txt").write_text("x", "utf-8")
    pass
    r = await run(reg, ctx, "search_files", path=".")
    assert "sub/" in r and "f.txt" in r
    r = await run(reg, ctx, "search_files", path=".", pattern="*.txt")
    assert "f.txt" in r


def test_install_patterns_complete():
    from app.security.core import INSTALL_PATTERNS
    import re
    assert len(INSTALL_PATTERNS) >= 10
    for cmd in ["pip3 install x", "choco install x", "cargo install x"]:
        assert any(re.search(p, cmd) for p in INSTALL_PATTERNS), cmd
