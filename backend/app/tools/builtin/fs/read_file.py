from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from ....util import imagex
from ....util.jsonx import err
from .common import _stat_info, physical_lines, resolve
from .lines import LinesError, parse_read_range
from .outline import build_outline, needs_outline
from ...text_limit import (MAX_OUTPUT, MAX_READ, TOOL_CONTEXT_LIMIT,
                           clip_both_clean as _clip_clean,
                           truncate_both as _truncate_both,
                           truncate as _truncate)

if TYPE_CHECKING:
    from ... import ToolContext

__all__ = ["f_read", "MAX_BATCH_READ", "MAX_READ_LINES"]

pass
pass
MAX_READ_LINES = 2_000

pass
_DOC_SUFFIXES = {".pdf", ".docx", ".xlsx", ".xlsm", ".pptx", ".doc", ".xls", ".ppt",
                ".db", ".sqlite", ".sqlite3", ".db3"}

_TABLE_SUFFIX = {".xlsx", ".xlsm", ".xls", ".db", ".sqlite", ".sqlite3", ".db3"}

_PPT_SUFFIX = {".pptx", ".ppt"}

_LEGACY_OFFICE = {".doc", ".xls", ".ppt"}

def _route_binary(suf: str, p: Path, ctx=None) -> dict:
    result: dict = {"error": None, "use_tool": None, "args": None, "next": None}
    tool_name = None
    if suf in _TABLE_SUFFIX:
        tool_name = "table"
        result["use_tool"] = "table"
        result["args"] = {"action": "inspect", "path": str(p)}
        result["error"] = f"这是二进制表格文件（{suf}），请用 table(action=inspect, path=...) 查看"
    elif suf in _PPT_SUFFIX:
        tool_name = "ppt"
        result["use_tool"] = "ppt"
        result["args"] = {"action": "inspect", "path": str(p)}
        result["error"] = f"这是 PowerPoint 文件（{suf}），请用 ppt(action=inspect, path=...) 查看"
    elif suf == ".pdf":
        tool_name = "pdf_convert"
        result["use_tool"] = "pdf_convert"
        result["args"] = {"path": str(p)}
        result["error"] = f"这是 PDF 文件，请用 pdf_convert(path=...) 转为 Markdown 后阅读"
    elif suf == ".docx":
        pass
        result["next"] = "docx"
        return result
    elif suf in _LEGACY_OFFICE:
        result["error"] = f"旧版 Office 格式（{suf}）不支持直接读取，建议先转换为新版格式（.docx/.xlsx/.pptx）"
        return result
    else:
        result["error"] = f"二进制文件（{suf}）不支持直接读取"
        return result
    pass
    if tool_name and ctx and hasattr(ctx, "suggest_tools") and hasattr(ctx, "registry"):
        reg = ctx.registry
        if reg and hasattr(reg, "schemas"):
            for s in reg.schemas:
                if s.get("function", {}).get("name") == tool_name:
                    ctx.suggest_tools([s])
                    break
    return result

class _ReadArgsError(ValueError):
    pass

def _coerce_line_spec(v):
    if v is None:
        return None
    if isinstance(v, bool):
        raise _ReadArgsError('lines 数组元素只能是行区间字符串/行号整数/空值，'
                             f'收到布尔值 {v!r}')
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return v if v.strip() else None
    raise _ReadArgsError(
        'lines 数组元素只能是行区间字符串（如 "1,20"）或行号整数，'
        f'收到 {type(v).__name__}: {repr(v)[:60]}')

def _normalize_read_args(path, lines, paths):
    if path is None:
        path = paths
    if path is None:
        raise _ReadArgsError(
            'f_read 需要 path（或 paths）参数；一次读多个请给 '
            'path=["a.py", "b.py"] 或 paths=[...]')
    if isinstance(lines, str):
        pass
        pass
        pass
        pass
        t = lines.strip()
        if t.startswith("[") and t.endswith("]"):
            try:
                decoded = json.loads(t)
            except ValueError:
                decoded = None
            if isinstance(decoded, list):
                lines = decoded
    if not isinstance(lines, (list, tuple)):
        return path, lines
    items = list(path) if isinstance(path, (list, tuple)) else [path] * len(lines)
    if len(items) != len(lines):
        raise _ReadArgsError(
            f'paths 与 lines 数组长度不一致（{len(items)} 个路径 vs '
            f'{len(lines)} 个区间）：它们按下标一一对应，错位一个就会读错文件、'
            '白耗上下文。请补齐后重发；只给一个区间用 '
            'f_read(path=[...], lines="A,B")，或写成 '
            '[{"path":...,"lines":...}, ...] 各自带区间')
    out = []
    for item, spec in zip(items, lines):
        one = _coerce_line_spec(spec)
        if isinstance(item, dict):
            d = dict(item)
            if 'lines' not in d and one is not None:
                d['lines'] = one
        else:
            d = {'path': item}
            if one is not None:
                d['lines'] = one
        out.append(d)
    return out, None

def f_read(path=None, ctx: "ToolContext" = None,
           lines: str | None = None,
           linenos: bool = False, info: bool = False, mode: str = "",
           raw: bool = False, paths=None) -> str:
    if ctx is None:
        return err('f_read 缺少运行上下文（ctx）')
    try:
        path, lines = _normalize_read_args(path, lines, paths)
    except _ReadArgsError as e:
        return err(str(e))
    if isinstance(path, (list, tuple)):
        return _read_many(path, ctx, lines, linenos, info, mode, raw)
    return _read_one(path, ctx, lines, linenos, info, mode, raw)

pass
pass
pass
pass
MAX_BATCH_READ = 8

pass
PER_FILE_CONTEXT = 9_000

BATCH_CONTEXT_CAP = 48_000


def _batch_budget(n: int) -> int:
    return min(BATCH_CONTEXT_CAP, max(TOOL_CONTEXT_LIMIT,
                                      n * PER_FILE_CONTEXT)) // max(1, n)


def _read_many(paths, ctx, lines, linenos: bool, info: bool,
               mode: str = "", raw: bool = False) -> str:
    if not paths:
        return err("f_read 批量模式：path 数组为空；传 [\"a.py\", \"b.py\"] 或"
                   " [{\"path\":\"a.py\",\"lines\":\"1,80\"}]，一次可给 8 个")
    total = len(paths)
    shown = list(paths[:MAX_BATCH_READ])
    rest = list(paths[MAX_BATCH_READ:])
    per = _batch_budget(len(shown)) if len(shown) > 1 else 0
    out: list[str] = []
    for item in shown:
        if isinstance(item, dict):
            one_path = item.get("path", "")
            one_lines = item.get("lines", lines)
            one_mode = item.get("mode", mode)
        else:
            one_path, one_lines, one_mode = item, lines, mode
        label = f"{one_path}" + (f" [{one_lines}]" if one_lines else "")
        body = _read_one(str(one_path), ctx, one_lines, linenos, info,
                         one_mode, raw)
        if per and len(body) > per and not raw:
            body = _truncate_both(
                body, per,
                "本段过长已收紧；要看中间请对该文件单独给 lines=\"A,B\" 取区间")
        out.append(f"===== {label} =====\n{body}")
    if rest:
        names = ", ".join(
            str(x.get("path", x)) if isinstance(x, dict) else str(x)
            for x in rest[:12])
        more = f"，还有 {len(rest) - 12} 个未列出" if len(rest) > 12 else ""
        out.append(
            f"===== 未读 {len(rest)} 个（本次共 {total} 个，已读前 "
            f"{len(shown)} 个）=====\n{names}{more}\n"
            "再发一次 f_read(path=[这些路径]) 即可补齐；不用重读已给过的文件。")
    return "\n\n".join(out)


def _attach_image(p: Path, ctx: "ToolContext") -> str:
    if not getattr(ctx, "images_channel", False):
        return err(f"当前上下文不支持读图（没有发图通道），请用 ocr 工具：{p}")
    pending = ctx.pending_images
    if len(pending) >= imagex.MAX_IMAGES:
        return err(f"一次最多 {imagex.MAX_IMAGES} 张图，本张未附上：{p}")
    data = imagex.to_data_url(str(p))
    if not data:
        return err(f"图片读不到或格式不支持：{p}")
    pending.append(data)
    size_kb = max(1, len(data) * 3 // 4 // 1024)
    return (f"[图片已读取：{p.name}，约 {size_kb}KB]\n"
            "内容会紧随本批工具结果，作为一条用户消息给出"
            "（能看图的模型直接看图，否则附文字描述）。不要再用 f_read 读它。")


def _read_one(path: str, ctx: "ToolContext", lines: str | None,
              linenos: bool, info: bool, mode: str = "",
              raw: bool = False) -> str:
    p = resolve(ctx, path)
    if not p.exists():
        return err(f"路径不存在: {p}")
    if info:
        return _stat_info(p)
    if not p.is_file():
        return json.dumps(
            {"error": f"不是文件（目录请用 search_files 只传 path 列目录）: {p}"},
            ensure_ascii=False)
    if p.stat().st_size > 5_000_000:
        return err("文件超过 5MB，请用 grep 定位后分段读")
    pass
    pass
    pass
    if imagex.is_image(p):
        return _attach_image(p, ctx)
    pass
    suf = p.suffix.lower()
    if suf in _DOC_SUFFIXES:
        r = _route_binary(suf, p, ctx)
        if r.get("error"):
            return json.dumps(r, ensure_ascii=False)
    pass
    text = p.read_text("utf-8", errors="replace")
    all_lines = physical_lines(text)
    pass
    pass
    pass
    pass
    pass
    want_outline = (mode == "outline" or
                    (lines is None and not raw and needs_outline(text)))
    if want_outline:
        outline = build_outline(text, str(path))
        if outline:
            return outline
    try:
        parsed = parse_read_range(lines, len(all_lines))
    except LinesError as e:
        return err(str(e))
    rng = None if parsed is None else (parsed[0], parsed[1])
    end_note = "" if parsed is None else parsed[2]
    if rng is None:
        sel = all_lines[:MAX_READ_LINES]
        base = 1
    else:
        start, end = rng
        sel = all_lines[start - 1:end]
        base = start
    if linenos:
        body = "\n".join(f"{i + base}\t{l}" for i, l in enumerate(sel))
    else:
        body = "\n".join(sel)
    pass
    pass
    if end_note:
        body += f"\n...[{end_note}；本次返回第 {base}~{base + len(sel) - 1} 行]"
    if rng is None and len(all_lines) > MAX_READ_LINES:
        body += (f"\n...[只给了前 {MAX_READ_LINES} 行，文件共 {len(all_lines)} 行；"
                 f"继续读请给 lines=\"{MAX_READ_LINES + 1},\"（可配合数组一次取多段）]")

    if len(body) <= MAX_READ:
        return body or "(空文件)"
    if raw:
        pass
        return _clip_clean(body, MAX_READ)[0] or "(空文件)"
    return _truncate_both(
        body, MAX_READ,
        f"全文过长已收紧，要看中间段落请给 lines=\"A,B\" 读区间"
        f"（当前路径 {path}）")
