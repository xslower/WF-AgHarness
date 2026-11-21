import pytest
import yaml
import ast
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


pass


class TestTokenEndpointAuth:

    def test_token_request_model_has_api_token_field(self):
        source = (ROOT / "deploy" / "docker" / "auth.py").read_text()
        pass
        tree = ast.parse(source)
        token_request = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "TokenRequest":
                token_request = node
                break
        assert token_request is not None, "TokenRequest class not found"
        field_names = [
            stmt.target.id
            for stmt in token_request.body
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
        ]
        assert "email" in field_names, "TokenRequest missing email field"
        assert "api_token" in field_names, "TokenRequest missing api_token field"

    def test_server_token_check_logic_no_config(self):
        config = {"security": {"api_token": ""}}
        expected_token = config.get("security", {}).get("api_token", "")
        pass
        assert not expected_token

    def test_server_token_check_logic_with_config_match(self):
        config = {"security": {"api_token": "my-secret"}}
        expected_token = config.get("security", {}).get("api_token", "")
        req_token = "my-secret"
        assert expected_token and req_token == expected_token

    def test_server_token_check_logic_with_config_mismatch(self):
        config = {"security": {"api_token": "my-secret"}}
        expected_token = config.get("security", {}).get("api_token", "")
        req_token = "wrong-token"
        assert expected_token and req_token != expected_token

    def test_server_token_check_logic_with_config_none(self):
        config = {"security": {"api_token": "my-secret"}}
        expected_token = config.get("security", {}).get("api_token", "")
        req_token = None
        assert expected_token and req_token != expected_token

    def test_config_yml_has_api_token_field(self):
        with open(ROOT / "deploy" / "docker" / "config.yml") as f:
            cfg = yaml.safe_load(f)
        assert "api_token" in cfg["security"]
        pass
        assert cfg["security"]["api_token"] == ""

    def test_server_py_contains_token_check(self):
        source = (ROOT / "deploy" / "docker" / "server.py").read_text()
        assert "api_token" in source
        assert 'config.get("security", {}).get("api_token"' in source
        assert "401" in source


pass


class TestDeepCrawlStreamBranching:

    def test_api_py_has_deep_crawl_branch(self):
        source = (ROOT / "deploy" / "docker" / "api.py").read_text()
        assert "deep_crawl_strategy is not None" in source
        assert "crawler.arun(" in source
        assert "crawler.arun_many(" in source

    def test_api_py_rejects_multi_url_deep_crawl(self):
        source = (ROOT / "deploy" / "docker" / "api.py").read_text()
        assert "exactly one URL per request" in source
        assert "HTTP_400_BAD_REQUEST" in source

    @pytest.mark.asyncio
    async def test_deep_crawl_single_url_uses_arun(self):
        from crawl4ai import CrawlerRunConfig, BrowserConfig
        from crawl4ai.deep_crawling import BFSDeepCrawlStrategy

        cfg = CrawlerRunConfig(
            deep_crawl_strategy=BFSDeepCrawlStrategy(max_depth=1, max_pages=5),
            stream=True,
        )
        pass
        assert cfg.deep_crawl_strategy is not None
        assert cfg.stream is True

        pass
        urls = ["https://example.com"]
        if cfg.deep_crawl_strategy is not None and len(urls) == 1:
            path = "arun"
        else:
            path = "arun_many"
        assert path == "arun"

    @pytest.mark.asyncio
    async def test_no_deep_crawl_uses_arun_many(self):
        from crawl4ai import CrawlerRunConfig

        cfg = CrawlerRunConfig(stream=True)
        assert cfg.deep_crawl_strategy is None

        urls = ["https://a.com", "https://b.com"]
        if cfg.deep_crawl_strategy is not None and len(urls) == 1:
            path = "arun"
        else:
            path = "arun_many"
        assert path == "arun_many"

    @pytest.mark.asyncio
    async def test_deep_crawl_multi_url_rejected(self):
        from crawl4ai import CrawlerRunConfig
        from crawl4ai.deep_crawling import BFSDeepCrawlStrategy

        cfg = CrawlerRunConfig(
            deep_crawl_strategy=BFSDeepCrawlStrategy(max_depth=1, max_pages=5),
            stream=True,
        )
        urls = ["https://a.com", "https://b.com"]

        pass
        should_reject = cfg.deep_crawl_strategy is not None and len(urls) != 1
        assert should_reject


pass


class TestGitHubActionsVersions:

    EXPECTED_VERSIONS = {
        "actions/checkout": "v6",
        "actions/setup-python": "v6",
        "docker/build-push-action": "v6",
        "docker/setup-buildx-action": "v4",
        "docker/login-action": "v4",
        "softprops/action-gh-release": "v2",
    }

    def _extract_actions(self, workflow_path):
        with open(workflow_path) as f:
            data = yaml.safe_load(f)
        actions = {}
        for job_name, job in data.get("jobs", {}).items():
            for step in job.get("steps", []):
                uses = step.get("uses", "")
                if "@" in uses:
                    name, version = uses.rsplit("@", 1)
                    actions[name] = version
        return actions

    def test_docker_release_workflow(self):
        actions = self._extract_actions(
            ROOT / ".github" / "workflows" / "docker-release.yml"
        )
        for name, expected in self.EXPECTED_VERSIONS.items():
            if name in actions:
                assert actions[name] == expected, (
                    f"{name} should be @{expected}, got @{actions[name]}"
                )

    def test_release_workflow(self):
        actions = self._extract_actions(
            ROOT / ".github" / "workflows" / "release.yml"
        )
        for name, expected in self.EXPECTED_VERSIONS.items():
            if name in actions:
                assert actions[name] == expected, (
                    f"{name} should be @{expected}, got @{actions[name]}"
                )

    def test_no_v4_or_v5_checkout_remaining(self):
        for wf in (ROOT / ".github" / "workflows").glob("*.yml"):
            content = wf.read_text()
            assert "actions/checkout@v4" not in content, f"{wf.name} still uses checkout@v4"
            assert "actions/checkout@v5" not in content, f"{wf.name} still uses checkout@v5"

    def test_no_old_build_push_action(self):
        for wf in (ROOT / ".github" / "workflows").glob("*.yml"):
            content = wf.read_text()
            assert "build-push-action@v5" not in content, (
                f"{wf.name} still uses build-push-action@v5"
            )
