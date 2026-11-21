from __future__ import annotations

import pytest
from app.security.audit.boundary import Boundary
from app.security.audit.risk import Decision, OpType, classify_operation, assess, RiskAssessment

PROJECT = "/home/user/project"


class TestClassifyOperation:
    def test_rm_is_delete(self):
        assert classify_operation("run_command", {"command": "rm /tmp/test.txt"}) == OpType.delete

    def test_rmdir_is_delete(self):
        assert classify_operation("run_command", {"command": "rmdir /tmp/old"}) == OpType.delete

    def test_mv_is_move(self):
        assert classify_operation("run_command", {"command": "mv /tmp/a /tmp/b"}) == OpType.move

    def test_chmod_is_permission(self):
        assert classify_operation("run_command", {"command": "chmod 755 /tmp/script"}) == OpType.permission

    def test_chown_is_permission(self):
        assert classify_operation("run_command", {"command": "chown user /tmp/file"}) == OpType.permission

    def test_redirect_is_create(self):
        assert classify_operation("run_command", {"command": "echo hello > /tmp/new.txt"}) == OpType.create

    def test_f_write_is_create(self):
        assert classify_operation("f_write", {"path": "/tmp/new.txt"}) == OpType.create

    def test_f_replace_is_modify(self):
        assert classify_operation("f_replace", {"path": "/tmp/new.txt"}) == OpType.modify

    def test_remote_edit_is_modify(self):
        assert classify_operation("remote_edit", {"file_path": "/tmp/test.txt"}) == OpType.modify

    def test_f_path_delete(self):
        assert classify_operation("f_path", {"action": "delete"}) == OpType.delete

    def test_f_path_move(self):
        assert classify_operation("f_path", {"action": "move"}) == OpType.move

    def test_f_path_copy(self):
        assert classify_operation("f_path", {"action": "copy"}) == OpType.create

    def test_f_path_chmod(self):
        assert classify_operation("f_path", {"action": "chmod"}) == OpType.permission

    def test_empty_command_is_read(self):
        assert classify_operation("run_command", {"command": ""}) == OpType.read

    def test_readonly_command_is_execute(self):
        assert classify_operation("run_command", {"command": "ls -la"}) == OpType.execute


class TestAssess:
    def test_project_inside_all_silent(self):
        r = assess("f_write", {"path": f"{PROJECT}/src/main.py"}, PROJECT)
        assert r.decision == Decision.silent
        assert r.boundary == Boundary.project_inside

    def test_project_outside_delete_needs_confirm(self):
        r = assess("run_command", {"command": "rm /tmp/test.txt"}, PROJECT)
        assert r.decision == Decision.confirm
        assert r.boundary == Boundary.project_outside

    def test_project_outside_create_is_notify(self):
        r = assess("f_write", {"path": "/tmp/new_file.txt"}, PROJECT)
        assert r.decision == Decision.notify

    def test_project_outside_modify_needs_confirm(self):
        r = assess("remote_edit", {"file_path": "/tmp/existing.txt"}, PROJECT)
        assert r.decision == Decision.confirm

    def test_critical_path_blocked(self):
        r = assess("run_command", {"command": "rm /etc/passwd"}, PROJECT)
        assert r.decision == Decision.block
        assert r.boundary == Boundary.critical

    def test_critical_path_write_blocked(self):
        r = assess("f_write", {"path": "/etc/nginx/nginx.conf"}, PROJECT)
        assert r.decision == Decision.block

    def test_critical_path_read_is_silent(self):
        r = assess("run_command", {"command": "cat /etc/hostname"}, PROJECT)
        assert r.decision == Decision.silent

    def test_no_paths_uses_conservative(self):
        r = assess("run_command", {"command": "python deploy.py"}, PROJECT)
        assert r.boundary == Boundary.project_outside
        assert r.unknown_paths is True

    def test_risk_assessment_to_error_json_block(self):
        r = RiskAssessment(
            decision=Decision.block, boundary=Boundary.critical,
            op_type=OpType.delete, paths=["/etc/passwd"],
            reason="禁止删除系统关键文件",
        )
        err = r.to_error_json()
        assert "audit_blocked" in err
        assert "/etc/passwd" in err

    def test_risk_assessment_to_error_json_confirm(self):
        r = RiskAssessment(
            decision=Decision.confirm, boundary=Boundary.project_outside,
            op_type=OpType.delete, paths=["/tmp/test.txt"],
            reason="需要确认",
        )
        err = r.to_error_json()
        assert "audit_confirm_required" in err
        assert "/tmp/test.txt" in err

    def test_multiple_paths_take_worst_boundary(self):
        from app.security.audit.risk import assess as a
        r = a("run_command", {"command": "rm /tmp/safe.txt /etc/dangerous.conf"}, PROJECT)
        assert r.boundary == Boundary.critical
        assert r.decision == Decision.block
