# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

import pytest

# doc_fixtures 在 tests/ 根（不是 tests/tools/）；tests/ 补上 __init__.py 后
# pytest 不再自动把它加进 sys.path，这里显式指向上一层，单跑/全量都能导入。
sys.path.insert(0, str(Path(__file__).parent.parent))
from doc_fixtures import (make_docx, make_pptx, make_xlsx,  # noqa: E402
                          make_xlsx_bad_styles)

import app.tools.builtin.docs.docfile as docfile
import app.tools.builtin.docs.ppt as ppt
import app.tools.builtin.docs.table as table
from app.tools.builtin.docs.exec import run_worker, worker_python
from app.tools import ToolContext, ToolRegistry


class _Ctx:
    def __init__(self, cwd):
        self.cwd = str(cwd)


def _reg() -> ToolRegistry:
    reg = ToolRegistry()
    table.register(reg)
    ppt.register(reg)
    return reg


def run(reg: ToolRegistry, ctx, name: str, args: dict) -> str:
    return asyncio.run(reg.execute(name, args, ctx))


def _skip_no_env() -> None:
    if not Path(worker_python()).is_file():
        pytest.skip(f"worker 解释器不存在: {worker_python()}")
    probe = run_worker({"op": "table_inspect", "path": "/etc/hosts"})
    if probe.get("code") in ("env_unavailable", "worker_missing"):
        pytest.skip(f"worker 环境不可用: {probe.get('error')}")


# ---------------------------------------------------------------- docx

def test_docx_headings_and_table(tmp_path):
    p = make_docx(tmp_path / "a.docx", [
        {"text": "第一章 概览", "style": "Heading1"},
        {"text": "正文第一段"},
        {"table": [["指标", "数值"], ["收入", "100"]]},
    ])
    text = docfile.docx_to_text(p)
    assert "# 第一章 概览" in text          # 标题层级还原成 #
    assert "正文第一段" in text
    assert "| 指标 | 数值 |" in text        # 表格转 markdown 管道表


def test_docx_read_paging(tmp_path):
    p = make_docx(tmp_path / "b.docx", [{"text": f"行{i}"} for i in range(1, 8)])
    body = docfile.read_docx(p, offset=2, limit=2)
    lines = [ln for ln in body.splitlines() if not ln.startswith("<!--")]
    assert lines[0].startswith("3\t")      # offset 0 基，显示行号 1 基
    assert "行3" in lines[0]


def test_docx_info(tmp_path):
    p = make_docx(tmp_path / "c.docx", [
        {"text": "标题", "style": "Heading1"},
        {"text": "正文"},
    ])
    info = docfile.docx_info(p)
    assert info["headings"] == 1
    assert info["lines"] >= 2


def test_docx_broken_file(tmp_path):
    p = tmp_path / "bad.docx"
    p.write_bytes(b"not a zip")
    assert "error" in docfile.docx_info(p)


# ---------------------------------------------------------------- table

def test_table_inspect_xlsx(tmp_path, reg=None):
    _skip_no_env()
    reg = _reg()
    p = make_xlsx(tmp_path / "book.xlsx",
                  [["姓名", "金额"], ["张三", 100], ["李四", 250]], ["账单"])
    res = json.loads(run(reg, _Ctx(tmp_path), "table",
                         {"action": "inspect", "path": str(p)}))
    assert res["ok"], res
    sheet = res["sheets"][0]
    assert sheet["sheet"] == "账单"
    assert sheet["columns"] == ["姓名", "金额"]
    assert sheet["preview"][0] == ["张三", "100"]


def test_table_rows_where_then_columns(tmp_path):
    _skip_no_env()
    reg = _reg()
    p = make_xlsx(tmp_path / "q.xlsx",
                  [["姓名", "金额"], ["张三", 100], ["李四", 250], ["王五", 900]])
    res = json.loads(run(reg, _Ctx(tmp_path), "table",
                         {"action": "rows", "path": str(p), "columns": ["姓名"],
                          "where": "金额>150"}))
    assert res["ok"], res
    assert res["columns"] == ["姓名"]
    assert res["rows"] == [["李四"], ["王五"]]


def test_table_xlsx_with_broken_styles(tmp_path):
    _skip_no_env()
    reg = _reg()
    p = make_xlsx_bad_styles(tmp_path / "bad.xlsx",
                             [["名称", "值"], ["甲", 1], ["乙", 2]])
    res = json.loads(run(reg, _Ctx(tmp_path), "table",
                         {"action": "inspect", "path": str(p)}))
    assert res["ok"], res
    assert res["sheets"][0]["columns"] == ["名称", "值"]


def test_table_csv_and_tsv(tmp_path):
    _skip_no_env()
    reg = _reg()
    p = tmp_path / "t.csv"
    p.write_text("姓名,金额\n张三,100\n李四,250\n", "utf-8")
    res = json.loads(run(reg, _Ctx(tmp_path), "table",
                         {"action": "rows", "path": str(p), "where": "金额>150"}))
    assert res["ok"] and res["rows"] == [["李四", "250"]]

    t = tmp_path / "t.tsv"
    t.write_text("a\tb\n1\t2\n", "utf-8")
    res2 = json.loads(run(reg, _Ctx(tmp_path), "table",
                          {"action": "inspect", "path": str(t)}))
    assert res2["ok"] and res2["sheets"][0]["columns"] == ["a", "b"]


def test_table_json_structure_then_rows(tmp_path):
    _skip_no_env()
    reg = _reg()
    p = tmp_path / "d.json"
    p.write_text(json.dumps([{"name": "a", "n": 1}, {"name": "b", "n": 2}]), "utf-8")
    ins = json.loads(run(reg, _Ctx(tmp_path), "table",
                         {"action": "inspect", "path": str(p)}))
    assert ins["ok"], ins
    assert ins["structure"]["__type__"] == "array"
    rows = json.loads(run(reg, _Ctx(tmp_path), "table",
                          {"action": "rows", "path": str(p), "columns": ["name"],
                           "where": "n>1"}))
    assert rows["ok"] and rows["rows"] == [["b"]]


def test_table_sqlite_inspect_and_query(tmp_path):
    _skip_no_env()
    reg = _reg()
    p = tmp_path / "x.db"
    con = sqlite3.connect(p)
    con.execute("create table t(a text, b integer)")
    con.executemany("insert into t values (?,?)", [("x", 1), ("y", 5)])
    con.commit()
    con.close()

    ins = json.loads(run(reg, _Ctx(tmp_path), "table",
                         {"action": "inspect", "path": str(p)}))
    assert ins["ok"], ins
    assert ins["sheets"][0]["sheet"] == "t"
    assert ins["sheets"][0]["rows"] == 2

    q = json.loads(run(reg, _Ctx(tmp_path), "table",
                       {"action": "query", "path": str(p),
                        "sql": "select a from t where b > 2"}))
    assert q["ok"] and q["rows"] == [["y"]]


@pytest.mark.parametrize("sql", [
    "delete from t", "update t set b=0", "drop table t",
    "select 1; delete from t",
])
def test_table_query_rejects_writes(tmp_path, sql):
    _skip_no_env()
    reg = _reg()
    p = tmp_path / "y.db"
    con = sqlite3.connect(p)
    con.execute("create table t(a)")
    con.commit()
    con.close()
    res = json.loads(run(reg, _Ctx(tmp_path), "table",
                         {"action": "query", "path": str(p), "sql": sql}))
    assert not res["ok"] and res["code"] == "bad_sql"


def test_table_rejects_unknown_suffix(tmp_path, reg=None):
    reg = _reg()
    p = tmp_path / "a.pdf"
    p.write_bytes(b"%PDF-1.4")
    res = json.loads(run(reg, _Ctx(tmp_path), "table",
                         {"action": "inspect", "path": str(p)}))
    assert not res["ok"] and res["code"] == "unsupported"
    assert "pdf_convert" in res["error"]  # 指路要指向真正的工具


def test_table_missing_file(reg=None):
    reg = _reg()
    res = json.loads(run(reg, _Ctx("/tmp"), "table",
                         {"action": "inspect", "path": "/tmp/nope.xlsx"}))
    assert not res["ok"] and res["code"] == "not_found"


# ---------------------------------------------------------------- ppt

def _pptx(tmp_path) -> Path:
    return make_pptx(tmp_path / "s.pptx", [
        {"title": "第一页", "text": "要点一\n要点二"},
        {"title": "第二页", "table": [["列A", "列B"], ["1", "2"]]},
        {"title": "第三页"},
    ])


def test_ppt_inspect(tmp_path):
    p = _pptx(tmp_path)
    res = json.loads(run(_reg(), _Ctx(tmp_path), "ppt",
                         {"action": "inspect", "path": str(p)}))
    assert res["ok"], res
    assert res["pages"] == 3
    assert res["slides"][0]["title"] == "第一页"
    assert res["slides"][1]["tables"] == 1
    assert res["slides"][2]["has_notes"] is False


def test_ppt_read_single_and_range(tmp_path):
    p = _pptx(tmp_path)
    reg = _reg()
    one = json.loads(run(reg, _Ctx(tmp_path), "ppt",
                         {"action": "read", "path": str(p), "slide": 1}))
    assert one["ok"] and one["read"] == [1]
    assert "要点一" in one["slides"][0]["text"]

    rng = json.loads(run(reg, _Ctx(tmp_path), "ppt",
                         {"action": "read", "path": str(p), "pages": "2-3"}))
    assert rng["ok"] and rng["read"] == [2, 3]
    assert "| 列A | 列B |" in rng["slides"][0]["text"]


def test_ppt_read_bad_slide(tmp_path):
    p = _pptx(tmp_path)
    res = json.loads(run(_reg(), _Ctx(tmp_path), "ppt",
                         {"action": "read", "path": str(p), "slide": 99}))
    assert not res["ok"] and res["code"] == "bad_slide"


def test_ppt_rejects_old_format(tmp_path, reg=None):
    p = tmp_path / "old.ppt"
    p.write_bytes(b"\xd0\xcf\x11\xe0")
    res = json.loads(run(_reg(), _Ctx(tmp_path), "ppt",
                         {"action": "inspect", "path": str(p)}))
    assert not res["ok"] and res["code"] == "unsupported"
    assert "另存为" in res["error"]


def test_ppt_edit_backs_up_first(tmp_path):
    _skip_no_env()
    p = _pptx(tmp_path)
    res = json.loads(run(_reg(), _Ctx(tmp_path), "ppt",
                         {"action": "replace_text", "path": str(p),
                          "old": "第一页", "new": "改过的"}))
    bak = p.with_suffix(p.suffix + ".bak")
    assert bak.is_file(), "写之前必须留下备份"
    if res.get("ok"):
        assert res["pages"] == 3
        again = json.loads(run(_reg(), _Ctx(tmp_path), "ppt",
                               {"action": "read", "path": str(p), "slide": 1}))
        assert "改过的" in again["slides"][0]["text"]
    else:
        assert res["code"] in ("missing_deps", "env_unavailable"), res


# ------------------------------------------------- ppt 写动作必须过安全裁决
class _CtxWithCheck:

    def __init__(self, cwd, allowed: bool, reason: str = "出项目目录"):
        self.cwd = str(cwd)
        self.calls: list[tuple[str, list[str]]] = []
        self._allowed = allowed
        self._reason = reason

    async def path_check(self, action, paths):
        self.calls.append((action, list(paths)))
        return self._allowed, self._reason


def test_ppt_write_action_goes_through_path_check(tmp_path):
    _skip_no_env()
    p = make_pptx(tmp_path / "deck.pptx", [{"title": "第一页"}])
    ctx = _CtxWithCheck(tmp_path, allowed=True)
    res = json.loads(run(_reg(), ctx, "ppt", {
        "action": "set_notes", "path": str(p), "slide": 1, "text": "备注"}))
    assert res.get("ok"), res
    assert ctx.calls and ctx.calls[0][0] == "modify", ctx.calls


def test_ppt_write_blocked_when_policy_denies(tmp_path):
    _skip_no_env()
    p = make_pptx(tmp_path / "deck.pptx", [{"title": "第一页"}])
    before = p.read_bytes()
    ctx = _CtxWithCheck(tmp_path, allowed=False, reason="目标在项目外")
    res = json.loads(run(_reg(), ctx, "ppt", {
        "action": "set_notes", "path": str(p), "slide": 1, "text": "备注"}))
    assert "error" in res and "目标在项目外" in res.get("reason", "")
    assert p.read_bytes() == before, "被拒后文件不能变"
    assert not (tmp_path / "deck.pptx.bak").exists(), "被拒后不该产生备份"


def test_ppt_read_actions_do_not_ask_policy(tmp_path):
    p = make_pptx(tmp_path / "deck.pptx", [{"title": "第一页"}])
    ctx = _CtxWithCheck(tmp_path, allowed=False)
    res = json.loads(run(_reg(), ctx, "ppt", {"action": "inspect", "path": str(p)}))
    assert "error" not in res
    assert ctx.calls == [], "只读动作不该调 path_check"
