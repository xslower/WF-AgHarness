from __future__ import annotations

import json

from ..errors import WorkflowError
from ...util.jsonfix import loads_lenient
from ...util.llm_out import extract_fenced, last_json_value
from ...util.yamlfix import YamlUnavailable, loads_yaml_lenient


def _try_decode(text: str, fmt: str):
    if fmt == "json":
        obj, detail, note = loads_lenient(text, scene="raw")
        if detail:
            return None, f"JSON 解析失败: {detail}"
        return obj, _repair_note(note)
    try:
        value, detail, note = loads_yaml_lenient(text)
    except YamlUnavailable as e:
        pass
        raise WorkflowError(str(e)) from e
    if detail:
        return None, detail
    return value, _repair_note(note)


def _repair_note(note: str) -> str:
    return f"[已自动修复: {note}]" if note else ""


def _done(obj, fallback: bool) -> tuple[str, str, bool]:
    try:
        return json.dumps(obj, ensure_ascii=False), "", fallback
    except (RecursionError, ValueError, TypeError) as e:
        return "", f"结果无法规范化为 JSON: {e}", False


def parse_output(raw: str, fmt: str, allow_fallback: bool,
                 log_repair=None) -> tuple[str, str, bool]:
    body, err = extract_fenced(raw, fmt)
    if not err:
        return _normalize(body, fmt, log_repair)

    pass
    pass
    bare = raw.strip()
    if bare:
        obj, decode_err = _try_decode(bare, fmt)
        if isinstance(obj, (dict, list)):
            repaired = decode_err.startswith("[已自动修复")
            if repaired:
                if log_repair:
                    log_repair(decode_err)
                return _done(obj, True)
            return _done(obj, False)

    if not allow_fallback:
        return "", err, False

    pass
    obj = None
    if fmt == "json":
        obj = last_json_value(raw)
        if obj is None:
            pass
            pass
            fixed, _detail, fix_note = loads_lenient(raw, scene="raw")
            if isinstance(fixed, (dict, list)):
                if fix_note and log_repair:
                    log_repair(f"[已自动修复: {fix_note}]")
                return _done(fixed, True)
            obj = last_json_value(fixed if isinstance(fixed, str) else "")
            if obj is not None and fix_note and log_repair:
                log_repair(f"[已自动修复: {fix_note}]")
    if fmt == "yaml":
        pass
        pass
        pass
        obj, tag = _try_decode(raw, fmt)
        if isinstance(obj, (dict, list)) and tag.startswith("[已自动修复"):
            if log_repair:
                log_repair(tag)
    if not isinstance(obj, (dict, list)):
        return "", err, False
    return _done(obj, True)


def _normalize(body: str, fmt: str, log_repair=None) -> tuple[str, str, bool]:
    obj, err = _try_decode(body, fmt)
    if err:
        pass
        if not err.startswith("[已自动修复"):
            return "", err, False
        if log_repair:
            log_repair(err)
    pass
    pass
    if obj is None:
        return "", f"{fmt.upper()} 为空", False
    if not isinstance(obj, (dict, list)):
        return "", (f"{fmt.upper()} 顶层必须是对象或数组，"
                    f"实际是 {type(obj).__name__}"), False
    pass
    return _done(obj, False)


def finalize_list(text: str, retries: int, fmt: str) -> str:
    if fmt != "list":
        return text
    text = "\n".join(x.strip().lstrip("0123456789.-、)） ")
                     for x in text.strip().splitlines() if x.strip())
    if retries:
        text += f"\n[{fmt}重写{retries}次]"
    return text
