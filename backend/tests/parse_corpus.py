from __future__ import annotations

from dataclasses import dataclass
from typing import Any

pass
REJECT = object()


@dataclass(frozen=True)
class Case:
    cid: str
    cat: str
    src: str
    raw: str
    want: Any
    mode: str
    note: str = ""


pass
pass
pass
JSON_CASES: list[Case] = [
    # ---- legal：合法数据一个字节都不许改（会话流程的护栏） ----
    Case("J-legal-01", "json/legal/string-content", "RFC 8259 §7",
         '{"url": "https://x/y", "path": "a//b"}',
         {"url": "https://x/y", "path": "a//b"}, "legal",
         "字符串里的 // 是内容，不是注释（上次 UnboundLocalError 的现场）"),
    Case("J-legal-02", "json/legal/string-content", "RFC 8259 §7",
         '{"cmd": "echo /* hi */ ok"}', {"cmd": "echo /* hi */ ok"}, "legal",
         "字符串里的 /* */ 是内容"),
    Case("J-legal-03", "json/legal/string-content", "RFC 8259 §7 / UTF-8",
         '{"note": "a：b", "cmd": "echo a:b"}',
         {"note": "a：b", "cmd": "echo a:b"}, "legal",
         "中文冒号 / 半角冒号在字符串里都不许被排版修复改掉"),
    Case("J-legal-04", "json/legal/legal-escape", "RFC 8259 §7",
         '{"s": "line1\\nline2\\tend"}', {"s": "line1\nline2\tend"}, "legal",
         "合法 \\n / \\t 转义不许被当成裸控制字符再转义一次"),
    Case("J-legal-05", "json/legal/legal-escape", "RFC 8259 §7",
         '{"s": "他说 \\"你好\\" 然后走了"}',
         {"s": '他说 "你好" 然后走了'}, "legal", "合法转义引号"),
    Case("J-legal-06", "json/legal/legal-escape", "RFC 8259 §7",
         '{"path": "C:\\\\Users\\\\x"}', {"path": "C:\\Users\\x"}, "legal",
         "合法反斜杠转义（Windows 路径）"),
    Case("J-legal-07", "json/legal/legal-escape", "RFC 8259 §7",
         '{"s": "\\u4e2d\\u6587"}', {"s": "中文"}, "legal", "合法 \\uXXXX"),
    Case("J-legal-08", "json/legal/number-literal", "RFC 8259 §2/§3",
         '{"n": 1e308, "m": -0, "b": true, "z": null}',
         {"n": 1e308, "m": 0, "b": True, "z": None}, "legal", "数值与小写字面量"),
    Case("J-legal-09", "json/legal/nested", "RFC 8259 §2",
         '{"arr": [1, [2, {"k": "v"}], {"a": 1}]}',
         {"arr": [1, [2, {"k": "v"}], {"a": 1}]}, "legal", "嵌套结构"),
    Case("J-legal-10", "json/legal/utf8", "RFC 8259 §8.1",
         '{"emoji": "\U0001f600", "中文键": "值"}',
         {"emoji": "\U0001f600", "中文键": "值"}, "legal", "UTF-8 与中文键"),
    Case("J-legal-11", "json/legal/empty", "RFC 8259 §2",
         "{}", {}, "legal", "空对象"),
    Case("J-legal-12", "json/legal/empty", "RFC 8259 §2",
         "[]", [], "legal", "空数组"),
    Case("J-legal-13", "json/legal/top-array", "RFC 8259 §2",
         '[1, 2, 3]', [1, 2, 3], "legal", "顶层数组"),
    Case("J-legal-14", "json/legal/string-content", "RFC 8259 §7",
         '["http://x", "a//b", "/*x*/"]',
         ["http://x", "a//b", "/*x*/"], "legal", "数组里的 URL/注释文本"),
    Case("J-legal-15", "json/legal/string-content", "RFC 8259 §7",
         '{"text": "a,}", "n": 1}', {"text": "a,}", "n": 1}, "legal",
         "字符串里的 ,} 不许被去尾逗号误伤"),
    Case("J-legal-16", "json/legal/string-content", "RFC 8259 §7",
         '{"text": "路径 C:\\\\new"}', {"text": "路径 C:\\new"}, "legal",
         "\\\\ + 字母 n 是合法转义序列（反斜杠 + n 两个字符）"),
    Case("J-legal-17", "json/legal/string-content", "RFC 8259 §7",
         '{"text": "# a: b // c"}', {"text": "# a: b // c"}, "legal",
         "字符串里的 # : // 全是内容"),
    Case("J-legal-18", "json/legal/string-content", "RFC 8259 §7",
         '{"text": "前言 a: 1，后记", "ok": true}',
         {"text": "前言 a: 1，后记", "ok": True}, "legal",
         "长得像 YAML 的正文不许被当结构"),

    # ---- repair：坏但能确定性修好 ----
    Case("J-rep-01", "json/llm/trailing-comma", "json_repair README: misplaced commas",
         '{"a": 1,}', {"a": 1}, "repair"),
    Case("J-rep-02", "json/llm/trailing-comma", "json_repair README: misplaced commas",
         '{"a": [1, 2,],}', {"a": [1, 2]}, "repair"),
    Case("J-rep-03", "json/llm/trailing-comma", "json_repair README: misplaced commas",
         '[1, 2, ]', [1, 2], "repair"),
    Case("J-rep-04", "json/llm/comment", "json_repair README: comments",
         '{"a": 1, // 说明\n "b": 2}', {"a": 1, "b": 2}, "repair"),
    Case("J-rep-05", "json/llm/comment", "json_repair README: comments",
         '{/* 说明 */"a": 1}', {"a": 1}, "repair"),
    Case("J-rep-06", "json/llm/comment", "json_repair README: comments",
         '{\n // x\n "a": 1\n}', {"a": 1}, "repair"),
    Case("J-rep-07", "json/llm/comment-url", "json_repair README + RFC 8259 §7",
         '{"url":"http://x/y", // 注释\n "a":1,}',
         {"url": "http://x/y", "a": 1}, "repair",
         "真注释与字符串内 URL 同时出现，只剥前者"),
    Case("J-rep-08", "json/llm/python-literal", "json_repair README: improperly formatted values",
         '{"ok": True, "x": None, "no": False}',
         {"ok": True, "x": None, "no": False}, "repair"),
    Case("J-rep-09", "json/llm/markdown-fence", "json_repair README: markdown fences",
         '```json\n{"a": 1}\n```', {"a": 1}, "repair"),
    Case("J-rep-10", "json/llm/markdown-fence", "json_repair README: markdown fences",
         '结果如下：\n```json\n{"a": 1,}\n```\n完毕', {"a": 1}, "repair"),
    Case("J-rep-11", "json/llm/untagged-fence", "json_repair README: markdown fences",
         '```\n{"a": 1}\n```', {"a": 1}, "repair"),
    Case("J-rep-12", "json/llm/stray-prose", "json_repair README: stray prose",
         '好的，参数如下：{"path": "a.txt"} 希望有帮助',
         {"path": "a.txt"}, "repair"),
    Case("J-rep-13", "json/decoder/extra-data", "CPython: Extra data",
         '{"a": 1} 后面还有字', {"a": 1}, "repair",
         "前后废话走 strip_fences 剥掉，不是编造"),
    Case("J-rep-14", "json/llm/incomplete-object", "json_repair README: incomplete objects",
         '{"a": 1, "b": [2, 3]', {"a": 1, "b": [2, 3]}, "repair",
         "内容完整、只缺收尾结构符"),
    Case("J-rep-15", "json/llm/incomplete-object", "json_repair README: incomplete objects",
         '{"a": {"b": [1, 2', {"a": {"b": [1, 2]}}, "repair"),
    Case("J-rep-16", "json/decoder/invalid-control-character",
         "CPython: Invalid control character at",
         '{"content": "第一行\n第二行"}',
         {"content": "第一行\n第二行"}, "repair", "字符串里真实换行 → \\n"),
    Case("J-rep-17", "json/decoder/invalid-control-character",
         "CPython: Invalid control character at",
         '{"content": "a\tb"}', {"content": "a\tb"}, "repair", "真实 tab → \\t"),
    Case("J-rep-18", "json/decoder/invalid-escape", "CPython: Invalid \\escape",
         '{"path": "C:\\qoo"}', {"path": "C:\\qoo"}, "repair",
         "非法反斜杠补齐转义，值不变"),
    Case("J-rej-15", "json/decoder/invalid-u-escape", "CPython: Invalid \\uXXXX escape",
         '{"s": "\\u12"}', REJECT, "reject",
         "不完整的 \\u 转义不许猜内容，安全报错"),
    Case("J-rep-19", "json/llm/unescaped-quotes", "json_repair README: unescaped characters",
         '{"command": "grep -n "x" file", "timeout": 120}',
         {"command": 'grep -n "x" file', "timeout": 120}, "repair",
         "命令里的裸引号（锚点法）"),
    Case("J-rep-20", "json/llm/unescaped-quotes", "json_repair README: unescaped characters",
         '{"s": "a "b" c"}', {"s": 'a "b" c'}, "repair"),

    # ---- reject：修不好必须安全报错，绝不编造 ----
    Case("J-rej-01", "json/decoder/unterminated-string",
         "CPython: Unterminated string starting at",
         '{"a": "半截', REJECT, "reject", "停在半截字符串里绝不补引号"),
    Case("J-rej-02", "json/llm/truncated-string", "json_repair README: truncated values",
         '{"a": "内容完整", "b": "半', REJECT, "reject",
         "raw 场景一个字节都不许丢"),
    Case("J-rej-03", "json/decoder/extra-data", "CPython: Extra data",
         '{"a": 1}{"b": 2}', REJECT, "reject", "多个顶层值不许拼接编造"),
    Case("J-rej-04", "json/decoder/expecting-value", "CPython: Expecting value",
         '我就是不给你结构化结果', REJECT, "reject"),
    Case("J-rej-05", "json/decoder/expecting-value", "CPython: Expecting value",
         '{"a": }', REJECT, "reject", "缺值不许补 null"),
    Case("J-rej-06", "json/decoder/nul-control", "RFC 8259 §7 / CPython: Invalid control character",
         '{"s": "a\x00b"}', REJECT, "reject", "NUL 不在可修控制字符白名单"),
    Case("J-rej-07", "json/decoder/expecting-value", "CPython: Expecting value",
         '{"n": 01}', REJECT, "reject", "非法数字不许改写"),
    Case("J-rej-08", "json/llm/deep-nesting", "CPython: RecursionError",
         '{"a": ' * 2000 + '1' + '}' * 2000, REJECT, "reject",
         "超深嵌套必须安全失败、不许抛 RecursionError 到会话流程"),
    Case("J-rej-09", "json/decoder/expecting-property-name",
         "CPython: Expecting property name enclosed in double quotes",
         '{a: 1}', REJECT, "reject", "未加引号的键不猜"),
    Case("J-rej-10", "json/llm/single-quotes", "json_repair README: missing quotes",
         "{'a': 1}", REJECT, "reject", "单引号不猜（本修复层的红线）"),
    Case("J-rej-11", "json/decoder/expecting-colon", "CPython: Expecting ':' delimiter",
         '{"a" 1}', REJECT, "reject"),
    Case("J-rej-12", "json/decoder/expecting-comma", "CPython: Expecting ',' delimiter",
         '{"a": 1 "b": 2}', REJECT, "reject"),
    Case("J-rej-13", "json/decoder/invalid-u-escape", "CPython: Invalid \\uXXXX escape",
         '{"s": "\\uZZZZ"}', REJECT, "reject"),
    Case("J-rej-14", "json/llm/missing-open-brace", "json_repair README: missing opening {",
         '"a": 1}', REJECT, "reject", "缺起始 { 不补（避免把半截文本编成对象）"),

    # ---- scalar：能解析但顶层不是结构化 ----
    Case("J-scalar-01", "json/scalar/number", "RFC 8259 §2", "42", 42, "scalar"),
    Case("J-scalar-02", "json/scalar/string", "RFC 8259 §2", '"一段文本"', "一段文本", "scalar"),
    Case("J-scalar-03", "json/scalar/bool", "RFC 8259 §3", "true", True, "scalar"),
    Case("J-scalar-04", "json/scalar/null", "RFC 8259 §3", "null", None, "scalar"),
]


pass
pass
pass
YAML_CASES: list[Case] = [
    # ---- legal：合法 YAML，不许被排版修复改掉 ----
    Case("Y-legal-01", "yaml/legal/basic", "PyYAML safe_load",
         'a: 1\nb:\n  - x\n  - y\n', {"a": 1, "b": ["x", "y"]}, "legal"),
    Case("Y-legal-02", "yaml/legal/url-colon", "PyYAML safe_load",
         'url: https://x/y\ncmd: echo a:b\n',
         {"url": "https://x/y", "cmd": "echo a:b"}, "legal",
         "值里的 : 与 // 都是内容"),
    Case("Y-legal-03", "yaml/legal/quoted-fullwidth", "PyYAML safe_load",
         'note: "a：b"\n', {"note": "a：b"}, "legal",
         "引号内中文冒号不许被 _fullwidth_colon 改掉"),
    Case("Y-legal-04", "yaml/legal/flow-seq", "PyYAML safe_load",
         'items: [1, 2, 3]\n', {"items": [1, 2, 3]}, "legal"),
    Case("Y-legal-05", "yaml/legal/comment", "PyYAML safe_load",
         '# 注释\na: 1\n', {"a": 1}, "legal", "# 注释行不许被补空格"),
    Case("Y-legal-06", "yaml/legal/nested", "PyYAML safe_load",
         'a:\n  b:\n    c: 1\n', {"a": {"b": {"c": 1}}}, "legal"),
    Case("Y-legal-07", "yaml/legal/block-scalar", "PyYAML safe_load",
         'text: |\n  第一行\n  第二行\n', {"text": "第一行\n第二行\n"}, "legal"),
    Case("Y-legal-08", "yaml/legal/top-list", "PyYAML safe_load",
         '- x\n- y\n', ["x", "y"], "legal"),
    Case("Y-legal-09", "yaml/legal/quoted-slashes", "PyYAML safe_load",
         'cmd: "echo /* hi */ ok"\n', {"cmd": "echo /* hi */ ok"}, "legal"),

    # ---- repair：YAML 排版毛病 ----
    Case("Y-rep-01", "yaml/scanner/tab-indent",
         "scanner.py:258 found character '\\t' that cannot start any token",
         'a:\n\tb: 1\n', {"a": {"b": 1}}, "repair"),
    Case("Y-rep-02", "yaml/scanner/tab-indent", "scanner.py:1313 Do not use tabs in YAML!",
         'items:\n\t- x\n\t- y\n', {"items": ["x", "y"]}, "repair"),
    Case("Y-rep-03", "yaml/scanner/mapping-values", "scanner.py:577 mapping values are not allowed here",
         'title：报告\nn: 3\n', {"title": "报告", "n": 3}, "repair"),
    Case("Y-rep-04", "yaml/scanner/mapping-values", "scanner.py:577 mapping values are not allowed here",
         'a:1\nb: 2\n', {"a": 1, "b": 2}, "repair"),
    Case("Y-rep-05", "yaml/scanner/combined", "scanner.py:258 + :577",
         'a:1\nb:\n\tc：2\n', {"a": 1, "b": {"c": 2}}, "repair",
         "tab / 中文冒号 / 缺空格三种毛病叠加"),
    Case("Y-rep-06", "yaml/llm/stray-prose", "json_repair README: stray prose",
         '前言\na: 1\nb:\n  - x\n  - y\n希望有帮助',
         {"a": 1, "b": ["x", "y"]}, "repair", "不许只认尾巴一段丢掉 a"),
    Case("Y-rep-07", "yaml/llm/stray-prose-all-broken", "scanner.py:577",
         '分析如下\na：1\nb：2\n', {"a": 1, "b": 2}, "repair",
         "所有候选都要靠修复才能解析时也要认"),
    Case("Y-rep-08", "yaml/llm/tab-fullwidth", "scanner.py:258 + :577",
         '标题：报告\n项目：\n\t- 甲\n\t- 乙\n',
         {"标题": "报告", "项目": ["甲", "乙"]}, "repair"),
    Case("Y-rep-09", "yaml/json-subset/trailing-comma", "RFC 8259 + json_repair README",
         '{"title": "报告", "n": 3,}', {"title": "报告", "n": 3}, "repair"),
    Case("Y-rep-10", "yaml/json-subset/comment", "json_repair README: comments",
         '{/* 说明 */"a": 1, "b": [1, 2,],}', {"a": 1, "b": [1, 2]}, "repair"),
    Case("Y-rep-11", "yaml/json-subset/python-literal", "json_repair README",
         '{"title": "报告", "ok": True}', {"title": "报告", "ok": True}, "repair"),
    Case("Y-rep-12", "yaml/json-subset/url", "RFC 8259 §7",
         '{"url": "http://x/y", "items": [1, 2,],}',
         {"url": "http://x/y", "items": [1, 2]}, "repair",
         "URL 里的 // 不许被当成注释"),

    # ---- reject：修不好必须安全报错 ----
    Case("Y-rej-01", "yaml/scanner/unexpected-eof",
         "scanner.py:1238 found unexpected end of stream",
         'a: "半截\nb: 1\n', REJECT, "reject"),
    Case("Y-rej-02", "yaml/scanner/unclosed-flow", "parser.py: expected ',' or ']'",
         'a: [1, 2\nb: "半截', REJECT, "reject"),
    Case("Y-rej-03", "yaml/composer/undefined-alias", "composer.py: found undefined alias",
         'a: *missing\n', REJECT, "reject", "不许编造锚点"),
    Case("Y-rej-04", "yaml/composer/multi-doc", "composer.py: expected a single document",
         '---\na: 1\n---\nb: 2\n', REJECT, "reject"),
    Case("Y-rej-05", "yaml/scanner/bad-escape",
         "scanner.py:1213 expected escape sequence of 4 hexadecimal numbers",
         'a: "\\uZZZZ"\n', REJECT, "reject"),
    Case("Y-rej-06", "yaml/llm/broken-not-fixable", "scanner.py:577",
         'a: b: c\nd: 1\n', REJECT, "reject", "不许把值里的冒号硬改成结构"),

    # ---- scalar：解析成功但顶层不是 dict/list ----
    Case("Y-scalar-01", "yaml/scalar/plain", "PyYAML safe_load",
         '就是一段话', "就是一段话", "scalar"),
    Case("Y-scalar-02", "yaml/scalar/number", "PyYAML safe_load", "42", 42, "scalar"),
    Case("Y-scalar-03", "yaml/scalar/bool", "PyYAML safe_load", "true", True, "scalar"),
]


def by_mode(cases: list[Case], mode: str) -> list[Case]:
    return [c for c in cases if c.mode == mode]


def ids(cases: list[Case]) -> list[str]:
    return [c.cid for c in cases]


def strict_error(raw: str, loader) -> str:
    try:
        loader(raw)
        return ""
    except Exception as e:
        return f"{type(e).__name__}: {e}"
