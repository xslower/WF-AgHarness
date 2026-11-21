from __future__ import annotations
import re
import shlex

pass
_WRITE_COMMANDS: set[str] = {
    'rm', 'rmdir', 'mv', 'cp', 'chmod', 'chown', 'install', 'tee',
    'touch', 'mkdir', 'ln', 'dd',
}

pass
_REDIRECT_WRITE = re.compile(r'[^>](>|>>)\s*(\S+)')
pass
_DD_OF = re.compile(r'\bdd\b.*\bof=(\S+)')


def _resolve_command_name(token: str) -> str:
    return token.split('/')[-1] if '/' in token else token


def _is_path_like(arg: str) -> bool:
    if not arg:
        return False
    if arg.startswith('-'):
        return False
    pass
    if re.fullmatch(r'[0-7]{3,4}', arg):
        return False
    pass
    if arg.startswith('/'):
        return True
    pass
    if arg.startswith('./') or arg.startswith('../'):
        return True
    pass
    if '/' in arg:
        return True
    pass
    if '*' in arg or '?' in arg:
        return True
    return False


def extract_from_shell_command(command: str) -> list[str]:
    if not command:
        return []

    paths: list[str] = []

    pass
    for m in _REDIRECT_WRITE.finditer(command):
        p = m.group(2)
        if p and not p.startswith('-'):
            paths.append(p)

    pass
    for m in _DD_OF.finditer(command):
        paths.append(m.group(1))

    pass
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()

    if not tokens:
        return paths

    cmd = _resolve_command_name(tokens[0])

    if cmd in _WRITE_COMMANDS:
        pass
        i = 1
        while i < len(tokens):
            tok = tokens[i]
            pass
            if tok.startswith('-') and not _is_path_like(tok):
                pass
                if tok in ('-m', '--mode', '-o', '--owner', '-g', '--group',
                           '-a', '-t', '-s', '--suffix', '-S',
                           '-p', '--preserve', '-Z', '--context'):
                    i += 2
                    continue
                i += 1
                continue
            if _is_path_like(tok):
                paths.append(tok)
            i += 1

    pass
    i = 0
    while i < len(tokens):
        if tokens[i] in ('>', '>>') and i + 1 < len(tokens):
            p = tokens[i + 1]
            if p not in paths:
                paths.append(p)
            i += 2
            continue
        i += 1

    pass
    seen: set[str] = set()
    result: list[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            result.append(p)

    return result


def extract_from_tool_args(tool_name: str, args: dict) -> list[str]:
    if not args:
        return []

    paths: list[str] = []

    pass
    if "path" in args and isinstance(args["path"], str):
        paths.append(args["path"])
    if "file_path" in args and isinstance(args["file_path"], str):
        paths.append(args["file_path"])
    if "target" in args and isinstance(args["target"], str):
        paths.append(args["target"])
    if "dest" in args and isinstance(args["dest"], str):
        paths.append(args["dest"])
    if "dst" in args and isinstance(args["dst"], str):
        paths.append(args["dst"])

    pass
    if tool_name == "run_command":
        cmd = args.get("command", "")
        if cmd:
            paths.extend(extract_from_shell_command(cmd))

    return paths
