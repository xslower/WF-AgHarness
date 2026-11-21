from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

pass
pass
pass
pass
pass
pass
pass
pass
HISTORICAL: set[str] = {
    "docs/HANDOVER_PROVIDER_OUTBOUND.md",
    "docs/research/LEARN_WORKBUDDY.md",
    "docs/research/LEARN_WORKBUDDY_PROMPT_COMPACTION.md",
    "docs/research/LEARN_WORKBUDDY_VS_HARNESS.md",
    "docs/research/LEARN_WORKBUDDY_EVALS.md",
    # 2026-11-20：发布方案里引用的 `scripts/release/*.py` 流水线尚未实现，
    # 正文自己已写明「P2 流水线脚本待实现」。这属于计划文档，不是现状；
    # 实现后再从本集合移出并重建校验。
    "docs/RELEASE_PLAN.md",
}

pass
ROOT_PREFIXES = ("backend/", "frontend/", "scripts/", "docs/", "plugins/",
                 "data/", "projects/", "runs/")
pass
RUNTIME_ONLY = re.compile(
    r"(^|/)("
    r"data/[A-Za-z0-9_.\-]+\.(json|jsonl|db)"
    r"|plugin\.yaml|plugin\.py|manifest\.json"
    r"|spec\.json|profile\.json|theme\.json|nodes\.json"
    r"|SKILL\.md|mcp\.json|config\.json"
    r")$")

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+?)(?:#[^)]*)?\)")
CODE_RE = re.compile(r"`([A-Za-z0-9_./\-]+\.(?:py|ts|tsx|js|mjs|json|md|sh|bat|yaml|yml|html|css))`")

pass
PLACEHOLDERS = {"docs/agent/xxx.md"}


def _candidates(raw: str) -> list[Path]:
    p = raw.strip()
    if p.startswith("./"):
        p = p[2:]
    while p.startswith("../"):
        p = p[3:]
    if p.startswith("/"):
        return []
    pass
    pass
    return [ROOT / p, ROOT / "backend" / "app" / p, ROOT / "frontend" / "src" / p]


def _is_root_relative(raw: str) -> bool:
    p = raw.strip()
    while p.startswith("./"):
        p = p[2:]
    while p.startswith("../"):
        p = p[3:]
    return p.startswith(ROOT_PREFIXES) or bool(
        re.match(r"^(kernel|features|themes|ui-plugins|components)/", p))


def check_doc(path: Path) -> tuple[list[str], list[str]]:
    text = path.read_text("utf-8", errors="replace")
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    errors: list[str] = []
    notes: list[str] = []
    seen: set[str] = set()
    for rx in (LINK_RE, CODE_RE):
        for m in rx.finditer(text):
            raw = m.group(1)
            if raw in seen:
                continue
            seen.add(raw)
            if raw.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if not _is_root_relative(raw):
                continue
            if RUNTIME_ONLY.search(raw):
                continue
            if raw.strip().lstrip("./") in PLACEHOLDERS:
                continue
            if any(c.exists() for c in _candidates(raw)):
                continue
            line = text[: m.start()].count("\n") + 1
            msg = f"{rel}:{line}: 路径不存在 → {raw}"
            (notes if rel in HISTORICAL else errors).append(msg)
    return errors, notes


def main() -> int:
    errors: list[str] = []
    notes: list[str] = []
    for doc in sorted(list(DOCS.glob("*.md")) + list(DOCS.glob("agent/*.md"))
                      + list(DOCS.glob("archive/*.md"))
                      + list(DOCS.glob("research/*.md"))):
        e, n = check_doc(doc)
        errors += e
        notes += n
    if notes:
        print(f"提示（历史文档，不计错）：{len(notes)} 条")
        for n in notes[:10]:
            print("  ·", n)
        if len(notes) > 10:
            print(f"  ...另 {len(notes) - 10} 条")
        print()
    if errors:
        print(f"文档路径检查失败：{len(errors)} 条指向不存在的文件")
        for e in errors:
            print(" -", e)
        print("\n解法：改文档里的路径，或把该文档标为历史（HISTORICAL）。"
              "文档写错路径比没文档更糟 —— 读者会怀疑整个文档体系。")
        return 1
    print("文档路径检查通过（所有根相对引用都真实存在）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
