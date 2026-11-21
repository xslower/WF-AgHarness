from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "backend" / "app"

pass
L0 = {"util", "store", "event"}
L1 = {
    # 根核心服务
    "config", "envs", "checkpoints",
    # 能力域
    "provider", "skills", "mcp", "github", "security", "project", "chat",
    "tools",
}
L2 = {"agent", "workflow", "plugins", "tools.builtin"}
L3 = {"api"}
L4 = {"factory", "main", "boot"}

pass
pass
SUBLAYER = {
    "tools.builtin": 2,
}

pass
pass
ALLOWED = {
    ("app.store.layout", "app.config"):
        "惰性读 DATA_DIR/RUNTIME_DIR：config 反过来要用 layout 算自己的路径，"
        "模块级 import 会成环；已限定在 data_dir()/runtime_root() 两个函数内",
    ("app.util.timeutil", "app.provider"):
        "TYPE_CHECKING 下的类型标注，运行时不 import",
}

pass
FILENAME_MODULES = L1 | L2 | L3 | L4 | L0


def layer_of(module: str) -> int:
    for prefix, lv in sorted(SUBLAYER.items(), key=lambda kv: -len(kv[0])):
        if module == prefix or module.startswith(prefix + "."):
            return lv
    top = module.split(".")[0]
    for lv, names in ((0, L0), (1, L1), (2, L2), (3, L3), (4, L4)):
        if top in names:
            return lv
    return 1


def resolve(mod_parts: list[str], is_pkg: bool, level: int,
            module: str | None) -> str:
    pkg = mod_parts if is_pkg else mod_parts[:-1]
    if level:
        up = level - 1
        base = pkg[: len(pkg) - up] if up else pkg
    else:
        base = []
    return ".".join(base + (module.split(".") if module else []))


def source_modules() -> list[tuple[Path, str, bool]]:
    out = []
    for p in APP.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        parts = list(p.relative_to(APP).with_suffix("").parts)
        is_pkg = parts[-1] == "__init__"
        if is_pkg:
            parts = parts[:-1]
        out.append((p, ".".join(parts), is_pkg))
    return out


def _type_checking_ids(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        name = getattr(test, "id", "") or getattr(test, "attr", "")
        if name != "TYPE_CHECKING":
            continue
        for inner in node.body:
            for sub in ast.walk(inner):
                if isinstance(sub, (ast.Import, ast.ImportFrom)):
                    ids.add(id(sub))
    return ids


def scan() -> list[tuple[int, int, str, str, int]]:
    bad = []
    for path, mod, is_pkg in source_modules():
        src_layer = layer_of(mod)
        try:
            tree = ast.parse(path.read_text("utf-8", errors="replace"))
        except SyntaxError:
            continue
        type_only = _type_checking_ids(tree)
        for node in ast.walk(tree):
            if id(node) in type_only:
                continue
            targets: list[str] = []
            if isinstance(node, ast.ImportFrom):
                pass
                raw_mod = node.module or ""
                if node.level:
                    targets = [resolve(mod.split("."), is_pkg, node.level, raw_mod)]
                else:
                    targets = [raw_mod[4:] if raw_mod.startswith("app.") else ""]
            elif isinstance(node, ast.Import):
                targets = [a.name[4:] if a.name.startswith("app.") else ""
                           for a in node.names]
            for target in targets:
                if not target:
                    continue
                dst_layer = layer_of(target)
                if dst_layer <= src_layer:
                    continue
                src_full = f"app.{mod}"
                dst_full = f"app.{target}"
                if any(src_full.startswith(s) and dst_full.startswith(d)
                       for s, d in ALLOWED):
                    continue
                bad.append((src_layer, dst_layer, src_full, dst_full, node.lineno))
    return bad


def main() -> int:
    bad = scan()
    if "--matrix" in sys.argv:
        import collections
        counter: collections.Counter[tuple[str, str]] = collections.Counter()
        for p, mod, is_pkg in source_modules():
            top_src = mod.split(".")[0]
            try:
                tree = ast.parse(p.read_text("utf-8", errors="replace"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    tgts = [resolve(mod.split("."), is_pkg, node.level or 0, node.module)]
                elif isinstance(node, ast.Import):
                    tgts = [a.name for a in node.names]
                else:
                    continue
                for t in tgts:
                    if t.startswith("app.") and t[4:].split(".")[0] in FILENAME_MODULES:
                        counter[(top_src, t[4:].split(".")[0])] += 1
        print("=== import 矩阵（源 → 目标，次数）===")
        for (a, b), n in sorted(counter.items(), key=lambda x: -x[1])[:40]:
            if a != b:
                print(f"{n:4d}  {a} → {b}")
        print()

    if bad:
        print(f"分层检查失败：{len(bad)} 条反向依赖（下层 import 上层）")
        for src, dst, a, b, line in sorted(bad):
            print(f" - L{src}→L{dst}  {a}:{line}  →  {b}")
        print("\n解法：把契约下沉到 kernel/contracts.py（数据结构/Protocol），"
              "由上层实现；或把纯计算下沉到 util/store；跨域取数用注入（见 factory.py）。")
        return 1
    print("分层检查通过（无反向依赖）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
