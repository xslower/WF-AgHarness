from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
TS_MSG_ROW = REPO / "frontend" / "src" / "kernel" / "ui" / "chat" / "MessageRow.tsx"
TS_BRIDGE = REPO / "frontend" / "src" / "kernel" / "api" / "eventBridge.ts"

pass
pass
pass
STRIP_CASES: list[str] = [
    "now: 2026年11月16日 18时7分\n你好",
    "now：2026年11月16日 18时7分\n你好",
    "now: 18时7分\n你好",
    "now: 18时7分你好",
    "  now: 18时7分   \n\n  你好",
    "now: 18时7分",
    "",
    "你好",
    "now: hello",
    "now: 5时",
    "now:18时07分\nx",
]


def _frontend_strip_regex() -> str:
    src = TS_MSG_ROW.read_text("utf-8")
    m = re.search(r"raw\.replace\(\s*/\^(.*?)/, \"\"\);", src, re.S)
    assert m, f"{TS_MSG_ROW} 里找不到 userCopyText 的 now: 剥除正则（改名/搬走了？）"
    return "^(?:" + m.group(1).rstrip() + ")"


def _js_strip(texts: list[str]) -> list[str]:
    node = shutil.which("node")
    if not node:
        pytest.skip("没有 node，无法执行前端正则（不静默通过）")
    pattern = _frontend_strip_regex()
    script = (
        "const re = new RegExp(" + json.dumps(pattern) + ");\n"
        f"const cases = {json.dumps(texts)};\n"
        "console.log(JSON.stringify(cases.map(t => t.replace(re, ''))));\n")
    out = subprocess.run([node, "-e", script], capture_output=True, text=True,
                         timeout=60)
    assert out.returncode == 0, f"node 执行前端正则失败: {out.stderr}"
    return json.loads(out.stdout)


@pytest.fixture(scope="module")
def js_stripped() -> list[str]:
    return _js_strip(STRIP_CASES)


@pytest.mark.parametrize("idx", range(len(STRIP_CASES)))
def test_now_marker_strip_agrees(idx, js_stripped):
    from app.chat.time_marker import strip_marker

    text = STRIP_CASES[idx]
    py = strip_marker(text)
    assert js_stripped[idx] == py, (
        f"前后端 now: 标注剥除结果不一致：{text!r}\n"
        f"  前端 → {js_stripped[idx]!r}\n"
        f"  后端 → {py!r}\n"
        "两边正则必须一致：不一致时用户复制到的内容会带/丢标注，且不报错")


def test_strip_regex_sources_are_equivalent():
    from app.chat.time_marker import _STRIP_RE

    assert _STRIP_RE.pattern.strip(), "后端 _STRIP_RE 是空正则"
    assert "now" in _STRIP_RE.pattern and "时" in _STRIP_RE.pattern
    assert "now" in _frontend_strip_regex()


pass


def _ts_number(path: Path, name: str) -> float:
    src = path.read_text("utf-8")
    m = re.search(rf"const {name} = ([\d_]+);", src)
    assert m, f"{path} 里找不到常量 {name}"
    return float(m.group(1).replace("_", ""))


def test_watchdog_threshold_is_larger_than_heartbeat():
    from app.api.routers.events import HEARTBEAT_SEC

    dead_after_ms = _ts_number(TS_BRIDGE, "DEAD_AFTER_MS")
    heartbeat_ms = HEARTBEAT_SEC * 1000
    assert dead_after_ms > heartbeat_ms * 2, (
        f"前端判活阈值 {dead_after_ms}ms 相对后端心跳 {heartbeat_ms}ms 太紧："
        "至少要容得下两次心跳（丢一个 ping 不该断线）")


def test_session_socket_thresholds_stay_independent():
    pass
    pass
    chat_socket = REPO / "frontend" / "src" / "kernel" / "ui" / "chat" / "chatSocket.ts"
    socket_dead = _ts_number(chat_socket, "SOCKET_DEAD_AFTER_MS")
    bridge_dead = _ts_number(TS_BRIDGE, "DEAD_AFTER_MS")
    assert socket_dead != bridge_dead, (
        "两条连接的判活阈值被改成同一个值了：它们的判活前提不同（前端自发心跳 "
        "vs 后端推 ping），统一会在其中一条上误杀")
    assert socket_dead < bridge_dead, (
        "会话 WS 的心跳间隔更短、阈值也应更短；顺序反了说明有人改了其中一边没同步")
