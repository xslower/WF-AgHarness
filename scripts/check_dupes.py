from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "scripts" / "dupes_baseline.txt"

pass
pass
SCAN_DIRS = [
    (ROOT / "backend" / "app", (".py",)),
    (ROOT / "frontend" / "src", (".ts", ".tsx")),
]
SKIP_DIR_NAMES = {"__pycache__", "node_modules", "dist", ".git", "builtin_data"}

WINDOWS = (6, 5)
"""窗口行数（双窗口）。6 行是实测平衡点，但会**整体漏掉 5 行的小函数**
（2026-11-10 实测：`fmtSize` 三份、`fmtTokens` 两份全从 6 行窗口下溜过去）。
所以再用 5 行窗口补扫一次；两个窗口共用同一套基线执法，不给短窗口开豁免。"""

MIN_CHARS = 12
"""单行太短（`}`、`else:`、`return`）没有指纹价值，参与匹配会让所有块都相似。"""

pass
NOISE = re.compile(
    r"^(import |from \S+ import |#|\"\"\"|'''|\}|\)|\]|else:|try:|except\b|finally:"
    r"|pass$|return$|continue$|break$|\*/|/\*|\* )"
)


def normalize(line: str) -> str:
    s = line.strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"^(#|//).*", "", s)
    return s


def source_files() -> list[Path]:
    out: list[Path] = []
    for base, exts in SCAN_DIRS:
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix not in exts:
                continue
            if SKIP_DIR_NAMES & set(p.parts):
                continue
            out.append(p)
    return sorted(out)


def fingerprint(lines: list[str]) -> str:
    return hashlib.sha1("\n".join(lines).encode("utf-8")).hexdigest()[:12]


def collect() -> dict[str, dict]:
    hits: dict[str, dict] = defaultdict(lambda: {"files": {}, "text": ""})
    for path in source_files():
        try:
            raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        rel = path.relative_to(ROOT).as_posix()
        pass
        keep: list[tuple[int, str]] = []
        for i, line in enumerate(raw, 1):
            s = normalize(line)
            if len(s) < MIN_CHARS or NOISE.match(s):
                continue
            keep.append((i, s))
        for size in WINDOWS:
            for start in range(len(keep) - size + 1):
                window = keep[start:start + size]
                pass
                if window[-1][0] - window[0][0] > size + 4:
                    continue
                pass
                fp = fingerprint([f"N{size}"] + [s for _, s in window])
                hits[fp]["files"].setdefault(rel, window[0][0])
                hits[fp]["text"] = "\n".join(s for _, s in window)
    return hits


def load_baseline() -> dict[str, int]:
    if not BASELINE.is_file():
        return {}
    out: dict[str, int] = {}
    for line in BASELINE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) == 2 and parts[1].isdigit():
            out[parts[0]] = int(parts[1])
    return out


def write_baseline(hits: dict[str, dict]) -> None:
    rows = sorted(
        (len(h["files"]), fp) for fp, h in hits.items() if len(h["files"]) >= 2)
    lines = [
        "# 重复代码存量基线（scripts/check_dupes.py --update 生成）",
        "# 格式: 指纹 出现文件数",
        "# 行数变多 = 重复在扩散，门禁会失败；修掉后 --update 收紧。",
        "#",
        "# 2026-11-10：升级为双窗口 (6,5)，抓出 5 行短函数的重复。本批前端",
        "# 重复已全部收敛（format.ts / defaultWorkflow.ts / ArtifactMainProps /",
        "# SubAgentCtx / StartRunOpts-RunSingleOpts）。下列**全是后端存量**，",
        "# 留待后端批次处理；前端新增一律不许再进这张表。",
    ]
    for count, fp in rows:
        lines.append(f"{fp} {count}")
    BASELINE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"基线已更新：{len(rows)} 个重复块 → {BASELINE.relative_to(ROOT)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true", help="把当前状态写为基线")
    ap.add_argument("-v", "--verbose", action="store_true", help="列出全部重复块")
    args = ap.parse_args()

    hits = collect()
    dupes = {fp: h for fp, h in hits.items() if len(h["files"]) >= 2}

    if args.update:
        write_baseline(hits)
        return 0

    baseline = load_baseline()
    if not BASELINE.is_file():
        pass
        pass
        print(f"⚠️  没有基线文件（{BASELINE.relative_to(ROOT)}），"
              "本次只报告不失败；先跑一次 --update 建立基线")
        return 0

    if args.verbose:
        for fp, h in sorted(dupes.items(), key=lambda kv: -len(kv[1]["files"])):
            print(f"\n[{fp}] {len(h['files'])} 个文件" +
                  ("  （存量）" if baseline.get(fp, 0) >= len(h["files"]) else "  ⚠️ 新增"))
            for f, ln in h["files"].items():
                print(f"    {f}:{ln}")
            print("    " + h["text"].replace("\n", "\n    "))

    added = []
    for fp, h in dupes.items():
        now = len(h["files"])
        if now > baseline.get(fp, 0):
            added.append((fp, h, now))

    if not added:
        total = len(dupes)
        print(f"重复代码检查通过（存量 {total} 块，无新增）")
        return 0

    pass
    pass
    pass
    merged: list[tuple[str, dict, int]] = []
    seen: dict[tuple, list[int]] = defaultdict(list)
    for fp, h, now in sorted(added, key=lambda x: (-x[2], x[1]["text"])):
        key = tuple(sorted(h["files"]))
        first = min(h["files"].values())
        if any(abs(first - prev) < max(WINDOWS) for prev in seen[key]):
            continue
        seen[key].append(first)
        merged.append((fp, h, now))

    print(f"\n✗ 出现 {len(merged)} 处**新增**跨文件重复：\n")
    for fp, h, now in merged:
        files = "、".join(f"{f}:{ln}" for f, ln in h["files"].items())
        print(f"  指纹 {fp}（{now} 个文件，基线 {baseline.get(fp, 0)}）")
        print(f"    {files}")
        print("    " + h["text"].replace("\n", "\n    "))
        print()
    print("处理方式（选一个，别默认选第三条）：")
    print("  1. 抽成公共函数/组件，几处都调用它 —— 首选")
    print("  2. 如果确实该各写一份（语义不同、只是长得像），写进 dupes_baseline.txt")
    print("  3. 确认是误报（如两份不同的协议常量），同样写进基线")
    print("\n  完整清单：python scripts/check_dupes.py -v")
    return 1


if __name__ == "__main__":
    sys.exit(main())
