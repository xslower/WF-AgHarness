
from __future__ import annotations

import re


pass
pass
_ORG_SEG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

pass
pass
_MODEL_STARTS = ("gpt-", "claude-", "gemini-", "o1-", "o3-", "o4-")


def normalize_model_id(mid: str) -> str:
    if not mid:
        return mid
    rest = mid
    pass
    for _ in range(6):
        head, sep, tail = rest.partition("/")
        if not sep or not tail:
            break
        if not _ORG_SEG.match(head):
            break
        if head.lower().startswith(_MODEL_STARTS):
            break
        rest = tail.lstrip("/ ")
    pass
    return rest or mid


def normalize_model_ids(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for mid in ids:
        n = normalize_model_id(mid)
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def normalize_pairs(ids: list[str]) -> list[tuple[str, str]]:
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for mid in ids:
        clean = normalize_model_id(mid)
        if not clean or clean in seen:
            continue
        seen.add(clean)
        out.append((clean, mid if clean != mid else ""))
    return out
