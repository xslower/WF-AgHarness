from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ....util.jsonx import err
from ....util.struct import (IniError, StructError, append_to, coerce_value,
                             del_path, desc, detect_format, dump, fmt_path,
                             get_path, load, merge_into, parse_path, set_path, verify)
from .approve import ApprovalBrokeSyntax, approve_hunks
from .common import _emit_file, guard_paths, resolve
from .plan import check_truncation
from .text import split_rows
from .write import (_atomic_write, _count_lines, _lock_for, read_baseline)
from . import revert

if TYPE_CHECKING:
    from ... import ToolContext

OPS = ("set", "delete", "merge", "append", "replace")
_TRUNCATE_GUARD_LINES = 20


async def config_write(path: str, ctx: "ToolContext", ops=None, mode: int = 1,
                       format: str = "", truncate_ok: bool = False) -> str:
    blocked = await guard_paths(ctx, "write", path)
    if blocked:
        return blocked
    p = resolve(ctx, path)
    async with _lock_for(p):
        return await _write_locked(p, ctx, ops, mode, format, truncate_ok)


async def _write_locked(p: Path, ctx: "ToolContext", ops, mode: int,
                        fmt_arg: str, truncate_ok: bool) -> str:
    old_text, existed, mode_err, done = await read_baseline(p, ctx, mode)
    if mode_err:
        return mode_err
    if done:
        return done

    try:
        fmt = detect_format(str(p), fmt_arg)
        items = _normalize_ops(ops)
        doc, style = load(old_text, fmt)
        notes: list[str] = []
        doc, changes = _apply_all(doc, items, fmt, existed, notes)
        new_text = dump(doc, style)
    except (StructError, IniError) as e:
        return err(str(e))

    if new_text == old_text:
        return "内容与原文件一致，未写入"
    bad = verify(new_text, style, doc.expected if fmt == "ini" else doc)
    if bad:
        return err(f"{bad}\n（{p.name} 未被修改；可先 f_read 看原文再试，或换个 op")

    blocked = _truncation(items, old_text, new_text, existed, truncate_ok)
    if blocked:
        return blocked
    try:
        approved = await approve_hunks(ctx, p, old_text, new_text, [])
    except ApprovalBrokeSyntax as e:
        return err(f"部分 hunk 批准后文件不合法：{e}")
    if approved is None:
        return err("文件写入被拒绝")
    if approved != new_text:
        pass
        bad = verify(approved, style, doc.expected if fmt == "ini" else doc)
        if bad:
            return err(f"仅批准的部分 hunk 落盘后不合法，未写入：{bad}")
        new_text = approved

    await ctx.auto_snapshot(f"config_write {p.name}", [p])
    _atomic_write(p, new_text)
    _emit_file(ctx, p, "modified" if existed else "created")
    if mode == 3:
        revert.pop(ctx, p)
    revert.push(ctx, p, old_text)
    return _summary(p, fmt, changes, notes, style, old_text, new_text, existed)


pass


def _normalize_ops(ops) -> list[dict]:
    if isinstance(ops, dict):
        ops = [ops]
    if not isinstance(ops, list) or not ops:
        raise StructError("ops 必须是非空数组，每项形如 "
                          '{"op": "set", "path": "a.b", "value": ...}')
    for i, item in enumerate(ops, 1):
        if not isinstance(item, dict):
            raise StructError(f"ops[{i}] 必须是对象，收到 {type(item).__name__}")
        act = str(item.get("op") or "set").strip().lower()
        if act not in OPS:
            raise StructError(f"ops[{i}].op 只能是 {'/'.join(OPS)}，收到 {act!r}")
    return ops


def _apply_all(doc: Any, ops: list[dict], fmt: str, existed: bool,
               notes: list[str]) -> tuple[Any, list[str]]:
    changes: list[str] = []
    for i, item in enumerate(ops, 1):
        act = str(item.get("op") or "set").strip().lower()
        where = f"ops[{i}]({act})"
        try:
            if fmt == "ini":
                changes += _apply_ini(doc, item, act, existed)
                continue
            value, note = coerce_value(item.get("value"),
                                       as_string=bool(item.get("as_string")))
            if note:
                notes.append(f"{where} {note}")
            if act == "replace":
                doc = value
                changes.append(f"整份替换：{_size(doc)}")
                continue
            changes += _apply_struct(doc, item, act, value)
        except (StructError, IniError) as e:
            raise StructError(f"{where} 失败：{e}") from None
    return doc, changes


def _tokens(item: dict, act: str) -> list[str]:
    raw = item.get("path")
    if act == "replace":
        if raw:
            raise StructError("op=replace 不接受 path（那是整份替换）；"
                              "只改某一块请用 set/merge")
        return []
    return parse_path(raw)


def _apply_struct(doc: Any, item: dict, act: str, value: Any) -> list[str]:
    tokens = _tokens(item, act)
    if act == "set":
        old = _peek(doc, tokens)
        set_path(doc, tokens, value)
        return [f"改 {fmt_path(tokens)}: {desc(old)} → {desc(value)}"]
    if act == "delete":
        old, _ = del_path(doc, tokens)
        return [f"删 {fmt_path(tokens)}: {desc(old)}"]
    if act == "merge":
        changed = merge_into(doc, tokens, value)
        return [f"合并 {name}" for name in changed]
    idx = append_to(doc, tokens, value)
    return [f"追加 {fmt_path(tokens)}[{idx}]: {desc(value)}"]


def _apply_ini(doc: Any, item: dict, act: str, existed: bool) -> list[str]:
    if act in ("merge", "append"):
        raise StructError(f"INI 不支持 {act}（没有嵌套结构）；用 set 逐个键写")
    if act == "replace":
        if existed:
            raise StructError("已存在的 INI 不允许 op=replace（会洗掉注释与排版）；"
                              "用 set/delete 改，或 f_write 整份重写")
        raise StructError("INI 整份新建请直接给 set/delete 的 ops（自动建段）")
    tokens = _tokens(item, act)
    if len(tokens) != 2:
        raise StructError("INI 的 path 只支持两级 section.key，"
                          f"收到 {fmt_path(tokens)}")
    section, key = tokens
    if act == "delete":
        doc.delete(section, key)
        return [f"删 [{section}] {key}"]
    raw = item.get("value")
    value, note = coerce_value(raw, as_string=bool(item.get("as_string")))
    if note:
        raise StructError("INI 的值一律是字符串，不接受结构化值；"
                          f"请直接给标量（收到 {desc(raw)}）")
    old = doc.expected.get(section, {}).get(key)
    doc.set(section, key, value)
    new = doc.expected.get(section, {}).get(key)
    return [f"改 [{section}] {key}: {desc(old)} → {desc(new)}"]


def _peek(doc: Any, tokens: list[str]) -> Any:
    try:
        return get_path(doc, tokens) if tokens else doc
    except StructError:
        return None


def _size(value: Any) -> str:
    if isinstance(value, dict):
        return f"{len(value)} 键"
    if isinstance(value, (list, tuple)):
        return f"{len(value)} 项"
    return type(value).__name__


pass


def _truncation(ops: list[dict], old_text: str, new_text: str,
                existed: bool, truncate_ok: bool) -> str | None:
    if not any(str(o.get("op") or "").lower() == "replace" for o in ops):
        return None
    return check_truncation({"kind": "overwrite"}, split_rows(old_text),
                            old_text, new_text, existed, truncate_ok,
                            _TRUNCATE_GUARD_LINES)


def _summary(p: Path, fmt: str, changes: list[str], notes: list[str],
             style, old_text: str, new_text: str, existed: bool) -> str:
    verb = "已新建" if not existed else "已写入"
    lines = [f"{verb} {p}（{fmt}）"]
    lines += [f"  {c}" for c in changes[:20]]
    if len(changes) > 20:
        lines.append(f"  …（共 {len(changes)} 处改动）")
    if fmt == "yaml":
        if style.yaml_engine == "ruamel":
            lines.append("  YAML 注释/锚点/引号风格已保留（ruamel round-trip）")
        else:
            lines.append("  ⚠ 未装 ruamel.yaml，已降级 PyYAML：注释与引号风格可能被重排")
    if fmt == "ini":
        lines.append("  INI 行级编辑：注释/空行/键大小写保留；值一律按文本写")
    lines += [f"  {n}" for n in dict.fromkeys(notes)]
    before, after = _count_lines(old_text), _count_lines(new_text)
    lines.append(f"文件 {before} 行 → {after} 行；如需核对请 f_read 指定区间，"
                 "mode=2 可撤销这次写入")
    return "\n".join(lines)
