from __future__ import annotations

pass
_CJK_RANGES = (
    ("\u3400", "\u4dbf"),
    ("\u4e00", "\u9fff"),
    ("\uf900", "\ufaff"),
    ("\u3040", "\u30ff"),
    ("\uac00", "\ud7af"),
)

pass
ASCII_PER_TOKEN = 3

pass
pass
pass
pass
pass
IMAGE_TOKENS = 1200


def is_cjk(ch: str) -> bool:
    for lo, hi in _CJK_RANGES:
        if lo <= ch <= hi:
            return True
    return False


def estimate_text(text: str) -> int:
    if not text:
        return 0
    cjk = sum(1 for ch in text if is_cjk(ch))
    return cjk + (len(text) - cjk) // ASCII_PER_TOKEN


def estimate_obj(obj) -> int:
    total = 0
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, str):
            total += IMAGE_TOKENS if cur.startswith("data:image/") else estimate_text(cur)
        elif isinstance(cur, dict):
            stack.extend(cur.values())
        elif isinstance(cur, (list, tuple)):
            stack.extend(cur)
        elif isinstance(cur, (int, float)) and not isinstance(cur, bool):
            total += 1
    return total
