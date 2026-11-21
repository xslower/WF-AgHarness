from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Optional


if TYPE_CHECKING:
    from ...registry import ToolContext, ToolRegistry


from ...project.manager import MARKER, ProjectManager
from ...util.fsx import rel_to
from ...util.jsonx import err, write_json

DOC_LIMIT = 8_000


class MemoryStore:
    def __init__(self, projects: ProjectManager) -> None:
        self.projects = projects

    pass

    def _path(self, project: str) -> Path:
        return Path(project) / MARKER / "memory.json"

    def load(self, project: str) -> list[dict]:
        p = self._path(project)
        if not p.exists():
            return []
        try:
            return json.loads(p.read_text("utf-8")).get("entries", [])
        except (ValueError, OSError):
            return []

    def add(self, project: str, content: str) -> dict:
        content = content.strip()
        if not content:
            raise ValueError("记忆内容为空")
        entries = self.load(project)
        pass
        for e in entries:
            if e["content"] == content:
                e["ts"] = time.time()
                self._save(project, entries)
                return e
        entry = {"id": uuid.uuid4().hex[:8], "content": content[:2000],
                 "ts": time.time()}
        entries.append(entry)
        self._save(project, entries)
        return entry

    def delete(self, project: str, mid: str) -> bool:
        entries = self.load(project)
        rest = [e for e in entries if e["id"] != mid]
        if len(rest) == len(entries):
            return False
        self._save(project, rest)
        return True

    def replace(self, project: str, mid: str, content: str) -> Optional[dict]:
        content = (content or "").strip()
        if not content:
            raise ValueError("记忆内容为空")
        entries = self.load(project)
        for e in entries:
            if e["id"] == mid:
                e["content"] = content[:2000]
                e["ts"] = time.time()
                self._save(project, entries)
                return e
        return None

    def _save(self, project: str, entries: list[dict]) -> None:
        pass
        write_json(self._path(project), {"entries": entries}, indent=1)

    pass

    def chain(self, project: str) -> list[str]:
        rel = rel_to(project, self.projects.root)
        if rel is None:
            return [project] if (Path(project) / MARKER).is_dir() else []
        root = Path(self.projects.root).resolve()
        out = [str(root)] if (root / MARKER).is_dir() else []
        cur = root
        for part in rel.parts:
            cur = cur / part
            if (cur / MARKER).is_dir():
                out.append(str(cur))
        return out

    def effective(self, project: str) -> list[dict]:
        by_content: dict[str, dict] = {}
        for p in self.chain(project):
            for e in self.load(p):
                by_content[e["content"]] = e
        return list(by_content.values())

    pass

    def search(self, project: str, query: str, limit: int = 10) -> list[dict]:
        terms = [t for t in re.split(r"\s+", (query or "").strip()) if t]
        if not terms:
            return self.effective(project)[:limit]
        scored = []
        for e in self.effective(project):
            text = e.get("content", "")
            score = sum(1 for t in terms if t in text)
            if score > 0:
                scored.append((score, e))
        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:limit]]

    pass

    def docs_files(self, project: str) -> list[str]:
        cfg = Path(project) / MARKER / "docs.json"
        if cfg.exists():
            try:
                return json.loads(cfg.read_text("utf-8")) or []
            except (ValueError, OSError):
                pass
        return ["README.md"]

    def read_docs(self, project: str) -> str:
        out = []
        for name in self.docs_files(project):
            f = Path(project) / name
            if f.is_file():
                text = f.read_text("utf-8", errors="replace")[:DOC_LIMIT]
                out.append(f"# {name}\n{text}")
        return "\n\n".join(out)

    pass

    def context_for(self, project: str) -> str:
        if not project:
            return ""
        parts = []
        mem = self.effective(project)
        if mem:
            lines = "\n".join(f"- {e['content']}" for e in mem)
            parts.append(f"[项目记忆（根→当前继承，长期重要信息）]\n{lines}")
        docs = self.read_docs(project)
        if docs:
            parts.append(f"[项目必读文档]\n{docs}")
        return "\n\n".join(parts)


GATE_PROMPT = """判断以下内容是否值得作为长期记忆保存。本项目记忆只存「对当前任务至关重要的信息」：
1. 已完成的工作（做了什么、改了哪些文件、结论是什么）——避免后续重复做
2. 踩过的坑（失败原因、错误方案、绕行方法）——避免重复踩坑
3. 关键决定与约定（架构选择、路径、配置、用户明确偏好）

必须拒绝的内容：
- 与项目/任务无关的个人信息（生日、身高、兴趣等生活杂事）
- 临时性/时效性内容（当前 bug 状态、一次性输出、会话细节）
- 零零碎碎、对后续任务没有参考价值的碎片

只输出 JSON：{"keep": true} 或 {"keep": false}。

内容："""


async def gate_memory(gateway, content: str) -> tuple[bool, str]:
    try:
        out = await gateway.call_utility(
            "classify", [{"role": "user", "content": GATE_PROMPT + content[:800]}])
    except Exception:
        return True, ""
    m = re.search(r"\{[^}]*\}", out, re.S)
    if not m:
        return True, ""
    try:
        return bool(json.loads(m.group(0)).get("keep")), ""
    except ValueError:
        return True, ""


async def memory(ctx: "ToolContext", action: str = "search", content: str = "",
                 query: str = "", limit: int = 10, ids: list[int] | None = None,
                 mid: str = "") -> str:
    act = (action or "search").strip().lower()
    if act == "history_get":
        if not ids:
            return err("action=history_get 需要 ids（消息编号数组，见视图里的 msg#N 标记）")
        if ctx.history_get is None:
            return err("history_get 不可用（非会话上下文）")
        return await ctx.history_get([int(i) for i in ids])
    if act == "save":
        if not (content or "").strip():
            return err("action=save 需要 content")
        if ctx.save_memory is None:
            return err("记忆功能不可用")
        return await ctx.save_memory(content)
    if act == "search":
        if ctx.memory_search is None:
            return err("记忆功能不可用")
        return await ctx.memory_search(query, limit)
    if act == "replace":
        if not (mid or "").strip():
            return err("action=replace 需要 mid（记忆条目 id，见 search 结果）")
        if not (content or "").strip():
            return err("action=replace 需要 content")
        if ctx.memory_replace is None:
            return err("记忆功能不可用")
        return await ctx.memory_replace(mid.strip(), content)
    if act == "delete":
        if not (mid or "").strip():
            return err("action=delete 需要 mid（记忆条目 id，见 search 结果）")
        if ctx.memory_delete is None:
            return err("记忆功能不可用")
        return await ctx.memory_delete(mid.strip())
    return err("action 必须是 save/search/replace/delete/history_get，收到: "
               f"{action}")


def register(reg) -> None:
    reg.register(
        "memory",
        "项目记忆 + 历史会话取回。记忆类动作：action=save 保存一条（只记对任务至关重要的信息："
        "已完成的工作、踩过的坑、关键决定与约定、用户明确偏好；用户明确要求记住的规则必须入库，"
        "提取关键部分而非原文照搬；与任务无关的个人信息、临时内容会被把关拒绝）；"
        "action=search 按关键词检索（含父级继承，开始任务前先查一遍避免重复劳动；结果带 id）；"
        "action=replace 用 content 覆盖 mid 指定的那条记忆（同样经把关）；"
        "action=delete 删除 mid 指定的那条记忆（只能删当前项目自己的，父级继承的删不了）。"
        "翻历史是另一件事：action=history_get 取回被压缩历史的原文——早期消息在上下文里"
        "只剩 [msg#N 一句总结]，需要细节时按编号取回，取回即见全文。",
        {"action": {"type": "string",
                    "enum": ["save", "search", "replace", "delete", "history_get"],
                    "description": "save=保存，search=检索，replace=改写，delete=删除，"
                                   "history_get=取回被压缩的历史消息原文"},
         "content": {"type": "string",
                     "description": "action=save/replace 必填：记忆内容"},
         "query": {"type": "string", "description": "action=search：关键词，空格分隔多个"},
         "limit": {"type": "integer", "description": "action=search：返回条数，默认 10"},
         "mid": {"type": "string",
                 "description": "action=replace/delete 必填：记忆条目 id（search 结果里的 id）"},
         "ids": {"type": "array", "items": {"type": "integer"},
                 "description": "action=history_get 必填：消息编号（上下文里 [msg#N] 的 N）"}},
        memory, ["action"])
