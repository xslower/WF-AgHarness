from __future__ import annotations

import asyncio
import json

import pytest

from app.provider.gateway import Chunk
from app.provider.stream import collect_text
from app.util.llm_out import extract_fenced, last_json_value, scan_json_values
from app.tools.builtin import build_tools as build_registry


pass
def text(t: str) -> list[Chunk]:
    return [Chunk(type="text", text=t)]


def reason_then(*, think: str, answer: str) -> list[Chunk]:
    return [Chunk(type="reason", text=think), Chunk(type="text", text=answer)]


class Gw:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls: list[dict] = []

    async def chat_stream(self, messages, tools=None, effort="medium",
                          spec="", session_id=""):
        self.calls.append({"messages": [dict(m) for m in messages]})
        reply = self.replies.pop(0) if self.replies else []
        for c in reply:
            yield c


def engine(tmp_path, gw):
    from app.workflow import WorkflowEngine
    return WorkflowEngine(gateway=gw, registry=build_registry(),
                          agent_runner=None, workspace=str(tmp_path),
                          workflows_dir=tmp_path / "wf")


def run_wf(tmp_path, gw, node):
    (tmp_path / "wf").mkdir(exist_ok=True)
    eng = engine(tmp_path, gw)
    eng.save({"name": "t", "nodes": [node]})
    return asyncio.run(eng.execute_sync("t", {}))


pass
def test_extract_fenced_takes_last_matching_block():
    out = ('先分析一下：\n```json\n{"wrong": 1}\n```\n'
           '再想想……还是这样：\n```json\n{"ok": 2}\n```\n以上。')
    body, err = extract_fenced(out, "json")
    assert err == "" and json.loads(body) == {"ok": 2}


def test_extract_fenced_accepts_untagged_and_yaml_tag():
    assert json.loads(extract_fenced("```\n[1, 2]\n```", "json")[0]) == [1, 2]
    assert extract_fenced("```yaml\na: 1\n```", "yaml")[0].strip() == "a: 1"


def test_extract_fenced_reports_missing_block():
    body, err = extract_fenced("没有代码块，只有文字", "json")
    assert body is None and "没有代码块" in err


def test_last_json_value_skips_thinking_braces():
    out = '我需要先想想 {} 这个问题……最终结果：{"title": "标题"}'
    assert last_json_value(out) == {"title": "标题"}
    starts = [i for i, _ in scan_json_values(out)]
    assert len(starts) == 2


pass
@pytest.mark.asyncio
async def test_collect_text_ignores_reason():
    async def stream():
        yield Chunk(type="reason", text="内心独白")
        yield Chunk(type="text", text="正文")
    assert await collect_text(stream()) == "正文"


@pytest.mark.asyncio
async def test_collect_text_raises_when_only_reason():
    from app.provider.gateway import EmptyResponseError

    async def stream():
        yield Chunk(type="reason", text="只有思考")
    with pytest.raises(EmptyResponseError):
        await collect_text(stream())


def test_llm_text_format_excludes_reason(tmp_path):
    gw = Gw([reason_then(think="我们要解析任务……" * 20, answer="最终答案")])
    rec = run_wf(tmp_path, gw, {"id": "l", "type": "llm", "prompt": "x"})
    assert rec.status == "done", rec.error
    assert rec.node_states["l"]["output"] == "最终答案"


def test_llm_json_ignores_braces_in_reason(tmp_path):
    gw = Gw([reason_then(
        think='我需要输出 {"segments": []} 这种结构，先试 ```json\n{}\n``` 再说。',
        answer='好的，结果如下：\n```json\n{"segments": [{"index": 1}]}\n```')])
    rec = run_wf(tmp_path, gw, {"id": "l", "type": "llm", "prompt": "分镜",
                                "format": "json"})
    assert rec.status == "done", rec.error
    assert json.loads(rec.node_states["l"]["output"]) == {
        "segments": [{"index": 1}]}


def test_llm_json_prompt_forbids_nothing_but_asks_fence(tmp_path):
    gw = Gw([text('```json\n{"a": 1}\n```')])
    run_wf(tmp_path, gw, {"id": "l", "type": "llm", "prompt": "x",
                          "format": "json", "jsonFields": "a"})
    prompt = gw.calls[0]["messages"][0]["content"]
    assert "```json" in prompt and "[输出协议]" in prompt
    assert "正文不限" in prompt


pass
def test_llm_json_no_fence_repairs_inline_json_without_retry(tmp_path):
    gw = Gw([text('前言 {"a": 1} 后记'), text('```json\n{"a": 1}\n```')])
    rec = run_wf(tmp_path, gw, {"id": "l", "type": "llm", "prompt": "x",
                                "format": "json"})
    assert rec.status == "done", rec.error
    assert json.loads(rec.node_states["l"]["output"]) == {"a": 1}
    assert len(gw.calls) == 1


def test_llm_json_no_fence_retries_with_protocol(tmp_path):
    gw = Gw([text("我不会输出结构化结果"), text('```json\n{"a": 1}\n```')])
    rec = run_wf(tmp_path, gw, {"id": "l", "type": "llm", "prompt": "x",
                                "format": "json"})
    assert rec.status == "done", rec.error
    assert json.loads(rec.node_states["l"]["output"]) == {"a": 1}
    retry = gw.calls[1]["messages"]
    pass
    assert any(m.get("role") == "assistant" for m in retry)
    assert "```json" in retry[-1]["content"]


def test_llm_json_fallback_after_emphasis(tmp_path):
    gw = Gw([text("没有代码块"),
             text('分析完就这些 {} 然后答案：{"a": 2} 结束')])
    rec = run_wf(tmp_path, gw, {"id": "l", "type": "llm", "prompt": "x",
                                "format": "json"})
    assert rec.status == "done", rec.error
    out = rec.node_states["l"]["output"]
    assert json.loads(out) == {"a": 2}


def test_llm_json_broken_block_retries(tmp_path):
    gw = Gw([text('```json\n{"a": }\n```'), text('```json\n{"a": 3}\n```')])
    rec = run_wf(tmp_path, gw, {"id": "l", "type": "llm", "prompt": "x",
                                "format": "json"})
    assert rec.status == "done", rec.error
    assert json.loads(rec.node_states["l"]["output"]) == {"a": 3}


def test_llm_yaml_ignores_reason(tmp_path):
    gw = Gw([reason_then(think="先想想 while scanning a simple key …",
                         answer='结果：\n```yaml\nscenes:\n  - id: 1\n```')])
    rec = run_wf(tmp_path, gw, {"id": "l", "type": "llm", "prompt": "x",
                                "format": "yaml"})
    assert rec.status == "done", rec.error
    assert json.loads(rec.node_states["l"]["output"])["scenes"][0]["id"] == 1


def test_llm_json_no_fence_logs_reason(tmp_path, monkeypatch):
    import app.workflow as wmod
    monkeypatch.setattr(wmod, "DATA_DIR", tmp_path)
    gw = Gw([text("完全不是 JSON"), text('```json\n{"a": 1}\n```')])
    rec = run_wf(tmp_path, gw, {"id": "l", "type": "llm", "prompt": "x",
                                "format": "json"})
    assert rec.status == "done", rec.error
    log = (tmp_path / "wf-json-errors.log").read_text("utf-8")
    assert "no_fence=1" in log
