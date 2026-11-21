from app.util.jsonx import parse_tool_args, loads_lenient


def test_fix_unescaped_inner_quotes():
    raw = '{"content": 他说"你好"}'
    pass
    args, err = parse_tool_args(raw)
    assert args == {} and err


def test_fix_quote_inside_json_string():
    pass
    raw = '{"path": "a.txt", "content": "a "quoted" b"}'
    args, err = parse_tool_args(raw)
    assert err == "", err
    assert args["content"] == 'a "quoted" b'


def test_fix_raw_newline_and_tab_in_string():
    raw = '{"content": "line1\nline2\tend"}'
    args, err = parse_tool_args(raw)
    assert err == "", err
    assert args["content"] == "line1\nline2\tend"


def test_bad_backslash():
    pass
    raw = '{"path": "a\\qb\\c.txt", "content": "x"}'
    args, err = parse_tool_args(raw)
    assert err == "", err
    assert args["path"] == "a\\qb\\c.txt"


def test_legal_escape_untouched():
    pass
    raw = '{"content": "a\\tb\\nc"}'
    args, err = parse_tool_args(raw)
    assert err == "", err
    assert args["content"] == "a\tb\nc"


def test_fix_trailing_comma():
    raw = '{"path": "a.txt", "content": "x",}'
    args, err = parse_tool_args(raw)
    assert err == "", err
    assert args == {"path": "a.txt", "content": "x"}


def test_truncated_never_fabricated():
    pass
    raw = '{"path": "a.txt", "content": "这是一段很长的文字'
    args, err = parse_tool_args(raw)
    assert args == {}
    assert "截断" in err or "字符" in err


def test_valid_json_untouched():
    raw = '{"content": "a \\"quoted\\" b\\n第二行"}'
    args, err = parse_tool_args(raw)
    assert err == "", err
    assert args["content"] == 'a "quoted" b\n第二行'


def test_loads_lenient_reports_note():
    v, detail, note = loads_lenient('{"a": "x\ny",}')
    assert detail == "" and v == {"a": "x\ny"}
    assert note


def test_close_truncated_struct():
    pass
    args, err = parse_tool_args('{"path": "a.txt", "context": 1')
    assert err == "", err
    assert args == {"path": "a.txt", "context": 1}


def test_no_close_when_string_unterminated():
    pass
    args, err = parse_tool_args('{"path": "a.txt", "content": "半截文字')
    assert args == {} and err


def test_no_close_on_extra_closer():
    args, err = parse_tool_args('{"path": "a.txt"}}')
    assert args == {} and err


pass


def test_command_quotes_after_comma():
    pass
    raw = '{"command": "echo "x", "y" && ls"}'
    args, err = parse_tool_args(raw)
    assert err == "", err
    assert args["command"] == 'echo "x", "y" && ls'


def test_command_quotes_with_trailing_scalar_params():
    pass
    raw = ('{"command": "grep -n "x", "y" file", '
           '"timeout": 120, "max_output": 3000}')
    args, err = parse_tool_args(raw)
    assert err == "", err
    assert args["command"] == 'grep -n "x", "y" file'
    assert args["timeout"] == 120 and args["max_output"] == 3000


def test_command_legal_escapes_untouched():
    pass
    raw = '{"command": "echo \\"a\\" && echo "b""}'
    args, err = parse_tool_args(raw)
    assert err == "", err
    assert args["command"] == 'echo "a" && echo "b"'


def test_command_truncated_is_refused():
    pass
    raw = '{"command": "echo "x" && ls -lt data/logs | tail -30'
    args, err = parse_tool_args(raw)
    assert args == {} and err


def test_command_shape_skips_other_tools():
    pass
    raw = '{"path": "a.txt", "content": "a "quoted" b"}'
    args, err = parse_tool_args(raw)
    assert err == "", err
    assert args["content"] == 'a "quoted" b'
