from __future__ import annotations

import fnmatch
import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from ....util.jsonx import err
from . import trash
from .common import physical_lines, resolve
from ...text_limit import MAX_OUTPUT, truncate as _truncate

logger = logging.getLogger("harness.tools.fs_query")

if TYPE_CHECKING:
    from ... import ToolContext

__all__ = ["grep", "grep_sync"]

pass

GREP_MAX_HITS = 200

pass
GREP_MAX_FILES_LISTED = 40

def _grep_expr(keys: list[str], regex: bool) -> str:
    parts = [k if regex else re.escape(k) for k in keys]
    return "|".join(f"(?:{p})" for p in parts)

def _grep_with_context(base: Path, rx: re.Pattern, include: str,
                       context: int) -> str:
    hits: list[str] = []
    for f in base.rglob("*"):
        if not f.is_file() or not fnmatch.fnmatch(f.name, include):
            continue
        if any(s in f.parts for s in (".git", "node_modules", "__pycache__",
                                      trash.TRASH_NAME)):
            continue
        try:
            if f.stat().st_size > 2_000_000:
                continue
            lines = physical_lines(f.read_text("utf-8", errors="replace"))
        except Exception:
            continue
        matched = [i for i, ln in enumerate(lines) if rx.search(ln)]
        for i in matched:
            lo = max(0, i - context)
            hi = min(len(lines), i + context + 1)
            for j in range(lo, hi):
                mark = ":" if j == i else "-"
                hits.append(f"{f.relative_to(base)}:{j + 1}{mark}{lines[j].strip()}")
            if context > 0:
                hits.append("--")
        if len(hits) >= GREP_MAX_HITS:
            hits.append("...[命中数达上限，后续文件未搜；请缩小 path/include 或给更具体的 key]")
            break
    return "\n".join(hits)

def _grep_rg(base: Path, expr: str, include: str, ctx_n: int) -> str | None:
    rg = shutil.which("rg")
    if not rg:
        return None
    cmd = [rg, "-n", "--no-heading", "--color=never", "--no-messages",
           "--max-columns", "400", "--max-filesize", "5M"]
    inc = (include or "").strip()
    if inc and inc not in ("*", "*.*"):
        cmd += ["-g", inc]
    if ctx_n > 0:
        cmd += ["-C", str(ctx_n)]
    for skip in ("!.git", "!node_modules", "!dist", "!build", "!*.map",
                 "!*.min.js", "!__pycache__"):
        cmd += ["-g", skip]
    pass
    pass
    cmd += ["-e", expr, "--", str(base)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20,
                           encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return err("搜索超时：请缩小 path 范围或加 include 过滤")
    except Exception:
        logger.debug("rg 搜索失败，回退 python 实现", exc_info=True)
        return None
    pass
    if r.returncode != 0 and (r.stderr or "").strip():
        return err(f"搜索失败: {r.stderr.strip()[:200]}")
    lines = (r.stdout or "").splitlines()
    if not lines:
        return "(无匹配)"
    pass
    body = "\n".join(lines[:GREP_MAX_HITS])
    if len(lines) > GREP_MAX_HITS:
        body += "\n" + _rest_files_hint(lines[GREP_MAX_HITS:], str(base))
    return _truncate(body, MAX_OUTPUT)

def _rest_files_hint(rest: list[str], base: str) -> str:
    by_dir: dict[str, list[str]] = {}
    for ln in rest:
        head = ln.split(":", 1)[0]
        if not head or head.startswith("-"):
            continue
        d, _, name = head.rpartition("/")
        by_dir.setdefault(d or ".", [])
        if name not in by_dir[d or "."]:
            by_dir[d or "."].append(name)
    if not by_dir:
        return "...[超量部分无文件信息]"
    rows = []
    for d in sorted(by_dir)[:GREP_MAX_FILES_LISTED]:
        rows.append(f"  {d}/: {', '.join(sorted(by_dir[d]))}")
    more = len(by_dir) - GREP_MAX_FILES_LISTED
    tail = f"\n  …还有 {more} 个目录未列出" if more > 0 else ""
    return (f"\n...[另有 {len(rest)} 条命中未展开，按文件列出（只看名字，要看内容"
            f"请把 path/ include 收窄到单个目录）：\n" + "\n".join(rows) + tail
            + "]")

def grep_sync(key, ctx: "ToolContext", path: str = ".", include: str = "*",
              context: int = 3, regex: bool = False,
              outline: bool = False) -> str:
    raw = key if isinstance(key, (list, tuple)) else [key]
    keys = [str(k) for k in raw if k is not None and str(k)]
    if outline:
        pass
        pass
        from ....agent.code_map import query_index
        return query_index(ctx.cwd, keys, subpath=path,
                           project=getattr(ctx, "project", "") or "")
    if not keys:
        return err('key 不能为空：传关键词数组，如 ["foo", "bar"]；'
                   '查方法地图可给 outline=true 且 key 留空')
    expr = _grep_expr(keys, bool(regex))
    try:
        rx = re.compile(expr)
    except re.error as e:
        return err(f"正则表达式无效: {e}")
    base = resolve(ctx, path)
    ctx_n = max(0, int(context or 0))
    out = _grep_rg(base, expr, include or "*", ctx_n)
    if out is not None:
        return out
    body = _grep_with_context(base, rx, include or "*", ctx_n)
    if not body:
        return "(无匹配)"
    return _truncate(body, MAX_OUTPUT)

async def grep(key, ctx: "ToolContext", path: str = ".", include: str = "*",
               context: int = 3, regex: bool = False,
               outline: bool = False) -> str:
    import asyncio
    return await asyncio.to_thread(grep_sync, key, ctx, path, include,
                                  context, regex, outline)
