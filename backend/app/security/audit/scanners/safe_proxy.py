from __future__ import annotations

import os
import json
import pathlib


class _SafeOSProxy:
    pass
    sep = os.sep
    pathsep = os.pathsep
    devnull = os.devnull
    linesep = os.linesep if hasattr(os, "linesep") else "\n"

    def __init__(self):
        self.path = _SafeOSPathProxy()

    def __getattr__(self, name: str):
        pass
        _denied = {
            "remove", "unlink", "rmdir", "removedirs", "rename", "renames",
            "chmod", "chown", "chdir", "chroot", "link", "symlink",
            "mkdir", "makedirs", "mkfifo", "mknod",
            "system", "popen", "popen2", "popen3", "popen4",
            "execv", "execve", "execvp", "execvpe",
            "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve",
            "spawnvp", "spawnvpe",
            "open", "fdopen", "read", "write",
            "stat", "lstat", "fstat", "statvfs",
            "access", "listdir", "scandir", "walk",
            "utime", "utimes", "futimes", "futimens",
            "tmpfile", "tmpnam", "tempnam",
            "truncate", "ftruncate",
            "getcwd", "getcwdb",
            "fork", "kill", "nice", "setsid",
            "setuid", "setgid", "seteuid", "setegid",
            "setreuid", "setregid", "setgroups", "initgroups",
        }
        if name in _denied or name.startswith("_"):
            raise AttributeError(f"os.{name} 不允许在审查环境中调用")
        raise AttributeError(f"os.{name} 未注册到安全代理")


class _SafeOSPathProxy:

    def join(self, *args):
        return os.path.join(*args)

    def split(self, p):
        return os.path.split(p)

    def dirname(self, p):
        return os.path.dirname(p)

    def basename(self, p):
        return os.path.basename(p)

    def splitext(self, p):
        return os.path.splitext(p)

    def normpath(self, p):
        return os.path.normpath(p)

    def abspath(self, p):
        pass
        if p.startswith("/"):
            return os.path.normpath(p)
        return os.path.normpath("/" + p)

    def expanduser(self, p):
        if p.startswith("~"):
            return os.path.expanduser(p)
        return p

    def __getattr__(self, name: str):
        pass
        _denied = {
            "exists", "isfile", "isdir", "islink", "ismount",
            "getsize", "getmtime", "getctime", "getatime",
            "samefile", "sameopenfile", "realpath", "relpath",
            "commonpath", "commonprefix",
        }
        if name in _denied or name.startswith("_"):
            raise AttributeError(f"os.path.{name} 不允许在审查环境中调用")
        raise AttributeError(f"os.path.{name} 未注册到安全代理")


class _SafePurePosixPath(pathlib.PurePosixPath):

    def exists(self):
        raise AttributeError("Path.exists() 不允许在审查环境中调用")

    def is_file(self):
        raise AttributeError("Path.is_file() 不允许在审查环境中调用")

    def is_dir(self):
        raise AttributeError("Path.is_dir() 不允许在审查环境中调用")

    def stat(self):
        raise AttributeError("Path.stat() 不允许在审查环境中调用")

    def lstat(self):
        raise AttributeError("Path.lstat() 不允许在审查环境中调用")

    def read_text(self):
        raise AttributeError("Path.read_text() 不允许在审查环境中调用")

    def read_bytes(self):
        raise AttributeError("Path.read_bytes() 不允许在审查环境中调用")

    def write_text(self):
        raise AttributeError("Path.write_text() 不允许在审查环境中调用")

    def write_bytes(self):
        raise AttributeError("Path.write_bytes() 不允许在审查环境中调用")

    def unlink(self):
        raise AttributeError("Path.unlink() 不允许在审查环境中调用")

    def rmdir(self):
        raise AttributeError("Path.rmdir() 不允许在审查环境中调用")

    def mkdir(self):
        raise AttributeError("Path.mkdir() 不允许在审查环境中调用")

    def rename(self):
        raise AttributeError("Path.rename() 不允许在审查环境中调用")

    def open(self):
        raise AttributeError("Path.open() 不允许在审查环境中调用")

    def touch(self):
        raise AttributeError("Path.touch() 不允许在审查环境中调用")

    def glob(self):
        raise AttributeError("Path.glob() 不允许在审查环境中调用")

    def iterdir(self):
        raise AttributeError("Path.iterdir() 不允许在审查环境中调用")

    def cwd(self):
        raise AttributeError("Path.cwd() 不允许在审查环境中调用")

    def home(self):
        raise AttributeError("Path.home() 不允许在审查环境中调用")


class _SafeJSON:

    @staticmethod
    def loads(s: str, *args, **kwargs):
        return json.loads(s, *args, **kwargs)

    @staticmethod
    def dumps(obj, *args, **kwargs):
        return json.dumps(obj, *args, **kwargs)

    def __getattr__(self, name: str):
        if name in ("load", "dump"):
            raise AttributeError(f"json.{name} 需要文件句柄，不允许")
        raise AttributeError(f"json.{name} 未注册")


def build_safe_env(extra_vars: dict | None = None) -> dict:
    env = {
        "__builtins__": {},
        "os": _SafeOSProxy(),
        "os.path": _SafeOSPathProxy(),
        "Path": _SafePurePosixPath,
        "PurePath": pathlib.PurePosixPath,
        "json": _SafeJSON(),
        "str": str, "int": int, "float": float, "bool": bool,
        "list": list, "dict": dict, "tuple": tuple, "set": set,
        "len": len, "range": range, "enumerate": enumerate,
        "True": True, "False": False, "None": None,
    }
    if extra_vars:
        env.update(extra_vars)
    return env
