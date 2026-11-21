from __future__ import annotations

import re
from datetime import datetime

INTERVAL_SECONDS = 600

_FULL_RE = re.compile(
    r"^\s*now[:：]\s*(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2})时(\d{1,2})分")
_TIME_RE = re.compile(r"^\s*now[:：]\s*(\d{1,2})时(\d{1,2})分")
_STRIP_RE = re.compile(
    r"^\s*now[:：]\s*(?:\d{4}年\d{1,2}月\d{1,2}日\s*)?\d{1,2}时\d{1,2}分[ \t]*\n*")


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                return str(part.get("text") or "")
    return ""


def last_marker(messages: list) -> datetime | None:
    hhmm: tuple[int, int] | None = None
    for m in reversed(messages or []):
        if not isinstance(m, dict) or m.get("role") != "user":
            continue
        text = _text_of(m.get("content"))
        full = _FULL_RE.match(text)
        if full:
            y, mo, d, h, mi = (int(x) for x in full.groups())
            if hhmm is not None:
                h, mi = hhmm
            try:
                return datetime(y, mo, d, h, mi)
            except ValueError:
                return None
        t = _TIME_RE.match(text)
        if t and hhmm is None:
            hhmm = (int(t.group(1)), int(t.group(2)))
    return None


def format_marker(when: datetime, with_date: bool) -> str:
    if with_date:
        return (f"now: {when.year}年{when.month}月{when.day}日 "
                f"{when.hour}时{when.minute}分")
    return f"now: {when.hour}时{when.minute}分"


def prefix_for(prev: datetime | None, when: datetime | None = None) -> str:
    when = when or datetime.now()
    if prev is None:
        return format_marker(when, True)
    delta = (when - prev).total_seconds()
    if 0 <= delta < INTERVAL_SECONDS:
        return ""
    return format_marker(when, when.date() != prev.date())


def inject(content: str, prev: datetime | None,
           when: datetime | None = None) -> tuple[str, str]:
    prefix = prefix_for(prev, when)
    if not prefix:
        return content, ""
    return (f"{prefix}\n\n{content}" if content else prefix), prefix


def strip_marker(content):
    if isinstance(content, str):
        return _STRIP_RE.sub("", content, count=1)
    if isinstance(content, list):
        out = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                part = {**part, "text": _STRIP_RE.sub("", str(part.get("text") or ""), count=1)}
            out.append(part)
        return out
    return content
