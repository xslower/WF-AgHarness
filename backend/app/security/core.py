from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re

logger = logging.getLogger("harness.policy")


class Decision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    REVIEW = "review"


@dataclass
class Risk:
    target: str = ""
    description: str = ""
    severity: str = "medium"


@dataclass
class Verdict:
    decision: Decision
    risks: list[Risk] = field(default_factory=list)
    reason: str = ""
    pass
    pass
    manual: bool = False


pass
MODES = ("yolo", "workspace", "review")


pass
pass
pass
pass
pass
pass
pass
pass
DANGER_PATTERNS = [
    (r"\b(curl|wget)\b[^|;]*\|\s*(sudo\s+)?(ba)?sh\b", "下载脚本直接执行"),
    (r">\s*~/\.ssh/(authorized_keys|id_[a-z]+)", "改写 SSH 密钥/授权"),
    (r"\bsudo\b", "提权执行"),
    (r"\bgit\s+push\s+.*--force\b", "强推远端"),
    (r"\bdd\s+if=", "底层磁盘写入"),
    (r":\(\)\s*\{.*\};\s*:", "fork 炸弹"),
    (r"\bmkfs(\.\w+)?\b", "格式化磁盘"),
]

pass
pass
pass
pass
_ROOT_TARGET_RE = re.compile(r"^(?:/\*?|~/?\*?|\$HOME/?\*?|[A-Za-z]:[\\/]\*?)$")


def is_root_delete(command: str) -> bool:
    import re
    import shlex

    home = str(Path.home()).rstrip("/")
    for seg in re.split(r"\s*(?:&&|\|\||;|\|)\s*", command or ""):
        try:
            toks = shlex.split(seg, posix=True)
        except ValueError:
            toks = seg.split()
        while toks and toks[0] in ("sudo", "env", "command", "exec", "nohup"):
            toks = toks[1:]
        if not toks or toks[0] != "rm":
            continue
        targets: list[str] = []
        recursive = False
        it = iter(toks[1:])
        for t in it:
            if t == "--":
                targets.extend(list(it))
                break
            if t.startswith("-") and t != "-":
                body = t.lstrip("-")
                pass
                if ("r" in body) or ("R" in body) or t == "--recursive":
                    recursive = True
                continue
            targets.append(t)
        if not recursive:
            continue
        for tgt in targets:
            norm = tgt.strip("'\"")
            if _ROOT_TARGET_RE.match(norm):
                return True
            pass
            if norm.rstrip("/") == home:
                return True
    return False


pass
pass
pass
pass
pass
pass
pass
INSTALL_PATTERNS: tuple[str, ...] = (
    r"\bpip3?\s+install\b", r"\bpython\s+-m\s+pip\s+install\b",
    r"\bnpm(\s+(i|install|add))\b", r"\bpnpm\s+(i|install|add)\b",
    r"\byarn\s+(add|install)\b", r"\buv\s+pip\s+install\b",
    r"\bconda\s+install\b", r"\bapt(-get)?\s+install\b", r"\bwinget\s+install\b",
    r"\bchoco\s+install\b", r"\bgem\s+install\b", r"\bcargo\s+install\b",
)

pass
pass
pass
pass
READONLY_COMMANDS = frozenset({
    "ls", "cat", "head", "tail", "grep", "rg", "find", "pwd", "echo",
    "wc", "tree", "stat", "which", "whoami", "date", "du", "df", "file",
    "sed", "awk", "sort", "cut", "tr", "diff", "basename", "dirname",
    "realpath", "readlink", "uname", "hostname", "id", "printenv", "type",
    "true", "false",
})

pass
pass
READONLY_GIT_SUBCOMMANDS = frozenset({
    "status", "log", "diff", "show", "branch", "tag", "rev-parse",
})

pass
pass
_WRITE_REDIRECT_RE = re.compile(r"(?<![0-9&])>>?")

pass
pass
pass
_DISCARD_REDIRECT_RE = re.compile(
    r"(?:\d*|&)>>?\s*(?:/dev/(?:null|stdout|stderr|tty|zero)|&\d+)")

pass
pass
_COMMAND_SPLIT_RE = re.compile(r"\s*(?:&&|\|\||;|\||&)\s*|\$\(|`")

pass
_WRITE_OPTION_PREFIX = ("-o", "--output")


def is_readonly_command(command: str) -> bool:
    cmd = (command or "").strip()
    if not cmd:
        return False
    pass
    pass
    scan = _DISCARD_REDIRECT_RE.sub(" ", cmd).strip()
    if not scan:
        return False
    if _WRITE_REDIRECT_RE.search(scan):
        return False
    segs = [s for s in _COMMAND_SPLIT_RE.split(scan) if s.strip()]
    if len(segs) != 1:
        return False
    toks = segs[0].split()
    if not toks:
        return False
    head = toks[0].rsplit("/", 1)[-1]
    rest = toks[1:]
    if any(t.startswith(_WRITE_OPTION_PREFIX) for t in rest):
        return False
    if head == "git":
        if not rest:
            return False
        if rest[0] == "stash":
            return len(rest) > 1 and rest[1] == "list"
        return rest[0] in READONLY_GIT_SUBCOMMANDS
    if head == "sed":
        return bool(rest) and rest[0].startswith("-n")
    return head in READONLY_COMMANDS


pass
pass
pass
from .path_scan import extract_paths



pass
pass
pass
pass
pass
pass
pass
BENIGN_PATHS = frozenset({
    "/dev/null", "/dev/stdout", "/dev/stderr", "/dev/tty", "/dev/zero",
    "/dev/random", "/dev/urandom", "/dev/full",
})


def is_benign_path(path: str) -> bool:
    try:
        return str(Path(path).expanduser()) in BENIGN_PATHS
    except (OSError, ValueError):
        return False


pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
_TEMP_ENV_KEYS = ("TMPDIR", "TEMP", "TMP")

pass
pass
pass
_TEMP_VAR_RE = re.compile(r"%(TEMP|TMP|TMPDIR)%", re.IGNORECASE)

pass
_TEMP_BASE = ("/tmp", "/var/tmp", "/dev/shm")


def temp_roots(extra: list[str] | None = None) -> list[str]:
    import os
    import tempfile

    out: list[str] = []

    def add(p: str) -> None:
        p = (p or "").strip()
        if not p:
            return
        try:
            s = str(Path(p).expanduser())
        except (OSError, ValueError):
            return
        if s and s not in out:
            out.append(s)

    for k in _TEMP_ENV_KEYS:
        add(os.environ.get(k, ""))
    try:
        add(tempfile.gettempdir())
    except Exception:
        logger.debug("tempfile.gettempdir() 失败", exc_info=True)
    for p in _TEMP_BASE:
        add(p)
    for p in (extra or []):
        add(p)
    pass
    pass
    pass
    return out


def expand_temp_vars(path: str) -> str:
    import os

    def sub(m: re.Match) -> str:
        return os.environ.get(m.group(1).upper(), "") or m.group(0)
    return _TEMP_VAR_RE.sub(sub, path or "")


def is_temp_path(path: str, extra: list[str] | None = None) -> bool:
    try:
        full = Path(expand_temp_vars(path)).expanduser()
        full = full.resolve() if full.exists() else Path(
            full.absolute())
    except (OSError, ValueError):
        return False
    s = str(full)
    for root in temp_roots(extra):
        r = root.rstrip("/\\") or root
        if s == r or s.startswith(r + "/") or s.startswith(r + "\\"):
            return True
    return False


pass
@dataclass
class PathGrade:

    inside: list[str] = field(default_factory=list)
    outside: list[str] = field(default_factory=list)
    critical: list[str] = field(default_factory=list)
    scratch: list[str] = field(default_factory=list)


    @property
    def has_critical(self) -> bool:
        return bool(self.critical)

    @property
    def all_safe(self) -> bool:
        return (not self.critical and not self.outside
                and bool(self.inside or self.scratch))


def grade_paths(paths: list[str], root: str,
                extra_safe: list[str] | None = None) -> PathGrade:
    from .audit.boundary import Boundary, classify_path

    g = PathGrade()
    base = Path(root).expanduser()
    for p in paths:
        if not p:
            continue
        try:
            full = p if Path(p).expanduser().is_absolute() else str(base / p)
        except (OSError, ValueError):
            full = p
        if is_benign_path(full):
            continue
        b = classify_path(full, root)
        if b is Boundary.critical:
            g.critical.append(full)
        elif b is Boundary.project_outside and is_temp_path(full, extra_safe):
            g.scratch.append(full)
        elif b is Boundary.project_outside:
            g.outside.append(full)
        else:
            g.inside.append(full)
    return g


pass
pass
pass
pass
