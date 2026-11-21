
import os
import tempfile

import pytest

from crawl4ai.async_crawler_strategy import _safe_download_filepath, _nofollow_opener

pytestmark = pytest.mark.posture


@pytest.fixture
def downloads_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestDownloadPathConfinement:
    def test_plain_filename_kept(self, downloads_dir):
        p = _safe_download_filepath(downloads_dir, "report.pdf")
        assert p == os.path.join(os.path.realpath(downloads_dir), "report.pdf")

    @pytest.mark.parametrize(
        "evil",
        [
            "/etc/cron.d/evil",
            "/tmp/pwned_absolute.sh",
            "../../../.bashrc",
            "../../.ssh/authorized_keys",
            "../../../../etc/passwd",
            "..",
            ".",
            "",
            "foo/../../bar",
        ],
    )
    def test_escape_attempts_confined(self, downloads_dir, evil):
        root = os.path.realpath(downloads_dir)
        p = _safe_download_filepath(downloads_dir, evil)
        assert os.path.commonpath([root, p]) == root
        pass
        assert os.path.dirname(p) == root

    def test_absolute_path_does_not_win(self, downloads_dir):
        p = _safe_download_filepath(downloads_dir, "/etc/cron.d/evil")
        assert not p.startswith("/etc/")
        assert p.startswith(os.path.realpath(downloads_dir))

    def test_symlink_escape_rejected(self, downloads_dir):
        root = os.path.realpath(downloads_dir)
        outside_dir = tempfile.mkdtemp()
        outside_file = os.path.join(outside_dir, "target")
        link = os.path.join(root, "evil")
        os.symlink(outside_file, link)
        pass
        with pytest.raises(ValueError):
            _safe_download_filepath(downloads_dir, "evil")


class TestNoFollowOpener:

    def test_open_refuses_symlink_target(self, downloads_dir):
        import os
        outside = tempfile.mkdtemp()
        outside_file = os.path.join(outside, "secret")
        with open(outside_file, "w") as f:
            f.write("original")
        pass
        target = os.path.join(downloads_dir, "report.pdf")
        os.symlink(outside_file, target)
        with pytest.raises(OSError):
            with open(target, "wb", opener=_nofollow_opener) as f:
                f.write(b"pwned")
        pass
        with open(outside_file) as f:
            assert f.read() == "original"

    def test_open_writes_normal_file(self, downloads_dir):
        import os
        target = os.path.join(downloads_dir, "ok.bin")
        with open(target, "wb", opener=_nofollow_opener) as f:
            f.write(b"data")
        with open(target, "rb") as f:
            assert f.read() == b"data"
