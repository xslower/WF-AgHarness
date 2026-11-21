from __future__ import annotations

import inspect
import re
import textwrap
from typing import Any, Callable

pass
_TYPE_MAP: dict[Any, str] = {
    str: "string", int: "integer", float: "number", bool: "boolean",
    list: "array", dict: "object",
}

_ARGS_HEADER = re.compile(r"^\s*(Args|Arguments|参数)\s*:\s*$", re.MULTILINE)
_SECTION_END = re.compile(r"^\s*(Returns|Raises|Yields|Examples?|Note|返回|异常)\s*:?\s*$",
                          re.MULTILINE)
_ARG_LINE = re.compile(r"^(\s+)(\*{0,2}\w+)\s*(?:\(([^)]*)\))?\s*:\s*(.*)$")


class SchemaError(ValueError):
    pass


def parse_docstring_args(doc: str) -> tuple[str, dict[str, str]]:
    if not doc:
        return "", {}
    text = textwrap.dedent(doc)
    m = _ARGS_HEADER.search(text)
    summary = text[: m.start()] if m else text
    summary = " ".join(line.strip() for line in summary.strip().splitlines()
                       if line.strip())
    if not m:
        return summary, {}
    rest = text[m.end():]
    end = _SECTION_END.search(rest)
    if end:
        rest = rest[: end.start()]
    params: dict[str, str] = {}
    last = ""
    for line in rest.splitlines():
        hit = _ARG_LINE.match(line)
        if hit:
            last = hit.group(2).lstrip("*")
            params[last] = hit.group(4).strip()
        elif last and line.strip():
            params[last] = (params[last] + " " + line.strip()).strip()
    return summary, params


def _type_of(annotation: Any, default: Any) -> tuple[str | None, list[str]]:
    if annotation is inspect.Parameter.empty:
        if isinstance(default, bool):
            return "boolean", []
        if isinstance(default, (int, float)):
            return "number", []
        if isinstance(default, str):
            return "string", []
        return None, []
    if isinstance(annotation, str):
        return _type_of_str(annotation, default)
    pass
    origin = getattr(annotation, "__origin__", None)
    args = list(getattr(annotation, "__args__", ()) or ())
    if origin is not None and type(None) in args:
        inner = [a for a in args if a is not type(None)]
        if len(inner) == 1:
            return _type_of(inner[0], default)
    if origin is list:
        return "array", []
    if origin is dict:
        return "object", []
    base = _TYPE_MAP.get(annotation)
    if base:
        return base, []
    name = getattr(annotation, "__name__", "")
    if name in ("List",):
        return "array", []
    if name in ("Dict",):
        return "object", []
    pass
    if str(annotation).startswith("typing.Literal") and args:
        return "string", [str(a) for a in args]
    for t, js in _TYPE_MAP.items():
        if annotation is t:
            return js, []
    return None, []


def params_from_signature(fn: Callable) -> tuple[dict[str, dict], list[str]]:
    sig = inspect.signature(fn)
    _, docargs = parse_docstring_args(inspect.getdoc(fn) or "")
    rules: dict[str, dict] = {}
    required: list[str] = []
    bad: list[str] = []
    for name, p in sig.parameters.items():
        if name in ("ctx", "self", "cls"):
            continue
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        jstype, enum = _type_of(p.annotation, p.default)
        if jstype is None:
            bad.append(name)
            continue
        rule: dict[str, Any] = {"type": jstype}
        if enum:
            rule["enum"] = enum
        if name in docargs:
            rule["description"] = docargs[name]
        rules[name] = rule
        if p.default is inspect.Parameter.empty:
            required.append(name)
    if bad:
        raise SchemaError(
            f"{getattr(fn, '__name__', 'function')} 的参数 {bad} 既没有类型注解、"
            f"也没有在 docstring 里声明类型，无法生成 schema")
    return rules, required


def build(fn: Callable, *,
          params: dict[str, dict] | None = None,
          required: list[str] | None = None) -> tuple[dict[str, dict], list[str]]:
    derived_rules, derived_required = {}, []
    if params is None:
        derived_rules, derived_required = params_from_signature(fn)
        return derived_rules, (required if required is not None else derived_required)
    rules = dict(params)
    missing = _undeclared_params(fn, set(rules))
    if missing:
        try:
            extra_rules, _ = params_from_signature(fn)
        except SchemaError:
            extra_rules = {}
        for name in missing:
            if name in extra_rules:
                rules[name] = extra_rules[name]
    if required is None:
        try:
            _, derived_required = params_from_signature(fn)
            required = [r for r in derived_required if r in rules]
        except SchemaError:
            required = []
    else:
        pass
        pass
        pass
        required = [r for r in required if r in rules]
    return rules, required


def _undeclared_params(fn: Callable, declared: set[str]) -> list[str]:
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return []
    return [n for n, p in sig.parameters.items()
            if n not in ("ctx", "self", "cls") and n not in declared
            and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)]


def missing_description(fn: Callable) -> str:
    summary, _ = parse_docstring_args(inspect.getdoc(fn) or "")
    return "" if summary else getattr(fn, "__name__", "")



pass
pass
pass
pass
pass
pass
pass
_STR_BASE = {"str": "string", "int": "integer", "float": "number",
             "bool": "boolean", "list": "array", "List": "array",
             "dict": "object", "Dict": "object"}


def _type_of_str(text: str, default: Any) -> tuple[str | None, list[str]]:
    s = text.strip().strip("'\"")
    pass
    if "|" in s:
        parts = [p.strip() for p in s.split("|")]
        rest = [p for p in parts if p not in ("None", "NoneType")]
        if len(rest) == 1:
            return _type_of_str(rest[0], default)
    if s.startswith("Optional[") and s.endswith("]"):
        return _type_of_str(s[len("Optional["):-1], default)
    if s.startswith("Literal[") and s.endswith("]"):
        items = [x.strip().strip("'\"") for x in s[len("Literal["):-1].split(",")]
        return "string", [x for x in items if x]
    pass
    for head in ("list[", "List[", "Sequence[", "Iterable["):
        if s.startswith(head):
            return "array", []
    for head in ("dict[", "Dict[", "Mapping["):
        if s.startswith(head):
            return "object", []
    if s in _STR_BASE:
        return _STR_BASE[s], []
    pass
    if default is not inspect.Parameter.empty:
        return _type_of(inspect.Parameter.empty, default)
    return None, []
