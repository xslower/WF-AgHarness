from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..jsonfix import loads_lenient

__all__ = ["FORMATS", "FMT_BY_SUFFIX", "StructError", "append_to", "coerce_value",
           "del_path", "desc", "detect_format", "fmt_path", "get_path",
           "merge_into", "parse_path", "plain", "same_value", "set_path"]

pass
FMT_BY_SUFFIX = {
    ".json": "json", ".jsonl": "jsonl", ".ndjson": "jsonl",
    ".yaml": "yaml", ".yml": "yaml",
    ".ini": "ini", ".cfg": "ini", ".conf": "ini",
}

FORMATS = ("json", "jsonl", "yaml", "ini")


class StructError(ValueError):
    pass


def detect_format(path: str, fmt: str = "") -> str:
    if fmt:
        f = fmt.strip().lower().lstrip(".")
        if f not in FORMATS:
            raise StructError(f"format 只能是 {'/'.join(FORMATS)}，收到 {fmt!r}")
        return f
    suffix = Path(path).suffix.lower()
    got = FMT_BY_SUFFIX.get(suffix)
    if not got:
        raise StructError(f"认不出 {suffix or '无后缀'} 该按什么格式写；支持 "
                          f"{sorted(set(FMT_BY_SUFFIX))}；其它请显式传 format")
    return got


pass

def parse_path(path: Any) -> list[str]:
    if isinstance(path, (list, tuple)):
        return [str(x) for x in path]
    s = str(path or "").strip()
    if s.startswith("$"):
        s = s[1:].lstrip(".")
    tokens: list[str] = []
    buf, i = "", 0
    while i < len(s):
        c = s[i]
        if c == '"':
            j = s.find('"', i + 1)
            if j < 0:
                raise StructError(f"路径引号未闭合：{path!r}")
            if buf:
                tokens.append(buf)
                buf = ""
            tokens.append(s[i + 1:j])
            i = j + 1
            if i < len(s) and s[i] == ".":
                i += 1
            continue
        if c == "[":
            j = s.find("]", i)
            if j < 0:
                raise StructError(f"路径方括号未闭合：{path!r}")
            if buf:
                tokens.append(buf)
                buf = ""
            inner = s[i + 1:j].strip()
            if inner[:1] == '"' and inner[-1:] == '"':
                inner = inner[1:-1]
            tokens.append(inner)
            i = j + 1
            if i < len(s) and s[i] == ".":
                i += 1
            continue
        if c == ".":
            if buf:
                tokens.append(buf)
                buf = ""
            i += 1
            continue
        buf += c
        i += 1
    if buf:
        tokens.append(buf)
    return tokens


def fmt_path(tokens: list[str]) -> str:
    return ".".join(tokens) if tokens else "(根)"


def _looks_index(token: str) -> bool:
    return token.lstrip("-").isdigit()


def _index(container: list, token: str) -> int:
    try:
        idx = int(token)
    except ValueError:
        raise StructError(f"列表下标必须是整数，收到 {token!r}") from None
    n = len(container)
    if idx < -n or idx > n:
        raise StructError(f"列表下标越界：{token}（当前长度 {n}；"
                          "等于长度=追加，负数从末尾数）")
    return idx


def desc(value: Any, limit: int = 60) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = repr(value)
    return text if len(text) <= limit else text[:limit] + "…"


def get_path(doc: Any, tokens: list[str]) -> Any:
    cur = doc
    for k in tokens:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        elif isinstance(cur, list) and _looks_index(k) and -len(cur) <= int(k) < len(cur):
            cur = cur[int(k)]
        else:
            raise StructError(f"路径不存在：{fmt_path(tokens)}")
    return cur


def set_path(doc: Any, tokens: list[str], value: Any) -> Any:
    if not tokens:
        return value
    if not isinstance(doc, (dict, list)):
        raise StructError(f"路径根节点是标量，无法向下写：{fmt_path(tokens)}；"
                          "要整份替换请用 op=replace")
    cur = doc
    for i, k in enumerate(tokens[:-1]):
        want_list = _looks_index(tokens[i + 1])
        if isinstance(cur, dict):
            nxt = cur.get(k)
            if nxt is None:
                nxt = cur[k] = [] if want_list else {}
            cur = nxt
        elif isinstance(cur, list):
            idx = _index(cur, k)
            if idx == len(cur):
                cur.append([] if want_list else {})
            cur = cur[idx]
        else:
            raise StructError(f"路径中途遇到标量（{desc(cur)}）：{fmt_path(tokens)}；"
                              "不会把标量自动改成容器，请确认路径或用 op=replace")
    tail = tokens[-1]
    if isinstance(cur, dict):
        cur[tail] = value
    elif isinstance(cur, list):
        idx = _index(cur, tail)
        if idx == len(cur):
            cur.append(value)
        else:
            cur[idx] = value
    else:
        raise StructError(f"路径的父节点是标量，无法写入：{fmt_path(tokens)}")
    return doc


def _squash(text: str) -> str:
    return re.sub(r"[\s_.\-]", "", str(text).lower())


def _near_keys(parent: dict, key: str) -> list[str]:
    want = _squash(key)
    if not want:
        return []
    hits = [k for k in parent
            if want in _squash(k) or _squash(k) in want]
    return hits[:5] or [k for k in parent if _squash(k)[:2] == want[:2]][:5]


def del_path(doc: Any, tokens: list[str]) -> tuple[Any, Any]:
    if not tokens:
        raise StructError("op=delete 需要 path（要删哪个键/下标）")
    parent = get_path(doc, tokens[:-1]) if len(tokens) > 1 else doc
    key = tokens[-1]
    if isinstance(parent, dict):
        if key not in parent:
            near = _near_keys(parent, key)
            hint = (f"；相近的键：{near}" if near
                    else f"；现有键：{list(parent)[:8] or '（空对象）'}")
            raise StructError(f"路径不存在：{fmt_path(tokens)}{hint}")
        return parent.pop(key), doc
    if isinstance(parent, list):
        idx = _index(parent, key)
        if idx >= len(parent):
            raise StructError(f"列表下标越界：{key}（当前长度 {len(parent)}）")
        return parent.pop(idx), doc
    raise StructError(f"路径的父节点是标量，无法删除：{fmt_path(tokens)}")


def merge_into(doc: Any, tokens: list[str], patch: Any) -> list[str]:
    if not isinstance(patch, dict):
        raise StructError(f"op=merge 的 value 必须是对象，收到 {type(patch).__name__}")
    target = get_path(doc, tokens) if tokens else doc
    if not isinstance(target, dict):
        raise StructError(f"op=merge 的目标不是对象：{fmt_path(tokens)}")
    changed: list[str] = []
    _merge(target, patch, tokens, changed)
    return changed


def _merge(target: dict, patch: dict, base: list[str], changed: list[str]) -> None:
    for k, v in patch.items():
        path = base + [str(k)]
        if isinstance(v, dict) and isinstance(target.get(k), dict):
            _merge(target[k], v, path, changed)
        else:
            target[k] = v
            changed.append(fmt_path(path))


def append_to(doc: Any, tokens: list[str], value: Any) -> int:
    target = get_path(doc, tokens) if tokens else doc
    if not isinstance(target, list):
        raise StructError(f"op=append 的目标不是列表：{fmt_path(tokens)}")
    target.append(value)
    return len(target) - 1


pass

_JSONISH = re.compile(r"^[\[{]")


def coerce_value(value: Any, *, as_string: bool = False) -> tuple[Any, str]:
    if as_string or not isinstance(value, str):
        return value, ""
    text = value.strip()
    if len(text) < 2 or not _JSONISH.match(text):
        return value, ""
    parsed, err, note = loads_lenient(text, scene="raw")
    if err or not isinstance(parsed, (dict, list)):
        return value, ""
    fix = f"（{note}）" if note else ""
    return parsed, f"value 是 JSON 字符串，已按结构写入{fix}"


def same_value(a: Any, b: Any) -> bool:
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    if isinstance(a, dict) and isinstance(b, dict):
        return list(a) == list(b) and all(same_value(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(same_value(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b


def plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {plain(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [plain(v) for v in value]
    for base in (bool, int, float, str):
        if isinstance(value, base):
            return base(value)
    return value
