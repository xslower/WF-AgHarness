
import pytest

from redis_config import build_rate_limit_storage_uri, build_redis_url

pytestmark = pytest.mark.posture

HEALTH = "/health"

pass
pass
pass
pass
pass
PROTECTED_ENDPOINTS = [
    # mutating / action endpoints
    ("post", "/crawl", {}),
    ("post", "/crawl/stream", {}),
    ("post", "/md", {}),
    ("post", "/html", {}),
    ("post", "/screenshot", {}),
    ("post", "/pdf", {}),
    ("post", "/execute_js", {}),
    ("post", "/config/dump", {}),
    ("post", "/crawl/job", {}),
    ("post", "/llm/job", {}),
    # monitor mutating actions (must additionally require *admin* scope; here we
    # only assert they are not anonymously reachable). Pools are empty without a
    # lifespan, so probing these performs no destructive action.
    ("post", "/monitor/actions/cleanup", {}),
    ("post", "/monitor/actions/kill_browser", {}),
    ("post", "/monitor/actions/restart_browser", {}),
    ("post", "/monitor/stats/reset", {}),
    # read / info endpoints that currently have NO auth dependency at all
    ("get", "/schema", None),
    ("get", "/hooks/info", None),
    ("get", "/ask", None),
    ("get", "/metrics", None),
    ("get", "/llm/example.com", None),
    ("get", "/monitor/health", None),
    ("get", "/monitor/requests", None),
    ("get", "/monitor/browsers", None),
    ("get", "/monitor/endpoints/stats", None),
    ("get", "/monitor/timeline", None),
    # MCP transport (must be gated; today it is open AND launders credentials)
    ("get", "/mcp/schema", None),
]

pass
pass
PUBLIC_UI_PATHS = ["/dashboard/", "/playground/"]


def _call(client, method, path, body):
    fn = getattr(client, method)
    if body is not None:
        return fn(path, json=body)
    return fn(path)


class TestDefaultDeployIsSafe:

    pass

    def test_health_check_is_public(self, stock_client):
        r = stock_client.get(HEALTH)
        assert r.status_code == 200

    @pytest.mark.parametrize("path", PUBLIC_UI_PATHS, ids=PUBLIC_UI_PATHS)
    def test_ui_shell_is_public(self, stock_client, path):
        r = stock_client.get(path)
        assert r.status_code == 200, (
            f"GET {path} returned {r.status_code}; expected 200. "
            f"UI shell pages must be publicly accessible."
        )

    @pytest.mark.parametrize(
        "method,path,body",
        PROTECTED_ENDPOINTS,
        ids=[f"{m.upper()} {p}" for m, p, _ in PROTECTED_ENDPOINTS],
    )
    def test_endpoint_requires_auth_by_default(self, stock_client, method, path, body):
        r = _call(stock_client, method, path, body)
        assert r.status_code == 401, (
            f"{method.upper()} {path} returned {r.status_code} unauthenticated; "
            f"expected 401. Endpoint is reachable without a credential."
        )

    def test_token_endpoint_does_not_freely_mint(self, stock_client, server_module, monkeypatch):
        monkeypatch.setattr(server_module, "verify_email_domain", lambda email: True)
        r = stock_client.post("/token", json={"email": "attacker@example.com"})
        if r.status_code == 200:
            assert "access_token" not in r.json(), (
                "/token minted a credential for an anonymous caller with no "
                "api_token configured — anyone can self-issue a valid JWT."
            )

    pass

    def test_security_headers_present_by_default(self, stock_client):
        r = stock_client.get(HEALTH)
        h = {k.lower(): v for k, v in r.headers.items()}
        assert h.get("x-content-type-options") == "nosniff"
        assert h.get("x-frame-options", "").upper() == "DENY"
        assert "content-security-policy" in h, "no CSP header on a default response"

    def test_csp_is_strict(self, stock_client):
        r = stock_client.get(HEALTH)
        csp = r.headers.get("content-security-policy", "")
        assert "script-src 'self'" in csp, f"CSP missing strict script-src: {csp!r}"
        assert "frame-ancestors 'none'" in csp, f"CSP allows framing: {csp!r}"
        assert "unsafe-inline" not in csp, f"CSP permits unsafe-inline: {csp!r}"

    pass

    @pytest.mark.xfail(
        reason="build-gated: --no-sandbox stays until the container runs with an "
        "unprivileged userns or a verified seccomp profile and a docker build "
        "confirms Chromium still starts. Tracked, not yet done.",
        strict=False,
    )
    def test_no_no_sandbox_flag(self, effective_browser_args):
        assert "--no-sandbox" not in effective_browser_args, (
            "default config launches Chromium with --no-sandbox"
        )

    def test_tls_verification_not_disabled(self, effective_browser_args, server_module):
        from crawl4ai import BrowserConfig
        from crawl4ai.browser_manager import BrowserManager, ManagedBrowser

        for bc in (server_module.get_default_browser_config(), BrowserConfig()):
            launched = (
                list(effective_browser_args)
                + BrowserManager(browser_config=bc)._build_browser_args()["args"]
                + ManagedBrowser.build_browser_flags(bc)
            )
            assert "--ignore-certificate-errors" not in launched
            assert "--ignore-certificate-errors-spki-list" not in launched
            assert "--allow-insecure-localhost" not in launched

    pass

    def test_security_enabled_by_default(self, effective_config):
        assert effective_config["security"]["enabled"] is True

    def test_redis_is_not_network_exposed(self, effective_redis_url, effective_config):
        rc = effective_config.get("redis", {})
        host = str(rc.get("host", "localhost")).lower()
        pw = rc.get("password", "") or ""
        loopback = host in ("localhost", "127.0.0.1", "::1")
        assert loopback or pw, (
            "redis is neither loopback-bound nor password-protected"
        )

    def test_redis_url_includes_acl_username_and_encoded_password(self, monkeypatch):
        monkeypatch.setenv("REDIS_PASSWORD", "p@ss/w:rd")
        cfg = {
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 0,
            }
        }
        url = build_redis_url(cfg)
        assert url.startswith("redis://default:")
        assert "p%40ss%2Fw%3Ard" in url
        assert url.endswith("@localhost:6379/0")

    def test_rate_limit_redis_storage_reuses_redis_password(self, monkeypatch):
        monkeypatch.setenv("REDIS_PASSWORD", "abc123")
        cfg = {
            "redis": {"host": "localhost", "port": 6379, "db": 0},
            "rate_limiting": {"storage_uri": "redis://localhost:6379/0"},
        }
        url = build_rate_limit_storage_uri(cfg)
        assert url.startswith("redis://default:")
        assert "abc123" in url
        assert url.endswith("@localhost:6379/0")

    def test_rate_limit_storage_preserves_explicit_auth(self, monkeypatch):
        monkeypatch.setenv("REDIS_PASSWORD", "container-secret")
        storage_uri = "redis://" + "alice" + ":" + "custom" + "@redis:6379/2"
        cfg = {
            "redis": {"host": "localhost", "port": 6379, "db": 0},
            "rate_limiting": {"storage_uri": storage_uri},
        }
        assert build_rate_limit_storage_uri(cfg) == storage_uri

    def test_rate_limit_storage_keeps_memory_backend(self, monkeypatch):
        monkeypatch.setenv("REDIS_PASSWORD", "abc123")
        cfg = {
            "redis": {"host": "localhost", "port": 6379, "db": 0},
            "rate_limiting": {"storage_uri": "memory://"},
        }
        assert build_rate_limit_storage_uri(cfg) == "memory://"

    def test_trusted_hosts_not_wildcard_when_exposed(self, effective_config):
        host = effective_config["app"]["host"]
        trusted = effective_config["security"]["trusted_hosts"]
        exposed = host not in ("127.0.0.1", "localhost", "::1")
        assert not (exposed and trusted == ["*"]), (
            f"app binds {host} but trusted_hosts is {trusted} (host guard disabled)"
        )

    pass

    def test_hooks_disabled_by_default(self, server_module):
        assert server_module.HOOKS_ENABLED is False

    def test_execute_js_disabled_by_default(self, server_module):
        assert server_module.EXECUTE_JS_ENABLED is False
