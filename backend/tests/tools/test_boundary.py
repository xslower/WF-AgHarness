from __future__ import annotations

import os
import pytest
from app.security.audit.boundary import Boundary, is_critical_path, is_project_path, classify_path, resolve_project_root


class TestIsCriticalPath:
    def test_etc_is_critical(self):
        assert is_critical_path("/etc/nginx/nginx.conf") is True
        assert is_critical_path("/etc/passwd") is True
        assert is_critical_path("/etc/shadow") is True
        assert is_critical_path("/etc/sudoers") is True

    def test_boot_is_critical(self):
        assert is_critical_path("/boot/vmlinuz") is True

    def test_usr_is_critical(self):
        assert is_critical_path("/usr/bin/python") is True
        assert is_critical_path("/usr/local/bin/app") is True

    def test_ssh_dir_is_critical(self):
        ssh_dir = os.path.expanduser("~/.ssh")
        assert is_critical_path(f"{ssh_dir}/authorized_keys") is True
        assert is_critical_path(f"{ssh_dir}/config") is True
        assert is_critical_path(f"{ssh_dir}/id_rsa") is True

    def test_tmp_is_not_critical(self):
        assert is_critical_path("/tmp/test.txt") is False
        assert is_critical_path("/var/log/app.log") is False
        assert is_critical_path("/home/user/project/file.py") is False

    def test_empty_path(self):
        assert is_critical_path("") is False

    def test_relative_path(self):
        assert is_critical_path("etc/hosts") is False


class TestIsProjectPath:
    def test_inside_project(self):
        root = "/home/user/project"
        assert is_project_path("/home/user/project/src/main.py", root) is True
        assert is_project_path("/home/user/project", root) is True
        assert is_project_path("/home/user/project/sub/dir/file.txt", root) is True

    def test_outside_project(self):
        root = "/home/user/project"
        assert is_project_path("/home/user/other/file.py", root) is False
        assert is_project_path("/tmp/file.txt", root) is False
        assert is_project_path("/etc/nginx.conf", root) is False

    def test_empty_args(self):
        assert is_project_path("", "") is False
        assert is_project_path("", "/root") is False
        assert is_project_path("/tmp", "") is False

    def test_tilde_expansion(self):
        root = os.path.expanduser("~/project")
        assert is_project_path("~/project/file.txt", root) is True


class TestClassifyPath:
    def test_critical_paths(self):
        assert classify_path("/etc/passwd", "/home/project") == Boundary.critical
        assert classify_path("/boot/vmlinuz", "/home/project") == Boundary.critical

    def test_project_inside(self):
        assert classify_path("/home/project/src/main.py", "/home/project") == Boundary.project_inside

    def test_project_outside(self):
        assert classify_path("/tmp/log.txt", "/home/project") == Boundary.project_outside
        assert classify_path("/var/log/app.log", "/home/project") == Boundary.project_outside

    def test_empty_path_is_inside(self):
        assert classify_path("", "/home/project") == Boundary.project_inside


class TestResolveProjectRoot:
    def test_with_harness_dir(self, tmp_path):
        project = tmp_path / "myproject"
        harness_dir = project / ".harness"
        harness_dir.mkdir(parents=True)
        subdir = project / "src" / "deep"
        subdir.mkdir(parents=True)

        root = resolve_project_root(str(subdir))
        assert root == str(project)

    def test_without_harness_dir(self, tmp_path):
        subdir = tmp_path / "no_harness" / "deep"
        subdir.mkdir(parents=True)

        root = resolve_project_root(str(subdir))
        assert root == str(subdir)


class TestSymlinkDualForm:

    def _pair(self, tmp_path):
        real = tmp_path / "real"
        (real / "proj" / "sub").mkdir(parents=True)
        (real / "proj" / "sub" / "a.py").write_text("x")
        link = tmp_path / "link"
        link.symlink_to(real, target_is_directory=True)
        return str(link / "proj"), str(real / "proj")

    def test_real_path_under_symlink_root(self, tmp_path):
        soft, real = self._pair(tmp_path)
        assert is_project_path(real + "/sub/a.py", soft) is True
        assert classify_path(real + "/sub/a.py", soft) == Boundary.project_inside

    def test_symlink_path_under_real_root(self, tmp_path):
        soft, real = self._pair(tmp_path)
        assert is_project_path(soft + "/sub/a.py", real) is True
        assert classify_path(soft + "/sub/a.py", real) == Boundary.project_inside

    def test_both_symlink(self, tmp_path):
        soft, _ = self._pair(tmp_path)
        assert is_project_path(soft + "/sub/a.py", soft) is True

    def test_outside_still_outside(self, tmp_path):
        soft, _ = self._pair(tmp_path)
        assert is_project_path(str(tmp_path / "real" / "other" / "x"), soft) is False
        assert classify_path("/tmp/x.log", soft) == Boundary.project_outside

    def test_symlink_escaping_project_still_inside(self, tmp_path):
        soft, _ = self._pair(tmp_path)
        out = tmp_path / "outside.txt"
        out.write_text("x")
        (tmp_path / "real" / "proj" / "escape").symlink_to(out)
        assert is_project_path(soft + "/escape", soft) is True

    def test_critical_through_symlink(self, tmp_path):
        link = tmp_path / "etc_link"
        link.symlink_to("/etc", target_is_directory=True)
        assert is_critical_path(str(link / "passwd")) is True
        assert classify_path(str(link / "passwd"), str(tmp_path)) == Boundary.critical

    def test_shm_still_exempt_through_realpath(self):
        assert is_critical_path("/dev/shm/x") is False
        assert is_critical_path("/dev/shm") is False
