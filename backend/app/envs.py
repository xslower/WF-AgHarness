from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


class EnvManager:
    def __init__(self, bindings: dict | None = None) -> None:
        pass
        self.bindings = bindings or {}

    pass

    def scan(self, workspace: str = "") -> list[dict]:
        out: list[dict] = []
        out += self._scan_conda()
        out += self._scan_uv()
        out += self._scan_local_venvs(workspace)
        out += self._scan_node()
        pass
        seen = set()
        uniq = []
        for e in out:
            key = (e["kind"], e["path"].lower())
            if key not in seen:
                seen.add(key)
                uniq.append(e)
        return uniq

    def _version_of(self, exe: str) -> str:
        try:
            r = subprocess.run([exe, "--version"], capture_output=True, text=True,
                               timeout=10, encoding="utf-8", errors="replace")
            return (r.stdout or r.stderr).strip()[:60]
        except Exception:
            return ""

    def _scan_conda(self) -> list[dict]:
        conda = shutil.which("conda")
        out = []
        if conda:
            condabin = Path(conda).parent
            envs_root = condabin.parent / "envs"
            if envs_root.is_dir():
                for d in envs_root.iterdir():
                    py = d / ("python.exe" if os.name == "nt" else "bin/python")
                    if py.is_file():
                        out.append({"kind": "python", "name": f"conda:{d.name}",
                                    "path": str(d), "python": str(py)})
            base_py = condabin.parent / ("python.exe" if os.name == "nt" else "bin/python")
            if base_py.is_file():
                out.append({"kind": "python", "name": "conda:base",
                            "path": str(condabin.parent), "python": str(base_py)})
        return out

    def _scan_uv(self) -> list[dict]:
        out = []
        for root in (Path.home() / ".venvs", Path.home() / ".local" / "share" / "uv" / "venvs"):
            if root.is_dir():
                for d in root.iterdir():
                    py = d / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
                    if py.is_file():
                        out.append({"kind": "python", "name": f"uv:{d.name}",
                                    "path": str(d), "python": str(py)})
        return out

    def _scan_local_venvs(self, workspace: str) -> list[dict]:
        out = []
        seen = set()
        roots = [Path(workspace)] if workspace else []
        for root in roots:
            if not root.is_dir():
                continue
            for d in [root] + [x for x in root.iterdir() if x.is_dir()]:
                for sub in (d / ".venv", d / "venv", d / ".server-venv"):
                    py = sub / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
                    if py.is_file() and str(sub).lower() not in seen:
                        seen.add(str(sub).lower())
                        out.append({"kind": "python",
                                    "name": f"venv:{sub.parent.name}/{sub.name}",
                                    "path": str(sub), "python": str(py)})
        return out

    def _scan_node(self) -> list[dict]:
        out = []
        node = shutil.which("node")
        if node:
            d = str(Path(node).parent)
            out.append({"kind": "node", "name": "node(系统)", "path": d})
        for p in (r"D:\Env\node", r"C:\Program Files\nodejs"):
            if Path(p).is_dir() and not any(e["path"] == p for e in out):
                out.append({"kind": "node", "name": f"node:{Path(p).name}", "path": p})
        return out

    pass

    def create_venv(self, path: str, base_python: str | None = None) -> dict:
        target = Path(path)
        if target.exists() and any(target.iterdir()):
            return {"ok": False, "error": f"目录非空: {target}"}
        base = base_python or sys.executable
        r = subprocess.run([base, "-m", "venv", str(target)],
                           capture_output=True, text=True, timeout=300,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            return {"ok": False, "error": (r.stderr or r.stdout)[-500:]}
        py = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        return {"ok": True, "path": str(target), "python": str(py)}

    pass

    def rewrite(self, command: str) -> str:
        py_dir = self.bindings.get("python", "")
        py_exe = str(Path(py_dir) / ("Scripts/python.exe" if os.name == "nt"
                                     else "bin/python")) if py_dir else ""
        node_dir = self.bindings.get("node", "")
        node_exe = str(Path(node_dir) / ("node.exe" if os.name == "nt" else "node")) if node_dir else ""
        npm_exe = str(Path(node_dir) / ("npm.cmd" if os.name == "nt" else "npm")) if node_dir else ""

        def q(p: str) -> str:
            return f'"{p}"' if " " in p else p

        if py_exe:
            command = re.sub(r'(?<![\w.\-"/])python3?(?= |$)',
                             lambda m: q(py_exe), command)
            command = re.sub(r'(?<![\w.\-"/])pip3?(?= |$)',
                             lambda m: f"{q(py_exe)} -m pip", command)
        if node_exe:
            command = re.sub(r'(?<![\w.\-"/])node(?= |$)',
                             lambda m: q(node_exe), command)
        if npm_exe:
            command = re.sub(r'(?<![\w.\-"/])npm(?= |$)',
                             lambda m: q(npm_exe), command)
        return command
