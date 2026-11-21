"""只跑「本次改动相关模块」的测试，别每次全量。

用法：
    ./scripts/test.sh tools              # 只跑 tools 模块（改工具/MCP/skill 时）
    ./scripts/test.sh config session     # 跑多个模块
    ./scripts/test.sh full               # 全量 + 覆盖率 78% 门槛（提交前/发版前才用）
    ./scripts/test.sh e2e                # 前端前后端联动（会真起一个隔离后端）
    ./scripts/test.sh fe                 # 前端单测（vitest，不含 e2e）

模块 → 目录对照：
    config   tests/config      配置（provider / 队列 / utility / 设置 / 项目）
    session  tests/session     会话（WS、持久化、压缩、子 Agent、计划模式）
    workflow tests/workflow    工作流 + 编排（llm 节点、表达式、人工闸门）
    tools    tests/tools       工具（fs / web / 检索 / 安全策略 / 记忆）
    plugins  tests/plugins     插件 + MCP + Skill
    kernel   tests/kernel      网关 / provider adapter / 内核契约 / 结构护栏
"""
set -u
cd "$(dirname "$0")/.." || exit 1
PY=".venv/bin/python"
MODS="config session workflow tools plugins kernel"

if [ $# -eq 0 ]; then
  echo "用法: $0 <模块...|full|e2e|fe>" >&2
  echo "模块: $MODS" >&2
  exit 2
fi

case "$1" in
  full)
    cd backend || exit 1
    exec "../$PY" -m pytest tests -q --cov-fail-under=78 "${@:2}"
    ;;
  e2e)
    cd frontend || exit 1
    exec npx vitest run src/__tests__/integration
    ;;
  fe)
    cd frontend || exit 1
    exec npx vitest run src/features src/kernel
    ;;
esac

PATHS=""
for m in "$@"; do
  case " $MODS " in
    *" $m "*) PATHS="$PATHS tests/$m" ;;
    *) echo "未知模块: $m（可选: $MODS）" >&2; exit 2 ;;
  esac
done

cd backend || exit 1
# 分模块只关心用例本身：关掉覆盖率统计（全量扫源码要 40s+），
# 覆盖率只在 `test.sh full` 里统计。
# shellcheck disable=SC2086
exec "../$PY" -m pytest $PATHS -q --no-cov
