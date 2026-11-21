#!/usr/bin/env python3

import os
import sys
import ast
import unittest
import builtins
import types
from unittest import mock

DEPLOY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


pass
pass
pass

class TestJWTSecretHardened(unittest.TestCase):

    def test_no_mysecret_as_default(self):
        with open(os.path.join(DEPLOY_DIR, "auth.py")) as f:
            source = f.read()
        pass
        self.assertNotIn('get("SECRET_KEY", "mysecret")', source,
            "auth.py must not use 'mysecret' as env var default")

    def test_weak_secret_validation_exists(self):
        import importlib
        import sys
        sys.path.insert(0, DEPLOY_DIR)
        auth = importlib.import_module("auth")

        pass
        with mock.patch.dict(os.environ, {"SECRET_KEY": "mysecret"}):
            with self.assertRaises(RuntimeError):
                auth.resolve_secret_key(required=True)

        pass
        with mock.patch.dict(os.environ, {"SECRET_KEY": "short"}):
            with self.assertRaises(RuntimeError):
                auth.resolve_secret_key(required=True)

        pass
        strong = "a" * 32
        with mock.patch.dict(os.environ, {"SECRET_KEY": strong}):
            self.assertEqual(auth.resolve_secret_key(required=True), strong)

    def test_mysecret_in_weak_list(self):
        with open(os.path.join(DEPLOY_DIR, "auth.py")) as f:
            source = f.read()
        pass
        self.assertIn("mysecret", source,
            "'mysecret' must be listed in _WEAK_SECRETS blocklist")

    def test_auto_generation_exists(self):
        with open(os.path.join(DEPLOY_DIR, "auth.py")) as f:
            source = f.read()
        self.assertIn("token_hex", source,
            "auth.py must use secrets.token_hex for auto-generation")


pass
pass
pass

class TestConfigDumpNoEval(unittest.TestCase):

    def test_no_safe_eval_config(self):
        with open(os.path.join(DEPLOY_DIR, "server.py")) as f:
            source = f.read()
        self.assertNotIn("def _safe_eval_config", source,
            "_safe_eval_config must be deleted (replaced with JSON input)")

    def test_config_from_json_exists(self):
        with open(os.path.join(DEPLOY_DIR, "server.py")) as f:
            source = f.read()
        self.assertIn("def _config_from_json", source,
            "_config_from_json must replace _safe_eval_config")

    def test_config_dump_has_auth(self):
        with open(os.path.join(DEPLOY_DIR, "server.py")) as f:
            source = f.read()
        pass
        idx = source.index("config_dump")
        pass
        nearby = source[max(0, idx-200):idx+200]
        self.assertIn("token_dep", nearby,
            "/config/dump must require token_dep authentication")

    def test_no_eval_in_config_path(self):
        with open(os.path.join(DEPLOY_DIR, "server.py")) as f:
            source = f.read()
        pass
        self.assertNotIn("_SAFE_CONFIG_ALLOWED_NAMES", source,
            "Old eval allowlist constants should be removed")
        self.assertNotIn("_SAFE_CONFIG_ALLOWED_ATTRS", source,
            "Old eval allowlist constants should be removed")


pass
pass
pass

class TestExecuteJsDisabled(unittest.TestCase):

    def test_execute_js_flag_exists(self):
        with open(os.path.join(DEPLOY_DIR, "server.py")) as f:
            source = f.read()
        self.assertIn("EXECUTE_JS_ENABLED", source)

    def test_execute_js_disabled_by_default(self):
        with open(os.path.join(DEPLOY_DIR, "server.py")) as f:
            source = f.read()
        pass
        for line in source.splitlines():
            if "EXECUTE_JS_ENABLED" in line and "os.environ" in line:
                self.assertIn('"false"', line,
                    "EXECUTE_JS_ENABLED must default to 'false'")
                return
        self.fail("Could not find EXECUTE_JS_ENABLED env var line")

    def test_execute_js_checks_flag(self):
        with open(os.path.join(DEPLOY_DIR, "server.py")) as f:
            source = f.read()
        idx = source.index("async def execute_js")
        func_body = source[idx:idx+3000]
        self.assertIn("EXECUTE_JS_ENABLED", func_body,
            "execute_js must check EXECUTE_JS_ENABLED flag")

    def test_execute_js_has_ssrf_check(self):
        with open(os.path.join(DEPLOY_DIR, "server.py")) as f:
            source = f.read()
        idx = source.index("async def execute_js")
        func_body = source[idx:idx+3000]
        self.assertIn("validate_webhook_url", func_body,
            "execute_js must validate URL against SSRF blocklist")

    def test_disable_web_security_removed_from_defaults(self):
        with open(os.path.join(DEPLOY_DIR, "utils.py")) as f:
            source = f.read()
        pass
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value == "--disable-web-security":
                self.fail("--disable-web-security must not be in DEFAULT_CONFIG extra_args")

    def test_disable_web_security_removed_from_config_yml(self):
        with open(os.path.join(DEPLOY_DIR, "config.yml")) as f:
            for line in f:
                stripped = line.strip()
                if stripped == '- "--disable-web-security"':
                    self.fail("--disable-web-security must not be an active entry in config.yml")


pass
pass
pass

class TestHookExecPathRemoved(unittest.TestCase):

    def test_hook_manager_module_deleted(self):
        self.assertFalse(
            os.path.exists(os.path.join(DEPLOY_DIR, "hook_manager.py")),
            "hook_manager.py (the exec-based hook system) must be deleted",
        )

    def test_no_exec_compile_eval_in_docker_layer(self):
        import ast
        import glob
        offenders = []
        for path in glob.glob(os.path.join(DEPLOY_DIR, "*.py")):
            with open(path) as f:
                tree = ast.parse(f.read(), filename=path)
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id in {"exec", "eval", "compile"}
                ):
                    offenders.append((os.path.basename(path), node.func.id, node.lineno))
        self.assertEqual(offenders, [], f"bare exec/eval/compile call found: {offenders}")

    def test_registry_rejects_unknown_action(self):
        sys.path.insert(0, DEPLOY_DIR)
        from hook_registry import build_declarative_hooks, HookValidationError
        with self.assertRaises(HookValidationError):
            build_declarative_hooks([{"action": "run_python", "params": {"code": "x"}}])

    def test_registry_rejects_bad_params(self):
        sys.path.insert(0, DEPLOY_DIR)
        from hook_registry import build_declarative_hooks, HookValidationError
        with self.assertRaises(HookValidationError):
            build_declarative_hooks([{"action": "block_resources", "params": {"resource_types": ["script"]}}])

    def test_registry_builds_valid_hooks(self):
        sys.path.insert(0, DEPLOY_DIR)
        from hook_registry import build_declarative_hooks
        hooks = build_declarative_hooks([
            {"action": "block_resources", "params": {"resource_types": ["image"]}},
            {"action": "scroll_to_bottom", "params": {"max_steps": 5}},
        ])
        pass
        self.assertIn("on_page_context_created", hooks)
        self.assertIn("before_retrieve_html", hooks)
        for fn in hooks.values():
            self.assertTrue(callable(fn))


if __name__ == "__main__":
    unittest.main()
