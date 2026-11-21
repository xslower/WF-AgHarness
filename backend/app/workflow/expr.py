from __future__ import annotations

import json
import re
from typing import Any

from ..util.jsonfix import loads_lenient
from ..util.yamlfix import YamlUnavailable, loads_yaml_lenient

pass
_HELPERS: dict[str, Any] = {
    "len": len, "str": str, "int": int, "float": float, "bool": bool,
    "list": list, "dict": dict, "tuple": tuple, "set": set,
    "abs": abs, "min": min, "max": max, "sum": sum, "sorted": sorted,
    "any": any, "all": all, "round": round,
    "enumerate": enumerate, "range": range,
}


def _strip_exit_prefix(text: str) -> str:
    s = text.lstrip()
    m = re.match(r"^\[exit\s*-?\d+\]\s*\n?", s)
    return s[m.end():] if m else text


def json_value(text: Any, default: Any = None) -> Any:
    if isinstance(text, (dict, list)):
        return text
    try:
        return json.loads(_strip_exit_prefix(str(text)))
    except (ValueError, TypeError, RecursionError):
        pass
    obj, _detail, _note = loads_lenient(str(text or ""), scene="raw")
    return obj if obj is not None else default


def _looks_structured(text: str) -> bool:
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("- ") or s == "-" or s.startswith("---"):
            return True
        if re.match(r"^[\w\u4e00-\u9fff.\-\"']+\s*[:：](\s|$)", s) and \
                " " not in re.split(r"[:：]", s)[0].strip():
            return True
    return False


def yaml_value(text: Any, default: Any = None) -> Any:
    if isinstance(text, (dict, list)):
        return text
    s = _strip_exit_prefix(str(text or ""))
    parsed = json_value(s, None)
    if parsed is not None:
        return parsed
    if not _looks_structured(s):
        return default
    try:
        value, detail, _note = loads_yaml_lenient(s)
    except YamlUnavailable:
        return default
    return default if detail else value


def parse_any(text: Any, default: Any = None) -> Any:
    if not isinstance(text, str):
        return text
    cleaned = _strip_exit_prefix(text)
    if not cleaned.strip():
        return text
    parsed = json_value(cleaned, None)
    if parsed is not None:
        return parsed
    pass
    return yaml_value(cleaned, default if default is not None else cleaned)


_TRUE_WORDS = {"1", "true", "yes", "y", "on", "ok", "pass", "通过",
               "是", "真", "批准", "成功"}


def boolv(text: Any) -> bool:
    if isinstance(text, bool):
        return text
    if isinstance(text, (int, float)):
        return text != 0
    s = str(text or "").strip().lower()
    if not s:
        return False
    if s in _TRUE_WORDS:
        return True
    head = re.split(r"[\s:：,，。;；]", s, maxsplit=1)[0]
    return head in _TRUE_WORDS


def num(text: Any, default: float = 0) -> float:
    try:
        return float(text)
    except (TypeError, ValueError):
        m = re.match(r"\s*-?\d+(\.\d+)?", str(text or ""))
        return float(m.group(0)) if m else default


def get_path(obj: Any, path: str, default: Any = None) -> Any:
    cur = json_value(obj, default) if isinstance(obj, str) else obj
    for part in str(path or "").split("."):
        if part == "":
            continue
        if isinstance(cur, dict):
            cur = cur.get(part, default)
        elif isinstance(cur, (list, tuple)):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return default
        else:
            return default
    return cur


def match(pattern: str, text: Any) -> bool:
    try:
        return re.search(str(pattern), str(text or "")) is not None
    except re.error:
        return False


def _json_ns() -> Any:
    def _parse(text: Any, default: Any = None) -> Any:
        return json_value(text, default)
    _parse.loads = json.loads
    _parse.dumps = json.dumps
    return _parse


def safe_env() -> dict:
    env = dict(_HELPERS)
    env.update({"json": _json_ns(), "yaml": yaml_value, "re": re,
                "boolv": boolv, "num": num, "get": get_path,
                "match": match, "contains": lambda a, b: b in a})
    return env


def evaluate_value(expr: str, env: dict, values: dict) -> tuple[Any, str]:
    namespace = {"__builtins__": {}, **env}
    try:
        return eval(expr, namespace, values), ""
    except Exception as e:
        return None, f"{type(e).__name__}: {e}（表达式: {expr}）"


def evaluate(expr: str, env: dict, values: dict) -> tuple[bool, str]:
    namespace = {"__builtins__": {}, **env}
    try:
        return bool(eval(expr, namespace, values)), ""
    except Exception as e:
        return False, f"{type(e).__name__}: {e}（表达式: {expr}）"
