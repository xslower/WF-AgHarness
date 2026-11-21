from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend" / "app"
FRONTEND = ROOT / "frontend" / "src"

pass
BUDGETS = [
    (ROOT / "backend" / "app" / "main.py", 150, "main.py 只做 create_app"),
    # AppShell 当前 328 行（槽位 + 布局事件都还在里面），拆分前临时放宽
    (ROOT / "frontend" / "src" / "kernel" / "app" / "AppShell.tsx", 330, "AppShell 只做固定槽位"),
]

pass
DEFAULT_LIMIT = 500

FORBIDDEN_SNIPPETS = [
    # 工作流节点类型分支：Phase 3 后应消失
    ('node["type"] ==', "禁止工作流节点类型 if-else，改用 NodeRegistry"),
    ("node['type'] ==", "禁止工作流节点类型 if-else，改用 NodeRegistry"),
]

pass
pass
pass
pass
STORAGE_RULES = [
    (re.compile(r"""DATA_DIR\s*/\s*["']"""),
     "路径不许自己拼：走 app.store.layout 的寻径函数",
     {"backend/app/store/layout.py"}),
    (re.compile(r"""sqlite3\.connect\("""),
     "不许直接 sqlite3.connect：走 store.db.open_db（WAL/建目录/超时只在这里）",
     {"backend/app/store/db/base.py"}),
    (re.compile(r"""\.open\(\s*["']a["']"""),
     "不许手写追加写：走 app.util.jsonx.append_jsonl / append_text_line",
     {"backend/app/util/jsonx.py"}),
]


def check_storage() -> list[str]:
    errors: list[str] = []
    for p in BACKEND.rglob("*.py"):
        r = rel(p)
        text = p.read_text("utf-8", errors="replace")
        for pattern, why, allowed in STORAGE_RULES:
            if r in allowed:
                continue
            for m in pattern.finditer(text):
                line = text[:m.start()].count("\n") + 1
                errors.append(f"{r}:{line}: {why}")
    return errors


def line_count(p: Path) -> int:
    try:
        return sum(1 for _ in p.open("r", encoding="utf-8", errors="replace"))
    except OSError:
        return 0


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def check_budgets() -> list[str]:
    errors: list[str] = []
    for path, limit, why in BUDGETS:
        if not path.exists():
            errors.append(f"缺少文件: {rel(path)}（{why}）")
            continue
        n = line_count(path)
        if n > limit:
            errors.append(f"{rel(path)}: {n} 行 > {limit} 行（{why}）")
    for p in BACKEND.rglob("*.py"):
        if p.name == "__init__.py" or p.name == "main.py":
            continue
        n = line_count(p)
        limit = DEFAULT_LIMIT
        if n > limit:
            errors.append(f"{rel(p)}: {n} 行 > {limit} 行")
    for p in FRONTEND.rglob("*"):
        if p.suffix not in (".ts", ".tsx"):
            continue
        n = line_count(p)
        limit = DEFAULT_LIMIT
        if n > limit:
            errors.append(f"{rel(p)}: {n} 行 > {limit} 行")
    return errors


def check_tool_dir_roles() -> list[str]:
    allowed = {"fs", "web", "docs", "exec", "media.py", "orchestration.py",
               "workflow_edit.py", "workflow_help.py", "meta.py", "__init__.py"}
    banned_prefix = ("skill", "plugin", "mcp", "adapter")
    errors: list[str] = []
    tools_dir = BACKEND / "tools" / "builtin"
    if not tools_dir.is_dir():
        return [f"缺少目录: {rel(tools_dir)}"]
    for p in tools_dir.iterdir():
        if p.name in allowed or p.name == "__pycache__":
            continue
        low = p.name.lower()
        if low.startswith(banned_prefix):
            errors.append(
                f"{rel(p)}: 能力源适配器不许住工具实现目录（该去 app/skills、"
                f"app/plugins、app/mcp），见 ARCH_STYLE §R2")
    return errors


def check_no_one_off_scripts() -> list[str]:
    errors: list[str] = []
    for p in BACKEND.rglob("*.py"):
        rel_p = rel(p)
        if "_migrations" in p.parts or p.name.startswith(("migrate_", "backfill_")):
            errors.append(
                f"{rel_p}: 一次性迁移脚本不许放 app/ —— "
                f"放 backend/scripts/（产品代码零 import）")
    return errors


def check_forbidden() -> list[str]:
    errors: list[str] = []
    for p in BACKEND.rglob("*.py"):
        text = p.read_text("utf-8", errors="replace")
        for snippet, why in FORBIDDEN_SNIPPETS:
            if snippet in text:
                errors.append(f"{rel(p)}: 发现 {snippet!r}，{why}")
        pass
        if p.name == "main.py" and re.search(r"ENV_PROVIDER_PRESETS|FILTERED_IMPORT|FREE_PATTERNS", text):
            errors.append(f"{rel(p)}: 厂商规则必须迁移到 provider presets")
    return errors


def main() -> int:
    errors = (check_budgets() + check_forbidden() + check_storage()
              + check_tool_dir_roles() + check_no_one_off_scripts())
    pass
    pass
    if "--methods" in sys.argv:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "scan_frontend_methods.py"),
                        "--top", "15"], check=False)
    if errors:
        print("结构检查失败:")
        for e in errors:
            print(" -", e)
        return 1
    print("结构检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
