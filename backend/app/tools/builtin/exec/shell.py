from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import TYPE_CHECKING

from ....util.jsonx import err
from ...cmd_output_filter import QUIET_FLAGS, command_kind, split_command
from ...text_limit import (CMD_TIMEOUT, MAX_OUTPUT, MAX_OUTPUT_HARD,
                           clip_both_clean as _clip_clean,
                           cut as _cut, truncate_both as _truncate_both)

if TYPE_CHECKING:
    from ... import ToolContext, ToolRegistry

logger = logging.getLogger("harness.tools.shell")

pass
pass
from ....security.core import INSTALL_PATTERNS


def _quiet_rewrite(command: str) -> tuple[str, list[str]]:
    parts = split_command(command)
    applied: list[str] = []
    for i in range(0, len(parts), 2):
        seg = parts[i]
        rule = QUIET_FLAGS.get(command_kind(seg))
        if rule is None:
            continue
        already, append = rule
        if any(flag in seg for flag in already):
            continue
        parts[i] = seg.rstrip() + " " + append
        applied.append(append)
    return "".join(parts), applied


def _spill_output(ctx, text: str, command: str) -> str | None:
    sid = getattr(ctx, "session_id", "") or "anon"
    try:
        from pathlib import Path
        from ....store import layout
        d = layout.session_tool_output_dir(str(getattr(ctx, "cwd", "") or ""), sid)
        d.mkdir(parents=True, exist_ok=True)
        name = f"cmd-{int(time.time() * 1000)}.log"
        p = d / name
        p.write_text(f"$ {command}\n\n{text}", encoding="utf-8", errors="replace")
        rel = Path(os.path.relpath(str(p), str(getattr(ctx, "cwd", "") or ".")))
        return str(rel)
    except Exception as e:
        logger.debug("长输出落盘失败: %s", e, exc_info=True)
        return None


async def run_command(command: str, ctx: "ToolContext", timeout: int = CMD_TIMEOUT,
                      meta: bool = False, max_output: int = MAX_OUTPUT,
                      split_stderr: bool = False, background: bool = False) -> str:
    pass
    pass
    pass
    if (ctx.policy_check is None
            and any(re.search(p, command) for p in INSTALL_PATTERNS)):
        return json.dumps(
            {"error": "安装类命令需要审批，但当前没有可用的安全裁决/审批通道。"},
            ensure_ascii=False)
    pass
    if ctx.env_rewrite is not None:
        command = ctx.env_rewrite(command)
    pass
    pass
    pass
    quiet_applied: list[str] = []
    if not meta and not background:
        command, quiet_applied = _quiet_rewrite(command)
    pass
    pass
    if ctx.policy_check is not None:
        verdict = await ctx.policy_check(command)
        if verdict.decision.value == "deny":
            return json.dumps({"error": "命令被安全策略拒绝",
                               "risks": [r.description for r in verdict.risks]},
                              ensure_ascii=False)
        if verdict.decision.value == "review":
            if ctx.request_approval is not None and not await ctx.request_approval(command, verdict):
                return json.dumps({"error": "命令等待人工审批被拒绝/超时",
                                   "risks": [r.description for r in verdict.risks]},
                                  ensure_ascii=False)

    if background:
        return await _start_background(command, ctx, timeout)

    try:
        code, text, stderr_text, over = await _execute(
            command, ctx, timeout, split_stderr=split_stderr, forward=True)
    except asyncio.TimeoutError:
        return err(f"命令超时({timeout}s)已终止")
    except Exception as e:
        return err(f"执行失败: {type(e).__name__}: {e}")
    if over:
        return err(
            f"输出超过硬顶 {MAX_OUTPUT_HARD} 字符已终止（不截断是为了不静默改数据）。"
            "这个量级请把结果写成文件，节点之间只传路径")

    if meta:
        pass
        pass
        body, original = _clip_clean(text, max_output)
        payload = {"ok": code == 0, "exit": code,
                   "output": body, "truncated": original != len(body),
                   "original_chars": original}
        if split_stderr:
            payload["stderr"] = _cut(stderr_text, MAX_OUTPUT)[0]
        return json.dumps(payload, ensure_ascii=False)
    shown = text if not stderr_text else f"{text}\n{stderr_text}"
    pass
    pass
    pass
    pass
    spilled = _spill_output(ctx, shown, command) if len(shown) > MAX_OUTPUT else None
    marker = "全量输出已在界面展示；结论与失败清单在下方尾部，中间省略的是进度输出"
    if spilled:
        marker = (f"完整输出已落盘 {spilled}（共 {len(shown)} 字符 / "
                  f"{len(shown.splitlines())} 行）；要看中间段落请用 "
                  f'f_read(path="{spilled}", lines="A,B")，不要重跑命令。'
                  "结论与失败清单在下方尾部")
    result = _truncate_both(f"[exit {code}]\n{shown}", MAX_OUTPUT, marker)
    pass
    pass
    if quiet_applied:
        result = f"[已自动补静默参数: {' / '.join(quiet_applied)}]\n\n" + result
    elif "pytest" in command and "-q" not in command:
        result = ("[提示] 下次跑 pytest 请带 `-q --tb=line`：一行一个 "
                  "FAILED 路径::方法，输出给全且不会被截断；"
                  "失败后用 `pytest --lf -q --tb=line` 只跑挂掉的。\n\n" + result)
    return result


async def _start_background(command: str, ctx: "ToolContext", timeout: int) -> str:
    from ....agent.bg_jobs import BG_TIMEOUT

    sid = getattr(ctx, "session_id", "") or ""

    async def _run() -> tuple[int, str]:
        pass
        pass
        code, out, err_out, over = await _execute(
            command, ctx, max(timeout, 0) or BG_TIMEOUT,
            split_stderr=False, forward=False)
        body = (out + ("\n" + err_out if err_out else "")) or ""
        if over:
            body += f"\n…[输出超过硬顶 {MAX_OUTPUT_HARD}，已截断]"
        return code, body

    try:
        job = ctx.bg_jobs.start(sid, command, _run)
    except Exception as e:
        return err(f"后台任务启动失败: {type(e).__name__}: {e}")
    return json.dumps({
        "ok": True, "background": True, "job_id": job.job_id,
        "command": command,
        "note": f"已在后台执行（{job.job_id}），立即返回。跑完后结果会自动作为一条"
                "[后台命令完成] 消息返回；期间可以继续做别的事。",
    }, ensure_ascii=False)


class _PumpState:

    __slots__ = ("over", "total")

    def __init__(self) -> None:
        self.over = False
        self.total = 0


async def _pump(stream, sink: list[str], state: _PumpState, proc, *,
                ctx: "ToolContext", push: bool) -> None:
    buf = ""
    while True:
        chunk = await stream.read(65536)
        if not chunk:
            break
        text = chunk.decode("utf-8", errors="replace")
        buf += text
        while "\n" in buf:
            line, _, buf = buf.partition("\n")
            sink.append(line + "\n")
            if push and ctx.emit_stream is not None:
                try:
                    await ctx.emit_stream({"type": "tool_output",
                                           "name": "run_command",
                                           "text": line + "\n"})
                except Exception:
                    logger.debug("推送 tool_output 失败", exc_info=True)
        pass
        state.total += len(text)
        if state.total > MAX_OUTPUT_HARD:
            state.over = True
            pass
            pass
            if buf:
                sink.append(buf)
                buf = ""
            _kill_tree(proc)
            return
    if buf:
        sink.append(buf)


async def _execute(command: str, ctx: "ToolContext", timeout: int,
                   split_stderr: bool = False, forward: bool = True
                   ) -> tuple[int, str, str, bool]:
    shell = "powershell.exe" if os.name == "nt" else "/bin/bash"
    arg = ("-c", command) if os.name != "nt" else ("/c", command)
    try:
        pass
        pass
        proc = await asyncio.create_subprocess_exec(
            shell, *arg, cwd=ctx.cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=(asyncio.subprocess.PIPE if split_stderr
                    else asyncio.subprocess.STDOUT),
            start_new_session=(os.name != "nt"),
        )
    except Exception as e:
        raise RuntimeError(f"启动失败: {e}") from e
    out_chunks: list[str] = []
    err_chunks: list[str] = []
    state = _PumpState()

    async def _drain() -> None:
        jobs = [_pump(proc.stdout, out_chunks, state, proc,
                      ctx=ctx, push=forward)]
        if split_stderr and proc.stderr is not None:
            jobs.append(_pump(proc.stderr, err_chunks, state, proc,
                              ctx=ctx, push=False))
        await asyncio.gather(*jobs)
        await proc.wait()

    try:
        await asyncio.wait_for(_drain(), timeout=timeout)
    except (asyncio.TimeoutError, Exception):
        await _finish(proc)
        raise
    return (proc.returncode, "".join(out_chunks), "".join(err_chunks),
            bool(state.over))


def _kill_tree(proc) -> None:
    try:
        if os.name != "nt":
            import signal
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        else:
            proc.kill()
    except Exception:
        try:
            proc.kill()
        except Exception:
            logger.debug("二次 kill 失败，进程已退出", exc_info=True)


async def _finish(proc) -> None:
    _kill_tree(proc)
    try:
        await asyncio.wait_for(proc.wait(), timeout=5)
    except Exception:
        logger.debug("等待进程退出失败（已退出）", exc_info=True)


def register(reg: "ToolRegistry") -> None:
    reg.register(
        "run_command",
        "在项目目录执行 shell 命令（安装类命令被禁止）。"
        "跑测试/构建/长任务请用 background=true：立即返回 job_id，不占本轮时间，"
        "跑完结果会自动随下一轮消息送回",
        {"command": {"type": "string"}, "timeout": {"type": "integer"},
         "background": {"type": "boolean",
                        "description": "true=扔后台立即返回（拿 job_id）。跑测试/构建/拉数据"
                                       "这类超过几十秒的命令都该用，别前台等"},
         "meta": {"type": "boolean",
                  "description": "true=返回 {ok,exit,output}，output 不带 [exit N] 前缀"
                                 "（工作流节点用）"},
         "max_output": {"type": "integer",
                        "description": "输出字符上限；0=不截断。工作流节点用 0，"
                                       "对话里保持默认 30000"},
         "split_stderr": {"type": "boolean",
                          "description": "true=stderr 单独放在 stderr 字段，不并入 output"}},
        run_command, ["command"])
