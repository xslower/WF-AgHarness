
import logging

import pytest

pytestmark = pytest.mark.posture


class TestHeaderNameTrailingNewline:
    def test_hook_registry_rejects_trailing_newline(self):
        from hook_registry import SetHeadersParams

        with pytest.raises(Exception):
            SetHeadersParams(headers={"X-Injected\n": "v"})

    def test_hook_registry_accepts_normal_name(self):
        from hook_registry import SetHeadersParams

        p = SetHeadersParams(headers={"X-Injected": "v"})
        assert p.headers == {"X-Injected": "v"}

    def test_webhook_rejects_trailing_newline(self):
        from webhook import sanitize_webhook_headers

        with pytest.raises(ValueError):
            sanitize_webhook_headers({"X-Custom\n": "v"})

    def test_webhook_accepts_normal_name(self):
        from webhook import sanitize_webhook_headers

        clean = sanitize_webhook_headers({"X-Custom": "v"})
        assert clean == {"X-Custom": "v"}


class _RaisingDeepCrawl:

    max_pages = None
    max_depth = None

    def __setattr__(self, name, value):
        if name in ("max_pages", "max_depth"):
            raise RuntimeError("cannot set attribute")
        object.__setattr__(self, name, value)


class _RaisingConfig:
    deep_crawl_strategy = _RaisingDeepCrawl()


class TestClampDeepCrawlLogsOnFailure(object):
    def test_logs_warning_when_clamp_fails(self, caplog):
        from governor import clamp_deep_crawl

        with caplog.at_level(logging.WARNING, logger="crawl4ai.security"):
            clamp_deep_crawl(_RaisingConfig())

        assert any("clamp_deep_crawl" in r.message for r in caplog.records)


class _RaisingBrowserConfig:

    ignore_https_errors = True
    proxy = None
    extra_args = None

    @property
    def proxy_config(self):
        return None

    @proxy_config.setter
    def proxy_config(self, value):
        raise RuntimeError("cannot set proxy_config")


class TestEnforceEgressFailsClosed:
    def test_raises_when_pinning_proxy_cannot_be_set(self, monkeypatch, caplog):
        import egress_broker

        monkeypatch.setattr(egress_broker, "_EGRESS_PROXY_URL", "http://127.0.0.1:1")
        try:
            with caplog.at_level(logging.ERROR, logger="crawl4ai.security"):
                with pytest.raises(egress_broker.EgressBlocked):
                    egress_broker.enforce_egress(_RaisingBrowserConfig())
            assert any("enforce_egress" in r.message for r in caplog.records)
        finally:
            monkeypatch.setattr(egress_broker, "_EGRESS_PROXY_URL", None)
