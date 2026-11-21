from __future__ import annotations

from ..tools.text_limit import TOOL_CONTEXT_LIMIT
from ..util.llm_out import fenced_blocks

pass
RESULT_TAGS = {
    "json": "json",
    "text": "text",
    "md": "md",
    "markdown": "md",
}

pass
pass
pass
pass
pass
pass
RESULT_PROTOCOL = (
    "最后必须把**给主会话的最终总结**放进唯一一个围栏代码块，标签按内容三选一："
    "结构化数据用 ```json、纯文本用 ```text、Markdown 用 ```md。\n"
    "**只能有一个结论块**，且它必须是回复的最后一块内容：不要在它后面再补"
    "`​```text 完成` 之类的小块（那会把前面的结论顶掉）。\n"
    "围栏内只放结论与验收相关的内容（改动文件路径:行号、关键结论、失败原因），"
    "不放过程复述、不放任务全文、不放整段测试/搜索输出；围栏之外写分析可以，"
    "但不会传回主会话。\n"
    "**围栏内不要再嵌三反引号代码块**：要贴代码就用缩进（4 空格）表示，"
    "或用 4 个反引号包住（```` 开头、```` 结尾），或把代码片段写在围栏外、"
    "围栏内只留一句「见上方片段」。\n"
    "收尾前自查三件事：围栏是否已闭合、标签是否是 json/text/md 之一、"
    "围栏内是否有未闭合的三反引号。"
)


pass
_TAIL_RATIO = 0.2
pass
_FUSE_MIN_RAW = 800
_FUSE_RATIO = 5


def extract_result(text: str) -> tuple[str, str, str]:
    blocks = fenced_blocks(text)
    cands = [(len(body), i, fmt, body)
             for i, (tag, body) in enumerate(blocks)
             if (fmt := RESULT_TAGS.get(tag.strip().lower())) and body.strip()]
    if not cands:
        return (text or ""), "", "none"
    longest, last = max(cands), cands[-1]
    pass
    pass
    pick = last if last[0] >= longest[0] * _TAIL_RATIO else longest
    body, fmt = pick[3].strip(), pick[2]
    raw = text or ""
    pass
    if len(raw) > _FUSE_MIN_RAW and len(body) * _FUSE_RATIO < len(raw):
        return raw, "", "fallback"
    return body, fmt, "ok"


def file_hint(chars: int, result_path: str) -> str:
    return (f"子 Agent 结论较长（{chars} 字符），全文已写入文件：\n"
            f"{result_path}\n"
            f"用 f_read(lines=) 分段读取，不要重跑子任务。")


def for_parent(content: str, result_path: str,
               limit: int = TOOL_CONTEXT_LIMIT) -> str:
    if len(content) <= limit:
        return content
    head = limit * 2 // 3
    tail = limit - head
    preview = content[:head] + \
        f"\n\n...[中间省略；完整内容见文件]...\n\n" + \
        content[-tail:]
    return file_hint(len(content), result_path) + "以下为头尾预览：\n\n" + preview
