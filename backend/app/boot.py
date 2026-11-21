from __future__ import annotations

import asyncio
import logging
import os
import time
from functools import partial

from .tools.builtin.fs import trash
from .api.deps import Container
from .event.schedule import TIMERS

from .store.runs import RunStore
from .store import layout
from .store.session_db import WF_SESSION_KIND

logger = logging.getLogger("harness")


pass
pass
JANITOR_START_DELAY = 60


pass

def migrate_legacy(c: Container) -> None:
    from .mcp import spec as mcp_spec
    try:
        moved = mcp_spec.migrate_legacy_config(c.store)
    except Exception:
        logger.warning("MCP 配置迁移失败（不影响启动，配置仍可从旧文件读）",
                       exc_info=True)
        return
    if moved:
        logger.info("已把 config.json 的 mcpServers 迁到 %s：%s",
                    layout.mcp_dir(), moved)


pass

async def warmup(c: Container) -> None:
    if not c.mcp.servers():
        return
    try:
        await c.mcp.reload()
        rows = c.mcp.status()
        logger.info("MCP 预热完成：%s", [
            f"{s['name']}={'已连接' if s['connected'] else ('已禁用' if s['disabled'] else '未连接')}"
            + (f"（{s['error'] or s['disabled_reason']}）"
               if not s["connected"] and (s["error"] or s["disabled_reason"]) else "")
            for s in rows])
    except Exception:
        logger.warning("MCP 预热失败", exc_info=True)


pass

async def run_janitors_once(c: Container) -> None:
    await asyncio.sleep(JANITOR_START_DELAY)
    await asyncio.to_thread(_janitors_once, c)


def _janitors_once(c: Container) -> None:
    _purge_trash_once(c)
    _purge_wfchat_once(c)


def _purge_trash_once(c: Container) -> None:
    try:
        s = c.store.config.settings
        days = int(s.trashRetentionDays)
        if s.trashEnabled and days > 0:
            pass
            pass
            pass
            trash.purge_tree(c.projects.tree(), days)
    except Exception:
        logger.debug("trash janitor failed", exc_info=True)


def _purge_wfchat_once(c: Container) -> None:
    try:
        days = int(c.store.config.settings.wfChatRetentionDays)
        if days > 0:
            removed = c.sessions.purge_old(days)
            if removed:
                logger.info("wfchat janitor: 清理 %s 条过期画布会话", removed)
    except Exception:
        logger.debug("wfchat janitor failed", exc_info=True)


pass

def wire_timers(c: Container, timers: "object | None" = None) -> None:
    timers = timers if timers is not None else TIMERS
    timers.set_action_handler("session", partial(timer_run_session, c))
    timers.set_action_handler("workflow", partial(timer_run_workflow, c))


async def timer_run_session(c: Container, task: dict) -> None:
    from .api.routers.chat_session import SessionTurn
    from .api.routers.chat_socket import make_headless

    p = dict(task.get("payload") or {})
    prompt = str(p.get("prompt") or "").strip()
    if not prompt:
        logger.warning("定时会话 %s 没配提示词，跳过", task.get("name"))
        return
    project = str(p.get("project") or "")
    s = c.sessions.create(title=str(p.get("title") or "定时任务"), project=project)
    sid = s["id"]
    rt = c.session_rt().get(sid)
    sender = make_headless(rt, sid, project=s.get("project") or "")
    turn = SessionTurn(c=c, s=s, sid=sid, rt=rt, emit=sender.emit)
    logger.info("定时会话开始：%s → 会话 %s（项目 %s）",
                task.get("name"), sid, project or "(全局)")
    await turn.handle({"content": prompt, "model": str(p.get("model") or ""),
                       "plan": False})


async def timer_run_workflow(c: Container, task: dict) -> None:
    p = dict(task.get("payload") or {})
    name = str(p.get("workflow") or "").strip()
    if not name:
        logger.warning("定时工作流 %s 没配工作流名，跳过", task.get("name"))
        return
    project = str(p.get("project") or "")
    rec = c.wf_engine(project).start(
        name, dict(p.get("inputs") or {}), human_mode="auto-approve")
    logger.info("定时工作流开始：%s → %s @%s（运行 %s）",
                task.get("name"), name, project or "(全局)", rec.id)


pass

def sweep_workflow_runs(c: Container) -> None:
    workspaces: list[str] = [""]
    try:
        for node in c.projects.tree().get("children", []):
            workspaces.extend(flatten_tree(node))
    except Exception:
        logger.debug("sweep: 项目树读取失败", exc_info=True)

    live_sessions = _live_wf_sessions(c)
    for ws in workspaces:
        try:
            store = RunStore(ws)
            gone = store.purge_legacy_runs(live_sessions=live_sessions)
            fixed = store.sweep_stale(live_ids=set())
        except Exception:
            logger.warning("sweep 工作流运行失败: %s", ws or "(全局)", exc_info=True)
            continue
        if gone or fixed:
            logger.info("工作流运行清扫 [%s]：删除孤儿记录 %s 条，收尾中断 %s 条",
                        ws or "(全局)", gone, fixed)
    pass
    try:
        removed = c.sessions.purge_empty_wf_sessions(kind=WF_SESSION_KIND)
        if removed:
            logger.info("工作流会话清扫：回收空会话 %s 条", removed)
    except Exception:
        logger.debug("sweep: 空工作流会话清理失败", exc_info=True)


def _live_wf_sessions(c: Container) -> set[str]:
    live: set[str] = set()
    try:
        for row in c.sessions.list(kind="wf-session") or []:
            sid = row.get("id") if isinstance(row, dict) else None
            if sid:
                live.add(str(sid))
    except Exception:
        logger.debug("sweep: 读工作流会话失败", exc_info=True)
    return live


def flatten_tree(node: dict) -> list[str]:
    out = [str(node.get("path") or "")]
    for child in node.get("children") or []:
        out.extend(flatten_tree(child))
    return [p for p in out if p]


pass

def dump_shutdown_forensics(app) -> None:
    import re
    import subprocess

    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    me = str(os.getpid())

    pass
    try:
        out = subprocess.run(["ps", "-eo", "pid,ppid,etime,args"],
                             capture_output=True, text=True, timeout=5).stdout
        pat = re.compile(
            r"run\.sh|restart|pkill|\bkill\b|uvicorn|app\.main|bash -c|sh -c|"
            r"workbuddy|codebuddy|agent|pytest|nohup|\.sh\b",
            re.IGNORECASE)
        hits = [ln for ln in out.splitlines() if pat.search(ln)]
        logger.warning("【关闭信号取证】pid=%s 时间=%s 进程表快照:\n%s",
                       me, stamp, "\n".join(hits[-80:]) or "(无匹配进程)")
    except Exception:
        logger.debug("shutdown forensics: ps 失败", exc_info=True)

    pass
    try:
        reg = app.state.container.session_rt()
        active = [
            f"  {sid} running={r.running} queue={len(r.queue)} "
            f"emit={'有' if r.emit else '无'}"
            for sid, r in (reg.items() if hasattr(reg, "items") else [])
            if r.running or r.queue
        ]
        if active:
            logger.warning("【关闭信号取证】活跃会话 %d 条:\n%s",
                           len(active), "\n".join(active))
    except Exception:
        logger.debug("shutdown forensics: 会话快照失败", exc_info=True)
