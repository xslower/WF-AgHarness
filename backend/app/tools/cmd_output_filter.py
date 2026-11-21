from __future__ import annotations

import os
import re

pass
_SEG_RE = re.compile(r"(\s*(?:&&|\|\||;|\|)\s*)")


def split_command(command: str) -> list[str]:
    return _SEG_RE.split(command)


def command_kind(seg: str) -> str:
    toks = seg.strip().split()
    if not toks:
        return ""
    first = os.path.basename(toks[0]).lower()
    second = toks[1].lower() if len(toks) > 1 else ""
    if first == "pytest" or (first in ("python", "python3") and second == "-m"
                             and len(toks) > 2
                             and os.path.basename(toks[2]) == "pytest"):
        return "pytest"
    if first == "tsc" or (first == "npx" and second == "tsc"):
        return "tsc"
    if first == "vitest" or (first == "npx" and second == "vitest"):
        return "vitest"
    if first == "git" and second == "log":
        return "git_log"
    return ""


def command_kinds(command: str) -> list[str]:
    kinds: list[str] = []
    for seg in split_command(command)[::2]:
        kind = command_kind(seg)
        if kind and kind not in kinds:
            kinds.append(kind)
    return kinds


pass
pass
pass
QUIET_FLAGS: dict[str, tuple[tuple[str, ...], str]] = {
    "pytest": (("-q", "--quiet", "--tb="), "-q --tb=line"),
    "tsc": (("--pretty",), "--pretty false"),
    "vitest": (("--reporter",), "--reporter=dot"),
    "git_log": (("--oneline",), "--oneline"),
}

pass
_COMMON_NOISE = tuple(re.compile(p) for p in (
    r"^\s*[.sFExXaN]+(?:\s+\[\s*\d+%\s*\])?\s*$",
    r"^\s*\S+\.py\s+[.sFExXaN\s]*(?:\[\s*\d+%\s*\])?\s*$",
    r"^\s*[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏|/\\\-]+\s*$",
    r"^\s*\[[\s=#>\-]*\]\s*\d*%?\s*$",
    r"^\s*\d+%\s*$",
    r"^\s*$",
))

pass
_PYTEST_NOISE = tuple(re.compile(p) for p in (
    r"^collecting(?:\s+\.\.\.)?\s*$",
    r"^collected\s+\d+\s+items?\s*$",
    r"^(?:rootdir|configfile|plugins|cachedir|testpaths|inifile)\s*:.*$",
    r"^platform\s+.*--\s+Python.*$",
    r"^=+\s*test session starts\s*=+\s*$",
))

_EXTRA_NOISE = {"pytest": _PYTEST_NOISE}

pass
pass
pass
_PROTECT = re.compile(
    r"FAILED|ERROR|FAILURES|ERRORS|PASSED|SKIPPED|XFAIL|XPASS|WARNING|"
    r"warnings summary|short test summary|Traceback|\bassert\b|"
    r"passed|failed|^\[exit|^\[已自动|^\[提示|^\[输出过滤|^\[后台|^\[命令超时|"
    r"^\[执行失败|完整输出|完整结果|界面展示|落盘|::|\.py:\d+|^E\s"
)

pass
_CONCLUSION = re.compile(
    r"FAILED|ERROR|PASSED|passed|failed|error|short test summary|"
    r"warnings summary|FAILURES|ERRORS|in \d+(?:\.\d+)?s"
)

pass
pass
pass
_PROGRESS_PCT = re.compile(r"(?<![\d.])(\d{1,3})\s*%")


def _noise_patterns(kinds: list[str]):
    pats = list(_COMMON_NOISE)
    for kind in kinds:
        pats.extend(_EXTRA_NOISE.get(kind, ()))
    return pats


def filter_for_llm(result: str, name: str, args: dict) -> str:
    if name != "run_command" or not isinstance(result, str):
        return result
    if not isinstance(args, dict) or args.get("meta") or args.get("background"):
        return result
    kinds = command_kinds(str(args.get("command") or ""))
    if not kinds:
        return result
    pats = _noise_patterns(kinds)
    kept: list[str] = []
    dropped = 0
    last_pct: int | None = None
    for line in result.split("\n"):
        pass
        for m in _PROGRESS_PCT.finditer(line):
            n = int(m.group(1))
            if n <= 100:
                last_pct = n
        pass
        norm = line.rsplit("\r", 1)[-1] if "\r" in line else line
        if not _PROTECT.search(norm) and any(p.match(norm) for p in pats):
            dropped += 1
            continue
        kept.append(norm)
    if not dropped:
        return result
    label = "/".join(kinds)
    parts = [f"{label} 剔除 {dropped} 行进度/头部噪声"]
    if last_pct is not None:
        parts.append(f"最后进度 {last_pct}%")
    head = "[输出过滤: " + "；".join(parts) + "]"
    if not any(_CONCLUSION.search(line) for line in kept):
        head += "；命令可能被中止或超时，没有测试结论"
    return head + "\n" + "\n".join(kept)
