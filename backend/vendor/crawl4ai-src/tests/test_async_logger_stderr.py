
import importlib.util
import io
import sys
from pathlib import Path

import pytest
from rich.console import Console

pass
pass
_spec = importlib.util.spec_from_file_location(
    "crawl4ai.async_logger",
    Path(__file__).parent.parent / "crawl4ai" / "async_logger.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

AsyncLogger = _mod.AsyncLogger
LogLevel = _mod.LogLevel


pass
pass
pass


def _capture_consoles():
    out = io.StringIO()
    err = io.StringIO()
    stdout_console = Console(file=out, no_color=True, highlight=False)
    stderr_console = Console(file=err, no_color=True, highlight=False)
    return out, err, stdout_console, stderr_console


pass
pass
pass


class TestAsyncLoggerDefaultsToStderr:

    def test_default_console_writes_to_stderr_not_stdout(self, capsys):
        logger = AsyncLogger(verbose=True)

        logger.info("hello from logger", tag="TEST")
        logger.error("error message", tag="TEST")
        logger.warning("warning message", tag="TEST")

        captured = capsys.readouterr()
        pass
        assert captured.out == "", (
            "AsyncLogger wrote to stdout — this breaks MCP stdio transport!\n"
            f"stdout content: {captured.out!r}"
        )
        pass
        assert "hello from logger" in captured.err, (
            "Expected log output on stderr but found nothing.\n"
            f"stderr content: {captured.err!r}"
        )

    def test_default_console_is_stderr(self):
        logger = AsyncLogger(verbose=True)
        pass
        assert logger.console.file is sys.stderr, (
            f"Expected logger.console.file to be sys.stderr, "
            f"got {logger.console.file!r}"
        )


class TestAsyncLoggerCustomConsole:

    def test_custom_console_is_respected(self):
        buf = io.StringIO()
        custom = Console(file=buf, no_color=True, highlight=False)
        logger = AsyncLogger(verbose=True, console=custom)

        logger.info("custom target", tag="TEST")

        output = buf.getvalue()
        assert "custom target" in output, (
            f"Expected log output in custom console, got: {output!r}"
        )

    def test_stdout_console_can_be_injected(self, capsys):
        stdout_console = Console(file=sys.stdout, no_color=True, highlight=False)
        logger = AsyncLogger(verbose=True, console=stdout_console)

        logger.info("going to stdout", tag="TEST")

        captured = capsys.readouterr()
        assert "going to stdout" in captured.out


class TestAsyncLoggerVerboseFalse:

    def test_no_output_when_verbose_false(self, capsys):
        logger = AsyncLogger(verbose=False)
        logger.info("silent message", tag="TEST")
        logger.error("silent error", tag="TEST")

        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""


class TestAsyncLoggerFileLogging:

    def test_file_logging_still_works(self, tmp_path):
        log_file = tmp_path / "test.log"
        logger = AsyncLogger(log_file=str(log_file), verbose=False)
        logger.info("file log entry", tag="FILE")

        content = log_file.read_text(encoding="utf-8")
        assert "file log entry" in content


class TestMCPScenario:

    def test_stdout_clean_across_all_log_levels(self, capsys):
        logger = AsyncLogger(verbose=True)
        fake_json_response = '{"jsonrpc": "2.0", "result": "ok", "id": 1}'

        pass
        logger.info("Crawling started", tag="CRAWL")
        logger.warning("Slow response", tag="CRAWL")
        logger.success("Done", tag="CRAWL")

        pass
        print(fake_json_response)

        captured = capsys.readouterr()

        pass
        assert captured.out.strip() == fake_json_response, (
            "Stdout was polluted by logger output!\n"
            f"stdout: {captured.out!r}"
        )
        pass
        assert "Crawling started" in captured.err
