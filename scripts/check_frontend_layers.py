from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "frontend" / "src"

pass
pass
pass
pass
KERNEL_ALLOWED_FEATURE_IMPORTERS = {
    "kernel/app/AppShell.tsx",
}


def _is_integration_test(rel: str) -> bool:
    return rel.startswith("__tests__/") or ".test." in rel

pass
pass
pass
pass
EXCEPTIONS: dict[tuple[str, str], str] = {}

pass
pass
API_IN_VIEW_EXCEPTIONS: dict[str, tuple[int, str]] = {
    # 2026-11-06：存量**已全部清空**（前端 MVC 第一轮收口完成）。
    # 这里保持空表而不是删掉机制：它允许将来出现"必须例外"的情况并写明理由，
    # 但新增一条必须同时把额度写清楚，评审时才看得见欠账。
}


pass
FROM_RE = re.compile(r"""\bfrom\s+["']([^"']+)["']""")


def _resolve(rel: str, spec: str) -> str | None:
    if not spec.startswith("."):
        return None
    parts: list[str] = []
    for seg in (Path(rel).parent.as_posix() + "/" + spec).split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if not parts:
                return None
            parts.pop()
        else:
            parts.append(seg)
    return "/".join(parts) or None


def _target_feature(resolved: str | None) -> str | None:
    if not resolved:
        return None
    parts = resolved.split("/")
    return parts[1] if parts[0] == "features" and len(parts) >= 2 else None


def _is_pure_logic(resolved: str) -> bool:
    name = resolved.rsplit("/", 1)[-1]
    if re.match(r"use[A-Z]", name):
        return False
    if (SRC / (resolved + ".tsx")).exists():
        return False
    if (SRC / resolved / "index.tsx").exists():
        return False
    return True

pass
API_CALL_RE = re.compile(r"\bapi\s*(?:\?\.)?\.[a-zA-Z_]\w*\s*\(")

pass
C_LAYER_FILE_RE = re.compile(r"(^|/)use[A-Za-z]\w*\.tsx?$")


def feature_of(path: Path) -> str | None:
    try:
        rel = path.relative_to(SRC / "features")
    except ValueError:
        return None
    return rel.parts[0] if rel.parts else None


def _is_view(path: Path) -> bool:
    rel = path.relative_to(SRC).as_posix()
    if not rel.endswith(".tsx"):
        return False
    pass
    return not rel.startswith("kernel/api/")


def scan() -> list[tuple[str, str, str, int]]:
    bad: list[tuple[str, str, str, int]] = []
    for path in SRC.rglob("*.ts"):
        bad.extend(_scan_file(path))
    for path in SRC.rglob("*.tsx"):
        bad.extend(_scan_file(path))
    return bad


def _scan_file(path: Path) -> list[tuple[str, str, str, int]]:
    rel = path.relative_to(SRC).as_posix()
    text = path.read_text("utf-8", errors="replace")
    src_feat = feature_of(path)
    out: list[tuple[str, str, str, int]] = []
    for i, line in enumerate(text.splitlines(), 1):
        if "from " not in line:
            continue
        for m in FROM_RE.finditer(line):
            resolved = _resolve(rel, m.group(1))
            target = _target_feature(resolved)
            if target is None:
                continue
            if src_feat is not None:
                if target == src_feat:
                    continue
                if (rel, target) in EXCEPTIONS:
                    continue
                pass
                pass
                if _is_pure_logic(resolved or ""):
                    continue
                out.append((rel, src_feat, target, i))
            elif rel in KERNEL_ALLOWED_FEATURE_IMPORTERS or _is_integration_test(rel):
                continue
            else:
                out.append((rel, "(kernel/装配层)", target, i))
    return out


def scan_api_in_view() -> list[tuple[str, int, str]]:
    counted: dict[str, list[tuple[int, str]]] = {}
    for path in sorted(SRC.rglob("*.tsx")) + sorted(SRC.rglob("*.ts")):
        rel = path.relative_to(SRC).as_posix()
        if not _is_view(path):
            continue
        if _is_integration_test(rel):
            continue
        if C_LAYER_FILE_RE.search(rel):
            continue
        text = path.read_text("utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith(("//", "*", "/*")):
                continue
            if API_CALL_RE.search(line):
                counted.setdefault(rel, []).append((i, line.strip()[:100]))

    bad: list[tuple[str, int, str]] = []
    for rel, hits in counted.items():
        quota = API_IN_VIEW_EXCEPTIONS.get(rel, (0, ""))[0]
        pass
        for line, snippet in hits[quota:]:
            bad.append((rel, line, snippet))
    return sorted(bad)


pass
pass
DATE_LOCALE_RE = re.compile(
    r"new\s+Date\s*\([^)]*\)\s*\.\s*toLocale(Date|Time)?String\s*\("
    r"|\.created_at\s*\*\s*1000\s*\)\s*\.\s*toLocale"
)


def scan_date_format() -> list[tuple[str, int, str]]:
    bad: list[tuple[str, int, str]] = []
    for path in sorted(SRC.rglob("*.tsx")) + sorted(SRC.rglob("*.ts")):
        rel = path.relative_to(SRC).as_posix()
        if _is_integration_test(rel) or rel == "kernel/ui/format.ts":
            continue
        text = path.read_text("utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith(("//", "*", "/*")):
                continue
            if DATE_LOCALE_RE.search(line):
                bad.append((rel, i, line.strip()[:100]))
    return sorted(bad)


def main() -> int:
    bad = scan()
    api_bad = scan_api_in_view()
    date_bad = scan_date_format()
    if "--list" in sys.argv:
        print(f"feature 互引存量例外 {len(EXCEPTIONS)} 条：")
        for (src, dst), why in EXCEPTIONS.items():
            print(f" - {src} → features/{dst}\n     {why}")
        print(f"\nV 层直调 api 存量例外 {len(API_IN_VIEW_EXCEPTIONS)} 个文件：")
        for src, (n, why) in API_IN_VIEW_EXCEPTIONS.items():
            print(f" - {src}  (剩余额度 {n})\n     {why}")
        return 0

    failed = False
    if bad:
        failed = True
        print(f"前端分层检查失败：{len(bad)} 条 feature 组件/hook 互引 / kernel 反向依赖")
        for rel, a, b, line in sorted(bad):
            print(f" - {rel}:{line}  {a} → features/{b}")
        print("\n解法：共享组件下沉 `kernel/ui/**`，共享纯逻辑归所属功能域后直接引用；"
              "确需长期例外请登记本脚本 EXCEPTIONS 并写明理由（只许减不许增）。\n")

    if api_bad:
        failed = True
        print(f"MVC 越层：{len(api_bad)} 处视图直接调用 api（应在 C 层 hook 里）")
        for rel, line, snippet in api_bad:
            print(f" - {rel}:{line}  {snippet}")
        print("\n解法：把取数/提交挪到同 feature 的 `useXxx.ts`（C 层），"
              "视图只拿 `{ data, actions }`；确需例外请登记 API_IN_VIEW_EXCEPTIONS。\n")

    if date_bad:
        failed = True
        print(f"时间格式化越层：{len(date_bad)} 处绕过 kernel/ui/format.ts 自己拼时间")
        for rel, line, snippet in date_bad:
            print(f" - {rel}:{line}  {snippet}")
        print("\n解法：统一用 `fmtStamp`（完整时间戳）/`shortTime`（窄栏）/"
              "`fmtClock`（消息尾部）。`toLocaleString()` 的输出随 locale 变，"
              "与项目口径既不同格式也不同长度。\n")

    if failed:
        return 1
    print("前端分层检查通过（无 feature 组件/hook 互引、无 kernel 反向依赖、"
          "无视图直调 api、无自拼时间格式）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
