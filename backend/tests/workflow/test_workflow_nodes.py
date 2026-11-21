from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.provider.models import ModelInfo, Provider
from app.provider.gateway import Chunk
from app.workflow.nodes.registry import NodeContext
from app.workflow import WorkflowEngine, WorkflowError


pass
class FakeGw:

    def __init__(self, replies=None, image=None, asr=None, providers=None):
        self.replies = list(replies or [])
        self.image = image or {"ok": True, "images": ["data/images/a.png"]}
        self.asr = asr or {"ok": True, "text": "语音内容"}
        self.calls: list[dict] = []
        self.config = SimpleNamespace(
            providers=providers if providers is not None else [
                Provider(id="p", name="p", baseUrl="", apiKey="",
                         models=[ModelInfo(id="m")])],
            # 队列非空才能通过「跑前体检」的队列校验（本文件的桩不做真调用）
            queues=SimpleNamespace(parent=["p/m"], child=["p/m"], summary=[]),
            settings=SimpleNamespace(policy="yolo"))
        pass
        pass
        from app.provider.registry import ModelRegistry
        self.registry = ModelRegistry(self.config)

    async def chat_stream(self, messages, tools=None, effort="medium",
                          spec="", session_id=""):
        self.calls.append({"messages": messages, "tools": tools, "spec": spec})
        reply = self.replies.pop(0) if self.replies else "默认回复"
        for c in reply:
            yield c

    async def generate_image(self, prompt, spec="", size="1024x1024", n=1):
        self.calls.append({"image_prompt": prompt, "size": size, "n": n, "spec": spec})
        return self.image

    async def transcribe_audio(self, path, spec=""):
        self.calls.append({"asr_path": path, "spec": spec})
        return self.asr

    async def ocr_image(self, path, prompt="", spec=""):
        entry = self.registry.get(spec) if spec else None
        if entry is None:
            entry = self.registry.first_of_kind("ocr")
        if entry is None:
            return {"ok": False, "error": "未指定模型且配置中无 kind=ocr 模型"}
        from pathlib import Path
        fp = Path(path)
        if not fp.is_file():
            return {"ok": False, "error": f"图片不存在: {path}"}
        import base64
        mime = "image/png" if str(path).lower().endswith(".png") else "image/jpeg"
        b64 = base64.b64encode(fp.read_bytes()).decode()
        self.calls.append({"messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {
                "url": f"data:{mime};base64,{b64}"}}]}], "spec": entry.spec})
        return {"ok": True, "text": "识别结果", "model": entry.spec}


class FakeRegistry:

    def __init__(self, results=None, schemas=None):
        self.results = results or {}
        self.schemas = schemas or []
        self.calls: list[tuple[str, dict]] = []

    async def execute(self, name, args, ctx):
        self.calls.append((name, args))
        return self.results.get(name, f"{name} 结果")


class FakeMcp:
    def __init__(self, result="mcp 结果"):
        self.result = result
        self.calls: list[tuple[str, dict]] = []

    async def call(self, name, args):
        self.calls.append((name, args))
        return self.result


def text(*parts) -> list[Chunk]:
    return [Chunk(type="text", text=p) for p in parts]


@pytest.fixture
def run(tmp_path):
    async def _run(nodes, inputs=None, *, gw=None, reg=None, mcp=None,
                   nodes_reg=None):
        eng = WorkflowEngine(gateway=gw or FakeGw(),
                             registry=reg or FakeRegistry(),
                             mcp=mcp, workspace=str(tmp_path),
                             workflows_dir=tmp_path / "wf",
                             nodes=nodes_reg)
        return await eng.execute_definition({"name": "t", "nodes": nodes},
                                            inputs or {})

    return _run


def nodes_of(rec) -> dict:
    return rec.node_states


pass
class SeqRegistry(FakeRegistry):

    def __init__(self, outs):
        super().__init__()
        self.outs = list(outs)

    async def execute(self, name, args, ctx):
        self.calls.append((name, args))
        return self.outs.pop(0) if self.outs else self.outs[-1:][0] if self.outs else ""


async def test_back_edge_is_do_while(run):
    reg = SeqRegistry(["x", "xx", "xxx"])
    rec = await run([
        {"id": "b1", "type": "code", "code": "pass", "next": "c1"},
        {"id": "c1", "type": "condition", "expr": "len(${b1}) < 3",
         "true": "b1", "false": "", "maxVisits": 5},
    ], reg=reg)
    assert rec.status == "done", rec.error
    assert len(reg.calls) == 3
    assert rec.node_states["c1"]["status"] == "done"


async def test_back_edge_stops_at_max_visits(run):
    rec = await run([
        {"id": "b1", "type": "code", "code": "pass", "next": "c1"},
        {"id": "c1", "type": "condition", "expr": "1 == 1",
         "true": "b1", "false": "", "maxVisits": 3},
    ])
    assert rec.status == "done", rec.error
    assert any(w["code"] == "max-visits" and w["node"] == "c1"
               for w in rec.warnings), rec.warnings
    pass
    assert rec.node_states["c1"]["status"] == "done"


async def test_condition_does_not_pollute_prev(run):
    reg = SeqRegistry(["上游内容", "第二轮", "结束"])
    rec = await run([
        {"id": "a1", "type": "exec", "command": "echo start", "next": "c1"},
        {"id": "c1", "type": "condition", "expr": "${b2} != \"结束\"",
         "true": "b2", "false": "", "maxVisits": 5},
        {"id": "b2", "type": "exec", "command": "echo ${prev}", "next": "c1"},
    ], reg=reg)
    assert rec.status == "done", rec.error
    cmds = [args["command"] for name, args in reg.calls
            if name == "run_command" and str(args.get("command", "")).startswith("echo ")]
    assert cmds == ["echo start", "echo 上游内容", "echo 第二轮"]


async def test_condition_output_has_pass_field(run):
    rec = await run([
        {"id": "c1", "type": "condition", "expr": "1 == 1",
         "true": "w1", "false": "w2"},
        {"id": "w1", "type": "write", "path": "true.txt", "content": "${c1.pass}"},
        {"id": "w2", "type": "write", "path": "false.txt", "content": "x"},
    ])
    assert rec.status == "done", rec.error
    assert json.loads(rec.node_states["c1"]["output"])["pass"] is True


async def test_while_is_rejected_with_migration_hint(run):
    with pytest.raises(WorkflowError) as e:
        await run([{"id": "w", "type": "while", "expr": "1 == 1", "body": "b1"}])
    assert "while" in str(e.value) and "condition 回边" in str(e.value)


pass
async def test_ocr_uses_kind_ocr_model(run, tmp_path):
    img = tmp_path / "p.png"
    img.write_bytes(b"\x89PNG\r\n")
    gw = FakeGw(replies=[text("识别结果")],
                providers=[Provider(id="p1", name="p", baseUrl="", apiKey="",
                                    models=[ModelInfo(id="glm-ocr", kind="ocr")])])
    rec = await run([{"id": "o", "type": "ocr", "path": str(img)}], gw=gw)
    assert rec.status == "done", rec.error
    assert rec.node_states["o"]["output"] == "识别结果"
    sent = gw.calls[0]
    pass
    assert sent["spec"] == "p/glm-ocr"
    pass
    content = sent["messages"][0]["content"]
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")


async def test_ocr_without_model_raises(run, tmp_path):
    img = tmp_path / "p.jpg"
    img.write_bytes(b"x")
    rec = await run([{"id": "o", "type": "ocr", "path": str(img)}])
    assert rec.status == "failed"
    assert "未指定模型且配置中无 kind=ocr 模型" in rec.error


async def test_ocr_missing_file_raises(run, tmp_path):
    gw = FakeGw(providers=[Provider(id="p", name="p", baseUrl="", apiKey="",
                                    models=[ModelInfo(id="m", kind="ocr")])])
    rec = await run([{"id": "o", "type": "ocr", "path": str(tmp_path / "no.png")}], gw=gw)
    assert rec.status == "failed" and "图片不存在" in rec.error


async def test_image_node_returns_paths(run):
    gw = FakeGw(image={"ok": True, "images": ["data/images/x.png"]})
    rec = await run([{"id": "i", "type": "image", "prompt": "画一只猫",
                      "size": "512x512", "n": 2}], gw=gw)
    assert rec.status == "done", rec.error
    assert json.loads(rec.node_states["i"]["output"])["images"] == ["data/images/x.png"]
    assert gw.calls[0] == {"image_prompt": "画一只猫", "size": "512x512", "n": 2, "spec": ""}


async def test_image_node_error_propagates(run):
    gw = FakeGw(image={"ok": False, "error": "额度不足"})
    rec = await run([{"id": "i", "type": "image", "prompt": "x"}], gw=gw)
    assert rec.status == "failed" and "额度不足" in rec.error


async def test_asr_node_returns_text(run, tmp_path):
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"x")
    gw = FakeGw(asr={"ok": True, "text": "你好世界"})
    rec = await run([{"id": "s", "type": "asr", "path": str(audio)}], gw=gw)
    assert rec.status == "done", rec.error
    assert rec.node_states["s"]["output"] == "你好世界"


async def test_asr_node_error_propagates(run, tmp_path):
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"x")
    gw = FakeGw(asr={"ok": False, "error": "无 asr 模型"})
    rec = await run([{"id": "s", "type": "asr", "path": str(audio)}], gw=gw)
    assert rec.status == "failed" and "无 asr 模型" in rec.error


pass
async def test_mcp_node_passes_argsjson_with_vars(run):
    mcp = FakeMcp("工具结果")
    rec = await run([{"id": "m", "type": "mcp", "tool": "mcp__srv__echo",
                      "argsJson": '{"text": "${inputs.q}", "n": 2}'}],
                    inputs={"q": "你好"}, mcp=mcp)
    assert rec.status == "done", rec.error
    assert mcp.calls == [("mcp__srv__echo", {"text": "你好", "n": 2})]
    assert rec.node_states["m"]["output"] == "工具结果"


async def test_mcp_node_bad_json_raises(run):
    rec = await run([{"id": "m", "type": "mcp", "tool": "t", "argsJson": "{不是json"}],
                    mcp=FakeMcp())
    assert rec.status == "failed" and "参数 JSON 无效" in rec.error


async def test_mcp_node_without_mcp_raises(run):
    rec = await run([{"id": "m", "type": "mcp", "tool": "t"}])
    assert rec.status == "failed" and "MCP 不可用" in rec.error


pass
async def test_web_fetch_calls_web_tool(run):
    reg = FakeRegistry({"web": "# 页面正文"})
    rec = await run([{"id": "f", "type": "web_fetch", "query": "${inputs.u}"}],
                    inputs={"u": "https://example.com"}, reg=reg)
    assert rec.status == "done", rec.error
    assert reg.calls == [("web", {"query": "https://example.com"})]


async def test_web_fetch_error_raises(run):
    reg = FakeRegistry({"web": '{"error": "抓取失败"} '})
    rec = await run([{"id": "f", "type": "web_fetch", "query": "https://x"}], reg=reg)
    assert rec.status == "failed" and "web_fetch 节点失败" in rec.error


async def test_web_search_passes_limit(run):
    reg = FakeRegistry({"web": "搜索结果"})
    rec = await run([{"id": "s", "type": "web_search", "query": "python", "limit": 3}],
                    reg=reg)
    assert rec.status == "done", rec.error
    assert reg.calls == [("web", {"query": "python", "limit": 3})]


pass
async def test_condition_llm_mode_true_branch(run):
    gw = FakeGw(replies=[text("true")])
    rec = await run([
        {"id": "c", "type": "condition", "mode": "llm", "expr": "内容是问候语",
         "input": "你好", "true": "y", "false": "n"},
        {"id": "y", "type": "write", "path": "yes.txt", "content": "Y", "next": ""},
        {"id": "n", "type": "write", "path": "no.txt", "content": "N", "next": ""},
    ], gw=gw)
    assert rec.status == "done", rec.error
    assert gw.calls[0]["spec"] == "summary"
    assert "condition=true" in rec.node_states["c"]["output"]
    assert "llm 判断" in rec.node_states["c"]["output"]
    assert (rec.node_states["y"]["output"])


async def test_condition_llm_mode_spec_can_be_overridden(run, tmp_path):
    gw = FakeGw(replies=[text("true")])
    rec = await run([
        {"id": "c", "type": "condition", "mode": "llm", "expr": "内容是问候语",
         "input": "你好", "model": "child", "true": "y", "false": "n"},
        {"id": "y", "type": "write", "path": "ov.txt", "content": "Y", "next": ""},
        {"id": "n", "type": "write", "path": "nv.txt", "content": "N", "next": ""},
    ], gw=gw)
    assert rec.status == "done", rec.error
    assert gw.calls[0]["spec"] == "child"


async def test_condition_llm_mode_false_branch(run, tmp_path):
    gw = FakeGw(replies=[text("false")])
    rec = await run([
        {"id": "c", "type": "condition", "mode": "llm", "expr": "是问候语",
         "input": "报个错", "true": "y", "false": "n"},
        {"id": "y", "type": "write", "path": "yes2.txt", "content": "Y", "next": ""},
        {"id": "n", "type": "write", "path": "no2.txt", "content": "N", "next": ""},
    ], gw=gw)
    assert rec.status == "done", rec.error
    assert "condition=false" in rec.node_states["c"]["output"]
    assert (tmp_path / "no2.txt").exists()
    assert not (tmp_path / "yes2.txt").exists()


pass
async def test_llm_json_format_retries_then_succeeds(run):
    gw = FakeGw(replies=[text("这不是JSON"), text('{"title": "标题"}')])
    rec = await run([{"id": "l", "type": "llm", "prompt": "生成",
                      "format": "json", "jsonFields": "title"}], gw=gw)
    assert rec.status == "done", rec.error
    out = rec.node_states["l"]["output"]
    pass
    assert json.loads(out) == {"title": "标题"}
    pass
    retry_msgs = gw.calls[1]["messages"]
    assert retry_msgs[-1]["role"] == "user" and "不符合要求" in retry_msgs[-1]["content"]
    assert any(m["role"] == "assistant" for m in retry_msgs)


async def test_llm_json_format_fails_after_3_retries(run):
    gw = FakeGw(replies=[text("坏")] * 4)
    rec = await run([{"id": "l", "type": "llm", "prompt": "x",
                      "format": "json", "jsonFields": "a"}], gw=gw)
    assert rec.status == "failed"
    assert "JSON 格式错误" in rec.error


async def test_llm_json_accepts_top_level_array(run):
    gw = FakeGw(replies=[text('[{"shot": "A"}, {"shot": "B"}]')])
    rec = await run([{"id": "l", "type": "llm", "prompt": "分镜", "format": "json"}],
                    gw=gw)
    assert rec.status == "done", rec.error
    assert json.loads(rec.node_states["l"]["output"]) == [{"shot": "A"}, {"shot": "B"}]


async def test_llm_yaml_format_normalizes_to_json(run):
    yml = "scenes:\n  - id: 1\n    shot: 开场\n  - id: 2\n    shot: 结尾\n"
    gw = FakeGw(replies=[text(yml)])
    rec = await run([{"id": "s1", "type": "llm", "prompt": "分镜",
                      "format": "yaml", "next": "w1"},
                     {"id": "w1", "type": "write", "path": "${s1.scenes.0.shot}.txt",
                      "content": "${s1.scenes.1.shot}"}], gw=gw)
    assert rec.status == "done", rec.error
    assert json.loads(rec.node_states["s1"]["output"])["scenes"][0]["shot"] == "开场"


async def test_llm_yaml_top_level_list(run, tmp_path):
    gw = FakeGw(replies=[text("- shot: 一\n- shot: 二\n")])
    rec = await run([{"id": "s1", "type": "llm", "prompt": "分镜",
                      "format": "yaml", "next": "w1"},
                     {"id": "w1", "type": "write", "path": "o.txt",
                      "content": "${s1.1.shot}"}], gw=gw)
    assert rec.status == "done", rec.error
    assert json.loads(rec.node_states["s1"]["output"]) == [{"shot": "一"},
                                                            {"shot": "二"}]
    assert (tmp_path / "o.txt").read_text("utf-8") == "二"


async def test_llm_yaml_bad_syntax_retries_then_succeeds(run):
    gw = FakeGw(replies=[text("- a: [未闭合"), text("- a: 1\n")])
    rec = await run([{"id": "s1", "type": "llm", "prompt": "x", "format": "yaml"}],
                    gw=gw)
    assert rec.status == "done", rec.error
    out = rec.node_states["s1"]["output"]
    assert json.loads(out.split("\n[")[0]) == [{"a": 1}]
    assert "不符合要求" in gw.calls[1]["messages"][-1]["content"]


async def test_llm_list_format_strips_numbering(run):
    gw = FakeGw(replies=[text("1. 苹果\n2) 香蕉\n- 橙子\n\n")])
    rec = await run([{"id": "l", "type": "llm", "prompt": "列水果", "format": "list"}],
                    gw=gw)
    assert rec.status == "done", rec.error
    assert rec.node_states["l"]["output"] == "苹果\n香蕉\n橙子"


async def test_llm_empty_reply_raises(run):
    gw = FakeGw(replies=[text("   ")])
    rec = await run([{"id": "l", "type": "llm", "prompt": "x"}], gw=gw)
    assert rec.status == "failed" and "空回复" in rec.error


async def test_llm_docs_are_prepended(run, tmp_path):
    d = tmp_path / "doc.md"
    d.write_text("文档正文", "utf-8")
    gw = FakeGw(replies=[text("ok")])
    rec = await run([{"id": "l", "type": "llm", "prompt": "总结",
                      "docs": str(d)}], gw=gw)
    assert rec.status == "done", rec.error
    prompt = gw.calls[0]["messages"][0]["content"]
    assert "[文档: doc.md]" in prompt and "文档正文" in prompt
    assert prompt.rstrip().endswith("总结")


async def test_llm_docs_missing_blocks_run(run, tmp_path):
    d = tmp_path / "doc.md"
    d.write_text("文档正文", "utf-8")
    with pytest.raises(WorkflowError) as err:
        await run([{"id": "l", "type": "llm", "prompt": "总结",
                    "docs": f"{d}\n{tmp_path/'missing.md'}"}])
    assert "missing.md" in str(err.value)


async def test_llm_tools_off_means_plain_chat(run):
    gw = FakeGw(replies=[text("纯文本")])
    reg = FakeRegistry(schemas=[{"function": {"name": "read_file"}}])
    rec = await run([{"id": "l", "type": "llm", "prompt": "x", "tools": "off"}],
                    gw=gw, reg=reg)
    assert rec.status == "done", rec.error
    assert gw.calls[0]["tools"] is None


async def test_llm_tools_loop_executes_tool_then_answers(run):
    tool_round = [
        Chunk(type="tool_meta", text=json.dumps({"id": "c1", "name": "grep"}),
              tool_index=0),
        Chunk(type="tool_args", text='{"key": ["x"]}', tool_index=0),
    ]
    gw = FakeGw(replies=[tool_round, text("最终答案")])
    reg = FakeRegistry({"grep": "命中 1 处"}, schemas=[{"function": {"name": "grep"}}])
    rec = await run([{"id": "l", "type": "llm", "prompt": "查一下", "tools": "auto"}],
                    gw=gw, reg=reg)
    assert rec.status == "done", rec.error
    assert rec.node_states["l"]["output"] == "最终答案"
    assert reg.calls == [("grep", {"key": ["x"]})]
    pass
    assert gw.calls[1]["messages"][-1] == {"role": "tool", "tool_call_id": "c1",
                                           "content": "命中 1 处"}


async def test_llm_tools_whitelist_filters_schemas(run):
    gw = FakeGw(replies=[text("ok")])
    reg = FakeRegistry(schemas=[{"function": {"name": "grep"}},
                                {"function": {"name": "read_file"}}])
    rec = await run([{"id": "l", "type": "llm", "prompt": "x", "tools": "grep"}],
                    gw=gw, reg=reg)
    assert rec.status == "done", rec.error
    assert [s["function"]["name"] for s in gw.calls[0]["tools"]] == ["grep"]


async def test_llm_tools_whitelist_all_missing_raises(run):
    gw = FakeGw(replies=[text("ok")])
    reg = FakeRegistry(schemas=[{"function": {"name": "grep"}}])
    rec = await run([{"id": "l", "type": "llm", "prompt": "x", "tools": "nope"}],
                    gw=gw, reg=reg)
    assert rec.status == "failed" and "指定的工具均不可用" in rec.error


async def test_llm_tools_auto_without_tools_falls_back_to_chat(run):
    gw = FakeGw(replies=[text("纯文本")])
    rec = await run([{"id": "l", "type": "llm", "prompt": "x", "tools": "auto"}],
                    gw=gw)
    assert rec.status == "done", rec.error
    assert gw.calls[0]["tools"] is None
    assert rec.node_states["l"]["output"] == "纯文本"


async def test_llm_node_passes_one_spec(run):
    gw = FakeGw(replies=[text("ok"), text("ok")])
    rec = await run([{"id": "l", "type": "llm", "prompt": "x",
                      "model": "child"}], gw=gw)
    assert rec.status == "done", rec.error
    assert gw.calls[0]["spec"] == "child"
    rec = await run([{"id": "l", "type": "llm", "prompt": "x",
                      "model": "p/m"}], gw=gw)
    assert rec.status == "done", rec.error
    assert gw.calls[1]["spec"] == "p/m"


async def test_llm_node_without_model_defaults_to_summary(run):
    gw = FakeGw(replies=[text("ok")])
    rec = await run([{"id": "l", "type": "llm", "prompt": "x"}], gw=gw)
    assert rec.status == "done", rec.error
    assert gw.calls[0]["spec"] == "summary"


async def test_llm_node_tools_loop_still_defaults_to_summary(run):
    from app.workflow.nodes.registry import NodeContext
    import app.workflow.nodes.llm as llm_mod
    gw = FakeGw(replies=[text("ok")])
    ctx = NodeContext(gateway=gw, run_id="rid", tools=None)
    got = await llm_mod._chat_with_tools(ctx, [{"role": "user", "content": "x"}],
                                         {"id": "l", "prompt": "x", "tools": "off"})
    assert got == "ok"
    assert gw.calls[0]["spec"] == "summary"
