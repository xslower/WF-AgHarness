from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ....util.jsonx import err
from .common import _emit_file, guard_paths, resolve
from .lines import LinesError, parse_write_target, split_lines
from .atomic import (atomic_write as _atomic_write,
                     count_lines as _count_lines, lock_for as _lock_for,
                     read_baseline)
from .match import apply_matches, locate
from . import revert
from .approve import ApprovalBrokeSyntax, approve_hunks
from .plan import (build_insert, build_overwrite, build_replace,
                   check_truncation, split_body)
from .structure import boundary_guard
from .text import Row, _split_new_lines, _syntax_gate, join_rows, split_rows

__all__ = ["f_write", "f_replace"]

if TYPE_CHECKING:  # 仅类型提示，避免工具实现反向依赖工具注册表
    from ... import ToolContext

# 整篇覆盖的熔断：新内容不到原文 30% 且原文超过这个行数时，要求显式确认
_TRUNCATE_GUARD_LINES = 20

# 改完不合法时按**写入量**分档（用户 2026-11-19 定）：
# 写入量 ≤ 这个行数却把合法文件写成不合法 = 一定不是本意 → 拒绝；
# 写入量更大 = 半成品/整块重写，落盘但明确警告。
BROKEN_MAX_LINES = 2

# 原子写 / 同一路径写入锁 / mode 三态基准在 fs/atomic.py（三个写工具共用）。


# ═══════════════════════════ 行级定位内核 ═══════════════════════════



def _near_rows(rows: list[Row], old: str, limit: int = 3) -> str:
    if not rows:
        return ""
    first = old.replace("\r\n", "\n").split("\n")[0].strip()
    if not first:
        return ""
    scored = []
    for i, r in enumerate(rows):
        s = r.content.strip()
        if not s:
            continue
        if first in s or s in first:
            scored.append((0, i, s))
        else:
            scored.append((-len(set(first) & set(s)), i, s))
    scored.sort(key=lambda x: (x[0], x[1]))
    return "\n".join(f"  第 {i + 1} 行| {s[:100]}" for _, i, s in scored[:limit])



# ═══════════════════════════ f_write ═══════════════════════════

async def f_write(path: str, ctx: "ToolContext", content: str | None = None,
                  before: int | None = None, after: int | None = None,
                  replace: str | None = None, expect: str | None = None,
                  append: bool = False, mode: int = 1,
                  truncate_ok: bool = False, edits=None) -> str:
    if edits is not None:
        from .batch import write_batch
        return await write_batch(path, ctx, edits, mode=mode,
                                 truncate_ok=truncate_ok)
    # mode=2 是纯撤销（把文件恢复成上一次写入前的内容）：它是安全动作，
    # 再要一次审批只会让"改错了想撤回"变得更麻烦。其余模式（含 mode=3，它要写新内容）
    # 照常裁决。
        blocked = await guard_paths(ctx, "write", path)
        if blocked:
            return blocked
    p = resolve(ctx, path)
    async with _lock_for(p):
        return await _f_write_locked(p, ctx, content, before, after, replace,
                                     expect, append, mode, truncate_ok)


async def _f_write_locked(p: Path, ctx: "ToolContext", content: str,
                          before: int | None, after: int | None,
                          replace: str | None, expect: str | None,
                          append: bool, mode: int, truncate_ok: bool) -> str:
    # 用 bytes 读：read_text 的 universal newlines 会把 CRLF 变成 LF
    old_text, existed, mode_err, done = await read_baseline(p, ctx, mode)
    if mode_err:
        return mode_err
    if done:
        return done

    # ── 2. 参数校验 + 算落点
    if content is None:
        return err("需要 content（要写入的文本）")

    rows = split_rows(old_text)
    try:
        target = parse_write_target(before, after, replace, append, len(rows))
    except LinesError as e:
        return err(str(e))

    try:
        new_text, summary, detail, written = _plan_write(
            target, rows, content, expect)
    except LinesError as e:
        return err(str(e))

    if new_text == old_text:
        return "内容与原文件一致，未写入"

    # ── 3. 合法性：parse 过零干预；缩进错自动修。修不好时按**写入量**分档：
    #    小改动（≤2 行）把合法文件写成不合法 = 一定不是本意 → 拒绝；
    #    大改动（≥3 行）多半是半成品/整块重写 → 落盘但明确警告。
    volume = _write_volume(content)
    notes: list[str] = []
    new_text, gate_note, allow = _syntax_gate(
        new_text, old_text, str(p), written,
        allow_broken=volume > BROKEN_MAX_LINES)
    if not allow:
        return err(f"{detail}\n{gate_note}")
    if gate_note:
        # 系统改了模型写的内容（或放行了不合法内容），这条信号必须在回显里保留
        notes.append(gate_note)

    # ── 3.5 边界：非 Python 的括号配平（Python 的合法性上面已判完，删函数不算坏）
    loss = boundary_guard(old_text, new_text, str(p), truncate_ok)
    if loss:
        if volume <= BROKEN_MAX_LINES:
            return err(f"{detail}\n{loss}")
        notes.append(loss + _broken_hint(volume))

    # ── 4. 整篇覆盖的误操作熔断
    blocked = check_truncation(target, rows, old_text, new_text, existed,
                               truncate_ok, _TRUNCATE_GUARD_LINES)
    if blocked:
        return blocked
    if notes:
        extra = "\n".join(notes)
        summary = f"{summary}\n{extra}"
        detail = f"{detail}\n{extra}"
    # ── 5. 文件级审批：展示整体 diff，可按 hunk 批准
    # ── 6. 文件级审批：展示整体 diff，可按 hunk 批准
    try:
        approved_text = await approve_hunks(ctx, p, old_text, new_text, written)
    except ApprovalBrokeSyntax as e:
        return err(f"{detail}\n{e}\n"
                   "部分 hunk 批准后文件不再是合法 Python（括号/缩进被拆开）。"
                   "请重新发一次，或在审批面板批准完整的一组改动。")
    if approved_text is None:
        return err("文件写入被拒绝")
    if approved_text != new_text:
        # 用户只批准了部分 hunk：回显必须按**实际落盘的那份**重算，
        # 否则「已写入 原 12 行 → 新 15 行」说的是模型原本想写的内容，
        # 而不是真正写进文件的内容。
        new_text = approved_text
        before_rows = len(split_rows(old_text))
        summary = (f"原 {before_rows} 行 → 新 {len(split_rows(new_text))} 行"
                   "（仅批准部分 hunk）")

    # ── 6. 落盘
    await ctx.auto_snapshot(f"write {p.name}", [p])
    _atomic_write(p, new_text)
    _emit_file(ctx, p, "modified" if existed else "created")
    if mode == 3:
        revert.pop(ctx, p)      # 栈顶就是刚才那版基准，去掉重复后再压回
    revert.push(ctx, p, old_text)
    verb = "已创建" if not existed else "已写入"
    # 行区间越界（例如 100 行文件写 replace="90,110"）时附改动前后三行，
    # 让模型一眼能核对系统究竟按哪一段落的笔。
    shown = f"\n{detail}" if target.get("note") else ""
    return (f"{verb} {p}：{summary}{shown}\n"
            f"如需核对改动请 f_read 指定行区间；mode=2 可撤销这次写入")


def _write_volume(content: str) -> int:
    return len(split_rows(content))


def _broken_hint(volume: int) -> str:
    return (f"\n（本次写入 {volume} 行，超过 {BROKEN_MAX_LINES} 行的门槛：已按你的"
            "内容落盘，但文件当前不合法。接着把它改好，或 mode=3 回滚后整体重写）")


def _plan_write(target: dict, rows: list[Row], content: str,
                expect: str | None) -> tuple[str, str, str, list[int]]:
    kind = target["kind"]
    if kind == "overwrite":
        new_text, summary, detail = build_overwrite(content, rows)
        # 整篇覆盖不进 written：新文件整个都是新内容，缩进修复无从谈起
        return new_text, summary, detail, []
    body = split_body(content)
    if kind == "insert":
        return build_insert(rows, target, body, expect)
    return build_replace(rows, target, body, expect)


# ═══════════════════════════ f_replace ═══════════════════════════

async def f_replace(path: str, ctx: "ToolContext", old: str = "",
                     new: str = "", mode: int = 1, replace_all: bool = False,
                     replace_count: int = 0, edits=None) -> str:
    if edits is not None:
        from .batch import replace_batch
        return await replace_batch(path, ctx, edits, mode=mode)
    blocked = await guard_paths(ctx, "modify", path)
    if blocked:
        return blocked
    p = resolve(ctx, path)
    async with _lock_for(p):
        return await _f_replace_locked(p, ctx, old, new, mode, replace_all,
                                       replace_count)


def _written_lines(matches: list, old_rows: list, new: str) -> list[int]:
    new_lines = _split_new_lines(new)
    written: list[int] = []
    consumed = 0
    for m in sorted(matches, key=lambda x: x.row_start):
        block_len = (m.row_end - m.row_start) if m.block else 1
        start = m.row_start + 1 - consumed
        written.extend(range(start, start + len(new_lines)))
        consumed += block_len - len(new_lines)
    return written


def _replace_volume(matches: list, new: str) -> int:
    return len(_split_new_lines(new)) * len(matches)


def _hit_detail(matches: list, old_rows: list, new_rows: list, fuzzy: bool) -> str:
    hit_lines = sorted({m.row_start + 1 for m in matches})
    detail = (f"第 {hit_lines[0]} 行" if len(hit_lines) == 1
              else f"第 {', '.join(str(x) for x in hit_lines[:10])} 行")
    if fuzzy:
        detail += "（按忽略缩进/空行匹配）"
    return (f"{detail}：{len(matches)} 处已替换，"
            f"原 {len(old_rows)} 行 → 现 {len(new_rows)} 行")



async def _f_replace_locked(p: Path, ctx: "ToolContext", old: str, new: str,
                            mode: int, replace_all: bool,
                            replace_count: int = 0) -> str:
    old_text, existed, mode_err, done = await read_baseline(p, ctx, mode)
    if mode_err:
        return mode_err
    if done:
        return done

    if not p.is_file():
        return err(f"文件不存在: {p}")
    if old is None or old == "":
        return err("old 不能为空（要改什么？给一段原文）")
    if new is None:
        return err("new 不能为空；只想删除这段请显式写 new=\"\"")
    if old == new:
        return "old 与 new 相同，未写入"

    rows = split_rows(old_text)
    matches, fuzzy = locate(rows, old)
    if not matches:
        near = _near_rows(rows, old)
        return err(f"在 {p} 里没找到要替换的内容。"
                   + (f"\n文件里最接近的几行：\n{near}" if near else "")
                   + "\n请先 f_read 看原文（注意缩进与空格），再改一次")
    if len(matches) > 1 and not replace_all and not replace_count:
        where = "\n".join(f"  第 {m.row_start + 1} 行" for m in matches[:10])
        more = f"\n  …共 {len(matches)} 处" if len(matches) > 10 else ""
        return err(f"要替换的内容在 {p} 里出现 {len(matches)} 次：\n{where}{more}\n"
                   "请给更长的唯一片段，或传 replace_all=true 全部替换。")
    # replace_count=N：只替换前 N 处（按文件顺序），其余保留。
    if replace_count and not replace_all:
        matches = matches[:max(0, replace_count)]

    new_rows = apply_matches(rows, matches, new)
    out = join_rows(new_rows)
    written = _written_lines(matches, rows, new)
    detail = _hit_detail(matches, rows, new_rows, fuzzy)

    # 合法性：parse 过零干预；缩进错自动修（只动写入行）；修不好按写入量分档
    vol = _replace_volume(matches, new)
    out, gate_note, allow = _syntax_gate(out, old_text, str(p), written,
                                         allow_broken=vol > BROKEN_MAX_LINES)
    if not allow:
        return err(f"{detail}\n{gate_note}")
    if gate_note:
        detail = f"{detail}\n{gate_note}"

    # 边界：非 Python 的括号配平（Python 的合法性上面已判完，删函数不算坏）
    loss = boundary_guard(old_text, out, str(p))
    if loss:
        if vol <= BROKEN_MAX_LINES:
            return err(f"{detail}\n{loss}")
        detail = f"{detail}\n{loss}{_broken_hint(vol)}"

    if ctx.request_file_approval:
        try:
            approved_text = await approve_hunks(
                ctx, p, old_text, out, written, verb="replace")
        except ApprovalBrokeSyntax as e:
            return err(
                f"{detail}\n{e}\n"
                "部分 hunk 批准后文件不再是合法 Python（括号/缩进被拆开）。"
                "请重新发一次，或在审批面板批准完整的一组改动。")
        if approved_text is None:
            return err(
                "文件写入被拒绝：审批未通过或安全策略拦截了 "
                f"replace {p.name}。别原样重试 —— 先在审批面板处理这条请求，"
                "或改用 f_write 的 edits 数组把改动拆小；确认计划模式已切到执行态再重试。")
        if approved_text != out:
            # 部分 hunk 批准：下面的 detail 是「模型原本想改的全部位置」，
            # 与真实落盘内容不再一一对应，必须明说，否则用户会以为全改了。
            detail = f"{detail}\n（仅批准部分 hunk：实际落盘内容与上面列出的位置不完全一致）"
        out = approved_text

    await ctx.auto_snapshot(f"replace {p.name}", [p])
    _atomic_write(p, out)
    _emit_file(ctx, p, "modified")
    if mode == 3:
        revert.pop(ctx, p)      # 栈顶就是刚才那版基准，去掉重复后再压回
    revert.push(ctx, p, old_text)
    return (f"已修改 {p}：{detail}\n"
            f"如需核对改动请 f_read 指定行区间；mode=2 可撤销这次修改")
