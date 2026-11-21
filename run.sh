#!/usr/bin/env bash
# 一键启动/停止/重启（Linux 版，对应 start_all.bat）
# 后端同时托管前端构建产物，无需独立前端服务
# 访问地址: http://127.0.0.1:8001
#
# 用法:
#   ./run.sh                  等价于 start
#   ./run.sh start            启动后端（dist 缺失时才构建）；已运行则跳过
#   ./run.sh stop             停止后端（先 TERM，10 秒后 KILL）
#   ./run.sh restart          停止 → 重新构建前端 → 启动（改完前端必用）
#   ./run.sh restart --no-build   重启但不重建前端（只改后端时更快）
#
# **单实例**（2026-11-02 起）：只有一份代码、一份数据目录、一个端口。
# 以前为了「重启不断会话」开过 8002 双实例（data-dev/ 隔离 + sync/promote），
# 但那套带来的是更多的麻烦：provider 快照分叉、事件跨实例串台、两套脚本。
# 现在改成「事件日志 + 断点续传」：重启后前端自动重连并补齐已发出的事件，
# 内容不丢（事件日志落盘 + 前端按序号重放）。
# 要跑旧版本/对比行为 → 用 git 分支，不要用第二套运行目录。
set -u
cd "$(dirname "$0")" || exit 1
ROOT="$(pwd)"

PORT="${HARNESS_PORT:-8001}"
CMD=start
EXTRA=""
while [ $# -gt 0 ]; do
  case "$1" in
    start|stop|restart|sync) CMD="$1"; shift ;;
    sync-full) CMD="$1"; shift ;;
    --port) PORT="$2"; shift 2 ;;
    *) EXTRA="$EXTRA $1"; shift ;;
  esac
done
[ -n "$EXTRA" ] && set -- $EXTRA

LOG="$ROOT/data/logs/backend-${PORT}.out"
PATTERN="^[^ ]*python.*uvicorn app.main:app.*--port ${PORT}"

mkdir -p "$ROOT/data/logs"

# 启动日志轮转：uvicorn 的 stdout 直接重定向到 .out，没有内建切割，
# 之前涨到 3.7MB 全是历史启动记录。超过 10MB 就滚一份，只留上一份。
rotate_log() {
  [ -f "$LOG" ] || return 0
  size=$(stat -c%s "$LOG" 2>/dev/null || echo 0)
  if [ "$size" -gt 10485760 ]; then
    mv -f "$LOG" "$LOG.1"
  fi
}

PY="$ROOT/.venv/bin/python"

pids() {
  pgrep -f "$PATTERN" 2>/dev/null || true
}

is_running() {
  [ -n "$(pids)" ]
}

build_frontend() {
  echo '正在构建前端...'
  ( cd "$ROOT/frontend" && npm run build ) || {
    echo '✗ 前端构建失败，未启动后端' >&2
    return 1
  }
}

start_backend() {
  if is_running; then
    echo "后端已在运行 (PID $(pids))，跳过启动"
    return 0
  fi
  if [ ! -x "$PY" ]; then
    echo "✗ 未找到 Python: $PY（请先创建 .venv）" >&2
    return 1
  fi
  cd "$ROOT/backend" || return 1
  rotate_log
  nohup "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" >> "$LOG" 2>&1 &
  newpid=$!
  sleep 2
  if ! kill -0 "$newpid" 2>/dev/null; then
    echo '✗ 后端启动失败，最后 20 行日志:' >&2
    tail -n 20 "$LOG" >&2
    return 1
  fi
  # 等端口真正就绪。startup 钩子已经把 MCP/provider 预热挪到后台任务，
  # 正常情况下 1-2s 就 ready，这里给 30s 兜住慢盘/冷缓存。
  i=0
  while [ $i -lt 30 ]; do
    if curl -s -m 2 -o /dev/null "http://127.0.0.1:$PORT/api/config"; then
      echo "后端已启动 (PID $newpid)，日志: $LOG"
      return 0
    fi
    sleep 0.5
    i=$((i + 1))
  done
  echo "⚠ 进程在跑但 30s 内未就绪，看日志: $LOG" >&2
  return 1
}

stop_backend() {
  list="$(pids)"
  if [ -z "$list" ]; then
    echo '后端未在运行'
    return 0
  fi
  echo "正在停止后端 (PID $list)..."
  kill $list 2>/dev/null || true
  i=0
  while [ $i -lt 20 ]; do
    sleep 0.5
    if ! is_running; then
      echo '后端已停止'
      return 0
    fi
    i=$((i + 1))
  done
  echo '优雅停止超时，强制结束' >&2
  kill -9 $list 2>/dev/null || true
  sleep 1
  if is_running; then
    echo '✗ 仍未能停止后端，请手动检查' >&2
    return 1
  fi
  echo '后端已停止'
  return 0
}

BUILD=yes
if [ "${1:-}" = "--no-build" ]; then
  BUILD=no
  shift
fi

case "$CMD" in
  start)
    if [ ! -d "$ROOT/frontend/dist" ]; then
      build_frontend || exit 1
    fi
    start_backend || exit 1
    ;;
  stop)
    stop_backend || exit 1
    exit 0
    ;;
  restart)
    stop_backend || exit 1
    if [ "$BUILD" = yes ]; then
      build_frontend || exit 1
    fi
    start_backend || exit 1
    ;;
  sync)
    "$ROOT/sync-to-agent.sh"
    ;;
  sync-full)
    "$ROOT/sync-to-agent.sh" --full
    ;;
  *)
    echo "用法: $0 [start|stop|restart|sync|sync-full] [--no-build] [--port N]" >&2
    exit 2
    ;;
esac

echo "访问地址: http://127.0.0.1:$PORT"
