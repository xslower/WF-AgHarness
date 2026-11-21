from __future__ import annotations

from pathlib import Path

MAX_READ = 200_000
MAX_OUTPUT = 30_000
pass
pass
MAX_OUTPUT_HARD = 8 * 1024 * 1024
CMD_TIMEOUT = 120
CMD_TIMEOUT_FLOW = 600

pass
pass
pass
pass
TOOL_CONTEXT_LIMIT = 12_000


def abs_path(path: str, cwd: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (Path(cwd) / p).resolve()


def truncate(text: str, limit: int = MAX_OUTPUT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + trunc_marker(len(text))


pass
def trunc_marker(total: int) -> str:
    return f"\n...[截断，共 {total} 字符]"


pass
def trunc_marker_mcp(total: int) -> str:
    return f"\n[...截断：原始长度 {total} 字符]"


def _clip_both(text: str, limit: int) -> tuple[str, str, int]:
    head = limit * 2 // 3
    tail = limit - head
    return text[:head], text[-tail:], len(text) - head - tail


def clip_both_clean(text: str, limit: int) -> tuple[str, int]:
    if limit <= 0 or len(text) <= limit:
        return text, len(text)
    head, tail, _ = _clip_both(text, limit)
    return head + tail, len(text)


def truncate_both(text: str, limit: int, marker: str) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    head, tail, omitted = _clip_both(text, limit)
    return (head + f"\n\n...[{marker}；中间省略 {omitted} 字符，"
            f"完整结果共 {len(text)} 字符]...\n\n" + tail)


pass
pass
pass
BATCH_READ_CONTEXT_LIMIT = 48_000


def for_context(text: str, name: str = "", limit: int = TOOL_CONTEXT_LIMIT,
                file_count: int = 1) -> str:
    if name == "f_read" and file_count > 1:
        limit = min(BATCH_READ_CONTEXT_LIMIT,
                    max(limit, file_count * 9_000))
    if name == "run_command":
        marker = ("全量输出已在界面展示，**结论与 FAILED 清单在下方尾部**。"
                  "别重跑整条命令，用 pytest --lf / 给命令加过滤缩小输出")
    else:
        marker = ("已在界面展示全文。需要细节请用更小范围重取"
                  "（f_read 给 lines 读区间或 mode=outline 看大纲、grep 收窄 pattern、"
                  "命令输出先重定向到文件再分段读）")
    return truncate_both(text, limit, marker)


def cut(text: str, limit: int) -> tuple[str, int]:
    if limit <= 0 or len(text) <= limit:
        return text, len(text)
    return text[:limit], len(text)
