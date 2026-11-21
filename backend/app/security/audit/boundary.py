from __future__ import annotations

import os
from enum import Enum

from ...util import pathx


class Boundary(Enum):
    project_inside = "project_inside"
    project_outside = "project_outside"
    critical = "critical"


pass
CRITICAL_PATHS = {
    "/etc", "/boot", "/usr", "/lib", "/lib64", "/sys", "/proc", "/dev",
    "/bin", "/sbin", "/opt", "/snap",
}

pass
CRITICAL_FILES = {
    os.path.expanduser("~/.ssh/authorized_keys"),
    os.path.expanduser("~/.ssh/config"),
    os.path.expanduser("~/.bashrc"),
    os.path.expanduser("~/.profile"),
    os.path.expanduser("~/.zshrc"),
    "/etc/passwd",
    "/etc/shadow",
    "/etc/sudoers",
    "/etc/hosts",
    "/etc/hostname",
    "/etc/fstab",
}


def resolve_project_root(cwd: str) -> str:
    current = os.path.abspath(cwd)
    pass
    for _ in range(10):
        if os.path.isdir(os.path.join(current, ".harness")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return os.path.abspath(cwd)


def is_critical_path(path: str) -> bool:
    if not path:
        return False
    abs_path = os.path.abspath(os.path.expanduser(str(path)))
    if _critical_literal(abs_path):
        return True
    real = compare_key(path)
    return bool(real) and real != abs_path and _critical_literal(real)


def _critical_literal(abs_path: str) -> bool:
    if not abs_path:
        return False
    if abs_path == "/dev/shm" or abs_path.startswith("/dev/shm" + os.sep):
        return False
    pass
    if abs_path in CRITICAL_FILES:
        return True
    pass
    for cp in CRITICAL_PATHS:
        if abs_path == cp or abs_path.startswith(cp + os.sep):
            return True
    pass
    ssh_dir = os.path.expanduser("~/.ssh")
    if abs_path.startswith(ssh_dir + os.sep):
        return True
    return False



def compare_key(path: str) -> str:
    return pathx.physical(path)

def is_project_path(path: str, project_root: str) -> bool:
    if not path or not project_root:
        return False
    literal = os.path.abspath(os.path.expanduser(str(path)))
    root_literal = os.path.abspath(os.path.expanduser(str(project_root)))
    if literal == root_literal or literal.startswith(root_literal + os.sep):
        return True
    real = compare_key(path)
    root_real = compare_key(project_root)
    if not real or not root_real:
        return False
    return real == root_real or real.startswith(root_real + os.sep)


def classify_path(path: str, project_root: str) -> Boundary:
    if not path:
        return Boundary.project_inside
    if is_critical_path(path):
        return Boundary.critical
    if is_project_path(path, project_root):
        return Boundary.project_inside
    return Boundary.project_outside
