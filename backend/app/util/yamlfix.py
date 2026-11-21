from __future__ import annotations

import re
from typing import Any

from .jsonfix import loads_lenient
from .llm_out import yaml_tail_candidates

__all__ = ["YamlUnavailable", "loads_yaml_lenient", "yaml_available"]


class YamlUnavailable(RuntimeError):
    pass


def _module():
    try:
        import yaml
        return yaml
    except ImportError:
        return None


def yaml_available() -> bool:
    return _module() is not None


def _strict(yaml, text: str) -> tuple[Any, bool, str]:
    try:
        return yaml.safe_load(text), True, ""
    except Exception as e:
        return None, False, f"YAML 解析失败: {e}"


pass
pass
pass

def _tabs(text: str) -> tuple[str, str]:
    out = re.sub(r"(?m)^(\t+)", lambda m: "  " * len(m.group(1)), text)
    return out, "行首 tab 换成空格" if out != text else ""


def _fullwidth_colon(text: str) -> tuple[str, str]:
    lines, hit = [], False
    for line in text.splitlines(keepends=True):
        head = line.split("：", 1)[0]
        if "：" in line and ":" not in head and '"' not in head and "'" not in head:
            line = line.replace("：", ": ", 1)
            hit = True
        lines.append(line)
    return "".join(lines), "中文冒号改半角" if hit else ""


def _space_after_colon(text: str) -> tuple[str, str]:
    lines, hit = [], False
    for line in text.splitlines(keepends=True):
        if "://" in line or line.lstrip().startswith("#"):
            lines.append(line)
            continue
        fixed = re.sub(r"^(\s*[^:\s][^:\n]*):(?=\S)", r"\1: ", line, count=1)
        hit = hit or fixed != line
        lines.append(fixed)
    return "".join(lines), "冒号后补空格" if hit else ""


_FIXERS = (_tabs, _fullwidth_colon, _space_after_colon)


def _variants(text: str) -> list[tuple[str, list[str]]]:
    if text.lstrip().startswith(("{", "[")):
        return [(text, [])]
    singles: list[tuple[str, list[str]]] = []
    for fix in _FIXERS:
        cand, note = fix(text)
        if note:
            singles.append((cand, [note]))
    combined, notes = text, []
    for fix in _FIXERS:
        combined, note = fix(combined)
        if note and note not in notes:
            notes.append(note)
    out: list[tuple[str, list[str]]] = []
    if notes and combined != text:
        out.append((combined, notes))
    out.extend(reversed(singles))
    if not out:
        out.append((text, []))
    return out


def _trim_prose(tail: str) -> str:
    lines = tail.splitlines()
    keep = len(lines)
    while keep > 1:
        line = lines[keep - 1]
        if line[:1].isspace() or yaml_tail_candidates(line):
            break
        keep -= 1
    return "\n".join(lines[:keep])


def _candidates(text: str) -> list[str]:
    tails = yaml_tail_candidates(text)
    out: list[str] = []
    if tails:
        out.append(tails[0])
        trimmed = _trim_prose(tails[0])
        if trimmed != tails[0]:
            out.append(trimmed)
    pass
    pass
    if not out and text.strip():
        out.append(text)
    return list(dict.fromkeys(out))


def loads_yaml_lenient(text: str) -> tuple[Any, str, str]:
    yaml = _module()
    if yaml is None:
        raise YamlUnavailable(
            "format=yaml 需要 PyYAML：请在项目环境里执行 "
            ".venv/bin/python -m pip install pyyaml")
    s = text or ""
    pass
    pass
    if s.lstrip().startswith(("{", "[")):
        obj, jdetail, jnote = loads_lenient(s, scene="raw")
        if not jdetail and isinstance(obj, (dict, list)):
            return obj, "", jnote
        return None, jdetail or "JSON 解析失败", ""
    value, ok, detail = _strict(yaml, s)
    if ok and isinstance(value, (dict, list)):
        return value, "", ""
    scalar = value if ok else None

    for cand, notes in _variants(s):
        for piece in _candidates(cand):
            v, good, _ = _strict(yaml, piece)
            if not (good and isinstance(v, (dict, list))):
                continue
            used = list(notes)
            pass
            pass
            if piece.strip() != cand.strip():
                used.append("剥掉前后多余说明文字")
            return v, "", "、".join(used)

    pass
    pass
    obj, jdetail, jnote = loads_lenient(s, scene="raw")
    if not jdetail and isinstance(obj, (dict, list)):
        return obj, "", jnote
    if scalar is not None:
        return scalar, "", ""
    return None, detail, ""
