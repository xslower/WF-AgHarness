from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from .jsonfix_common import (_CTRL, _STRIP_COMMENT, _drop_trailing_commas,
                             _try_load, _try_load5, close_open_structs)

__all__ = ["ScenePolicy", "repair_long_value", "drop_incomplete_tail",
           "scene_for_tool"]

pass
pass
pass

pass
_SCALAR_TAIL = re.compile(
    r',\s*"[A-Za-z_]\w*"\s*:\s*(?:true|false|null|True|False|None|-?\d+(?:\.\d+)?)\s*$')

pass
pass
_SHORT_STR_TAIL = re.compile(
    r',\s*"[A-Za-z_]\w*"\s*:\s*"[^"\\\n]{0,60}"\s*$')

def repair_long_value(text: str, long_keys: Iterable[str]) -> tuple[str, str]:
    keys = tuple(long_keys)
    if not keys:
        return "", ""
    body = (text or "").rstrip()
    closers = ""
    while body and body[-1] in "}]":
        closers = body[-1] + closers
        body = body[:-1].rstrip()
    scalar_tail = ""
    while True:
        m = _SCALAR_TAIL.search(body) or _SHORT_STR_TAIL.search(body)
        if not m:
            break
        scalar_tail = body[m.start():] + scalar_tail
        body = body[:m.start()].rstrip()
    if not body.endswith('"'):
        return "", ""
    pass
    start, pat, hit_key = -1, None, keys[0]
    for k in keys:
        for mm in re.finditer(r'"%s"\s*:\s*"' % re.escape(k), body):
            if mm.start() > start:
                start, pat, hit_key = mm.start(), mm, k
    if not start or pat is None:
        return "", ""
    inner = body[pat.end():-1]
    out: list[str] = []
    i, n, escaped_n = 0, 0, 0
    while i < len(inner):
        c = inner[i]
        if c == "\\" and i + 1 < len(inner):
            out.append(inner[i:i + 2])
            i += 2
        elif c == '"':
            out.append('\\"')
            i += 1
            n += 1
        elif c in _CTRL:
            out.append(_CTRL[c])
            i += 1
            escaped_n += 1
        else:
            out.append(c)
            i += 1
    if not n and not escaped_n:
        return "", ""
    core = body[:pat.end()] + "".join(out) + '"' + scalar_tail + closers
    pass
    closed, _why = close_open_structs(core)
    fixed = closed or core
    notes = []
    if n:
        notes.append(f"转义 {hit_key} 内 {n} 个未转义双引号")
    if escaped_n:
        notes.append(f"转义 {hit_key} 内 {escaped_n} 个裸换行/制表符")
    return fixed, f"锚点法：{'、'.join(notes)}"

pass
pass
pass


def _cut_points(text: str) -> list[int]:
    pts: list[int] = []
    depth = 0
    in_str = esc = False
    prev_closer = False
    for i, c in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c in "{[(":
            depth += 1
            prev_closer = False
        elif c in "})]":
            depth -= 1
            prev_closer = True
            if depth >= 1:
                pts.append(i + 1)
            continue
        elif c == ",":
            if depth <= 1 or prev_closer:
                pts.append(i)
        prev_closer = False
    return pts

def drop_incomplete_tail(text: str, *, max_drop: int = 4000,
                         max_ratio: float = 0.5) -> tuple[str, str, int]:
    n = len(text or "")
    if n < 2:
        return "", "", 0
    for cut in reversed(_cut_points(text)):
        dropped = n - cut
        if dropped <= 0 or dropped > max_drop:
            continue
        if cut < n * (1 - max_ratio):
            continue
        core, _ = _drop_trailing_commas(text[:cut].rstrip())
        fixed, _ = close_open_structs(core)
        if not fixed:
            continue
        v, ok = _try_load5(fixed)
        if ok and isinstance(v, (dict, list)):
            return fixed, f"丢弃末尾不完整片段 {dropped} 字符后补齐结构", dropped
    return "", "", 0

pass
pass
pass


@dataclass(slots=True)
class ScenePolicy:
    long_keys: tuple[str, ...] = ()
    drop_tail: bool = False
    label: str = ""

_POLICIES: dict[str, ScenePolicy] = {
    # run_command：长命令 + 短标量参数；命令被截断绝不救（不许执行半截命令）
    "command": ScenePolicy(("command",), False, "命令参数"),
    # f_write / f_replace：edits 数组里有 content/old/new 长文本，允许丢尾部元素
    "edits": ScenePolicy(("content", "old", "new"), True, "文件改动参数"),
    # 其它多参数工具（f_read / f_path / grep ...）：通用 + 允许丢尾部
    "args": ScenePolicy(("content", "command", "text", "body"), True, "工具参数"),
    # 非工具场景（SSE 帧、外部 JSON）：只通用层，一个字节都不许丢
    "raw": ScenePolicy((), False, "外部 JSON"),
}

pass
_TOOL_SCENE = {
    "run_command": "command",
    "f_write": "edits",
    "f_replace": "edits",
}

def scene_for_tool(tool_name: str | None) -> str:
    if not tool_name:
        return "args"
    return _TOOL_SCENE.get(tool_name, "args")

def _policy(scene: str) -> ScenePolicy:
    return _POLICIES.get(scene, _POLICIES["args"])
