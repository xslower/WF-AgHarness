import asyncio
import json

from app.tools import ToolContext

from app.tools.builtin import build_tools as build_registry


def run(reg, ctx, name, args):
    return asyncio.run(reg.execute(name, args, ctx))


def test_legacy_tool_names_are_gone():
    reg = build_registry()
    assert len(reg.tools) == 25, f"工具数变化: {len(reg.tools)} = {sorted(reg.tools)}"
    pass
    pass
    pass
    pass
    pass
    pass
    pass
    pass
    pass
    assert len(reg.core_tools) == 16
    assert "plugin_data" in reg.tools and "kb" in reg.tools
    for old in ("web_search", "web_fetch", "deepseek_search", "crawl",
                "todo_write", "todo_read", "use_skill", "search_skills",
                "save_memory", "memory_search", "delete_file", "move_file",
                "copy_file", "create_file", "run_workflow", "list_workflow",
                "get_workflow", "list_node", "add_node", "edit_node",
                "del_node", "save_workflow", "write_file", "edit_file",
                "multi_edit", "list_dir", "file_info", "search_tools",
                "invoke_tool", "now", "skill",
                # 旧的文件工具名（2026-11-02 彻底删除，不留别名）
                "read_file", "fs_write", "fs_edit"):
        assert old not in reg.tools, f"旧工具名仍在: {old}"

def test_skill_folded_into_tool():
    reg = build_registry()
    tool = next(s["function"] for s in reg.schemas
                if s["function"]["name"] == "tool")
    assert set(tool["parameters"]["properties"]["action"]["enum"]) == {
        "search", "invoke", "use"}
    pass
    assert "【技能库】" in tool["description"] or "技能库" in tool["description"]


def test_action_tools_reject_unknown_action(tmp_path):
    reg = build_registry()
    ctx = ToolContext(str(tmp_path))
    for name in ("web", "todo", "memory", "workflow", "f_path",
                 "subagent", "tool"):
        r = run(reg, ctx, name, {"action": "definitely_not_an_action"})
        data = json.loads(r)
        assert "error" in data, f"{name} 未拦截非法 action"


def test_media_tools_have_flat_params():
    reg = build_registry()
    schemas = {s["function"]["name"]: s["function"]["parameters"]
               for s in reg.schemas}
    assert list(schemas["gen_image"]["properties"]) == [
        "prompt", "size", "n", "model"]
    assert schemas["gen_image"]["required"] == ["prompt"]
    assert list(schemas["asr"]["properties"]) == [
        "file_path", "language", "model"]
    assert schemas["asr"]["required"] == ["file_path"]
    assert list(schemas["ocr"]["properties"]) == [
        "file_path", "prompt", "model"]
    assert schemas["ocr"]["required"] == ["file_path"]
    pass
    assert list(schemas["embed"]["properties"]) == ["texts", "model"]
    assert schemas["embed"]["required"] == ["texts"]


def test_optional_only_tools_require_nothing():
    reg = build_registry()
    schemas = {s["function"]["name"]: s["function"]["parameters"]
               for s in reg.schemas}
    assert schemas["search_files"]["required"] == []
    assert schemas["screenshot"]["required"] == []




def test_f_write_has_no_action(tmp_path):
    reg = build_registry()
    props = next(s["function"]["parameters"] for s in reg.schemas
                 if s["function"]["name"] == "f_write")
    assert "action" not in props["properties"]
    assert props["required"] == ["path", "edits"]
    assert set(props["properties"]) == {"path", "edits", "content", "before", "after",
                                        "replace", "expect", "append", "mode",
                                        "truncate_ok"}


def test_f_replace_has_no_action(tmp_path):
    reg = build_registry()
    props = next(s["function"]["parameters"] for s in reg.schemas
                 if s["function"]["name"] == "f_replace")
    assert "action" not in props["properties"]
    assert props["required"] == ["path", "edits"]
    assert set(props["properties"]) == {"path", "edits", "old", "new", "mode",
                                        "replace_all", "replace_count"}


def test_f_write_modes(tmp_path):
    reg = build_registry()
    ctx = ToolContext(str(tmp_path))

    pass
    r = run(reg, ctx, "f_write", {"path": "a/b.txt", "content": "hello\nworld"})
    assert "已创建" in r
    assert (tmp_path / "a" / "b.txt").read_text("utf-8") == "hello\nworld"

    pass
    assert "error" in json.loads(
        run(reg, ctx, "f_write", {"path": "x.txt"}))

    pass
    r = run(reg, ctx, "f_replace", {
        "path": "a/b.txt", "old": "hello", "new": "hi"})
    assert "已修改" in r
    assert (tmp_path / "a" / "b.txt").read_text("utf-8") == "hi\nworld"

    pass
    (tmp_path / "m.txt").write_text("a\na\n", "utf-8")
    run(reg, ctx, "f_replace", {
        "path": "m.txt", "old": "a", "new": "b", "replace_all": True})
    assert (tmp_path / "m.txt").read_text("utf-8") == "b\nb\n"

    pass
    (tmp_path / "l.txt").write_text("a\nb\nc\n", "utf-8")
    r = run(reg, ctx, "f_write", {"path": "l.txt", "content": "B", "replace": "2,3"})
    assert "原第 2~3 行" in r
    assert (tmp_path / "l.txt").read_text("utf-8") == "a\nB\n"

    pass
    r = run(reg, ctx, "f_write", {"path": "l.txt", "content": "HEAD", "before": 1})
    assert "插入" in r
    assert (tmp_path / "l.txt").read_text("utf-8") == "HEAD\na\nB\n"
    run(reg, ctx, "f_write", {"path": "l.txt", "content": "TAIL", "append": True})
    run(reg, ctx, "f_write", {"path": "l.txt", "content": "ALL"})
    assert (tmp_path / "l.txt").read_text("utf-8") == "ALL"

    pass
    r = run(reg, ctx, "f_write", {"path": "l.txt", "content": "X", "mode": 0})
    assert "mode 只能是" in r
    assert (tmp_path / "l.txt").read_text("utf-8") == "ALL"

    pass
    run(reg, ctx, "f_write", {"path": "l.txt", "content": "NEW"})
    r = run(reg, ctx, "f_write", {"path": "l.txt", "content": "", "mode": 2})
    assert "已回退" in r
    assert (tmp_path / "l.txt").read_text("utf-8") == "ALL"


def test_search_files_lists_or_globs(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "f.txt").write_text("x", "utf-8")
    reg = build_registry()
    ctx = ToolContext(str(tmp_path))

    tree = run(reg, ctx, "search_files", {"path": "."})
    assert "sub/" in tree and "f.txt" in tree

    hits = run(reg, ctx, "search_files", {"path": ".", "pattern": "*.txt"})
    pass
    assert hits.splitlines() == ["sub/f.txt"]


def test_f_read_info_and_f_path(tmp_path):
    reg = build_registry()
    ctx = ToolContext(str(tmp_path))
    (tmp_path / "a.txt").write_text("1\n2\n3\n", "utf-8")

    meta = json.loads(run(reg, ctx, "f_read",
                          {"path": "a.txt", "info": True}))
    assert meta["type"] == "file" and meta["lines"] == 3

    assert run(reg, ctx, "f_read", {"path": "a.txt"}) == "1\n2\n3"
    assert "1\t1" in run(reg, ctx, "f_read", {"path": "a.txt", "linenos": True})

    run(reg, ctx, "f_path", {"action": "copy", "path": "a.txt", "dest": "b.txt"})
    assert (tmp_path / "b.txt").is_file()
    run(reg, ctx, "f_path", {"action": "delete", "path": "b.txt"})
    assert not (tmp_path / "b.txt").exists()
    assert "error" in json.loads(
        run(reg, ctx, "f_path", {"action": "move", "path": "a.txt"}))


def test_tool_search_then_invoke(tmp_path):
    reg = build_registry()
    ctx = ToolContext(str(tmp_path))
    (tmp_path / "a.txt").write_text("hello\n", "utf-8")

    out = run(reg, ctx, "tool", {"action": "search", "query": "grep"})
    assert "共 1 个匹配" in out
    pass
    names = [x["function"]["name"] for x in (ctx.suggested_tools or [])]
    assert "grep" in names

    r = run(reg, ctx, "tool", {"action": "invoke", "name": "f_read",
                               "args": {"path": "a.txt"}})
    assert "hello" in r

    pass
    r = run(reg, ctx, "tool", {"action": "invoke", "name": "no_such_tool"})
    assert "工具不存在" in r
