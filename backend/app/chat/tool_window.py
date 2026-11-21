from __future__ import annotations

import json
from dataclasses import dataclass

pass
pass
KEEP_RECENT = 6

pass
KEEP_TOOLS = 6

pass
pass
NOTE_EVERY = 10

pass
FOLDED_TAG = "已折叠"

pass
FOLD_NOTE = "中间过程已压缩，原文可 memory(action=history_get, ids=[{ids}]) 取回"

pass
TEST_COMMANDS = (
    "pytest", "vitest", "jest", "npm test", "npm run test",
    "yarn test", "pnpm test", "check_all.sh",
)

pass
TEST_TOOLS = frozenset({"run_command", "bash", "shell", "exec"})


def text_of(msg: dict) -> str:
    c = msg.get("content")
    if isinstance(c, list):
        return " ".join(p.get("text", "") for p in c if isinstance(p, dict))
    return str(c or "")


def has_text(msg: dict) -> bool:
    return msg.get("role") in ("user", "assistant") and bool(text_of(msg).strip())


def keep_from(messages: list[dict], keep_recent: int = KEEP_RECENT) -> int:
    seen = 0
    for i in range(len(messages) - 1, -1, -1):
        if has_text(messages[i]):
            seen += 1
            if seen >= keep_recent:
                return i
    return 0


def has_full_text_window(messages: list[dict], start: int,
                         keep_recent: int = KEEP_RECENT) -> bool:
    return sum(1 for m in messages[start:] if has_text(m)) >= keep_recent


@dataclass
class ToolGroup:

    indices: list[int]
    is_test: bool
    label: str


def is_test_call(msg: dict) -> bool:
    for tc in (msg.get("tool_calls") or []):
        fn = tc.get("function") or {}
        if fn.get("name") not in TEST_TOOLS:
            continue
        arg = fn.get("arguments") or ""
        if not isinstance(arg, str):
            arg = json.dumps(arg, ensure_ascii=False)
        if any(k in arg.lower() for k in TEST_COMMANDS):
            return True
    return False


def _call_label(msg: dict) -> str:
    names = [(tc.get("function") or {}).get("name", "tool")
             for tc in (msg.get("tool_calls") or [])]
    return "/".join(str(n) for n in names[:3]) or "tool"


def tool_groups(messages: list[dict], start: int) -> list[ToolGroup]:
    groups: list[ToolGroup] = []
    cur: ToolGroup | None = None
    for i in range(start, len(messages)):
        m = messages[i]
        if m.get("role") == "assistant" and m.get("tool_calls"):
            cur = ToolGroup([i], is_test_call(m), _call_label(m))
            groups.append(cur)
        elif m.get("role") == "tool":
            if cur is not None:
                cur.indices.append(i)
            else:
                pass
                groups.append(ToolGroup([i], False, "tool"))
        else:
            cur = None
    return groups


def _kept_indices(groups: list[ToolGroup], quota: int) -> set[int]:
    kept: set[int] = set()
    used = 0
    test_kept = False
    for g in reversed(groups):
        if g.is_test and test_kept:
            continue
        if used >= quota:
            continue
        kept.update(g.indices)
        used += 1
        if g.is_test:
            test_kept = True
    return kept


def _folded_placeholder(g: ToolGroup, verbose: bool) -> dict:
    ids = ",".join(str(i) for i in g.indices)
    head = f"[msg#{ids} 调用 {g.label} · {FOLDED_TAG}"
    if verbose:
        head += f"；{FOLD_NOTE.format(ids=ids)}"
    return {"role": "user", "content": head + "]"}


def trim_tail(messages: list[dict], start: int,
              quota: int = KEEP_TOOLS) -> list[dict]:
    groups = tool_groups(messages, start)
    if not groups:
        return list(messages[start:])
    by_index = {i: g for g in groups for i in g.indices}
    kept = _kept_indices(groups, quota)
    out: list[dict] = []
    folded_n = 0
    for i in range(start, len(messages)):
        m = messages[i]
        g = by_index.get(i)
        if g is None or i in kept:
            out.append(m)
        elif i == g.indices[0]:
            out.append(_folded_placeholder(g, folded_n % NOTE_EVERY == 0))
            folded_n += 1
        pass
    return out
