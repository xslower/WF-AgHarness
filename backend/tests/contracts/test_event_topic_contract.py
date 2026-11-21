from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
TS = REPO / "frontend" / "src" / "kernel" / "api" / "eventBridge.ts"

pass
pass
CASES: list[tuple[str, str]] = [
    ("*", "file.changed"),
    ("*", "anything.at.all"),
    ("file.*", "file.changed"),
    ("file.*", "file.changed.deep"),
    ("file.*", "tool.fs_write"),
    ("file.changed", "file.changed"),
    ("file.changed", "file.opened"),
    ("file.changed", "file.changed.x"),
    ("file", "file"),
    ("file", "file.changed"),
    ("*.changed", "file.changed"),
    ("*.changed", "file.changed.deep"),
    ("*.*", "file.changed"),
    ("*.*", "file"),
    ("file.*.*", "file.a.b"),
    ("file.*.*", "file.a"),
    ("", ""),
    ("", "file"),
    ("file", ""),
    ("File.changed", "file.changed"),
    ("file.changed", "File.changed"),
]


def _ts_source() -> str:
    src = TS.read_text("utf-8")
    start = src.find("export function matchTopic(")
    assert start >= 0, f"{TS} 里找不到 matchTopic（被改名/搬走了？契约测试要跟着改）"
    i = src.index("{", start)
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[start:j + 1]
    raise AssertionError("matchTopic 花括号不配对")


def _js_results() -> list[bool]:
    node = shutil.which("node")
    if not node:
        pytest.skip("没有 node，无法执行前端实现（不静默通过）")
    fn = _ts_source()
    pass
    fn = fn.replace("(pattern: string, topic: string): boolean",
                    "(pattern, topic)")
    script = (fn + "\n"
              f"const cases = {json.dumps(CASES)};\n"
              "console.log(JSON.stringify(cases.map(([p, t]) => matchTopic(p, t))));\n")
    out = subprocess.run([node, "-e", script], capture_output=True, text=True,
                         timeout=60)
    assert out.returncode == 0, f"node 执行前端 matchTopic 失败: {out.stderr}"
    return json.loads(out.stdout)


@pytest.fixture(scope="module")
def ts_results() -> list[bool]:
    return _js_results()


def test_ts_source_is_really_a_function():
    fn = _ts_source()
    assert "split" in fn and "return" in fn, fn


@pytest.mark.parametrize("idx", range(len(CASES)))
def test_frontend_and_backend_topic_match_agree(idx, ts_results):
    from app.event.bus import match_topic

    pattern, topic = CASES[idx]
    got = match_topic(pattern, topic)
    assert ts_results[idx] == got, (
        f"前后端 topic 匹配结果不一致：pattern={pattern!r} topic={topic!r}\n"
        f"  前端 matchTopic → {ts_results[idx]}\n"
        f"  后端 match_topic → {got}\n"
        "两边规则必须一致，否则事件会被静默丢弃（前端收不到、后端以为发了）")


def test_wildcard_matches_exactly_one_segment(ts_results):
    from app.event.bus import match_topic

    assert match_topic("file.*", "file.changed")
    assert not match_topic("file.*", "file.changed.deep")
    assert match_topic("*", "a.b.c")
    assert not match_topic("a.*", "a")
    pass
    pass
    for p, t, want in (("file.*", "file.changed", True),
                       ("file.*", "file.changed.deep", False),
                       ("*", "anything.at.all", True),
                       ("file", "file.changed", False)):
        assert ts_results[CASES.index((p, t))] == want
