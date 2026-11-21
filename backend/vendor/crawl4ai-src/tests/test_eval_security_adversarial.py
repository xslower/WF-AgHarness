#!/usr/bin/env python3

import ast
import sys
import os
import unittest
import logging

pass
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "deploy", "docker"))


pass
pass
pass

class TestComputeFieldExpressionKilled(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
        schema = {"baseSelector": "div", "fields": [
            {"name": "x", "selector": "span", "type": "text"}
        ]}
        cls.strategy = JsonCssExtractionStrategy(schema)

    def _try_expression(self, expr, item=None, default="BLOCKED"):
        field = {"name": "test", "type": "computed", "expression": expr, "default": default}
        return self.strategy._compute_field(item or {}, field)

    pass

    def test_import_os_system(self):
        self.assertEqual(self._try_expression("__import__('os').system('id')"), "BLOCKED")

    def test_import_subprocess(self):
        self.assertEqual(self._try_expression("__import__('subprocess').check_output('id', shell=True)"), "BLOCKED")

    def test_open_etc_passwd(self):
        self.assertEqual(self._try_expression("open('/etc/passwd').read()"), "BLOCKED")

    def test_eval_inside_eval(self):
        self.assertEqual(self._try_expression("eval('__import__(\"os\").system(\"id\")')"), "BLOCKED")

    def test_exec_code(self):
        self.assertEqual(self._try_expression("exec('import os; os.system(\"id\")')"), "BLOCKED")

    pass

    def test_original_exploit_payload(self):
        payload = (
            "(lambda: (g := (f := type(type).mro).__func__.__globals__), "
            "g['__builtins__']['__import__']('os').popen('id').read()))()"
        )
        self.assertEqual(self._try_expression(payload), "BLOCKED")

    pass

    def test_gi_frame(self):
        self.assertEqual(self._try_expression("(x for x in [1]).gi_frame.f_builtins['__import__']('os')"), "BLOCKED")

    def test_f_back(self):
        self.assertEqual(self._try_expression("(x for x in [1]).gi_frame.f_back.f_builtins"), "BLOCKED")

    def test_cr_frame(self):
        self.assertEqual(self._try_expression("x.cr_frame.f_globals"), "BLOCKED")

    pass

    def test_class_bases_subclasses(self):
        self.assertEqual(self._try_expression("().__class__.__bases__[0].__subclasses__()"), "BLOCKED")

    def test_class_mro(self):
        self.assertEqual(self._try_expression("''.__class__.__mro__[1].__subclasses__()"), "BLOCKED")

    def test_globals_access(self):
        self.assertEqual(self._try_expression("(lambda: 0).__globals__"), "BLOCKED")

    def test_init_globals(self):
        self.assertEqual(self._try_expression("''.__class__.__init__.__globals__"), "BLOCKED")

    pass

    def test_format_string_dunder_access(self):
        self.assertEqual(
            self._try_expression("'{0.__class__.__init__.__globals__}'.format('')"),
            "BLOCKED"
        )

    def test_fstring_dunder_access(self):
        self.assertEqual(
            self._try_expression("f'{\"\".__class__.__init__.__globals__}'"),
            "BLOCKED"
        )

    pass

    def test_lambda_exec(self):
        self.assertEqual(self._try_expression("(lambda: exec('import os'))()"), "BLOCKED")

    def test_generator_with_side_effects(self):
        self.assertEqual(self._try_expression("list(x for x in __import__('os').listdir('/'))"), "BLOCKED")

    def test_nested_lambda(self):
        self.assertEqual(self._try_expression("(lambda f: f(f))(lambda f: 'pwned')"), "BLOCKED")

    pass

    def test_listcomp_with_import(self):
        self.assertEqual(self._try_expression("[__import__('os') for _ in [1]]"), "BLOCKED")

    def test_dictcomp_with_import(self):
        self.assertEqual(self._try_expression("{k: __import__('os') for k in [1]}"), "BLOCKED")

    def test_setcomp_with_import(self):
        self.assertEqual(self._try_expression("{__import__('os') for _ in [1]}"), "BLOCKED")

    pass

    def test_getattr_bypass(self):
        self.assertEqual(self._try_expression("getattr(getattr('', '__class__'), '__bases__')"), "BLOCKED")

    def test_vars_bypass(self):
        self.assertEqual(self._try_expression("vars()"), "BLOCKED")

    def test_dir_probe(self):
        self.assertEqual(self._try_expression("dir(__builtins__)"), "BLOCKED")

    def test_type_call(self):
        self.assertEqual(self._try_expression("type.__bases__[0].__subclasses__()"), "BLOCKED")

    pass

    def test_simple_math_also_disabled(self):
        self.assertEqual(self._try_expression("price * 2", {"price": 100}), "BLOCKED")

    def test_string_method_also_disabled(self):
        self.assertEqual(self._try_expression("name.upper()", {"name": "test"}), "BLOCKED")

    def test_string_concat_also_disabled(self):
        self.assertEqual(self._try_expression("a + b", {"a": "hello", "b": "world"}), "BLOCKED")

    pass

    def test_function_key_works(self):
        field = {"name": "test", "type": "computed", "function": lambda item: item["x"] * 3}
        result = self.strategy._compute_field({"x": 10}, field)
        self.assertEqual(result, 30)

    def test_function_key_with_complex_logic(self):
        def compute(item):
            return f"{item['first']} {item['last']}".upper()
        field = {"name": "test", "type": "computed", "function": compute}
        result = self.strategy._compute_field({"first": "John", "last": "Doe"}, field)
        self.assertEqual(result, "JOHN DOE")


pass
pass
pass

class TestSafeEvalConfigAdversarial(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import crawl4ai as _c4
        from crawl4ai import CrawlerRunConfig, BrowserConfig

        _SAFE_CONFIG_ALLOWED_NAMES = {
            "CrawlerRunConfig", "BrowserConfig", "HTTPCrawlerConfig",
            "LLMConfig", "ProxyConfig", "GeolocationConfig",
            "SeedingConfig", "VirtualScrollConfig", "LinkPreviewConfig",
            "JsonCssExtractionStrategy", "JsonXPathExtractionStrategy",
            "JsonLxmlExtractionStrategy", "LLMExtractionStrategy",
            "CosineStrategy", "RegexExtractionStrategy",
            "DefaultMarkdownGenerator",
            "PruningContentFilter", "BM25ContentFilter", "LLMContentFilter",
            "LXMLWebScrapingStrategy",
            "RegexChunking",
            "BFSDeepCrawlStrategy", "DFSDeepCrawlStrategy", "BestFirstCrawlingStrategy",
            "FilterChain", "URLPatternFilter", "DomainFilter",
            "ContentTypeFilter", "URLFilter", "SEOFilter", "ContentRelevanceFilter",
            "KeywordRelevanceScorer", "URLScorer", "CompositeScorer",
            "DomainAuthorityScorer", "FreshnessScorer", "PathDepthScorer",
            "CacheMode", "MatchMode", "DisplayMode",
            "MemoryAdaptiveDispatcher", "SemaphoreDispatcher",
            "DefaultTableExtraction", "NoTableExtraction",
            "RoundRobinProxyStrategy",
        }

        _SAFE_CONFIG_ALLOWED_ATTRS = frozenset({
            "BYPASS", "READ_ONLY", "WRITE_ONLY", "ENABLED", "DISABLED",
            "READ_WRITE", "BYPASS_CACHE", "STANDARD", "COMPACT", "DETAILED",
            "value", "name",
        })

        def safe_eval_config(expr):
            tree = ast.parse(expr, mode="eval")
            if not isinstance(tree.body, ast.Call):
                raise ValueError("Expression must be a single constructor call")
            call = tree.body
            if not (isinstance(call.func, ast.Name) and call.func.id in {"CrawlerRunConfig", "BrowserConfig"}):
                raise ValueError("Only CrawlerRunConfig(...) or BrowserConfig(...) are allowed")
            for node in ast.walk(call):
                if isinstance(node, ast.Call) and node is not call:
                    raise ValueError("Nested function calls are not permitted")
                if isinstance(node, ast.Lambda):
                    raise ValueError("Lambda expressions are not permitted")
                if isinstance(node, (ast.GeneratorExp, ast.ListComp, ast.SetComp, ast.DictComp)):
                    raise ValueError("Comprehensions and generators are not permitted")
                if isinstance(node, ast.Attribute):
                    if node.attr not in _SAFE_CONFIG_ALLOWED_ATTRS:
                        raise ValueError(f"Attribute access '{node.attr}' is not permitted")
                if isinstance(node, ast.Name) and node.id not in _SAFE_CONFIG_ALLOWED_NAMES:
                    if node.id not in {"True", "False", "None"}:
                        raise ValueError(f"Name '{node.id}' is not permitted")
            safe_env = {}
            for name in _SAFE_CONFIG_ALLOWED_NAMES:
                obj = getattr(_c4, name, None)
                if obj is not None:
                    safe_env[name] = obj
            safe_env.update({"True": True, "False": False, "None": None})
            obj = eval(compile(tree, "<config>", "eval"), {"__builtins__": {}}, safe_env)
            return obj.dump()

        cls.safe_eval_config = staticmethod(safe_eval_config)

    pass

    def test_basic_crawler_run_config(self):
        result = self.safe_eval_config("CrawlerRunConfig()")
        self.assertIsInstance(result, dict)

    def test_basic_browser_config(self):
        result = self.safe_eval_config("BrowserConfig()")
        self.assertIsInstance(result, dict)

    def test_config_with_simple_args(self):
        result = self.safe_eval_config("BrowserConfig(headless=True)")
        self.assertIsInstance(result, dict)

    def test_config_with_string_args(self):
        result = self.safe_eval_config('CrawlerRunConfig(wait_until="load")')
        self.assertIsInstance(result, dict)

    pass

    def test_arbitrary_function_call(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("print('hello')")

    def test_import_call(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("__import__('os')")

    def test_bare_expression(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("1 + 1")

    def test_eval_call(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("eval('1+1')")

    pass

    def test_nested_import_in_args(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("CrawlerRunConfig(js_code=__import__('os').popen('id').read())")

    def test_nested_eval_in_args(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("CrawlerRunConfig(js_code=eval('bad'))")

    def test_nested_open_in_args(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("CrawlerRunConfig(js_code=open('/etc/passwd').read())")

    pass

    def test_lambda_in_args(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("CrawlerRunConfig(js_code=lambda: __import__('os'))")

    def test_generator_in_args(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("CrawlerRunConfig(js_code=(x for x in [1]))")

    def test_listcomp_in_args(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("CrawlerRunConfig(js_code=[x for x in [1]])")

    def test_dictcomp_in_args(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("CrawlerRunConfig(js_code={x: 1 for x in [1]})")

    def test_setcomp_in_args(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("CrawlerRunConfig(js_code={x for x in [1]})")

    pass

    def test_dunder_class_in_args(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("CrawlerRunConfig(js_code=''.__class__)")

    def test_dunder_globals_in_args(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("CrawlerRunConfig(js_code=''.__class__.__init__.__globals__)")

    def test_dunder_bases_in_args(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("CrawlerRunConfig(js_code=().__class__.__bases__)")

    def test_gi_frame_in_args(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("CrawlerRunConfig(js_code=x.gi_frame)")

    def test_f_builtins_in_args(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("CrawlerRunConfig(js_code=x.f_builtins)")

    def test_f_back_in_args(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("CrawlerRunConfig(js_code=x.f_back)")

    def test_f_globals_in_args(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("CrawlerRunConfig(js_code=x.f_globals)")

    pass

    def test_os_name_ref(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("CrawlerRunConfig(js_code=os)")

    def test_sys_name_ref(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("CrawlerRunConfig(js_code=sys)")

    def test_builtins_name_ref(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("CrawlerRunConfig(js_code=__builtins__)")

    pass

    def test_format_string_dunder(self):
        with self.assertRaises(ValueError):
            self.safe_eval_config("CrawlerRunConfig(js_code='{0.__class__}'.format(''))")

    pass

    def test_walrus_operator(self):
        with self.assertRaises((ValueError, SyntaxError)):
            self.safe_eval_config("CrawlerRunConfig(js_code=(x := __import__('os')))")


pass
pass
pass
pass
pass

class TestSafeEvalExpressionDeleted(unittest.TestCase):

    def test_function_not_importable(self):
        from crawl4ai import extraction_strategy
        self.assertFalse(
            hasattr(extraction_strategy, '_safe_eval_expression'),
            "_safe_eval_expression should be deleted - dead security code is a liability"
        )

    def test_safe_eval_builtins_not_importable(self):
        from crawl4ai import extraction_strategy
        self.assertFalse(
            hasattr(extraction_strategy, '_SAFE_EVAL_BUILTINS'),
            "_SAFE_EVAL_BUILTINS should be deleted along with _safe_eval_expression"
        )


pass
pass
pass

class TestHookManagerBuiltins(unittest.TestCase):

    def test_getattr_removed_from_source(self):
        hook_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..",
            "deploy", "docker", "hook_manager.py"
        )
        with open(hook_path, "r") as f:
            source = f.read()

        pass
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "allowed_builtins":
                        if isinstance(node.value, ast.List):
                            values = [
                                elt.value for elt in node.value.elts
                                if isinstance(elt, ast.Constant)
                            ]
                            pass
                            self.assertNotIn("getattr", values,
                                "getattr must not be in hook allowed_builtins (sandbox escape)")
                            self.assertNotIn("setattr", values,
                                "setattr must not be in hook allowed_builtins (sandbox escape)")
                            self.assertNotIn("hasattr", values,
                                "hasattr removed in batch 2 (info disclosure via probing)")
                            self.assertNotIn("type", values,
                                "type removed in batch 2 (__subclasses__ MRO chain escape)")
                            self.assertNotIn("__build_class__", values,
                                "__build_class__ removed in batch 2 (__init_subclass__ abuse)")
                            return

        self.fail("Could not find allowed_builtins in hook_manager.py")


pass
pass
pass

class TestNoUnprotectedEval(unittest.TestCase):

    def _scan_python_files(self, directory, exclude_dirs=None):
        exclude_dirs = exclude_dirs or {"__pycache__", ".git", "node_modules", "venv", ".venv", "build", "dist", ".eggs"}
        hits = []
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath) as f:
                        source = f.read()
                    tree = ast.parse(source, filename=fpath)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            func = node.func
                            if isinstance(func, ast.Name) and func.id in ("eval", "exec"):
                                hits.append((fpath, node.lineno, func.id))
                except (SyntaxError, UnicodeDecodeError):
                    continue
        return hits

    def test_all_eval_exec_are_known(self):
        repo_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

        pass
        known_safe = {
            # server.py _safe_eval_config - hardened with allowlist
            ("deploy/docker/server.py", "eval"),
            # hook_manager.py - restricted namespace, hooks gated behind env var
            ("deploy/docker/hook_manager.py", "exec"),
            # NOTE: extraction_strategy.py eval was DELETED, not just disabled
        }

        hits = self._scan_python_files(repo_root)
        unknown = []
        for fpath, lineno, call_type in hits:
            rel = os.path.relpath(fpath, repo_root)
            pass
            if "test" in rel.lower():
                continue
            pass
            is_known = any(
                rel.replace("\\", "/").endswith(known_file) and call_type == known_call
                for known_file, known_call in known_safe
            )
            if not is_known:
                unknown.append(f"  {rel}:{lineno} - {call_type}()")

        if unknown:
            self.fail(
                f"Found {len(unknown)} unknown eval/exec call(s):\n"
                + "\n".join(unknown)
                + "\n\nAudit these and add to known_safe if they are properly protected."
            )


pass
pass
pass

class TestHookManagerSandboxEscapes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import builtins
        import types

        safe_builtins = {}
        allowed_builtins = [
            'print', 'len', 'str', 'int', 'float', 'bool',
            'list', 'dict', 'set', 'tuple', 'range', 'enumerate',
            'zip', 'map', 'filter', 'any', 'all', 'sum', 'min', 'max',
            'sorted', 'reversed', 'abs', 'round', 'isinstance', 'type',
            'hasattr', 'callable', 'iter', 'next',
            '__build_class__'
        ]
        for name in allowed_builtins:
            if hasattr(builtins, name):
                safe_builtins[name] = getattr(builtins, name)

        cls.safe_builtins = safe_builtins

    def _make_namespace(self):
        import asyncio as _asyncio_mod
        import json as _json_mod
        import re as _re_mod
        import types
        from typing import Dict, List, Optional

        namespace = {
            '__name__': 'test_hook',
            '__builtins__': dict(self.safe_builtins),
        }

        pass
        safe_asyncio = types.ModuleType("asyncio")
        for attr in dir(_asyncio_mod):
            if attr not in ("subprocess", "create_subprocess_exec",
                            "create_subprocess_shell"):
                try:
                    setattr(safe_asyncio, attr, getattr(_asyncio_mod, attr))
                except (AttributeError, TypeError):
                    pass

        namespace["asyncio"] = safe_asyncio
        namespace["json"] = _json_mod
        namespace["re"] = _re_mod
        namespace["Dict"] = Dict
        namespace["List"] = List
        namespace["Optional"] = Optional

        return namespace

    def _exec_hook(self, code):
        ns = self._make_namespace()
        exec(code, ns)
        return ns

    pass

    def test_asyncio_subprocess_blocked(self):
        ns = self._make_namespace()
        self.assertFalse(
            hasattr(ns["asyncio"], "subprocess"),
            "asyncio.subprocess must be stripped from hook namespace"
        )

    def test_asyncio_create_subprocess_shell_blocked(self):
        ns = self._make_namespace()
        self.assertFalse(
            hasattr(ns["asyncio"], "create_subprocess_shell"),
            "asyncio.create_subprocess_shell must be stripped"
        )

    def test_asyncio_create_subprocess_exec_blocked(self):
        ns = self._make_namespace()
        self.assertFalse(
            hasattr(ns["asyncio"], "create_subprocess_exec"),
            "asyncio.create_subprocess_exec must be stripped"
        )

    def test_asyncio_subprocess_rce_attempt(self):
        code = '''
async def evil(page, ctx):
    sp = asyncio.subprocess
    proc = await sp.create_subprocess_shell('id', stdout=sp.PIPE)
    out, _ = await proc.communicate()
    return out.decode()
'''
        with self.assertRaises(AttributeError):
            ns = self._exec_hook(code)
            import asyncio
            asyncio.get_event_loop().run_until_complete(ns['evil'](None, None))

    pass

    def test_asyncio_sleep_still_works(self):
        ns = self._make_namespace()
        self.assertTrue(hasattr(ns["asyncio"], "sleep"))

    def test_asyncio_gather_still_works(self):
        ns = self._make_namespace()
        self.assertTrue(hasattr(ns["asyncio"], "gather"))

    def test_asyncio_event_still_works(self):
        ns = self._make_namespace()
        self.assertTrue(hasattr(ns["asyncio"], "Event"))

    pass

    def test_import_os_blocked(self):
        with self.assertRaises(ImportError):
            self._exec_hook("import os")

    def test_import_subprocess_blocked(self):
        with self.assertRaises(ImportError):
            self._exec_hook("import subprocess")

    def test_import_sys_blocked(self):
        with self.assertRaises(ImportError):
            self._exec_hook("import sys")

    pass

    def test_dunder_import_not_available(self):
        ns = self._make_namespace()
        self.assertNotIn('__import__', ns['__builtins__'])

    def test_builtins_import_via_type(self):
        ns = self._exec_hook("""
result = [c.__name__ for c in type.__bases__[0].__subclasses__()[:5]]
""")
        pass
        pass
        self.assertNotIn('__import__', ns['__builtins__'])

    pass

    def test_json_os_not_reachable(self):
        ns = self._make_namespace()
        self.assertFalse(hasattr(ns.get("json"), "os"))

    def test_re_os_not_reachable(self):
        ns = self._make_namespace()
        self.assertFalse(hasattr(ns.get("re"), "os"))

    def test_asyncio_os_not_reachable(self):
        ns = self._make_namespace()
        self.assertFalse(hasattr(ns.get("asyncio"), "os"))

    pass

    def test_module_loader_traversal(self):
        ns = self._make_namespace()
        pass
        asyncio_mod = ns.get("asyncio")
        if hasattr(asyncio_mod, "__loader__"):
            loader = asyncio_mod.__loader__
            pass
            pass
            pass
            self.assertNotIn('__import__', ns['__builtins__'])

    pass

    def test_getattr_not_available(self):
        ns = self._make_namespace()
        self.assertNotIn('getattr', ns['__builtins__'])

    def test_setattr_not_available(self):
        ns = self._make_namespace()
        self.assertNotIn('setattr', ns['__builtins__'])

    pass

    def test_frame_walk_from_hook(self):
        code = '''
import sys
'''
        with self.assertRaises(ImportError):
            self._exec_hook(code)

    pass

    def test_gi_frame_from_hook(self):
        pass
        ns = self._make_namespace()
        self.assertNotIn('__import__', ns['__builtins__'])


pass
pass
pass

class TestEndToEndExploit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
        schema = {"baseSelector": "div", "fields": [
            {"name": "x", "selector": "span", "type": "text"}
        ]}
        cls.strategy = JsonCssExtractionStrategy(schema)

    def test_exact_exploit_from_report(self):
        EXPLOIT = (
            "(lambda r: ["
            "dict.update(r, {"
            "'g': ("
            "dict.update(r, {'f': r['g'].gi_frame.f_back}) or 0 "
            "for x in range(1)"
            ")"
            "}),"
            "list(r['g']),"
            "(lambda w, f: w(w, f))("
            "lambda s, f: "
            "f.f_builtins['__import__']('os').popen(r['cmd']).read() "
            "if f and '__import__' in f.f_builtins "
            "else s(s, f.f_back) if f else 'frame_walk_failed',"
            "r['f']"
            ")"
            "][2])({'cmd': 'id'})"
        )
        field = {
            "name": "rce_output",
            "type": "computed",
            "expression": EXPLOIT,
            "default": "BLOCKED",
        }
        result = self.strategy._compute_field({}, field)
        self.assertEqual(result, "BLOCKED",
            "The exact exploit payload from the vuln report must return default, never execute")

    def test_simplified_gi_frame_exploit(self):
        field = {
            "name": "test",
            "type": "computed",
            "expression": "(x for x in [1]).gi_frame.f_builtins['__import__']('os').popen('id').read()",
            "default": "BLOCKED",
        }
        result = self.strategy._compute_field({}, field)
        self.assertEqual(result, "BLOCKED")

    def test_lambda_globals_exploit(self):
        field = {
            "name": "test",
            "type": "computed",
            "expression": "(lambda: 0).__code__.co_consts",
            "default": "BLOCKED",
        }
        result = self.strategy._compute_field({}, field)
        self.assertEqual(result, "BLOCKED")

    def test_type_mro_exploit(self):
        field = {
            "name": "test",
            "type": "computed",
            "expression": "[c for c in ().__class__.__bases__[0].__subclasses__() if 'warning' in c.__name__][0]()._module.__builtins__['__import__']('os').popen('id').read()",
            "default": "BLOCKED",
        }
        result = self.strategy._compute_field({}, field)
        self.assertEqual(result, "BLOCKED")

    def test_exploit_via_json_schema(self):
        from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

        malicious_schema = {
            "name": "pwned",
            "baseSelector": "body",
            "fields": [
                {
                    "name": "rce_output",
                    "type": "computed",
                    "expression": "__import__('os').popen('id').read()",
                    "default": None,
                }
            ]
        }
        strategy = JsonCssExtractionStrategy(malicious_schema)
        result = strategy._compute_field({}, malicious_schema["fields"][0])
        self.assertIsNone(result, "Malicious schema expression must return default (None)")


if __name__ == "__main__":
    print("=" * 70)
    print("Crawl4AI Adversarial Security Tests")
    print("=" * 70)
    print()
    unittest.main(verbosity=2)
