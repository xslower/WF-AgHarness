#!/usr/bin/env bash
# 一键检查：结构守卫 + 重复代码 + 后端测试（含覆盖率门槛）+ 前端类型/单测/构建。
# 用法: scripts/check_all.sh   任一步失败即退出非零。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY="python3"

step() { printf '\n\033[1;36m==> %s\033[0m\n' "$1"; }

step "结构检查（行数预算 / 禁止耦合）"
"$PY" "$ROOT/scripts/check_structure.py"

step "包边界检查（R5：__init__.py 只许导入/适配）"
"$PY" "$ROOT/scripts/check_init_py.py"

step "后端分层检查（R1 上下分层：禁止反向 import）"
"$PY" "$ROOT/scripts/check_layers.py"

step "前端分层检查（R2 左右分层 + MVC：禁止 feature 互引 / 视图直调 api）"
"$PY" "$ROOT/scripts/check_frontend_layers.py"

step "前端布局检查（弹性行内裸文本：长描述会挤飞操作按钮）"
"$PY" "$ROOT/scripts/check_flex_text.py"

step "重复代码检查（新增跨文件重复块）"
"$PY" "$ROOT/scripts/check_dupes.py"

step "文档路径检查（docs 里的代码路径必须真实存在）"
"$PY" "$ROOT/scripts/check_docs.py"

step "项目路径检查（禁止 resolve/realpath 展开软链）"
"$PY" "$ROOT/scripts/check_project_paths.py"

step "后端测试（离线，含 --cov-fail-under）"
cd "$ROOT/backend"
"$PY" -m pytest -q -m "not network" --cov-fail-under=78

step "前端类型检查"
cd "$ROOT/frontend"
npx tsc --noEmit

step "前端单元测试"
npx vitest run

step "前端构建"
npm run build

printf '\n\033[1;32m全部通过\033[0m\n'
