from __future__ import annotations
import json
import re
import time
from pathlib import Path

from .errors import WorkflowError
from ..util.jsonfix import loads_lenient
pass
INLINE_OUTPUT_LIMIT = 12000


def _stat_bytes(path: str) -> str | None:
    try:
        return str(Path(path).stat().st_size)
    except OSError:
        return None


def _walk_path(val, path: str):
    for part in path.split("."):
        if isinstance(val, dict):
            val = val.get(part)
        elif isinstance(val, list):
            try:
                val = val[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return val


def _from_output(vars: dict, base: str, path: str):
    meta = (vars.get("output_paths") or {}).get(base)
    if meta:
        if path == "path":
            return meta
        if path == "bytes":
            return _stat_bytes(meta)
    val = vars.get("outputs", {}).get(base)
    if isinstance(val, str):
        try:
            val = json.loads(val)
        except (ValueError, RecursionError):
            pass
            pass
            fixed, detail, _note = loads_lenient(val, scene="raw")
            if detail:
                return None
            val = fixed
    return _walk_path(val, path)


def _lookup(vars: dict, key: str):
    ins, outs = vars.get("inputs", {}), vars.get("outputs", {})
    if key == "inputs":
        pass
        return ins or None
    if key.startswith("inputs."):
        return ins.get(key[7:])
    if key in outs:
        return outs[key]
    if "." in key:
        base, _, path = key.partition(".")
        return _from_output(vars, base, path)
    return None


def _output_reference(key: str, text: str, path: str) -> str:
    preview = text[:1200]
    lines = text.count("\n") + 1
    return (
        f"[节点 {key} 的输出已落盘：下面是文件引用，不是内容]\n"
        f"文件: {path}\n"
        f"共 {len(text)} 字符 / {lines} 行\n"
        f"--- 开头预览（仅供判断内容类型与结构）---\n{preview}\n"
        f"--- 预览结束 ---\n"
        f"需要完整或后续内容时，用工具自己取："
        f"f_read(path=\"{path}\", lines=\"A,B\")."
        f"不要假设全文已在上面，也不要在未读取前引用具体细节。"
    )


def substitute(text: str, vars: dict, long_ref: bool = False,
               clean: bool = False) -> str:
    def repl(m: re.Match) -> str:
        key, filt = _split_filter(m.group(1).strip())
        val = _lookup(vars, key)
        if val is None and not _missing_or_none(key, vars):
            raise WorkflowError(_missing_var_message(key, vars))
        if filt == "json":
            return json.dumps("" if val is None else str(val), ensure_ascii=False)
        if filt == "py":
            return repr("" if val is None else str(val))
        if filt == "url":
            from urllib.parse import quote
            return quote("" if val is None else str(val))
        if filt == "raw":
            val = _raw_value(val) if isinstance(val, str) else val
        if isinstance(val, (dict, list)):
            val = json.dumps(val, ensure_ascii=False)
        text_val = "" if val is None else str(val)
        if clean:
            text_val = _unquote_scalar(text_val)
            if isinstance(val, (dict, list)):
                return text_val
        paths = vars.get("output_paths") or {}
        if long_ref and "." not in key and len(text_val) > INLINE_OUTPUT_LIMIT:
            path = paths.get(key)
            if path:
                return _output_reference(key, text_val, str(path))
        return text_val

    pass
    guarded = str(text).replace("$${", "\x00{")
    out = re.sub(r"\$\{([^}]+?)\}", repl, guarded)
    return out.replace("\x00{", "${")


_SOFT_MISSING = {"prev", "__item__", "__i__", "__final__"}
_FILTERS = ("raw", "json", "py", "url")


def _split_filter(inner: str) -> tuple[str, str]:
    for sep in ("!", "|"):
        if sep in inner:
            head, _, tail = inner.rpartition(sep)
            if tail.strip() in _FILTERS:
                return head.strip(), tail.strip()
    return inner, ""


def _missing_var_message(key: str, vars: dict) -> str:
    import difflib
    known = set((vars.get("outputs") or {}).keys())
    known |= {f"inputs.{k}" for k in (vars.get("inputs") or {})}
    known |= _SOFT_MISSING
    near = difflib.get_close_matches(key, sorted(known), n=1)
    hint = f"；是不是「{near[0]}」？" if near else ""
    shown = ", ".join(sorted(x for x in known if x)[:20])
    return (f"未定义的变量 ${{{key}}}{hint}（已产出：{shown or '无'}）。"
            "拼错就改名，文档里想写字面量请用 $${}")


def _unquote_scalar(text: str) -> str:
    t = text.strip()
    if len(t) >= 2 and t[0] == '"' and t[-1] == '"':
        try:
            v = json.loads(t)
        except (ValueError, RecursionError):
            return text
        return str(v) if isinstance(v, str) else text
    return text


def _raw_value(val):
    if not isinstance(val, str):
        return val
    t = val.strip()
    if not t:
        return val
    pass
    if t[0] in "[{\"" or t in ("true", "false", "null") \
            or re.fullmatch(r"-?\d+(\.\d+)?", t):
        try:
            return json.loads(t)
        except (ValueError, RecursionError):
            pass
    pass
    from .expr import parse_any
    return parse_any(t, t)


def _is_known(key: str, vars: dict) -> bool:
    known = vars.get("_known") or set()
    if key in known:
        return True
    base = key.split(".")[0]
    if base in known:
        return True
    if key.startswith("inputs.") and "inputs" in known:
        return True
    return False


def _missing_or_none(key: str, vars: dict) -> bool:
    return key in _SOFT_MISSING or _is_known(key, vars)


def substitute_expr(expr: str, vars: dict) -> str:
    def repl(m: re.Match) -> str:
        inner = m.group(1).strip()
        key, filt = _split_filter(inner)
        val = _lookup(vars, key)
        if val is None and not _missing_or_none(key, vars):
            raise WorkflowError(_missing_var_message(key, vars))
        if filt == "raw":
            return repr(_raw_value(val))
        if filt == "json":
            return repr(json.dumps("" if val is None else str(val), ensure_ascii=False))
        if isinstance(val, (dict, list)):
            val = json.dumps(val, ensure_ascii=False)
        return repr(str("" if val is None else val))

    guarded = str(expr).replace("$${", "\x00{")
    out = re.sub(r"\$\{([^}]+?)\}", repl, guarded)
    return out.replace("\x00{", "${")


def _log_json_error(wf_name: str, node_id: str, attempt: int,
                    err: str, output: str, no_fence: bool = False,
                    used_fallback: bool = False) -> None:
    from . import DATA_DIR
    from ..util.jsonx import append_text_line
    from ..store.layout import JSON_ERROR_LOG
    append_text_line(
        DATA_DIR / JSON_ERROR_LOG,
        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] wf={wf_name} "
        f"node={node_id} attempt={attempt} err={err} "
        f"no_fence={int(no_fence)} used_fallback={int(used_fallback)} "
        f"len={len(output)} output={output[:500]!r}")
