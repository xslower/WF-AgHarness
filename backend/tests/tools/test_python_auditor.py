from __future__ import annotations

import pytest
from app.security.audit.python_auditor import PythonAuditor
from app.security.audit.base import PathConfidence


@pytest.fixture
def auditor():
    return PythonAuditor()


class TestSafeCode:
    def test_pure_computation(self, auditor):
        code = 'x = 1 + 2\nprint(x)'
        result = auditor.audit(code)
        assert result.safe is True
        assert len(result.callsites) == 0

    def test_readonly_operations(self, auditor):
        code = 'import os\nfiles = os.listdir("/tmp")'
        result = auditor.audit(code)
        assert len(result.callsites) == 0

    def test_empty_code(self, auditor):
        result = auditor.audit("")
        assert result.safe is True


class TestBlacklistDetection:
    def test_os_remove(self, auditor):
        code = 'import os\nos.remove("/tmp/test.txt")'
        result = auditor.audit(code)
        assert len(result.callsites) == 1
        assert result.callsites[0].method == "os.remove"

    def test_os_unlink(self, auditor):
        code = 'import os\nos.unlink("/tmp/test.txt")'
        result = auditor.audit(code)
        assert len(result.callsites) == 1
        assert result.callsites[0].method == "os.unlink"

    def test_shutil_rmtree(self, auditor):
        code = 'import shutil\nshutil.rmtree("/tmp/cache")'
        result = auditor.audit(code)
        assert len(result.callsites) == 1

    def test_shutil_move(self, auditor):
        code = 'import shutil\nshutil.move("/tmp/a", "/tmp/b")'
        result = auditor.audit(code)
        assert len(result.callsites) == 1

    def test_os_chmod(self, auditor):
        code = 'import os\nos.chmod("/tmp/script.sh", 0o755)'
        result = auditor.audit(code)
        assert len(result.callsites) == 1

    def test_open_write(self, auditor):
        code = 'open("/tmp/log.txt", "w").write("data")'
        result = auditor.audit(code)
        assert len(result.callsites) >= 1

    def test_pathlib_unlink(self, auditor):
        code = 'from pathlib import Path\nPath("/tmp/test.txt").unlink()'
        result = auditor.audit(code)
        assert len(result.callsites) == 1

    def test_multiple_dangerous_calls(self, auditor):
        code = '''
import os
os.remove("/tmp/a.txt")
os.remove("/tmp/b.txt")
'''
        result = auditor.audit(code)
        assert len(result.callsites) == 2


class TestForbiddenDetection:
    def test_os_system(self, auditor):
        code = 'import os\nos.system("rm -rf /")'
        result = auditor.audit(code)
        assert len(result.forbidden_calls) >= 1

    def test_subprocess_run(self, auditor):
        code = 'import subprocess\nsubprocess.run(["ls", "-la"])'
        result = auditor.audit(code)
        assert len(result.forbidden_calls) >= 1

    def test_eval(self, auditor):
        code = 'eval("1 + 1")'
        result = auditor.audit(code)
        assert len(result.forbidden_calls) >= 1


class TestPathTracking:
    def test_literal_path_is_known(self, auditor):
        code = 'import os\nos.remove("/tmp/test.txt")'
        result = auditor.audit(code)
        assert result.callsites[0].paths[0].confidence == PathConfidence.known
        assert result.callsites[0].paths[0].value == "/tmp/test.txt"

    def test_variable_tracking(self, auditor):
        code = '''
import os
path = "/tmp/test.txt"
os.remove(path)
'''
        result = auditor.audit(code)
        cs = [c for c in result.callsites if c.method == "os.remove"]
        assert len(cs) >= 1
        pass
        assert cs[0].paths[0].confidence == PathConfidence.known
        assert cs[0].paths[0].value == "/tmp/test.txt"

    def test_fstring_concat(self, auditor):
        code = '''
import os
base = "/var/log"
name = "app"
path = f"{base}/{name}.log"
os.remove(path)
'''
        result = auditor.audit(code)
        cs = [c for c in result.callsites if c.method == "os.remove"]
        assert len(cs) >= 1
        assert cs[0].paths[0].confidence == PathConfidence.known
        assert "/var/log/app.log" in cs[0].paths[0].value

    def test_unknown_variable(self, auditor):
        code = '''
import os
os.remove(unknown_var)
'''
        result = auditor.audit(code)
        cs = [c for c in result.callsites if c.method == "os.remove"]
        assert len(cs) >= 1
        assert cs[0].paths[0].confidence == PathConfidence.unknown


class TestSyntaxError:
    def test_syntax_error_returns_error(self, auditor):
        result = auditor.audit("import os os.remove(/)")
        assert result.safe is False
        assert len(result.errors) >= 1
