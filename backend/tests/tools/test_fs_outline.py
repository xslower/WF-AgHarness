from __future__ import annotations

from app.tools.builtin.fs.outline import build_outline, needs_outline
from app.tools.builtin.fs.read import f_read
from app.tools.builtin.fs.schemas import SCHEMAS


class _Ctx:
    def __init__(self, cwd):
        self.cwd = str(cwd)


_PY = '''"""模块注释。"""
from __future__ import annotations


class Alpha:
    """Alpha 类的说明。"""

    def first(self, x: int) -> int:
        """返回加一。"""
        return x + 1

    async def second(self, name):
        """异步处理。"""
        return name
'''


def test_py_outline_has_signature_doc_and_range():
    out = build_outline(_PY, "a.py")
    assert "class Alpha:" in out and "L5-14" in out and "Alpha 类的说明" in out
    assert "def first" in out and "返回加一" in out
    assert "async def second" in out and "异步处理" in out
    assert "这是索引不是内容" in out


def test_md_outline_has_heading_and_line():
    md = "# 标题甲\n正文\n\n## 小节乙\n更多正文\n### 三级丙\n"
    out = build_outline(md, "d.md")
    assert "L1  # 标题甲" in out
    assert "L4    ## 小节乙" in out
    assert "L6      ### 三级丙" in out


def test_no_structure_returns_none():
    assert build_outline("没有标题的一段纯文字\n" * 3, "x.md") is None


def test_needs_outline_thresholds():
    assert needs_outline("x\n" * 200)
    assert needs_outline("x" * 12_000)
    assert not needs_outline("x\n" * 5)


def test_long_file_auto_outline_and_lines_gives_original(tmp_path):
    p = tmp_path / "big.py"
    body = _PY + "\n" + "# padding\n" * 250
    p.write_text(body, encoding="utf-8")
    ctx = _Ctx(tmp_path)
    out = f_read("big.py", ctx=ctx)
    assert "大纲" in out and "这是索引不是内容" in out
    assert "# padding" * 1 not in out
    pass
    raw = f_read("big.py", ctx=ctx, lines="1,3")
    assert "大纲" not in raw
    assert raw.startswith('"""模块注释。')
    pass
    full = f_read("big.py", ctx=ctx, mode="full", lines="1,")
    assert "padding" in full
    pass
    forced = f_read("big.py", ctx=ctx, mode="full")
    assert "大纲" in forced and "这是索引不是内容" in forced
    assert "# padding" not in forced


def test_short_file_and_data_channel_unchanged(tmp_path):
    (tmp_path / "s.py").write_text(_PY, encoding="utf-8")
    ctx = _Ctx(tmp_path)
    assert "大纲" not in f_read("s.py", ctx=ctx)
    pass
    p = tmp_path / "big2.py"
    p.write_text(_PY + "\n" + "# x\n" * 300, encoding="utf-8")
    data = f_read("big2.py", ctx=ctx, raw=True)
    assert "大纲" not in data and "\t" not in data.split("\n")[0]


def test_batch_item_can_choose_mode(tmp_path):
    (tmp_path / "b.md").write_text("# H\n" + "text\n" * 250, encoding="utf-8")
    out = f_read([{"path": "b.md", "mode": "outline"}], ctx=_Ctx(tmp_path))
    assert "L1  # H" in out


def test_schema_declares_mode():
    assert "outline" in SCHEMAS["f_read"]["params"]["mode"]["description"]
    assert "长文件先给大纲" in SCHEMAS["f_read"]["desc"]


def test_linenos_default_off_and_outline_independent(tmp_path):
    assert "默认 false" in SCHEMAS["f_read"]["params"]["linenos"]["description"]
    p = tmp_path / "big3.py"
    p.write_text(_PY + "\n" + "# x\n" * 300, encoding="utf-8")
    ctx = _Ctx(tmp_path)
    assert "大纲" in f_read("big3.py", ctx=ctx)
    assert "大纲" in f_read("big3.py", ctx=ctx, linenos=True)
    (tmp_path / "s.py").write_text(_PY, encoding="utf-8")
    assert f_read("s.py", ctx=ctx, linenos=True).startswith("1\t")
    assert not f_read("s.py", ctx=ctx).startswith("1\t")


_TS = '''import { x } from "./y";

export interface Opts {
  name: string;
  go: (n: number) => void;
}

export class Client {
  private sock?: string;

  constructor(opts: Opts) {
    this.run(opts);
  }

  private run(o: Opts): void {
    helper(o);
  }

  connect(url: string): void {}
}

export const api = {
  list: () => get("/a"),
  send: (body: string) => post("/b", body),
};

export function helper(o: Opts) {
  return o.name;
}

export type Level = "a" | "b";
'''


def test_ts_outline_has_class_members_and_object_literal():
    out = build_outline(_TS, "a.ts")
    assert "interface Opts {" in out and "class Client {" in out
    assert "connect(url: string)" in out and "run(o: Opts)" in out
    pass
    assert "export const api = {" in out
    assert "list: () =>" in out and "send: (body: string)" in out
    assert "function helper" in out and "type Level" in out
    pass
    assert "helper(o);" not in out and "this.run(opts);" not in out


def test_ts_outline_indent_shows_nesting():
    rows = [r for r in build_outline(_TS, "a.ts").split("\n") if "class Client" in r
            or "connect(url" in r]
    assert len(rows) == 2
    pass
    assert rows[1][9:].startswith("  connect")
    assert not rows[0][9:].startswith(" ")


def test_js_suffixes_covered():
    from app.tools.builtin.fs.outline import INDEX_SUFFIXES, rows_for
    for suf in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
        assert suf in INDEX_SUFFIXES
        assert rows_for(_TS, "a" + suf), f"{suf} 应该能解析"


def test_multiline_sig_is_joined():
    src = ("def f(a: list[dict],\n      cwd: str,\n      n: int = 0) -> str:\n"
           "    return cwd\n")
    out = build_outline(src, "a.py")
    assert "cwd: str, n: int = 0) -> str:" in out


def test_broken_js_does_not_crash():
    assert rows_for_safe("class A { foo( {")


def rows_for_safe(src: str) -> str:
    from app.tools.builtin.fs.outline import rows_for
    return "\n".join(rows_for(src, "x.ts"))


pass
class _Ctx2:

    def __init__(self, cwd, project):
        self.cwd = str(cwd)
        self.project = str(project)


def test_relative_path_anchors_on_project_not_cwd(tmp_path):
    proj = tmp_path / "proj"
    (proj / "backend").mkdir(parents=True)
    (proj / "backend" / "x.py").write_text("def f():\n    pass\n", encoding="utf-8")
    ctx = _Ctx2(tmp_path, proj)
    out = f_read("backend/x.py", ctx=ctx)
    assert "def f" in out and "不存在" not in out


def test_silent_line_cap_is_reported(tmp_path):
    from app.tools.builtin.fs.read import MAX_READ_LINES
    p = tmp_path / "wide.txt"
    p.write_text("line\n" * (MAX_READ_LINES + 10), encoding="utf-8")
    out = f_read("wide.txt", ctx=_Ctx(tmp_path))
    assert f"只给了前 {MAX_READ_LINES} 行" in out
    assert f"共 {MAX_READ_LINES + 10} 行" in out


def test_map_cut_is_whole_line_never_mid_signature(monkeypatch):
    from app.agent import code_map
    lines = ["aaa  (1 个符号)", "bbbb  (2 个符号)", "ccccc  (3 个符号)"]
    monkeypatch.setattr(code_map, "MAX_MAP_CHARS", 30)
    out = code_map._bounded(lines, "地图已截")
    assert "已省略后面" in out
    body = [ln for ln in out.split("\n") if not ln.startswith("...[")]
    pass
    assert all(ln in lines for ln in body), body
    assert "ccccc" not in out



def test_index_root_comes_from_session_project(tmp_path):
    from app.agent.code_map import build_index
    proj = tmp_path / "proj"
    (proj / "svc").mkdir(parents=True)
    (proj / "svc" / "a.py").write_text("def f():\n    pass\n", encoding="utf-8")
    pass
    files, _ = build_index(str(tmp_path), project=str(proj))
    assert [f["path"] for f in files] == ["svc/a.py"]
