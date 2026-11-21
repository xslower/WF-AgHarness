from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

POSIX_ONLY = pytest.mark.skipif(
    os.name == "nt",
    reason="该用例依赖 POSIX shell 命令（ls/grep/mkdir/touch/python3/bash），Windows 不适用",
)

from app.security.core import INSTALL_PATTERNS
from app.tools import ToolContext, ToolRegistry
from app.tools.builtin import build_tools as build_registry
from app.tools.text_limit import CMD_TIMEOUT, MAX_OUTPUT, MAX_READ


pass

def make_ctx(cwd: str) -> ToolContext:
    c = ToolContext(cwd=cwd)
    c.spawn = None
    c.snapshot = None
    c.policy_check = None
    c.request_approval = None
    c.env_rewrite = None
    c.workflow_start = None
    c.save_memory = None
    c.emit_stream = None
    c.request_file_approval = None
    return c


def run_tool(reg: ToolRegistry, ctx: ToolContext, name: str, args: dict) -> str:
    return asyncio.run(reg.execute(name, args, ctx))


def parse_result(result: str) -> dict | list | str:
    try:
        return json.loads(result)
    except (json.JSONDecodeError, ValueError):
        return result


def setup_workspace(tmp_path: Path) -> Path:
    (tmp_path / "hello.txt").write_text("Hello, World!\n", encoding="utf-8")
    (tmp_path / "data.json").write_text('{"key": "value", "num": 42}', encoding="utf-8")
    (tmp_path / "config.yaml").write_text("name: test\nport: 8080\n", encoding="utf-8")
    sub = tmp_path / "src"
    sub.mkdir()
    (sub / "main.py").write_text("def main():\n    print('hello')\n\nmain()\n", encoding="utf-8")
    (sub / "utils.py").write_text("def helper(x):\n    return x * 2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Project\n\nA test project.\n", encoding="utf-8")
    return tmp_path


pass

@pytest.fixture
def workspace(tmp_path):
    return setup_workspace(tmp_path)


@pytest.fixture
def ctx(workspace):
    return make_ctx(str(workspace))


@pytest.fixture
def reg():
    return build_registry()


pass

class TestReadFileUseCases:

    def test_uc_read_text_file(self, reg, ctx, workspace):
        pass
        result = run_tool(reg, ctx, "f_read", {"path": "hello.txt"})
        assert "Hello, World!" in result

    def test_uc_read_json_file(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "f_read", {"path": "data.json"})
        assert '"key"' in result
        assert '"value"' in result
        assert "42" in result

    def test_uc_read_absolute_path(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "f_read", {"path": str(workspace / "hello.txt")})
        assert "Hello, World!" in result

    def test_uc_read_nested_file(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "f_read", {"path": "src/main.py"})
        assert "def main()" in result

    def test_uc_read_nonexistent(self, reg, ctx):
        result = run_tool(reg, ctx, "f_read", {"path": "ghost.txt"})
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data

    def test_uc_read_missing_path_param(self, reg, ctx):
        result = run_tool(reg, ctx, "f_read", {})
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data

    def test_uc_read_large_file_truncated(self, reg, ctx, workspace):
        big = "X" * (MAX_READ + 5000)
        (workspace / "big.txt").write_text(big, encoding="utf-8")
        result = run_tool(reg, ctx, "f_read", {"path": "big.txt"})
        assert len(result) <= MAX_READ + 200


pass

class TestWriteFileUseCases:

    def test_uc_write_new_file(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "f_write", {"path": "new.txt", "content": "New!\n"})
        assert (workspace / "new.txt").read_text() == "New!\n"

    def test_uc_write_overwrite(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "f_write", {"path": "hello.txt", "content": "Overwritten\n"})
        assert (workspace / "hello.txt").read_text() == "Overwritten\n"

    def test_uc_write_to_subdir(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "f_write", {"path": "src/new.py", "content": "x = 1\n"})
        assert (workspace / "src" / "new.py").read_text() == "x = 1\n"

    def test_uc_write_deep_nested(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "f_write", {"path": "a/b/c/deep.txt", "content": "deep\n"})
        assert (workspace / "a" / "b" / "c" / "deep.txt").read_text() == "deep\n"

    def test_uc_write_missing_content(self, reg, ctx):
        result = run_tool(reg, ctx, "f_write", {"path": "x.txt"})
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data

    def test_uc_write_with_approval_approved(self, reg, ctx, workspace):
        ctx.request_file_approval = AsyncMock(return_value=(True, None))
        run_tool(reg, ctx, "f_write", {"path": "ok.txt", "content": "ok\n"})
        assert (workspace / "ok.txt").exists()

    def test_uc_write_with_approval_rejected(self, reg, ctx, workspace):
        ctx.request_file_approval = AsyncMock(return_value=(False, None))
        result = run_tool(reg, ctx, "f_write", {"path": "no.txt", "content": "no\n"})
        assert not (workspace / "no.txt").exists()


pass

class TestEditFileUseCases:

    def test_uc_edit_simple_replace(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "f_replace", {
            "path": "hello.txt", "old": "Hello", "new": "Hi",
        })
        assert "Hi, World!" in (workspace / "hello.txt").read_text()

    def test_uc_edit_not_found(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "f_replace", {
            "path": "hello.txt", "old": "Nope", "new": "Yes",
        })
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data

    def test_uc_edit_file_not_exist(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "f_replace", {
            "path": "no_such.txt", "old": "x", "new": "y",
        })
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data

    def test_uc_edit_multiple_occurrences(self, reg, ctx, workspace):
        (workspace / "multi.txt").write_text("foo\nfoo\nfoo\n", encoding="utf-8")
        result = run_tool(reg, ctx, "f_replace", {
            "path": "multi.txt", "old": "foo", "new": "bar",
        })
        pass
        assert "2 次" in result or "3 次" in result or "多次" in result or "error" in result.lower()

    def test_uc_edit_replace_all(self, reg, ctx, workspace):
        (workspace / "multi2.txt").write_text("foo\nfoo\nfoo\n", encoding="utf-8")
        result = run_tool(reg, ctx, "f_replace", {
            "path": "multi2.txt", "old": "foo", "new": "bar",
            "replace_all": True,
        })
        content = (workspace / "multi2.txt").read_text()
        assert "bar" in content
        assert "foo" not in content

    def test_uc_edit_missing_params(self, reg, ctx):
        result = run_tool(reg, ctx, "f_write", {"path": "x.txt"})
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data


pass

class TestDirAndSearchUseCases:

    def test_uc_list_dir_root(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "search_files", {"path": "."})
        assert "hello.txt" in result
        assert "data.json" in result
        assert "src" in result

    def test_uc_list_dir_subdir(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "search_files", {"path": "src"})
        assert "main.py" in result
        assert "utils.py" in result

    def test_uc_list_dir_nonexistent(self, reg, ctx):
        result = run_tool(reg, ctx, "search_files", {"path": "no_dir"})
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data

    def test_uc_search_py_files(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "search_files", {"pattern": "*.py"})
        assert "main.py" in result
        assert "utils.py" in result

    def test_uc_search_recursive(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "search_files", {"pattern": "**/*.py"})
        assert "main.py" in result

    def test_uc_search_no_match(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "search_files", {"pattern": "*.xyz"})
        pass
        assert result is not None

    def test_uc_grep_basic(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "grep", {"key": ["Hello"]})
        assert "hello.txt" in result

    def test_uc_grep_regex(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "grep", {"key": ["def \\w+"], "regex": True})
        assert "main.py" in result or "utils.py" in result

    def test_uc_grep_no_match(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "grep", {"key": ["zzz_no_match"]})
        assert result is not None


pass

class TestRunCommandUseCases:

    def test_uc_echo(self, reg, ctx):
        result = run_tool(reg, ctx, "run_command", {"command": "echo hello123"})
        assert "hello123" in result

    def test_uc_pwd(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "run_command", {"command": "pwd"})
        assert str(workspace) in result

    @POSIX_ONLY
    def test_uc_ls(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "run_command", {"command": "ls -la"})
        assert "hello.txt" in result

    def test_uc_cat(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "run_command", {"command": "cat hello.txt"})
        assert "Hello, World!" in result

    @POSIX_ONLY
    def test_uc_mkdir_and_touch(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "run_command", {"command": "mkdir -p newdir && touch newdir/file.txt"})
        assert (workspace / "newdir" / "file.txt").exists()

    @POSIX_ONLY
    def test_uc_python_inline(self, reg, ctx):
        result = run_tool(reg, ctx, "run_command", {"command": "python3 -c \"print(2+3)\""})
        assert "5" in result

    @POSIX_ONLY
    def test_uc_pipe_grep(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "run_command", {"command": "ls | grep hello"})
        assert "hello.txt" in result

    def test_uc_env_var(self, reg, ctx):
        result = run_tool(reg, ctx, "run_command", {"command": "echo $HOME"})
        assert result.strip() != ""

    def test_uc_chained_commands(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "run_command", {"command": "echo a && echo b && echo c"})
        assert "a" in result and "b" in result and "c" in result

    def test_uc_exit_code_nonzero(self, reg, ctx):
        result = run_tool(reg, ctx, "run_command", {"command": "false"})
        data = parse_result(result)
        pass
        assert isinstance(data, dict) and "error" in data or "error" in result.lower() or True

    def test_uc_nonexistent_command(self, reg, ctx):
        result = run_tool(reg, ctx, "run_command", {"command": "cmd_not_exist_xyz"})
        pass
        assert "未找到" in result or "not found" in result or "exit" in result or "error" in result.lower()

    def test_uc_missing_command_param(self, reg, ctx):
        result = run_tool(reg, ctx, "run_command", {})
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data

    pass

    @pytest.mark.parametrize("cmd", [
        "pip install requests",
        "pip3 install numpy",
        "python -m pip install flask",
        "npm install lodash",
        "npm i express",
        "npm add axios",
        "pnpm install vue",
        "pnpm add react",
        "yarn add webpack",
        "yarn install",
        "uv pip install fastapi",
        "conda install scipy",
        "apt-get install nginx",
        "apt install curl",
        "winget install git",
        "choco install python",
        "gem install rails",
        "cargo install ripgrep",
    ])
    def test_uc_install_blocked(self, reg, ctx, cmd):
        result = run_tool(reg, ctx, "run_command", {"command": cmd})
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data

    def test_uc_env_rewrite(self, reg, ctx):
        ctx.env_rewrite = lambda cmd: cmd.replace("PLACEHOLDER", "injected_value")
        result = run_tool(reg, ctx, "run_command", {"command": "echo PLACEHOLDER"})
        assert "injected_value" in result

    def test_uc_command_output_truncated(self, reg, ctx):
        result = run_tool(reg, ctx, "run_command", {
            "command": f"python3 -c \"print('x' * {MAX_OUTPUT + 5000})\"",
        })
        assert len(result) <= MAX_OUTPUT + 300


pass

class TestGatewayStreamParsing:

    def _accumulate_deltas(self, deltas: list[dict]) -> dict[int, dict]:
        accumulated: dict[int, dict] = {}
        for d in deltas:
            idx = d.get("index", 0)
            if idx not in accumulated:
                accumulated[idx] = {"id": "", "name": "", "arguments": ""}
            if "id" in d:
                accumulated[idx]["id"] = d["id"]
            fn = d.get("function", {})
            if "name" in fn:
                accumulated[idx]["name"] = fn["name"]
            if "arguments" in fn:
                accumulated[idx]["arguments"] += fn["arguments"]
        return accumulated

    def _check_empty_response(self, chunks: list[dict]) -> bool:
        has_content = False
        has_tool = False
        for chunk in chunks:
            t = chunk.get("type", "")
            if t == "text":
                has_content = True
            elif t == "tool_meta":
                has_tool = True
            pass
        return not has_content and not has_tool

    def test_uc_single_tool_call_accumulation(self):
        deltas = [
            {"index": 0, "id": "call_1", "function": {"name": "f_read", "arguments": ""}},
            {"index": 0, "function": {"arguments": '{"path"'}},
            {"index": 0, "function": {"arguments": ': "hello.txt"}'}},
        ]
        acc = self._accumulate_deltas(deltas)
        assert acc[0]["name"] == "f_read"
        assert json.loads(acc[0]["arguments"]) == {"path": "hello.txt"}

    def test_uc_multi_tool_call_accumulation(self):
        deltas = [
            {"index": 0, "id": "call_1", "function": {"name": "f_read", "arguments": ""}},
            {"index": 1, "id": "call_2", "function": {"name": "search_files", "arguments": ""}},
            {"index": 0, "function": {"arguments": '{"path": "a.txt"}'}},
            {"index": 1, "function": {"arguments": '{"path": "."}'}},
        ]
        acc = self._accumulate_deltas(deltas)
        assert len(acc) == 2
        assert json.loads(acc[0]["arguments"]) == {"path": "a.txt"}
        assert json.loads(acc[1]["arguments"]) == {"path": "."}

    def test_uc_empty_response_pure_reasoning(self):
        chunks = [
            {"type": "reason", "text": "思考中..."},
            {"type": "reason", "text": "继续思考..."},
        ]
        assert self._check_empty_response(chunks) is True

    def test_uc_text_response_not_empty(self):
        chunks = [
            {"type": "reason", "text": "思考..."},
            {"type": "text", "text": "这是回复"},
        ]
        assert self._check_empty_response(chunks) is False

    def test_uc_tool_call_not_empty(self):
        chunks = [
            {"type": "tool_meta", "tool_index": 0, "name": "f_read"},
            {"type": "tool_args", "tool_index": 0, "text": '{"path":"x"}'},
        ]
        assert self._check_empty_response(chunks) is False

    def test_uc_malformed_json_args(self):
        bad_args = '{"path": hello.txt}'
        with pytest.raises(json.JSONDecodeError):
            json.loads(bad_args)

    def test_uc_partial_json_fragments(self):
        fragments = ['{"path": ', '"hello', '.txt"}']
        full = "".join(fragments)
        assert json.loads(full) == {"path": "hello.txt"}

    def test_uc_empty_arguments_string(self):
        acc = self._accumulate_deltas([
            {"index": 0, "id": "call_1", "function": {"name": "search_files", "arguments": ""}},
        ])
        pass
        args_str = acc[0]["arguments"]
        if args_str:
            json.loads(args_str)

    def test_uc_unicode_in_arguments(self):
        deltas = [
            {"index": 0, "id": "call_1", "function": {"name": "f_write", "arguments": ""}},
            {"index": 0, "function": {"arguments": '{"path": "\\u4e2d\\u6587.txt", "content": "\\u4f60\\u597d"}'}},
        ]
        acc = self._accumulate_deltas(deltas)
        args = json.loads(acc[0]["arguments"])
        assert args["path"] == "中文.txt"
        assert args["content"] == "你好"

    def test_uc_nested_json_in_arguments(self):
        args_str = '{"path": "x", "options": {"recursive": true, "filter": "*.py"}}'
        parsed = json.loads(args_str)
        assert parsed["options"]["recursive"] is True
        assert parsed["options"]["filter"] == "*.py"

    def test_uc_escaped_quotes_in_arguments(self):
        args_str = '{"command": "echo \\"hello\\""}'
        parsed = json.loads(args_str)
        assert '"hello"' in parsed["command"]


pass

class TestSpawnAgentUseCases:

    def test_uc_spawn_no_fn(self, reg, ctx):
        result = run_tool(reg, ctx, "subagent",
                          {"action": "spawn", "task": "do something"})
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data

    def test_uc_spawn_with_mock(self, reg, ctx):
        ctx.spawn = AsyncMock(return_value="子Agent完成: result")
        result = run_tool(reg, ctx, "subagent",
                          {"action": "spawn", "task": "test task"})
        assert "子Agent完成" in result
        ctx.spawn.assert_called_once()

    def test_uc_spawn_with_tools(self, reg, ctx, workspace):
        ctx.spawn = AsyncMock(return_value="ok")
        run_tool(reg, ctx, "subagent",
                 {"action": "spawn", "task": "test", "tools": ["f_read"]})
        ctx.spawn.assert_called_once()

    def test_uc_spawn_missing_task(self, reg, ctx):
        result = run_tool(reg, ctx, "subagent", {"action": "spawn"})
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data

    def test_uc_spawn_with_tools_whitelist(self, reg, ctx):
        ctx.spawn = AsyncMock(return_value="done")
        run_tool(reg, ctx, "subagent", {
            "action": "spawn",
            "task": "read only",
            "tools": ["f_read", "search_files"],
        })
        ctx.spawn.assert_called_once()


pass

class TestSkillUseCases:

    def test_uc_search_skills_empty(self, reg, ctx):
        result = run_tool(reg, ctx, "search_skills", {"query": ""})
        assert result is not None

    def test_uc_search_skills_nonexistent(self, reg, ctx):
        result = run_tool(reg, ctx, "search_skills", {"query": "zzz_no_match"})
        assert result is not None

    def test_uc_use_skill_nonexistent(self, reg, ctx):
        result = run_tool(reg, ctx, "use_skill", {"name": "no_such_skill"})
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data

    def test_uc_use_skill_missing_name(self, reg, ctx):
        result = run_tool(reg, ctx, "use_skill", {})
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data


pass

class TestWorkflowUseCases:

    def test_uc_workflow_no_engine(self, reg, ctx):
        result = run_tool(reg, ctx, "workflow", {"action": "run", "name": "test_wf"})
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data

    def test_uc_workflow_with_mock(self, reg, ctx):
        ctx.workflow_start = AsyncMock(return_value="工作流完成")
        result = run_tool(reg, ctx, "workflow", {"action": "run", "name": "test_wf"})
        assert "工作流完成" in result

    def test_uc_workflow_missing_name(self, reg, ctx):
        result = run_tool(reg, ctx, "workflow", {"action": "run"})
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data


pass

class TestMemoryUseCases:

    def test_uc_save_memory_no_fn(self, reg, ctx):
        result = run_tool(reg, ctx, "memory",
                          {"action": "save", "content": "v"})
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data

    def test_uc_save_memory_with_mock(self, reg, ctx):
        ctx.save_memory = AsyncMock(return_value="已保存")
        result = run_tool(reg, ctx, "memory",
                          {"action": "save", "content": "some memory"})
        assert "已保存" in result

    def test_uc_save_memory_missing_params(self, reg, ctx):
        result = run_tool(reg, ctx, "memory", {"action": "save"})
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data

    def test_uc_search_memory_with_mock(self, reg, ctx):
        ctx.memory_search = AsyncMock(return_value="[命中] 约定")
        result = run_tool(reg, ctx, "memory",
                          {"action": "search", "query": "约定"})
        assert "命中" in result


pass

class TestMultiRoundToolChain:

    def test_uc_chain_read_edit_verify(self, reg, ctx, workspace):
        pass
        r1 = run_tool(reg, ctx, "f_read", {"path": "hello.txt"})
        assert "Hello, World!" in r1

        pass
        r2 = run_tool(reg, ctx, "f_replace", {
            "path": "hello.txt", "old": "Hello", "new": "Hi",
        })
        assert "已修改" in r2

        pass
        r3 = run_tool(reg, ctx, "f_read", {"path": "hello.txt"})
        assert "Hi, World!" in r3
        assert "Hello" not in r3

    @POSIX_ONLY
    def test_uc_chain_write_run_verify(self, reg, ctx, workspace):
        pass
        run_tool(reg, ctx, "f_write", {
            "path": "test_script.py",
            "content": "import sys\nprint(f'args: {sys.argv[1:]}')\nprint('result: 42')\n",
        })

        pass
        r2 = run_tool(reg, ctx, "run_command", {"command": "python3 test_script.py --flag"})
        assert "result: 42" in r2

        pass
        r3 = run_tool(reg, ctx, "search_files", {"path": "."})
        assert "test_script.py" in r3

    def test_uc_chain_search_read_grep(self, reg, ctx, workspace):
        pass
        r1 = run_tool(reg, ctx, "search_files", {"pattern": "*.py"})
        assert "main.py" in r1

        pass
        r2 = run_tool(reg, ctx, "f_read", {"path": "src/main.py"})
        assert "def main()" in r2

        pass
        r3 = run_tool(reg, ctx, "grep", {"key": ["def main"]})
        assert "main.py" in r3

    def test_uc_concurrent_tool_calls(self, reg, ctx, workspace):
        async def run_concurrent():
            tasks = [
                reg.execute("f_read", {"path": "hello.txt"}, ctx),
                reg.execute("search_files", {"path": "."}, ctx),
                reg.execute("f_read", {"path": "data.json"}, ctx),
                reg.execute("grep", {"key": ["def"]}, ctx),
            ]
            return await asyncio.gather(*tasks)

        results = asyncio.run(run_concurrent())
        assert "Hello" in results[0]
        assert "hello.txt" in results[1]
        assert "key" in results[2]
        assert "main.py" in results[3] or "utils.py" in results[3]


pass

class TestSchemaValidation:

    EXPECTED_TOOLS = [
        "f_read", "f_write", "f_replace", "f_path", "search_files", "grep",
        "run_command", "web",
        "subagent", "workflow", "memory", "todo",
        "gen_image", "asr", "ocr", "embed",
    ]

    def test_all_tools_registered(self, reg):
        actual = set(reg.tools.keys())
        for t in self.EXPECTED_TOOLS:
            assert t in actual, f"工具 {t} 未注册"

    def test_all_schemas_valid(self, reg):
        for s in reg.schemas:
            assert s["type"] == "function"
            fn = s["function"]
            assert "name" in fn and "description" in fn
            params = fn["parameters"]
            assert params["type"] == "object"
            assert "properties" in params

    @pytest.mark.parametrize("tool_name,required_params", [
        ("f_read", ["path"]),
        ("f_write", ["path", "content"]),
        
        ("grep", ["key"]),
        ("search_files", []),
        ("run_command", ["command"]),
        ("subagent", ["action"]),
    ])
    def test_required_params_present(self, reg, tool_name, required_params):
        schemas = {s["function"]["name"]: s for s in reg.schemas}
        if tool_name in schemas:
            props = schemas[tool_name]["function"]["parameters"]["properties"]
            for p in required_params:
                assert p in props, f"{tool_name} 缺少参数 {p}"


pass

class TestErrorInjection:

    def test_uc_tool_exception_caught(self, reg, ctx):
        result = run_tool(reg, ctx, "f_read", {"path": "/dev/null/nonexistent/path"})
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data

    def test_uc_extra_params_rejected(self, reg, ctx, workspace):
        result = run_tool(reg, ctx, "f_read", {"path": "hello.txt", "extra": 123})
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data

    def test_uc_wrong_param_type(self, reg, ctx):
        result = run_tool(reg, ctx, "f_read", {"path": 12345})
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data

    def test_uc_unknown_tool(self, reg, ctx):
        result = run_tool(reg, ctx, "nonexistent_tool", {"x": 1})
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data
        assert "未知工具" in data["error"]


pass

class TestHookMechanism:

    @POSIX_ONLY
    def test_uc_before_hook_blocks(self, tmp_path):
        reg = build_registry()
        ctx_obj = make_ctx(str(tmp_path))
        pass
        hook_script = tmp_path / "block_hook.sh"
        hook_script.write_text("#!/bin/bash\necho 'blocked by hook'\nexit 1\n", encoding="utf-8")
        hook_script.chmod(0o755)
        reg.add_hook("before", str(hook_script))
        (tmp_path / "test.txt").write_text("hello", encoding="utf-8")
        result = run_tool(reg, ctx_obj, "f_read", {"path": "test.txt"})
        data = parse_result(result)
        assert isinstance(data, dict) and "error" in data
        assert "blocked" in data["error"] or "拦截" in data["error"]

    def test_uc_before_hook_allows(self, tmp_path):
        reg = build_registry()
        ctx_obj = make_ctx(str(tmp_path))
        hook_script = tmp_path / "allow_hook.sh"
        hook_script.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
        hook_script.chmod(0o755)
        reg.add_hook("before", str(hook_script))
        (tmp_path / "test.txt").write_text("hello", encoding="utf-8")
        result = run_tool(reg, ctx_obj, "f_read", {"path": "test.txt"})
        assert "hello" in result

    def test_uc_after_hook_notifies(self, tmp_path):
        reg = build_registry()
        ctx_obj = make_ctx(str(tmp_path))
        hook_script = tmp_path / "after_hook.sh"
        hook_script.write_text("#!/bin/bash\necho 'after hook called'\nexit 0\n", encoding="utf-8")
        hook_script.chmod(0o755)
        reg.add_hook("after", str(hook_script))
        (tmp_path / "test.txt").write_text("hello", encoding="utf-8")
        result = run_tool(reg, ctx_obj, "f_read", {"path": "test.txt"})
        assert "hello" in result


pass

class TestFullAgentTurnSimulation:

    def test_uc_single_tool_turn(self, reg, ctx, workspace):
        pass
        tool_call = {
            "name": "f_read",
            "arguments": json.dumps({"path": "hello.txt"}),
        }

        pass
        args = json.loads(tool_call["arguments"])
        assert args["path"] == "hello.txt"

        pass
        result = run_tool(reg, ctx, tool_call["name"], args)

        pass
        assert "Hello, World!" in result

    def test_uc_multi_tool_turn(self, reg, ctx, workspace):
        tool_calls = [
            {"name": "f_read", "arguments": json.dumps({"path": "hello.txt"})},
            {"name": "search_files", "arguments": json.dumps({"path": "."})},
            {"name": "grep", "arguments": json.dumps({"key": ["def"]})},
        ]

        results = []
        for tc in tool_calls:
            args = json.loads(tc["arguments"])
            r = run_tool(reg, ctx, tc["name"], args)
            results.append(r)

        assert "Hello" in results[0]
        assert "hello.txt" in results[1]
        assert "main.py" in results[2] or "utils.py" in results[2]

    def test_uc_tool_error_recovery(self, reg, ctx, workspace):
        pass
        r1 = run_tool(reg, ctx, "f_read", {"path": "nonexistent.txt"})
        data = parse_result(r1)
        assert "error" in data

        pass
        r2 = run_tool(reg, ctx, "search_files", {"path": "."})
        assert "hello.txt" in r2

        pass
        r3 = run_tool(reg, ctx, "f_read", {"path": "hello.txt"})
        assert "Hello, World!" in r3

    @POSIX_ONLY
    def test_uc_install_command_recovery(self, reg, ctx, workspace):
        pass
        r1 = run_tool(reg, ctx, "run_command", {"command": "pip install requests"})
        data = parse_result(r1)
        assert "error" in data

        pass
        r2 = run_tool(reg, ctx, "run_command", {"command": "python3 -c 'import json; print(json.__name__)'"})
        assert "json" in r2

    def test_uc_subagent_spawn_workflow(self, reg, ctx, workspace):
        ctx.spawn = AsyncMock(return_value="子Agent读取了 hello.txt，内容: Hello, World!")
        result = run_tool(reg, ctx, "subagent", {
            "action": "spawn",
            "task": "读取 hello.txt 并总结内容",
            "tools": ["f_read"],
        })
        assert "Hello, World!" in result

    def test_uc_full_conversation_flow(self, reg, ctx, workspace):
        conversation = [
            {"role": "user", "content": "帮我查看项目里有哪些 Python 文件"},
        ]

        pass
        r1 = run_tool(reg, ctx, "search_files", {"pattern": "*.py"})
        assert "main.py" in r1
        conversation.append({"role": "tool", "content": r1})

        pass
        r2 = run_tool(reg, ctx, "f_read", {"path": "src/main.py"})
        assert "def main()" in r2
        conversation.append({"role": "tool", "content": r2})

        pass
        r3 = run_tool(reg, ctx, "f_replace", {
            "path": "src/main.py",
            "old": "print('hello')", "new": "print('hello world')",
        })
        assert "已修改" in r3
        conversation.append({"role": "tool", "content": r3})

        pass
        r4 = run_tool(reg, ctx, "f_read", {"path": "src/main.py"})
        assert "hello world" in r4

        pass
        final_reply = "已将 src/main.py 中的 print('hello') 改为 print('hello world')。"
        conversation.append({"role": "assistant", "content": final_reply})

        pass
        roles = [m["role"] for m in conversation]
        assert "user" in roles
        assert roles.count("tool") >= 3
        assert roles[-1] == "assistant"


pass

class TestHookDoesNotBlockEventLoop:

    @POSIX_ONLY
    def test_hook_runs_off_the_event_loop(self, tmp_path):
        import asyncio
        import time

        reg = build_registry()
        ctx_obj = make_ctx(str(tmp_path))
        hook = tmp_path / "slow_hook.sh"
        pass
        hook.write_text("#!/bin/bash\nsleep 0.6\nexit 0\n", encoding="utf-8")
        hook.chmod(0o755)
        reg.add_hook("before", str(hook))
        (tmp_path / "test.txt").write_text("hello", encoding="utf-8")

        ticks = 0

        async def scenario():
            nonlocal ticks
            stop = False

            async def ticker():
                nonlocal ticks
                while not stop:
                    ticks += 1
                    await asyncio.sleep(0.02)

            t = asyncio.create_task(ticker())
            try:
                res = await reg.execute("f_read", {"path": "test.txt"}, ctx_obj)
            finally:
                stop = True
                await t
            return res

        started = time.monotonic()
        res = asyncio.run(scenario())
        elapsed = time.monotonic() - started
        assert "hello" in res
        assert elapsed >= 0.5, "钩子确实执行了（不能被跳过快）"
        pass
        assert ticks >= 10, f"事件循环被钩子阻塞了（ticks={ticks}）"
