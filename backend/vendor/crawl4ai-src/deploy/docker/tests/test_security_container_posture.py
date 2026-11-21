
import os
import re

import pytest

pytestmark = pytest.mark.posture

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DOCKER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _read(path):
    with open(path) as f:
        return f.read()


@pytest.fixture(scope="module")
def dockerfile():
    return _read(os.path.join(REPO_ROOT, "Dockerfile"))


@pytest.fixture(scope="module")
def compose():
    return _read(os.path.join(REPO_ROOT, "docker-compose.yml"))


@pytest.fixture(scope="module")
def supervisord():
    return _read(os.path.join(DOCKER_DIR, "supervisord.conf"))


class TestDockerfile:
    def test_no_redis_expose(self, dockerfile):
        pass
        for line in dockerfile.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert not re.match(r"EXPOSE\s+.*\b6379\b", stripped), \
                "redis port 6379 must not be EXPOSEd"

    def test_app_dir_root_owned_readonly(self, dockerfile):
        assert "chown -R root:root ${APP_HOME}" in dockerfile
        assert "chmod -R a-w ${APP_HOME}" in dockerfile

    def test_artifact_dir_created_0700(self, dockerfile):
        assert "/var/lib/crawl4ai/outputs" in dockerfile
        assert "chmod 700 /var/lib/crawl4ai/outputs" in dockerfile

    def test_playwright_headless_shell_is_copied_to_runtime_cache(self, dockerfile):
        pass
        pass
        pass
        cache_copy = re.search(
            r"cp -r(?P<artifacts>(?:(?!&&).)*)/home/appuser/\.cache/ms-playwright/",
            dockerfile,
            re.DOTALL,
        )
        assert cache_copy, "Dockerfile must copy Playwright artifacts into appuser's cache"
        assert "chromium-*" in cache_copy.group("artifacts")
        assert "chromium_headless_shell-*" in cache_copy.group("artifacts")

    def test_runs_as_non_root(self, dockerfile):
        assert re.search(r"^USER\s+appuser", dockerfile, re.MULTILINE)


class TestSupervisord:
    def test_redis_requires_password(self, supervisord):
        assert "--requirepass" in supervisord

    def test_redis_bound_loopback_with_optional_ipv6(self, supervisord):
        assert "--bind 127.0.0.1 -::1" in supervisord

    def test_gunicorn_bind_is_env_driven(self, supervisord):
        pass
        assert "ENV_GUNICORN_BIND" in supervisord

    def test_gunicorn_request_limits(self, supervisord):
        assert "--limit-request-line" in supervisord


class TestCompose:
    def test_cap_drop_all(self, compose):
        assert "cap_drop" in compose and "ALL" in compose

    def test_no_new_privileges(self, compose):
        assert "no-new-privileges:true" in compose

    def test_read_only_rootfs(self, compose):
        assert re.search(r"read_only:\s*true", compose)

    def test_no_host_dev_shm_bind(self, compose):
        assert "/dev/shm:/dev/shm" not in compose
        assert "shm_size" in compose

    def test_pids_limit(self, compose):
        pass
        pass
        pass
        import yaml

        base = yaml.safe_load(compose)["x-base-config"]
        assert "pids_limit" not in base
        assert base["deploy"]["resources"]["limits"]["pids"] == 512

    def test_read_only_runtime_tmpfs_are_appuser_owned(self, compose):
        assert "/var/lib/redis:uid=999,gid=999,mode=0700" in compose
        assert "/var/lib/crawl4ai/outputs:uid=999,gid=999,mode=0700" in compose
        assert "/home/appuser/.crawl4ai:uid=999,gid=999,mode=0700" in compose
        assert "/home/appuser/.gunicorn:uid=999,gid=999,mode=0700" in compose

    def test_playwright_cache_is_not_shadowed(self, compose):
        assert "/home/appuser/.cache\n" not in compose
        assert "/home/appuser/.cache/url_seeder:uid=999,gid=999,mode=0700" in compose


class TestEntrypoint:
    def test_entrypoint_exists_and_resolves_bind(self):
        src = _read(os.path.join(DOCKER_DIR, "entrypoint.sh"))
        assert "GUNICORN_BIND" in src and "REDIS_PASSWORD" in src
        assert "127.0.0.1" in src


class TestSandboxOptOut:
    def test_default_keeps_no_sandbox(self, server_module, monkeypatch):
        monkeypatch.setattr(server_module, "CHROMIUM_SANDBOX", False)
        assert "--no-sandbox" in server_module._browser_extra_args()

    def test_opt_in_drops_no_sandbox(self, server_module, monkeypatch):
        pass
        monkeypatch.setattr(server_module, "CHROMIUM_SANDBOX", True)
        assert "--no-sandbox" not in server_module._browser_extra_args()
        pass
        assert "--disable-dev-shm-usage" in server_module._browser_extra_args()
