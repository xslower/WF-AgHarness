from __future__ import annotations

import pytest
from app.security.audit.paths import extract_from_shell_command, extract_from_tool_args


class TestExtractFromShellCommand:
    def test_rm_single_file(self):
        paths = extract_from_shell_command("rm /tmp/test.txt")
        assert "/tmp/test.txt" in paths

    def test_rm_multiple_files(self):
        paths = extract_from_shell_command("rm /tmp/a.txt /tmp/b.txt")
        assert len(paths) >= 1

    def test_rm_rf(self):
        paths = extract_from_shell_command("rm -rf /var/cache/*")
        assert "/var/cache/*" in paths

    def test_mv_paths(self):
        paths = extract_from_shell_command("mv /tmp/a.txt /tmp/b.txt")
        assert "/tmp/b.txt" in paths

    def test_chmod(self):
        paths = extract_from_shell_command("chmod 755 /opt/script.sh")
        assert "/opt/script.sh" in paths

    def test_chown(self):
        paths = extract_from_shell_command("chown root:root /etc/app.conf")
        assert "/etc/app.conf" in paths

    def test_redirect_write(self):
        paths = extract_from_shell_command("echo hello > /tmp/output.txt")
        assert "/tmp/output.txt" in paths

    def test_redirect_append(self):
        paths = extract_from_shell_command("echo hello >> /tmp/output.txt")
        assert "/tmp/output.txt" in paths

    def test_dd_of(self):
        paths = extract_from_shell_command("dd if=/dev/zero of=/tmp/image.img bs=1M count=100")
        assert "/tmp/image.img" in paths

    def test_install(self):
        paths = extract_from_shell_command("install -m 755 /src/app /usr/local/bin/app")
        assert "/usr/local/bin/app" in paths

    def test_cp_dest(self):
        paths = extract_from_shell_command("cp /src/a.txt /dst/b.txt")
        assert "/dst/b.txt" in paths

    def test_readonly_commands_no_paths(self):
        paths = extract_from_shell_command("ls -la /tmp")
        assert len(paths) == 0

    def test_empty_command(self):
        assert extract_from_shell_command("") == []


class TestExtractFromToolArgs:
    def test_f_write(self):
        paths = extract_from_tool_args("f_write", {"path": "/home/project/test.txt"})
        assert "/home/project/test.txt" in paths

    def test_remote_write(self):
        paths = extract_from_tool_args("remote_write", {
            "file_path": "/home/project/config.yaml",
            "content": "key: value"
        })
        assert "/home/project/config.yaml" in paths

    def test_f_path_with_target(self):
        paths = extract_from_tool_args("f_path", {
            "path": "/src",
            "target": "/dst"
        })
        assert "/src" in paths
        assert "/dst" in paths

    def test_run_command_delegates_to_shell(self):
        paths = extract_from_tool_args("run_command", {
            "command": "rm /tmp/cleanup.sh"
        })
        assert "/tmp/cleanup.sh" in paths

    def test_run_command_empty_cmd(self):
        paths = extract_from_tool_args("run_command", {"command": ""})
        assert paths == []

    def test_unknown_tool(self):
        paths = extract_from_tool_args("unknown_tool", {"path": "/tmp/x"})
        assert "/tmp/x" in paths

    def test_empty_args(self):
        assert extract_from_tool_args("f_write", {}) == []
