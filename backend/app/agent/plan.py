from __future__ import annotations

from enum import Enum
import logging
import re

logger = logging.getLogger("harness.plan_controller")


class PlanState(Enum):
    idle = "idle"
    planning = "planning"
    awaiting_approval = "awaiting_approval"
    executing = "executing"
    cancelled = "cancelled"


INTENT_PATTERNS: dict[str, list[str]] = {
    "approve": [
        r"^(确认|同意|执行|开始|没问题|可以|好的|ok|yes|go|行|好|干|搞|来吧)$",
        r"^(确认|同意).*(执行|开始|操作)",
        r"^(开始|直接|马上).*(执行|操作|搞)",
        r"^没问题.*(执行|开始|做)",
        r"^好的.*(没问题|可以|行|确认|执行|开始)",
        r"^按.*(计划|plan).*(执行|来|做)",
    ],
    "cancel": [
        r"^(取消|算了|不做了|停止|终止|停|别|no|cancel|stop|abort)$",
        r"^(先|暂时).*(不|取消|停)",
    ],
    "modify": [
        r"^(修改|调整|换|改成|不要|去掉|加上|增加|改为)",
        r"^(第.*步|步骤).*(改|换|调整|不要)",
        r"^不要.*(这个|这样)",
    ],
}

WRITE_TOOL_NAMES: set[str] = {
    "f_write",
    "f_replace",
    "config_write",
    "run_command",
    "f_path",
    "workflow",
    # tool / subagent / mcp / 其他写类工具也在 READONLY_TOOL_ACTIONS 里按 action 细分。
    # 它们必须进这个集合，否则下面「name in WRITE_TOOL_NAMES」的内层 action 判定根本走不到。
    "tool",
    "subagent",
}

pass
pass
pass
READONLY_TOOL_ACTIONS: dict[str, set[str]] = {
    "workflow": {"help", "list", "get", "list_node", "wait"},
    "table": {"inspect", "rows", "query"},
    "ppt": {"inspect", "read"},
    # spawn 也放行：计划模式本就要靠子 Agent 做只读调研。子 Agent 的工具集在
    # SpawnMixin._spawn 里按 plan 状态强制为只读（不含 run_command/写删/再建子 Agent），
    # 所以放行 spawn 不会打开写盘口子。
    "subagent": {"list", "get", "wait", "spawn"},
    # tool(action=invoke) 能调任意工具（包括 f_write / run_command），
    # 是「按工具名拦」最大的绕过口：名字是 tool，实际干的是写。
    # 所以只读模式只放行 search / use，invoke 一律拦。
    "tool": {"search", "use"},
}

pass
pass
pass
pass
pass
pass
WRITE_COMMAND_PATTERNS: list[str] = [
    r"\b(rm|rmdir|unlink|mv|dd|mkfs|truncate|shred)\b",
    r"\b(chmod|chown|chgrp|ln)\b",
    r"\b(tee|touch|mkdir)\b",
    r"\b(pip|pip3|npm|yarn|pnpm|apt|apt-get|yum|dnf|apk|conda|brew)\b.*\s(install|uninstall|add|remove|update|upgrade)\b",
    r"\b(systemctl\s+(start|stop|restart|enable|disable))",
    r"\bservice\s+\S+\s+(start|stop|restart|reload)\b",
    r"\b(git\s+(push|commit|merge|rebase|reset|checkout|clean|stash))",
    r"\b(sed\s+-i|perl\s+-i)",
    # 下载落盘才算写；`-o /dev/null` 是常见的探测写法，别误拦
    r"\b(curl|wget)\b.*(--output[= ]|\s-[oO]\s+)(?!/dev/null|/dev/std)",
    r"\b(curl|wget)\b.*\|\s*(sh|bash)\b",
    # 真实文件重定向：排除 /dev/null、/dev/stdout、2>&1 这类无副作用写法
    r">>?\s*(?!/dev/null|/dev/stdout|/dev/stderr|&)[\"']?[\w./~-]",
]

pass
pass
pass
pass
pass
pass
INLINE_EXEC_PATTERN = (
    r"\b(python[0-9.]*|pypy[0-9.]*|node|nodejs|deno|bun|perl|ruby|php|lua|sh|bash|zsh|fish)\b"
    r"[^\n|;&]*\s(-c|-e|--eval|-p|--print)\b"
)

pass
pass
pass
PY_WRITE_API_PATTERNS: list[str] = [
    # open(..., 'w'/'a'/'x'/'+')（'rb' 这类读取不算）
    r"\bopen\s*\([^)]*['\"][rwaxb+]*[wax+][rwaxb+]*['\"]",
    r"\.write_text\s*\(|\.write_bytes\s*\(",
    r"\bos\.(remove|unlink|rename|renames|replace|mkdir|makedirs|rmdir|removedirs|"
    r"chmod|chown|symlink|link|truncate|write)\b",
    r"\bshutil\.(copy|copy2|copyfile|copyfileobj|copytree|move|rmtree|"
    r"make_archive|unpack_archive)\b",
    r"\bsubprocess\.(run|call|check_call|check_output|Popen)\b",
    r"\bos\.system\s*\(|\bos\.popen\s*\(",
    r"\b(json|yaml|toml|pickle|shelve)\.dump\s*\(",
    r"\.to_csv\s*\(|\.to_excel\s*\(|\.to_json\s*\(|\.to_parquet\s*\(|"
    r"\.savefig\s*\(|\.save\s*\(",
    r"\bnp\.save\w*\s*\(|\btorch\.save\s*\(",
    r"\b(openpyxl|docx|pptx)\b",
    # Node / JS（不带 fs. 前缀的裸调用：require('fs').writeFileSync(...)）
    r"\bwriteFileSync\s*\(|\bwriteFile\s*\(|\bappendFileSync\s*\(|\bappendFile\s*\(",
    r"\bfs\.(write|writeFile|writeFileSync|appendFile|appendFileSync|rename|"
    r"renameSync|unlink|unlinkSync|rm|rmSync|mkdir|mkdirSync|copyFile|copyFileSync)\b",
    r"\bchild_process\b|\bexecSync\s*\(|\bspawnSync\s*\(",
]

pass
SCRIPT_FILE_PATTERN = re.compile(
    r"(?:^|[\s;&|])(?:python[0-9.]*|pypy[0-9.]*|node|nodejs|deno|bun|perl|ruby|php|lua|sh|bash|zsh)"
    r"\s+(?:-[^\s]+\s+)*([^\s;&|]+\.(?:py|js|mjs|cjs|ts|sh|bash|pl|rb|php|lua))"
)


def _resolve_script(path: str, cwd: str) -> str:
    import os
    p = (path or "").strip().strip("'\"")
    if not p:
        return ""
    cand = p if os.path.isabs(p) else os.path.join(cwd or ".", p)
    try:
        if os.path.isfile(cand) and os.path.getsize(cand) <= 2_000_000:
            with open(cand, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
    except OSError:
        return ""
    return ""


def _script_writes(body: str) -> bool:
    if not body:
        return False
    pass
    scan = re.sub(r"(?m)#.*$|//.*$", "", body)
    pass
    return any(re.search(p, scan, re.IGNORECASE) for p in PY_WRITE_API_PATTERNS)


PLAN_MODE_SYSTEM_PROMPT = """
【写操作约束】系统可能按当前轮的安全状态进入只读拦截，拦截结果由工具返回值传达。

查看类调用一律允许（不必犹豫，直接用）：
- 读文件 / 搜文件 / grep、`table` 的 inspect·rows·query、`ppt` 的 inspect·read
- `workflow` 的 help / list / get / list_node（查看工作流定义、列节点）
- `subagent` 的 list / get / wait，以及 spawn 开只读调研子 Agent
  （计划模式下 spawn 出的子 Agent 只能用只读工具：读文件/搜索/grep/web，
   不能跑命令、不能写删、不能再建子 Agent）
- run_command 跑查询类命令（ls/cat/grep/ps/df/curl 探测等）

写操作被拦时工具返回 `plan_blocked`（涉及 f_write、f_replace、f_path 的增删移拷、
workflow 的 add_node/edit_node/del_node/save/run、破坏性 shell 命令）。此时按以下规则处理：

1. 若任务只需查询/解释/分析，直接正常作答，不必出计划。
2. 若任务**需要修改文件或执行写命令**，或改动比较复杂：先输出方案，再等用户确认。
   方案格式：以 `## 📋 实施计划` 开头，用表格列出「序号 | 步骤 | 涉及文件 | 操作类型 | 风险」，
   最后说明影响范围与回滚方式。
3. 写操作被拦下时**不要重试工具**：直接把方案写出来，等用户确认。
4. 用户确认后，系统会重新发起一次执行，届时写操作才被放行。

要不要拦截由系统按当前轮状态决定，**不要从这段话推断本轮是否被拦**；
没收到 `plan_blocked` 就说明写操作可用。
"""

pass
pass
pass
pass
pass


def try_parse_intent(user_input: str, plan_state: PlanState) -> str | None:
    if plan_state != PlanState.awaiting_approval:
        return None
    text = user_input.strip().lower()
    if len(text) <= 4:
        short_map = {
            "确认": "approve", "同意": "approve", "执行": "approve",
            "开始": "approve", "ok": "approve", "yes": "approve", "go": "approve",
            "好": "approve", "行": "approve", "干": "approve",
            "取消": "cancel", "算了": "cancel", "停": "cancel",
            "别": "cancel", "no": "cancel", "stop": "cancel",
            "改": "modify", "换": "modify",
        }
        if text in short_map:
            return short_map[text]
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                return intent
    return None


def is_likely_write_command(command: str, cwd: str = "") -> bool:
    cmd = (command or "").strip()
    if not cmd:
        return False
    pass
    scan = re.sub(r"'[^']*'|\"[^\"]*\"", '""', cmd)
    low = scan.lower()
    if any(re.search(p, low) for p in WRITE_COMMAND_PATTERNS):
        return True
    pass
    pass
    m = re.search(INLINE_EXEC_PATTERN, cmd, re.IGNORECASE)
    if m:
        code = cmd[m.end():]
        return _script_writes(code) or any(
            re.search(p, code.lower()) for p in WRITE_COMMAND_PATTERNS)
    pass
    m = SCRIPT_FILE_PATTERN.search(cmd)
    if m:
        return _script_writes(_resolve_script(m.group(1), cwd))
    return False


class PlanController:

    def __init__(self):
        self._state: PlanState = PlanState.idle
        self._plan_text: str = ""
        self._session_id: str | None = None

    @property
    def state(self) -> PlanState:
        return self._state

    @property
    def plan_text(self) -> str:
        return self._plan_text

    @property
    def is_write_allowed(self) -> bool:
        return self._state == PlanState.executing

    @property
    def awaiting_approval(self) -> bool:
        return self._state == PlanState.awaiting_approval

    @property
    def is_active(self) -> bool:
        return self._state in (
            PlanState.planning,
            PlanState.awaiting_approval,
            PlanState.executing,
        )

    def enter_planning(self, session_id: str):
        self._state = PlanState.planning
        self._session_id = session_id
        self._plan_text = ""

    def on_plan_complete(self, plan_text: str) -> bool:
        if self._state != PlanState.planning:
            return False
        self._state = PlanState.awaiting_approval
        self._plan_text = plan_text
        pass
        self._notify("plan-awaiting")
        return True

    def approve(self) -> bool:
        if self._state != PlanState.awaiting_approval:
            return False
        self._state = PlanState.executing
        self._notify("plan-approved")
        return True

    def modify(self, feedback: str = "") -> bool:
        if self._state != PlanState.awaiting_approval:
            return False
        self._state = PlanState.planning
        self._plan_text = ""
        self._notify("plan-modified")
        return True

    def cancel(self) -> bool:
        if self._state not in (PlanState.planning, PlanState.awaiting_approval, PlanState.executing):
            return False
        self._state = PlanState.cancelled
        self._notify("plan-cancelled")
        return True

    def reset(self):
        was = self._state
        self._state = PlanState.idle
        self._plan_text = ""
        if was != PlanState.idle:
            self._notify("plan-reset")
        self._session_id = None

    def _notify(self, reason: str) -> None:
        try:
            from ..event.attention import notify
            notify(self._session_id or "", reason)
        except Exception:
            logger.debug("广播计划状态失败: %s", reason, exc_info=True)


pass
pass
pass

def modify_note(feedback: str) -> str:
    return (f"[计划修改意见] {feedback}\n"
            "请在上文那份计划的基础上只调整这些点，重新给出完整计划；"
            "不必重新调研，也不要执行任何写操作。")


def decide_plan(plan, decision: str, feedback: str = "") -> tuple[str, str, str | None]:
    if decision == "approve":
        if plan.approve():
            return "plan_approved", "计划已确认，开始执行...", ""
        return "notice", "当前无待确认的计划", None

    if decision == "modify":
        plan.modify(feedback)
        fb = f"：{feedback}" if feedback else ""
        return "plan_modify", f"计划将根据反馈重新生成{fb}", modify_note(feedback)

    if decision == "cancel":
        plan.cancel()
        return "plan_cancelled", "计划已取消", None

    return "notice", f"未知的 plan_decision：{decision}", None
