from __future__ import annotations

import json

import pytest

from app.tools import ToolContext
from app.tools.builtin.fs.config_write import config_write

NASTY = [
    '含 "双引号" 的值', "含 : 冒号", "#井号开头", "yes", "01", "1.0",
    "2026-11-21", "多行\n文本", "中文与 emoji 🎉", "", "a: b",
]


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(str(tmp_path))


def put(tmp_path, name: str, text: str):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, "utf-8")
    return p


pass

async def test_json_set_keeps_indent_and_key_order(ctx, tmp_path):
    p = put(tmp_path, "c.json", '{\n    "a": 1,\n    "中文": "值"\n}\n')
    r = await config_write("c.json", ctx,
                           ops=[{"op": "set", "path": "a", "value": 2}])
    assert "已写入" in r
    text = p.read_text("utf-8")
    assert text.startswith('{\n    "a": 2,'), text
    assert list(json.loads(text)) == ["a", "中文"]


async def test_json_nested_create_list_index_append(ctx, tmp_path):
    p = put(tmp_path, "c.json", '{"a": {"b": [{"x": 1}]}}\n')
    await config_write("c.json", ctx, ops=[
        {"op": "set", "path": "a.b.0.y", "value": 2},
        {"op": "set", "path": "a.b.1", "value": {"x": 9}},
    ])
    assert json.loads(p.read_text("utf-8")) == {
        "a": {"b": [{"x": 1, "y": 2}, {"x": 9}]}}


async def test_json_preserves_crlf_and_no_trailing_newline(ctx, tmp_path):
    p = tmp_path / "c.json"
    p.write_bytes(b'{\r\n  "a": 1\r\n}')
    await config_write("c.json", ctx, ops=[{"op": "set", "path": "a", "value": 9}])
    raw = p.read_bytes()
    assert b"\r\n" in raw and not raw.endswith(b"\n")
    assert json.loads(raw.decode("utf-8")) == {"a": 9}


async def test_json_unicode_escape_style_kept(ctx, tmp_path):
    p = put(tmp_path, "c.json", '{\n  "k": "\\u4e2d\\u6587"\n}\n')
    await config_write("c.json", ctx,
                       ops=[{"op": "set", "path": "n", "value": "中文"}])
    text = p.read_text("utf-8")
    assert "\\u4e2d\\u6587" in text
    assert json.loads(text)["k"] == "中文"


async def test_json_nasty_values_roundtrip(ctx, tmp_path):
    p = put(tmp_path, "c.json", "{}\n")
    ops = [{"op": "set", "path": f"k{i}", "value": v, "as_string": True}
           for i, v in enumerate(NASTY)]
    await config_write("c.json", ctx, ops=ops)
    got = json.loads(p.read_text("utf-8"))
    assert got == {f"k{i}": v for i, v in enumerate(NASTY)}


async def test_json_stringified_object_is_coerced(ctx, tmp_path):
    p = put(tmp_path, "c.json", "{}\n")
    r = await config_write("c.json", ctx, ops=[
        {"op": "set", "path": "a", "value": '{"x": 1,}'}])
    assert "JSON 字符串" in r
    assert json.loads(p.read_text("utf-8")) == {"a": {"x": 1}}


async def test_json_as_string_keeps_literal(ctx, tmp_path):
    p = put(tmp_path, "c.json", "{}\n")
    await config_write("c.json", ctx, ops=[
        {"op": "set", "path": "a", "value": '{"x": 1}', "as_string": True}])
    assert json.loads(p.read_text("utf-8")) == {"a": '{"x": 1}'}


async def test_json_merge_delete_append(ctx, tmp_path):
    p = put(tmp_path, "c.json", '{"a": {"b": 1, "c": 2}, "t": [1]}\n')
    r = await config_write("c.json", ctx, ops=[
        {"op": "merge", "path": "a", "value": {"c": 3, "d": 4}},
        {"op": "delete", "path": "a.b"},
        {"op": "append", "path": "t", "value": 2},
    ])
    assert "合并 a.d" in r
    assert json.loads(p.read_text("utf-8")) == {"a": {"c": 3, "d": 4}, "t": [1, 2]}


async def test_json_replace_whole_doc(ctx, tmp_path):
    p = put(tmp_path, "c.json", '{"a": 1}\n')
    await config_write("c.json", ctx,
                       ops=[{"op": "replace", "value": {"z": [1, 2]}}])
    assert json.loads(p.read_text("utf-8")) == {"z": [1, 2]}


pass

async def test_bad_path_aborts_whole_batch(ctx, tmp_path):
    src = '{"a": 1}\n'
    p = put(tmp_path, "c.json", src)
    r = await config_write("c.json", ctx, ops=[
        {"op": "set", "path": "a", "value": 2},
        {"op": "delete", "path": "nope"},
    ])
    assert "路径不存在" in r and "现有键" in r
    assert p.read_text("utf-8") == src


async def test_delete_suggests_near_keys(ctx, tmp_path):
    p = put(tmp_path, "c.json", '{"timeout": 1, "retries": 2}\n')
    r = await config_write("c.json", ctx, ops=[{"op": "delete", "path": "time_out"}])
    assert "相近的键" in r and "timeout" in r


async def test_scalar_parent_is_rejected(ctx, tmp_path):
    src = '{"a": "x"}\n'
    p = put(tmp_path, "c.json", src)
    r = await config_write("c.json", ctx,
                           ops=[{"op": "set", "path": "a.b", "value": 1}])
    assert "标量" in r
    assert p.read_text("utf-8") == src


async def test_list_index_out_of_range(ctx, tmp_path):
    p = put(tmp_path, "c.json", '{"t": [1]}\n')
    r = await config_write("c.json", ctx,
                           ops=[{"op": "set", "path": "t.5", "value": 1}])
    assert "下标越界" in r


async def test_unknown_suffix_needs_format(ctx, tmp_path):
    p = put(tmp_path, "c.txt", "{}\n")
    r = await config_write("c.txt", ctx,
                           ops=[{"op": "set", "path": "a", "value": 1}])
    assert "认不出" in r and "format" in r
    r2 = await config_write("c.txt", ctx, format="json",
                            ops=[{"op": "set", "path": "a", "value": 1}])
    assert "已写入" in r2


async def test_nan_value_rejected(ctx, tmp_path):
    p = put(tmp_path, "c.json", "{}\n")
    r = await config_write("c.json", ctx,
                           ops=[{"op": "set", "path": "a", "value": float("nan")}])
    assert "error" in r
    assert p.read_text("utf-8") == "{}\n"


async def test_broken_source_reports_instead_of_guessing(ctx, tmp_path):
    p = put(tmp_path, "c.json", '{"a": }\n')
    r = await config_write("c.json", ctx,
                           ops=[{"op": "set", "path": "b", "value": 1}])
    assert "error" in r
    assert p.read_text("utf-8") == '{"a": }\n'


pass

async def test_yaml_keeps_comments_and_quotes(ctx, tmp_path):
    src = "# 顶部注释\nmodels:\n  - id: m1    # 行内\n    temp: 0.7\n"
    p = put(tmp_path, "c.yaml", src)
    await config_write("c.yaml", ctx,
                       ops=[{"op": "set", "path": "models.0.temp", "value": 0.3}])
    text = p.read_text("utf-8")
    assert "# 顶部注释" in text and "# 行内" in text
    assert "temp: 0.3" in text


async def test_yaml_ambiguous_scalars_are_quoted(ctx, tmp_path):
    import yaml
    p = put(tmp_path, "c.yaml", "seed: 1\n")
    ops = [{"op": "set", "path": f"k{i}", "value": v}
           for i, v in enumerate(["yes", "01", "2026-11-21", "null", "1.0"])]
    await config_write("c.yaml", ctx, ops=ops)
    got = yaml.safe_load(p.read_text("utf-8"))
    assert got == {"seed": 1, "k0": "yes", "k1": "01",
                   "k2": "2026-11-21", "k3": "null", "k4": "1.0"}


async def test_yaml_new_file(ctx, tmp_path):
    r = await config_write("new.yml", ctx, ops=[
        {"op": "set", "path": "a.b", "value": [1, 2]}])
    assert "已新建" in r
    import yaml
    assert yaml.safe_load((tmp_path / "new.yml").read_text("utf-8")) == {"a": {"b": [1, 2]}}


pass

async def test_ini_surgical_edit_keeps_comments_case_and_separator(ctx, tmp_path):
    src = "; 顶部\n[server]\nHost = 127.0.0.1   ; 行内\nPort=8000\n"
    p = put(tmp_path, "c.ini", src)
    r = await config_write("c.ini", ctx, ops=[
        {"op": "set", "path": "server.Port", "value": 9000}])
    text = p.read_text("utf-8")
    assert text == "; 顶部\n[server]\nHost = 127.0.0.1   ; 行内\nPort=9000\n"
    assert "值一律按文本写" in r


async def test_ini_new_key_and_section(ctx, tmp_path):
    p = put(tmp_path, "c.ini", "[a]\nk = 1\n")
    await config_write("c.ini", ctx, ops=[
        {"op": "set", "path": "a.j", "value": "v"},
        {"op": "set", "path": "b.n", "value": 2},
    ])
    assert p.read_text("utf-8") == "[a]\nk = 1\nj = v\n\n[b]\nn = 2\n"


async def test_ini_delete_key(ctx, tmp_path):
    p = put(tmp_path, "c.ini", "[a]\nk = 1\nj = 2\n")
    r = await config_write("c.ini", ctx, ops=[{"op": "delete", "path": "a.k"}])
    assert "删 [a] k" in r
    assert p.read_text("utf-8") == "[a]\nj = 2\n"


async def test_ini_rejects_merge_and_deep_path_and_replace(ctx, tmp_path):
    p = put(tmp_path, "c.ini", "[a]\nk = 1\n")
    src = p.read_text("utf-8")
    assert "不支持 merge" in await config_write(
        "c.ini", ctx, ops=[{"op": "merge", "path": "a", "value": {"x": 1}}])
    assert "两级" in await config_write(
        "c.ini", ctx, ops=[{"op": "set", "path": "a.b.c", "value": 1}])
    assert "不允许 op=replace" in await config_write(
        "c.ini", ctx, ops=[{"op": "replace", "value": {}}])
    assert p.read_text("utf-8") == src


async def test_ini_delete_missing_key_lists_available(ctx, tmp_path):
    p = put(tmp_path, "c.ini", "[a]\nfoo = 1\n")
    r = await config_write("c.ini", ctx, ops=[{"op": "delete", "path": "a.bar"}])
    assert "没有键" in r and "foo" in r


pass

async def test_jsonl_append_and_render(ctx, tmp_path):
    p = put(tmp_path, "x.jsonl", '{"a":1}\n{"a":2}\n')
    r = await config_write("x.jsonl", ctx,
                           ops=[{"op": "append", "path": "", "value": {"a": 3}}])
    assert "追加" in r
    assert p.read_text("utf-8") == '{"a": 1}\n{"a": 2}\n{"a": 3}\n'


pass

async def test_mode2_undo_restores_previous_content(ctx, tmp_path):
    p = put(tmp_path, "c.json", '{"a": 1}\n')
    await config_write("c.json", ctx,
                       ops=[{"op": "set", "path": "a", "value": 2}])
    r = await config_write("c.json", ctx, mode=2)
    assert "已回退" in r
    assert p.read_text("utf-8") == '{"a": 1}\n'


async def test_approval_reject_keeps_file_intact(ctx, tmp_path):
    p = put(tmp_path, "c.json", '{"a": 1}\n')

    async def reject(*a, **kw):
        return False, None

    ctx.request_file_approval = reject
    r = await config_write("c.json", ctx,
                           ops=[{"op": "set", "path": "a", "value": 2}])
    assert "被拒绝" in r
    assert p.read_text("utf-8") == '{"a": 1}\n'


async def test_path_guard_blocks_write(ctx, tmp_path):
    p = put(tmp_path, "c.json", "{}\n")

    async def deny(action, paths):
        return False, "测试拒绝"

    ctx.path_check = deny
    r = await config_write("c.json", ctx,
                           ops=[{"op": "set", "path": "a", "value": 1}])
    assert "安全策略" in r
    assert p.read_text("utf-8") == "{}\n"


def test_registered_as_core_and_plan_blocked():
    from app.agent.plan import WRITE_TOOL_NAMES
    from app.tools.registry import ToolRegistry
    assert "config_write" in ToolRegistry.CORE_TOOLS
    assert "config_write" in WRITE_TOOL_NAMES


def test_schema_declares_ops_required():
    from app.tools.builtin.fs.schemas import SCHEMAS
    spec = SCHEMAS["config_write"]
    assert spec["required"] == ["path", "ops"]
    assert set(spec["params"]["format"]["enum"]) == {"json", "jsonl", "yaml", "ini"}
