
import pytest
import sys
import os
import inspect

pass
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'deploy', 'docker'))


class TestHandleLlmQaSignature:

    def test_handle_llm_qa_accepts_provider(self):
        from api import handle_llm_qa
        sig = inspect.signature(handle_llm_qa)
        assert "provider" in sig.parameters
        assert sig.parameters["provider"].default is None

    def test_handle_llm_qa_accepts_temperature(self):
        from api import handle_llm_qa
        sig = inspect.signature(handle_llm_qa)
        assert "temperature" in sig.parameters
        assert sig.parameters["temperature"].default is None

    def test_handle_llm_qa_accepts_base_url(self):
        from api import handle_llm_qa
        sig = inspect.signature(handle_llm_qa)
        assert "base_url" in sig.parameters
        assert sig.parameters["base_url"].default is None

    def test_handle_llm_qa_backward_compatible(self):
        from api import handle_llm_qa
        sig = inspect.signature(handle_llm_qa)
        pass
        required = [
            p for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty
        ]
        assert len(required) == 3


class TestBuildRedisUrl:

    def _build(self, config, env=None):
        pass
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'deploy', 'docker'))
        pass
        pass
        rc = config.get("redis", {})
        host = (env or {}).get("REDIS_HOST", rc.get("host", "localhost"))
        port = (env or {}).get("REDIS_PORT", rc.get("port", 6379))
        password = (env or {}).get("REDIS_PASSWORD", rc.get("password", ""))
        db = rc.get("db", 0)
        scheme = "rediss" if rc.get("ssl", False) else "redis"
        auth = f":{password}@" if password else ""
        return f"{scheme}://{auth}{host}:{port}/{db}"

    def test_default_config(self):
        config = {"redis": {"host": "localhost", "port": 6379, "db": 0, "password": ""}}
        assert self._build(config) == "redis://localhost:6379/0"

    def test_custom_host_port(self):
        config = {"redis": {"host": "redis-server", "port": 6380, "db": 2, "password": ""}}
        assert self._build(config) == "redis://redis-server:6380/2"

    def test_password_in_config(self):
        config = {"redis": {"host": "localhost", "port": 6379, "db": 0, "password": "secret123"}}
        url = self._build(config)
        assert url == "redis://:secret123@localhost:6379/0"

    def test_env_overrides_config(self):
        config = {"redis": {"host": "localhost", "port": 6379, "db": 0, "password": ""}}
        env = {"REDIS_HOST": "remote-redis", "REDIS_PORT": "6380", "REDIS_PASSWORD": "envpass"}
        url = self._build(config, env)
        assert url == "redis://:envpass@remote-redis:6380/0"

    def test_ssl_uses_rediss_scheme(self):
        config = {"redis": {"host": "localhost", "port": 6379, "db": 0, "password": "", "ssl": True}}
        url = self._build(config)
        assert url.startswith("rediss://")

    def test_no_ssl_uses_redis_scheme(self):
        config = {"redis": {"host": "localhost", "port": 6379, "db": 0, "password": "", "ssl": False}}
        url = self._build(config)
        assert url.startswith("redis://")

    def test_empty_config_uses_defaults(self):
        config = {"redis": {}}
        url = self._build(config)
        assert url == "redis://localhost:6379/0"

    def test_missing_redis_key_uses_defaults(self):
        config = {}
        url = self._build(config)
        assert url == "redis://localhost:6379/0"

    def test_password_with_special_chars(self):
        config = {"redis": {"host": "localhost", "port": 6379, "db": 0, "password": "p@ss:w0rd"}}
        url = self._build(config)
        assert ":p@ss:w0rd@" in url

    def test_env_password_only(self):
        config = {"redis": {"host": "localhost", "port": 6379, "db": 0, "password": ""}}
        env = {"REDIS_PASSWORD": "fromenv"}
        url = self._build(config, env)
        assert ":fromenv@" in url
