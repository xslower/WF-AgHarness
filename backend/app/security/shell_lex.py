from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass, field
from enum import Enum


class Role(str, Enum):

    CMD = "cmd"
    ENV = "env"
    ARG = "arg"
    REDIR = "redir"
    CD = "cd"
    CODE = "code"
    NAME = "name"


pass
GRADED_ROLES = frozenset({Role.ARG, Role.REDIR})


@dataclass
class Token:

    text: str
    role: Role
    seg: int = 0
    quoted: bool = False


@dataclass
class Segment:

    index: int
    tokens: list[Token] = field(default_factory=list)
    cwd: str = "."


pass
_SPLIT_RE = re.compile(r"\s*(?:&&|\|\||;|\|)\s*")
pass
_ASSIGN_RE = re.compile(r"([A-Za-z_]\w*)=(.*)", re.S)
pass
_VAR_RE = re.compile(r"\$\{?(\w+)\}?")
pass
pass
pass
_CODE_FLAGS = frozenset({"-c", "-e", "--eval"})
pass
pass
_SUBCMD_PROGS = frozenset({"git", "docker", "npm", "yarn", "pnpm", "cargo",
                          "kubectl", "go", "pip", "conda", "uv", "poetry"})
pass
pass
_ENV_WRAPPER = "env"
pass
pass
pass
_REDIR_OP_RE = re.compile(
    r"^(?:\d*|&)(?:<<?|>>?)(?:&\d+|&-)?$|^<<?$|^&>>?$|^>&\d+$"
    r"|^<<-?\s*[\"']?\w+[\"']?$")


def split_segments(text: str) -> list[str]:
    return [s for s in _SPLIT_RE.split(text or "") if s.strip()]


def subcommands(text: str) -> list[str]:
    out: list[str] = []
    depth = 0
    start = -1
    i = 0
    while i < len(text):
        two = text[i:i + 2]
        if two == "$(":
            if depth == 0:
                start = i + 2
            depth += 1
            i += 2
            continue
        if text[i] == "`":
            j = text.find("`", i + 1)
            if j > i:
                out.append(text[i + 1:j])
                i = j + 1
                continue
        if text[i] == ")" and depth:
            depth -= 1
            if depth == 0 and start >= 0:
                out.append(text[start:i])
                start = -1
        i += 1
    return [s for s in out if s.strip()]


def _tokenize(seg: str) -> list[str]:
    try:
        return shlex.split(seg, posix=True)
    except ValueError:
        return seg.split()


def _quoted_mask(seg: str) -> list[bool]:
    mask: list[bool] = []
    cur_quoted = False
    cur: list[str] = []
    quote: str | None = None
    for ch in seg:
        if quote:
            if ch == quote:
                quote = None
            else:
                cur.append(ch)
            continue
        if ch in "\"'":
            quote = ch
            cur_quoted = True
            continue
        if ch.isspace():
            if cur or cur_quoted:
                mask.append(cur_quoted)
                cur = []
                cur_quoted = False
            continue
        cur.append(ch)
    if cur or cur_quoted:
        mask.append(cur_quoted)
    return mask


def expand(token: str, env: dict[str, str],
           keep_unknown: bool = True) -> str:
    if "$" not in token:
        return token

    def rep(m: re.Match) -> str:
        name = m.group(1)
        if name in env:
            return env[name]
        val = os.environ.get(name)
        return val if val is not None else m.group(0)

    out = _VAR_RE.sub(rep, token)
    if "$" in out and not keep_unknown:
        return ""
    return out


def _subcmd_index(tokens: list[str]) -> int:
    head = 0
    while head < len(tokens) and _ASSIGN_RE.fullmatch(tokens[head]):
        head += 1
    if head >= len(tokens):
        return -1
    prog = expand(tokens[head], {}, keep_unknown=False).rsplit("/", 1)[-1]
    if prog not in _SUBCMD_PROGS:
        return -1
    i = head + 1
    while i < len(tokens) and tokens[i].startswith("-"):
        i += 1
    return i if i < len(tokens) else -1


def _role_of(prev: str, raw: str) -> Role:
    if prev in _CODE_FLAGS:
        return Role.CODE
    if prev == ">" or prev == ">>" or _REDIR_OP_RE.match(prev or ""):
        return Role.REDIR
    if _REDIR_OP_RE.match(raw or ""):
        return Role.NAME
    return Role.ARG


def parse(command: str, track_cd: bool = True) -> list[Segment]:
    segs: list[Segment] = []
    cwd = "."
    for idx, seg_text in enumerate(split_segments(command)):
        toks = _tokenize(seg_text)
        if not toks:
            continue
        masks = _quoted_mask(seg_text)
        seg = Segment(index=idx, cwd=cwd)

        def q(i: int) -> bool:
            return masks[i] if i < len(masks) else False

        pass
        pass
        local_env: dict[str, str] = {}
        head = 0
        while head < len(toks):
            m = _ASSIGN_RE.fullmatch(toks[head])
            if m:
                local_env[m.group(1)] = m.group(2).strip("\"'")
                seg.tokens.append(Token(toks[head], Role.ENV, idx, q(head)))
                head += 1
                continue
            if expand(toks[head], local_env, keep_unknown=False).rsplit(
                    "/", 1)[-1] == _ENV_WRAPPER:
                seg.tokens.append(Token(toks[head], Role.CMD, idx, q(head)))
                head += 1
                continue
            break
        if head >= len(toks):
            segs.append(seg)
            continue
        pass
        seg.tokens.append(Token(toks[head], Role.CMD, idx, q(head)))
        sub_idx = _subcmd_index(toks)
        for i in range(head + 1, len(toks)):
            role = _role_of(toks[i - 1], toks[i])
            if i == sub_idx:
                role = Role.NAME
            seg.tokens.append(Token(toks[i], role, idx, q(i)))
        segs.append(seg)

        pass
        name = expand(toks[head], local_env, keep_unknown=False).rsplit("/", 1)[-1]
        if track_cd and name == "cd" and head + 1 < len(toks):
            for t in seg.tokens[head + 1:]:
                if t.role is Role.ARG:
                    t.role = Role.CD
            target = expand(toks[head + 1], local_env, keep_unknown=False)
            if target:
                cwd = (target if os.path.isabs(target) or target.startswith("~")
                       else os.path.normpath(os.path.join(cwd, target)))
    return segs


def exec_env(segs: list[Segment]) -> dict[str, str]:
    env: dict[str, str] = {}
    for seg in segs:
        for t in seg.tokens:
            if t.role is Role.ENV:
                m = _ASSIGN_RE.fullmatch(t.text)
                if m:
                    env[m.group(1)] = m.group(2).strip("\"'")
    return env
