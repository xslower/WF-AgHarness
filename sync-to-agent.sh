#!/usr/bin/env bash
# sync-to-agent.sh — 同步 code/harness 核心数据到移动硬盘 agent/harness
# 用法: ./sync-to-agent.sh          # 仅同步 data/ + .agent/ 等核心数据
#       ./sync-to-agent.sh --full   # 完整同步（包含代码，排除 .venv/node_modules）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR"
DST="$HOME/agent/harness"

if [ ! -d "$DST" ]; then
  echo "✗ 目标不存在: $DST（移动硬盘未挂载？）" >&2
  exit 1
fi

echo "=== sync-to-agent: $SRC → $DST ==="

# --- 核心数据（始终同步）---
echo '→ data/（agent.db / keystore / config / skills / workflows）'
rsync -av --delete \
  --exclude 'agent.db-shm' \
  --exclude 'agent.db-wal' \
  --exclude 'logs/' \
  --exclude 'usage.jsonl' \
  --exclude 'wf-json-errors.log' \
  "$SRC/data/" "$DST/data/"

echo '→ .agent/'
rsync -av --delete --exclude 'subagents/' "$SRC/.agent/" "$DST/.agent/"

if [ -d "$SRC/backend/.agent" ]; then
  echo '→ backend/.agent/'
  rsync -av --delete "$SRC/backend/.agent/" "$DST/backend/.agent/"
fi

# --- 全量同步 ---
if [ "${1:-}" = "--full" ]; then
  echo '→ 完整同步（排除 .venv / node_modules / __pycache__ / .git）'
  rsync -av --delete \
    --exclude '.venv/' \
    --exclude 'node_modules/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude 'data/agent.db-shm' \
    --exclude 'data/agent.db-wal' \
    --exclude 'data/logs/' \
    --exclude 'data/usage.jsonl' \
    --exclude 'data/wf-json-errors.log' \
    --exclude 'logs/' \
    --exclude 'runs/' \
    --exclude '.coverage' \
    --exclude 'coverage.json' \
    --exclude '.git/' \
    "$SRC/" "$DST/"
fi

echo '✓ 同步完成'
