from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .jsonfix_common import (_CTRL, _STATS, _STRIP_COMMENT, _bump, _coerce_literals,
                             _drop_trailing_commas, _fix_string_literals, _try_load,
                             _try_load5, close_open_structs, json_error_detail,
                             logger, reset_stats, stats, strip_fences)
from .jsonfix_scenes import (
    ScenePolicy, _POLICIES, _TOOL_SCENE, _policy, drop_incomplete_tail,
    repair_long_value, scene_for_tool,
)

__all__ = ["ScenePolicy", "RepairResult", "close_open_structs",
           "drop_incomplete_tail", "json_error_detail", "loads_lenient",
           "parse_tool_args", "parse_tool_args_report", "repair",
           "repair_long_value", "scene_for_tool", "stats", "reset_stats",
           "valid_tool_args"]

pass
pass
pass


@dataclass(slots=True)
class RepairResult:
    value: Any = None
    detail: str = ""
    note: str = ""
    level: str = "ok"
    dropped: int = 0

    @property
    def ok(self) -> bool:
        return self.level != "failed"

def repair(text: str, *, scene: str = "raw") -> RepairResult:
    raw = text or ""
    v, ok = _try_load5(raw)
    if ok:
        if _had_json5_features(raw):
            notes5 = _json5_note(raw)
            _bump("fixed:json5")
            return RepairResult(value=v, note=notes5, level="fixed")
        return RepairResult(value=v)
    pass
    pass
    pass
    try:
        return RepairResult(value=json.loads(raw))
    except (ValueError, RecursionError) as e:
        detail = json_error_detail(e, raw)

    pol = _policy(scene)
    notes: list[str] = []

    pass
    base, note = strip_fences(raw)
    if note:
        notes.append(note)
        v, ok = _try_load(base)
        if ok:
            return _fixed(v, notes, scene, raw)
        pass
        pass
        pass
        v2, ok2 = _try_load5(base)
        if ok2:
            n5 = _json5_note(base)
            if n5:
                notes.append(n5)
            return _fixed(v2, notes, scene, raw)

    pass
    for cand, n2 in ((base, ""),):
        fixed, why = repair_long_value(cand, pol.long_keys)
        if fixed:
            v, ok = _try_load(fixed)
            if ok:
                notes.append(why)
                return _fixed(v, notes, scene, raw)
            notes.append(why + "（仍不合法）")

    pass
    ladder: list[tuple[str, str]] = []
    s1, hit = _fix_string_literals(base)
    if hit:
        ladder.append((s1, "转义字符串内的裸引号/换行/反斜杠"))
    s2, hit = _coerce_literals(s1)
    if hit:
        ladder.append((s2, "True/False/None 改小写"))
    for cand, why in ladder:
        for step, s, w in _close_variants(cand):
            v, ok = _try_load(s)
            if ok:
                notes.append(why)
                notes.append(w)
                return _fixed(v, notes, scene, raw)

    pass
    s3, hit = _fix_string_literals(base)
    s4, hit4 = _drop_trailing_commas(s3)
    s5, hit5 = close_open_structs(s4)
    if hit or hit4 or hit5:
        v, ok = _try_load(s5)
        if ok:
            notes.append("转义 + 去尾逗号 + 补结构符")
            return _fixed(v, notes, scene, raw)

    pass
    if pol.drop_tail:
        fixed, why, dropped = drop_incomplete_tail(base)
        if fixed:
            v, ok = _try_load(fixed)
            if ok:
                notes.append(why)
                r = _fixed(v, notes, scene, raw)
                r.level = "salvaged"
                r.dropped = dropped
                return r

    pass
    if notes:
        detail += ("（已尝试自动修正：" + "、".join(notes) +
                   "，仍无法解析：多半是内容被输出长度截断、不全，"
                   "请拆小这次调用后重发，不要原样重试）")
    _bump(f"fail:{scene}")
    return RepairResult(detail=detail, note="、".join(notes), level="failed")

def _json5_features(raw: str) -> tuple[bool, bool]:
    _, comma = _drop_trailing_commas(raw)
    outside = _STRIP_COMMENT.sub(
        lambda m: " " * len(m.group(1)) if m.group(1) else m.group(0), raw)
    return comma, ("//" in outside or "/*" in outside)


def _had_json5_features(raw: str) -> bool:
    return any(_json5_features(raw))


def _json5_note(raw: str) -> str:
    comma, comment = _json5_features(raw)
    notes = [x for x, hit in (("去掉末尾多余逗号", comma),
                              ("去掉注释", comment)) if hit]
    return "、".join(notes) or "宽松语法修正"

def _close_variants(text: str) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = [(text, text, "")]
    s, hit = _drop_trailing_commas(text)
    if hit:
        out.append((text, s, "去掉多余的尾逗号"))
    closed, why = close_open_structs(s)
    if closed:
        out.append((text, closed, why))
    return out

def _fixed(value: Any, notes: list[str], scene: str, raw: str = "") -> RepairResult:
    pass
    seen: list[str] = []
    for x in notes:
        if x and x not in seen:
            seen.append(x)
    note = "、".join(seen)
    _bump(f"fixed:{scene}")
    logger.warning("模型输出 JSON 已自动修正（场景 %s：%s），原文片段: %r",
                   scene, note, (raw or "")[:160])
    return RepairResult(value=value, note=note, level="fixed")

pass
pass
pass


def loads_lenient(text: str, *, scene: str = "raw") -> tuple[Any, str, str]:
    r = repair(text, scene=scene)
    if r.level == "failed":
        return None, r.detail, r.note
    return r.value, "", r.note

def parse_tool_args(text: str, *, scene: str = "args") -> tuple[dict, str]:
    r = repair(text or "{}", scene=scene)
    if r.level == "failed":
        return {}, r.detail
    if not isinstance(r.value, dict):
        return {}, (f"参数必须是 JSON 对象（形如 {{\"path\": \"x\"}}），"
                    f"实际是 {type(r.value).__name__}：{repr((text or '')[:120])}")
    return r.value, ""

def parse_tool_args_report(text: str, *, scene: str = "args") -> tuple[dict, str, str]:
    r = repair(text or "{}", scene=scene)
    if r.level == "failed":
        return {}, r.detail, ""
    if not isinstance(r.value, dict):
        return {}, (f"参数必须是 JSON 对象（形如 {{\"path\": \"x\"}}），"
                    f"实际是 {type(r.value).__name__}：{repr((text or '')[:120])}"), ""
    return r.value, "", r.note

def valid_tool_args(raw: Any) -> bool:
    if not isinstance(raw, str):
        return False
    try:
        return isinstance(json.loads(raw), dict)
    except (ValueError, TypeError, RecursionError):
        return False
