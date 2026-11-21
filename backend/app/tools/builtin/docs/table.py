# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING

from ...text_limit import abs_path as _abs
from ._common import finish_doc, resolve_doc
from .exec import run_worker

if TYPE_CHECKING:  # 仅类型提示，避免工具实现反向依赖工具注册表
    from ... import ToolContext, ToolRegistry

TABLE_ACTIONS = ("inspect", "rows", "query")

TABLE_SUFFIX = (".xlsx", ".xlsm", ".xltx", ".xls", ".csv", ".tsv", ".txt",
                ".json", ".jsonl", ".yaml", ".yml",
                ".db", ".sqlite", ".sqlite3", ".db3")


def _fail(code: str, msg: str, **extra) -> str:
    return json.dumps({"ok": False, "code": code, "error": msg, **extra},
                      ensure_ascii=False)


async def table(action: str, ctx: "ToolContext", path: str = "", sheet: str = "",
                columns: list[str] | None = None, where: str = "",
                offset: int = 0, limit: int = 100, sql: str = "") -> str:
    if action not in TABLE_ACTIONS:
        return _fail("bad_action", f"action 只能是 {list(TABLE_ACTIONS)}，收到 {action!r}")

    def suffix_ok(fp: Path) -> str | None:
        suf = fp.suffix.lower()
        if suf not in TABLE_SUFFIX:
            return (f"table 不支持 {suf}；支持 {list(TABLE_SUFFIX)}。"
                    f"PDF 走 pdf_convert，PPT 走 ppt。")
        return None

    p, err = resolve_doc(path, ctx.cwd, _abs, _fail, suffix_ok)
    if err is not None:
        return err

    if action == "inspect":
        payload = {"op": "table_inspect", "path": str(p)}
    elif action == "rows":
        payload = {"op": "table_rows", "path": str(p), "sheet": sheet or "",
                   "columns": list(columns) if columns else None,
                   "where": where or "", "offset": int(offset or 0),
                   "limit": int(limit or 100)}
    else:
        payload = {"op": "table_query", "path": str(p), "sql": sql or "",
                   "limit": int(limit or 200)}

    # 子进程是阻塞调用，必须离开事件循环（否则卡死 WS 流式输出）
    out = await asyncio.to_thread(run_worker, payload)
    return finish_doc(out, p, action)


def register(reg: "ToolRegistry") -> None:
    reg.register(
        "table",
        "读表格型文件：Excel(.xlsx/.xls/.xlsm)、CSV/TSV、JSON/JSONL、YAML、SQLite。"
        "先 action=inspect 拿结构（sheet 名、行列数、列名、前 5 行预览），"
        "再 action=rows 用 columns/where/offset/limit 只取需要的那部分——不要一上来全量读。"
        "action=query 只对 SQLite 开放，只接受 SELECT/WITH 只读查询。"
        "参数 where 写成「列名>值」单条件，如 金额>1000、状态=已完成；多条件请用 query。"
        "不要用它读普通文本（用 f_read）、不要读 PDF（pdf_convert）、不要读 PPT（ppt）。",
        {"action": {"type": "string", "enum": list(TABLE_ACTIONS),
                    "description": "inspect=看结构；rows=取数据行；query=SQLite 只读查询"},
         "path": {"type": "string", "description": "表格文件路径"},
         "sheet": {"type": "string",
                   "description": "action=rows：工作表名/表名/SQLite 表名，留空取第一个"},
         "columns": {"type": "array", "items": {"type": "string"},
                     "description": "action=rows：只取这几列（留空=全部列）"},
         "where": {"type": "string",
                   "description": "action=rows：单条件过滤，如 金额>1000（按列名+比较符+值）"},
         "offset": {"type": "integer", "description": "action=rows：跳过前 N 行，默认 0"},
         "limit": {"type": "integer", "description": "action=rows 默认 100，inspect 忽略"},
         "sql": {"type": "string", "description": "action=query：SELECT/WITH 语句"}},
        table, ["action", "path"])
