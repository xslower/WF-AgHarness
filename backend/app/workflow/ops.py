from __future__ import annotations

import difflib
import importlib.util
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ..store import layout

logger = logging.getLogger("harness.workflow.ops")


@dataclass(frozen=True)
class OpSpec:

    name: str
    fn: Callable[..., Any]
    desc: str = ""
    params: tuple[str, ...] = ()
    source: str = ""


class OpRegistry:

    def __init__(self) -> None:
        self._items: dict[str, OpSpec] = {}
        self._errors: dict[str, str] = {}

    pass
    def register(self, spec: OpSpec) -> OpSpec:
        self._items[spec.name] = spec
        return spec

    def add(self, name: str, fn: Callable[..., Any], desc: str = "",
            params: tuple[str, ...] | list[str] = (),
            source: str = "") -> OpSpec:
        return self.register(OpSpec(str(name), fn, desc, tuple(params), source))

    def fail(self, where: str, error: str) -> None:
        self._errors[where] = error

    pass
    def get(self, name: str) -> OpSpec | None:
        return self._items.get(name)

    def names(self) -> list[str]:
        return sorted(self._items)

    def errors(self) -> dict[str, str]:
        return dict(self._errors)

    def catalog(self) -> list[dict]:
        return [{"name": s.name, "desc": s.desc, "params": list(s.params),
                 "source": s.source}
                for s in sorted(self._items.values(), key=lambda s: s.name)]

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, name: object) -> bool:
        return str(name) in self._items

    pass
    def run(self, name: str, args: dict) -> tuple[Any, str]:
        spec = self._items.get(str(name))
        if spec is None:
            return None, self._missing(str(name))
        try:
            return spec.fn(**args), ""
        except TypeError as e:
            return None, (f"算子 {name} 参数不匹配（给了 {sorted(args)}，"
                          f"声明 {list(spec.params) or '未声明'}）：{e}")
        except ModuleNotFoundError as e:
            return None, (f"算子 {name} 缺少依赖模块 {e.name!r}：当前进程「"
                          f"{sys.executable}」里没有它。要么把它装进这个环境，"
                          f"要么把该算子留在 exec 节点里跑在装了它的解释器上。")
        except Exception as e:
            return None, f"算子 {name} 执行失败：{type(e).__name__}: {e}"

    def _missing(self, name: str) -> str:
        near = difflib.get_close_matches(name, list(self._items), n=3)
        head = f"未知算子 {name!r}（已有 {len(self._items)} 个"
        if near:
            head += f"；相近的：{', '.join(near)}"
        head += "）"
        if not self._errors:
            return head
        detail = "; ".join(f"{k}: {v[:120]}" for k, v in self._errors.items())
        return f"{head}；算子目录有 {len(self._errors)} 处加载失败：{detail}"


pass

pass
pass
pass
_CACHE: dict[str, tuple[tuple, OpRegistry]] = {}

pass
_MODULES: dict[str, tuple[float, Any]] = {}


def op_files(project: str | Path) -> list[Path]:
    if not project:
        return []
    out: list[Path] = []
    try:
        chain = layout.project_chain(project)
    except (OSError, ValueError):
        return []
    for p in chain:
        d = layout.project_ops_dir(p)
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.py")):
            if f.name.startswith("_"):
                continue
            if f not in out:
                out.append(f)
    return out


def ops_for(project: str | Path) -> OpRegistry:
    files = op_files(project)
    key = str(project or "")
    try:
        sig = tuple((str(f), f.stat().st_mtime) for f in files)
    except OSError:
        sig = ()
    hit = _CACHE.get(key)
    if hit is not None and hit[0] == sig:
        return hit[1]
    reg = OpRegistry()
    for f in files:
        _load_one(f, reg)
    _CACHE[key] = (sig, reg)
    return reg


def _load_one(path: Path, reg: OpRegistry) -> None:
    try:
        mod = _import_file(path)
        fn = getattr(mod, "register", None)
        if not callable(fn):
            raise AttributeError(f"{path.name} 缺少 register(reg)")
        fn(reg)
    except Exception as e:
        reg.fail(str(path), f"{type(e).__name__}: {e}")
        logger.warning("加载算子文件失败 %s: %s", path, e, exc_info=True)


def _import_file(path: Path):
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0
    got = _MODULES.get(str(path))
    if got is not None and got[0] == mtime:
        return got[1]
    modname = f"_wf_ops_{abs(hash(str(path))) % 10 ** 10}"
    spec = importlib.util.spec_from_file_location(modname, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载算子文件: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(modname, None)
        raise
    _MODULES[str(path)] = (mtime, mod)
    return mod


def reset_cache() -> None:
    _CACHE.clear()
    _MODULES.clear()


__all__ = ["OpSpec", "OpRegistry", "op_files", "ops_for", "reset_cache"]
