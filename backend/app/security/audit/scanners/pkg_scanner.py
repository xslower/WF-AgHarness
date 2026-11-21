from __future__ import annotations

import ast
import importlib
import importlib.metadata
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from ..ast import call_name
from ..call_policy import PKG_SCAN_NAMES
from ....util.fsx import ensure_parent

logger = logging.getLogger("harness.audit.pkg")

pass
pass
_BLACKLIST_NAMES = PKG_SCAN_NAMES

pass
_KNOWN_SAFE = {
    "json", "math", "re", "datetime", "collections", "itertools",
    "functools", "typing", "enum", "dataclasses", "abc",
    "hashlib", "base64", "uuid", "csv", "textwrap", "string",
    "random", "statistics", "decimal", "fractions", "numbers",
    "copy", "pprint", "reprlib", "types", "warnings",
    "argparse", "logging", "configparser", "tomllib",
    "pathlib", "os.path", "tempfile",
    "io", "codecs", "struct", "binascii",
    "html", "xml", "urllib", "http",
    "email", "smtplib", "imaplib",
    "subprocess",
}


@dataclass
class PkgAuditResult:
    package: str
    version: str
    safe: bool
    blacklist_calls: list[str] = field(default_factory=list)
    error: str = ""


class PkgScanner:

    def __init__(self, cache_dir: str = ""):
        self._cache: dict[str, PkgAuditResult | None] = {}
        self._cache_dir = cache_dir or ""

    @property
    def cache_dir(self) -> str:
        return self._cache_dir

    @cache_dir.setter
    def cache_dir(self, value: str):
        self._cache_dir = value

    def is_safe(self, package_name: str) -> bool | None:
        pass
        if package_name.split(".")[0] in _KNOWN_SAFE:
            return True
        if package_name in _KNOWN_SAFE:
            return True

        pass
        if package_name in self._cache:
            result = self._cache[package_name]
            return result.safe if result else None

        pass
        cached = self._load_cache(package_name)
        if cached:
            self._cache[package_name] = cached
            return cached.safe

        return None

    def scan(self, package_name: str, project_root: str = "") -> PkgAuditResult:
        pass
        if package_name.split(".")[0] in _KNOWN_SAFE:
            result = PkgAuditResult(package=package_name, version="builtin", safe=True)
            self._cache[package_name] = result
            return result

        pass
        try:
            version = importlib.metadata.version(package_name)
        except Exception:
            version = "unknown"

        pass
        try:
            mod = importlib.import_module(package_name)
            pkg_path = getattr(mod, "__path__", None)
            if pkg_path:
                root = Path(pkg_path[0])
            else:
                pkg_file = getattr(mod, "__file__", None)
                if pkg_file:
                    root = Path(pkg_file).parent
                else:
                    return PkgAuditResult(
                        package=package_name, version=version,
                        safe=False, error="无法定位包路径",
                    )
        except Exception as e:
            return PkgAuditResult(
                package=package_name, version=version,
                safe=False, error=f"导入失败: {e}",
            )

        pass
        blacklist: set[str] = set()
        py_files = list(root.rglob("*.py"))
        for py_file in py_files[:200]:
            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        name = self._resolve_name(node)
                        if name and name in _BLACKLIST_NAMES:
                            blacklist.add(name)
            except Exception:
                continue

        is_safe = len(blacklist) == 0
        result = PkgAuditResult(
            package=package_name, version=version,
            safe=is_safe, blacklist_calls=sorted(blacklist),
        )

        self._cache[package_name] = result
        self._save_cache(result)
        return result

    def scan_or_load(self, package_name: str, project_root: str = "") -> PkgAuditResult:
        cached = self.is_safe(package_name)
        if cached is not None:
            if package_name in self._cache:
                return self._cache[package_name]
            pass
            return PkgAuditResult(package=package_name, version="builtin", safe=cached)
        return self.scan(package_name, project_root)

    def _resolve_name(self, node: ast.Call) -> str | None:
        return call_name(node)


    def _cache_key(self, package: str) -> str:
        return f"{package}.json"

    def _cache_path(self, package: str) -> Path | None:
        if not self._cache_dir:
            return None
        p = Path(self._cache_dir) / self._cache_key(package)
        return p

    def _load_cache(self, package: str) -> PkgAuditResult | None:
        path = self._cache_path(package)
        if not path or not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return PkgAuditResult(
                package=data["package"],
                version=data.get("version", ""),
                safe=data.get("safe", False),
                blacklist_calls=data.get("blacklist_calls", []),
                error=data.get("error", ""),
            )
        except Exception:
            return None

    def _save_cache(self, result: PkgAuditResult):
        path = self._cache_path(result.package)
        if not path:
            return
        try:
            ensure_parent(path)
            path.write_text(json.dumps({
                "package": result.package,
                "version": result.version,
                "safe": result.safe,
                "blacklist_calls": result.blacklist_calls,
                "error": result.error,
            }, ensure_ascii=False, indent=2))
        except Exception:
            logger.debug("保存包审计缓存失败", exc_info=True)
