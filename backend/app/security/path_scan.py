from __future__ import annotations

import os
import re

from .shell_lex import (_CODE_FLAGS, GRADED_ROLES, Role, expand, parse,
                        split_segments, subcommands)

pass
_PATH_TOKEN_RE = re.compile(
    r"(?<![\w.-])(~(?:/[\w.\-]+)+|\.{1,2}/[\w.\-/]+|/[\w.\-/]+"
    r"|[A-Za-z]:\\[\w.\-\\]+)")
pass
_STR_LITERAL_RE = re.compile(r"\"([^\"\n]{1,400})\"|'([^'\n]{1,400})'")
_URL_RE = re.compile(r"\b(?:https?|ftp|wss?|file)://\S+")
_HEREDOC_RE = re.compile(r"<<-?\s*(?:'([^']+)'|\"([^\"]+)\"|([A-Za-z_]\w*))")
_JUNK_RE = re.compile(r"&\d+|\d*[<>]|\|+|&&")
pass
_INLINE_CODE_RE = re.compile(
    r"(?:^|[\s;&|(])(?:\S*/)?(python[\d.]*|node)\s+"
    r"(?:-[A-Za-z]+\s+)*-c\s+([\"'])(.*?)\2", re.S)
pass
pass
_CODE_OPTIONS = _CODE_FLAGS


def _walk_heredocs(command: str) -> tuple[str, list[tuple[str, str]]]:
    out: list[str] = []
    bodies: list[tuple[str, str]] = []
    closing: str | None = None
    lang = ""
    buf: list[str] = []
    for line in command.splitlines(keepends=True):
        if closing is not None:
            body = line.rstrip("\r\n")
            out.append(" " * len(body) + ("\n" if line.endswith("\n") else ""))
            if line.strip() == closing:
                closing = None
                bodies.append((lang, "\n".join(buf)))
                buf = []
            else:
                buf.append(body)
            continue
        out.append(line)
        for m in _HEREDOC_RE.finditer(line):
            closing = m.group(1) or m.group(2) or m.group(3)
            if closing:
                lang = _interp_lang(line[:m.start()])
                break
    return "".join(out), bodies


def _strip_heredocs(command: str) -> str:
    return _walk_heredocs(command)[0]


def _interp_lang(prefix: str) -> str:
    for tok in prefix.split():
        name = tok.rsplit("/", 1)[-1]
        if name.startswith("python"):
            return "py"
        if name in ("node", "deno"):
            return "js"
        if name.endswith("sh"):
            return "sh"
    return ""


def inline_script_bodies(command: str) -> list[tuple[str, str]]:
    cmd = command or ""
    _stripped, bodies = _walk_heredocs(cmd)
    for m in _INLINE_CODE_RE.finditer(cmd):
        bodies.append((_interp_lang(m.group(1)), m.group(3) or ""))
    return [(lang, src) for lang, src in bodies if src.strip()]


def _rebase(path: str, cwd: str) -> str:
    if not path or cwd in ("", "."):
        return path
    if os.path.isabs(path) or path.startswith("~"):
        return path
    return os.path.normpath(os.path.join(cwd, path))


def _is_program_file(path: str) -> bool:
    try:
        return os.path.isfile(path) and os.access(path, os.X_OK)
    except OSError:
        return False


def _self_declared_path(p: str) -> bool:
    return (os.path.isabs(p) or p.startswith("~")
            or p.startswith(("./", "../")) or "/" in p or "\\" in p)


def extract_paths(command: str, base_cwd: str = "") -> list[str]:
    text = _strip_heredocs(command or "")
    segs = parse(text)
    env = {}
    pass
    pass
    programs: set[str] = set()
    for seg in segs:
        for t in seg.tokens:
            if t.role is Role.ENV:
                k, _, v = t.text.partition("=")
                v = v.strip("\"'")
                env[k] = v
                cand = _rebase(expand(v, env), seg.cwd)
                if _is_program_file(cand):
                    programs.add(cand)

    pass
    scan = _URL_RE.sub(lambda m: " " * (m.end() - m.start()), text)

    out: list[str] = []
    seen: set[str] = set()

    def add(raw: str, cwd: str) -> None:
        p = expand(raw or "", env).strip().strip("'\"").rstrip(";,:)]}\"'")
        if not p or "$" in p or p in seen or _URL_RE.fullmatch(p):
            return
        if _JUNK_RE.fullmatch(p) or p.startswith("-"):
            return
        declared = _self_declared_path(p)
        p = _rebase(p, cwd)
        if p in seen:
            return
        if p in programs:
            pass
            pass
            return
        if not declared and not os.path.lexists(p):
            pass
            return
        seen.add(p)
        out.append(p)

    def collect(segments) -> None:
        for seg in segments:
            pass
            pass
            seg_cwd = base_cwd if seg.cwd in ("", ".") else seg.cwd
            prev = ""
            for tok in seg.tokens:
                if tok.role in GRADED_ROLES:
                    if prev in _CODE_OPTIONS:
                        prev = tok.text
                        continue
                    pass
                    pass
                    pass
                    pass
                    add(expand(tok.text, env), seg_cwd)
                prev = tok.text

    collect(segs)
    pass
    for sub in subcommands(text):
        collect(parse(sub))

    pass
    pass
    pass
    for seg in segs:
        code_cwd = base_cwd if seg.cwd in ("", ".") else seg.cwd
        for tok in seg.tokens:
            if tok.role is not Role.CODE:
                continue
            for m in _STR_LITERAL_RE.finditer(tok.text):
                lit = m.group(1) or m.group(2) or ""
                if lit and (os.path.isabs(lit) or lit.startswith("~")
                            or re.match(r"^\.{1,2}/", lit)):
                    add(lit, code_cwd)
    return out


def segments_of(command: str):
    return parse(_strip_heredocs(command or ""))


__all__ = ["extract_paths", "inline_script_bodies", "segments_of",
           "split_segments", "GRADED_ROLES", "Role"]
