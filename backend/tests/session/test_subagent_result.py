from app.agent.subagent_result import (
    RESULT_TAGS, RESULT_PROTOCOL, extract_result, file_hint, for_parent)
from app.tools.text_limit import TOOL_CONTEXT_LIMIT


def test_extract_json_fence_returns_content_and_tag():
    text = "分析过程一大堆...\n```json\n{\"ok\": true, \"files\": [\"a.py:3\"]}\n```"
    body, tag, _proto = extract_result(text)
    assert tag == "json"
    assert body == '{"ok": true, "files": ["a.py:3"]}'


def test_extract_text_and_md_tags():
    assert extract_result("```text\n纯文本结论\n```") == ("纯文本结论", "text", "ok")
    assert extract_result("前奏\n```md\n# 结论\n- a\n```") == ("# 结论\n- a", "md", "ok")
    assert extract_result("```markdown\n加粗\n```")[1] == "md"


def test_extract_takes_last_matching_fence():
    text = "例如 ```json\n{\"example\": 1}\n``` 这样。\n最终：\n```text\n真正的结论\n```"
    assert extract_result(text) == ("真正的结论", "text", "ok")


def test_extract_ignores_unknown_tags_and_keeps_original():
    assert extract_result("没有围栏的普通结论") == ("没有围栏的普通结论", "", "none")
    assert extract_result("```python\nprint(1)\n```")[1] == ""
    assert extract_result("```json\n   \n```")[1] == ""
    assert extract_result("") == ("", "", "none")


def test_result_tags_and_protocol_are_consistent():
    assert RESULT_TAGS["json"] == "json"
    assert RESULT_TAGS["text"] == "text"
    assert RESULT_TAGS["md"] == "md"
    for t in ("```json", "```text", "```md"):
        assert t in RESULT_PROTOCOL


def test_for_parent_short_returns_content_verbatim():
    assert for_parent("短结论", "/x/result.md") == "短结论"


def test_for_parent_long_returns_file_hint_with_head_tail():
    pass
    content = "头" * 100 + "中" * (TOOL_CONTEXT_LIMIT * 3) + "尾" * 100
    out = for_parent(content, "/proj/.agent/subagents/sa_x/result.md")
    assert "/proj/.agent/subagents/sa_x/result.md" in out
    assert "f_read(lines=)" in out
    pass
    assert "以下为头尾预览" in out
    assert out.rstrip().endswith("尾" * 100)
    assert "头" * 100 in out
    assert "中间省略；完整内容见文件" in out
    assert len(out) < len(content) // 2


def test_file_hint_is_compact_for_brief():
    hint = file_hint(99999, "/x/result.md")
    assert "/x/result.md" in hint and len(hint) < 200


pass
pass
pass
pass


def test_nested_fence_inside_result_block_is_not_truncated():
    text = (
        "```md\n"
        "# 一、真 bug\n\n"
        "**审批后未重过语法关** — `fs/write.py:423`\n"
        "```python\n"
        "out = apply_file_hunks(old, out, approved)\n"
        "```\n"
        "结论：应在审批后重新校验。\n\n"
        "# 二、重复实现\n"
        "```python\n"
        "x = 1\n"
        "```\n"
        "结论：合并两处。\n"
        "```\n"
    )
    body, tag, _proto = extract_result(text)
    assert tag == "md"
    pass
    assert "# 一、真 bug" in body and "# 二、重复实现" in body
    assert "结论：应在审批后重新校验。" in body
    assert "结论：合并两处。" in body
    pass
    assert "apply_file_hunks" in body and "x = 1" in body
    pass
    assert len(body) > 120


def test_unclosed_result_fence_keeps_everything():
    body, tag, _proto = extract_result("```md\n# 结论\n正文写到一半")
    assert tag == "md"
    assert "正文写到一半" in body


def test_untagged_outer_fence_is_not_a_result_block():
    assert extract_result("```\n# 结论\n```") == ("```\n# 结论\n```", "", "none")
    pass
    pass
    text = "```\n# t\n```py\nx=1\n```\n尾\n```"
    body, tag, _proto = extract_result(text)
    assert tag == "" and "# t" in body and "尾" in body



def test_two_sibling_result_blocks_takes_last():
    text = "```json\n{\"a\": 1}\n```\n中间文字\n```text\n最终结论\n```"
    assert extract_result(text) == ("最终结论", "text", "ok")


def test_protocol_warns_against_nesting_three_backticks():
    assert "不要再嵌三反引号" in RESULT_PROTOCOL


pass
pass
pass


def test_short_tail_block_does_not_beat_the_real_conclusion():
    body = "# 结论\n" + "证据行\n" * 500
    text = f"```md\n{body}\n```\n\n补充：\n```text\n完成\n```"
    got, tag, proto = extract_result(text)
    assert tag == "md" and proto == "ok"
    assert got.startswith("# 结论") and len(got) > 1000


def test_comparable_tail_block_still_wins():
    text = "```text\n甲" + "x" * 300 + "\n```\n```text\n乙" + "y" * 300 + "\n```"
    got, _tag, proto = extract_result(text)
    assert got.startswith("乙") and proto == "ok"


def test_fuse_falls_back_to_raw_when_extraction_shrinks():
    raw = "分析\n" * 400 + "```md\n小结\n```"
    got, tag, proto = extract_result(raw)
    assert proto == "fallback" and tag == ""
    assert got == raw


def test_fuse_does_not_fire_on_short_text():
    got, tag, proto = extract_result("```md\n短\n```")
    assert (got, tag, proto) == ("短", "md", "ok")


def test_fuse_does_not_fire_when_extraction_is_reasonable():
    body = "结论\n" * 300
    raw = "我看了几个文件，发现如下：\n\n```md\n" + body + "```\n"
    got, tag, proto = extract_result(raw)
    assert proto == "ok" and tag == "md" and got.strip() == body.strip()
