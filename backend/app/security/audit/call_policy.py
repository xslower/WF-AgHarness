from __future__ import annotations

pass
pass
BLACKLIST: list[tuple[str, str, int, list[int]]] = [
    # 写操作
    ("open", "open", 1, [0]),
    ("io.open", "io.open", 1, [0]),
    ("pathlib.Path.write_text", "pathlib.Path.write_text", 1, []),
    ("pathlib.Path.write_bytes", "pathlib.Path.write_bytes", 1, []),
    ("file.write", "file.write", 0, []),
    ("file.writelines", "file.writelines", 0, []),
    # 删除操作
    ("os.remove", "os.remove", 1, [0]),
    ("os.unlink", "os.unlink", 1, [0]),
    ("pathlib.Path.unlink", "pathlib.Path.unlink", 1, []),
    ("shutil.rmtree", "shutil.rmtree", 1, [0]),
    ("os.rmdir", "os.rmdir", 1, [0]),
    ("os.removedirs", "os.removedirs", 1, [0]),
    # 移动/权限
    ("shutil.move", "shutil.move", 2, [0, 1]),
    ("os.chmod", "os.chmod", 1, [0]),
    ("os.chown", "os.chown", 1, [0]),
]

pass
FORBIDDEN_CALLS: list[tuple[str, str]] = [
    ("os.system", "os.system"),
    ("os.popen", "os.popen"),
    ("subprocess.run", "subprocess.run"),
    ("subprocess.Popen", "subprocess.Popen"),
    ("subprocess.call", "subprocess.call"),
    ("subprocess.check_output", "subprocess.check_output"),
    ("subprocess.check_call", "subprocess.check_call"),
    ("exec", "exec"),
    ("eval", "eval"),
    ("compile", "compile"),
    ("ctypes.CDLL", "ctypes.CDLL"),
    ("ctypes.WinDLL", "ctypes.WinDLL"),
]

BLACKLIST_NAMES: frozenset[str] = frozenset(name for name, *_ in BLACKLIST)
FORBIDDEN_NAMES: frozenset[str] = frozenset(name for name, _ in FORBIDDEN_CALLS)

pass
PKG_SCAN_NAMES: frozenset[str] = frozenset({
    "os.remove", "os.unlink", "os.rmdir", "os.removedirs",
    "shutil.rmtree", "shutil.move",
    "os.chmod", "os.chown",
})
assert PKG_SCAN_NAMES <= BLACKLIST_NAMES, "包扫描名单必须是全量名单的子集"
