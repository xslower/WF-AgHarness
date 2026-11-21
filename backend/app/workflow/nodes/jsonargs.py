from __future__ import annotations

import json

from ...util.jsonfix import loads_lenient
from ..errors import WorkflowError
from .registry import NodeContext

pass
_PATH_KEYS = ("path", "dest", "file", "from", "to")
_PATH_SUFFIXES = ("_path", "_file", "_dir")


def parse_args(label: str, text: str) -> dict:
    raw = (text or "").strip() or "{}"
    try:
        args = json.loads(raw)
    except (ValueError, RecursionError) as e:
        obj, detail, _note = loads_lenient(raw, scene="raw")
        if detail or not isinstance(obj, dict):
            raise WorkflowError(f"{label} 参数 JSON 无效: {e}") from None
        return obj
    if not isinstance(args, dict):
        raise WorkflowError(f"{label} 参数必须是对象，实际是 {type(args).__name__}")
    return args


def is_path_key(key: str) -> bool:
    k = str(key).lower()
    return k in _PATH_KEYS or k.endswith(_PATH_SUFFIXES)


def sub_values(args: dict, ctx: NodeContext, vars: dict) -> dict:
    out: dict = {}
    for k, v in args.items():
        if not isinstance(v, str):
            out[k] = v
            continue
        whole = _whole_ref(v)
        if whole is not None:
            out[k] = _ref_value(whole, ctx, vars)
        else:
            out[k] = ctx.sub_path(v, vars) if is_path_key(k) else ctx.sub(v, vars)
    return out


pass
_WHOLE_REF = __import__("re").compile(r"^\s*\$\{([^}]+?)\}\s*$")


def _whole_ref(text: str) -> str | None:
    m = _WHOLE_REF.match(text)
    return m.group(1).strip() if m else None


def _ref_value(inner: str, ctx: NodeContext, vars: dict):
    ctx_vars = vars if isinstance(vars, dict) else {}
    pass
    pass
    if (ctx.extras or {}).get("native_refs") is False or \
            not ctx_vars.get("_known"):
        return ctx.sub("${" + inner + "}", vars)
    from ..expr import evaluate_value, safe_env
    from ..vars import substitute_expr
    value, err = evaluate_value(substitute_expr("${" + inner + "!raw}", vars),
                                safe_env(), {})
    if err:
        raise WorkflowError(f"参数引用 ${{{inner}}} 求值失败：{err}") from None
    return value


def load_args(label: str, node: dict, ctx: NodeContext, vars: dict) -> dict:
    return sub_values(parse_args(label, node.get("argsJson") or "{}"), ctx, vars)


__all__ = ["parse_args", "is_path_key", "sub_values", "load_args"]
