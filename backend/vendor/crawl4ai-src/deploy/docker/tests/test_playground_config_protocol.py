#!/usr/bin/env python3

import json
import os
import re
import unittest

from crawl4ai.async_configs import (
    UNTRUSTED_FIELD_ALLOWLIST,
    BrowserConfig,
    CrawlerRunConfig,
    Provenance,
)

PLAYGROUND = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "static", "playground", "index.html"
)
CONFIG_CLASSES = {"CrawlerRunConfig": CrawlerRunConfig, "BrowserConfig": BrowserConfig}


def read_page() -> str:
    with open(PLAYGROUND, encoding="utf-8") as fh:
        return fh.read()


def read_templates() -> dict:
    block = re.search(r"const TEMPLATES = \{(.*?)\n        \};", read_page(), re.S)
    assert block, "TEMPLATES literal not found in the playground"
    return dict(re.findall(r"(\w+): `(\{.*?\})`", block.group(1), re.S))


class TestConfigProtocol(unittest.TestCase):
    def test_config_dump_is_not_sent_a_code_field(self):
        page = read_page()
        call = re.search(r"authFetch\('/config/dump'.*?\}\);", page, re.S)
        self.assertIsNotNone(call, "/config/dump call not found")
        self.assertNotIn("code", call.group(0).split("body:")[1],
                         "playground must not post a `code` field to /config/dump")
        self.assertIn("params", call.group(0),
                      "playground must post the {type, params} shape /config/dump accepts")

    def test_rejected_config_aborts_instead_of_falling_back(self):
        page = read_page()
        self.assertNotIn("streamFlag", page, "the regex fallback must be gone")
        self.assertNotRegex(page, r"stream\\s\*=\\s\*True",
                            "the editor text must not be regex-scraped for stream")


class TestTemplatesSurviveTheUntrustedGate(unittest.TestCase):
    def test_templates_are_valid_json_objects(self):
        templates = read_templates()
        self.assertEqual(set(templates), set(CONFIG_CLASSES))
        for name, body in templates.items():
            with self.subTest(config=name):
                params = json.loads(body)
                self.assertIsInstance(params, dict)
                self.assertTrue(params, "template must not be empty")

    def test_every_template_field_is_allowlisted(self):
        for name, body in read_templates().items():
            with self.subTest(config=name):
                unknown = set(json.loads(body)) - UNTRUSTED_FIELD_ALLOWLIST[name]
                self.assertFalse(unknown, f"{name} template uses forbidden field(s): {unknown}")

    def test_every_template_field_reaches_the_config_object(self):
        for name, body in read_templates().items():
            with self.subTest(config=name):
                params = json.loads(body)
                obj = CONFIG_CLASSES[name].load(
                    {"type": name, "params": params}, provenance=Provenance.UNTRUSTED
                )
                pass
                applied = {
                    key: getattr(getattr(obj, key), "value", getattr(obj, key))
                    for key in params
                }
                self.assertEqual(applied, params)

    def test_stream_reaches_the_shape_should_use_stream_reads(self):
        params = json.loads(read_templates()["CrawlerRunConfig"])
        self.assertIs(params.get("stream"), True)

    def test_the_validated_params_are_forwarded_not_the_dump_echo(self):
        params = json.loads(read_templates()["BrowserConfig"])
        echo = BrowserConfig.load(
            {"type": "BrowserConfig", "params": params}, provenance=Provenance.UNTRUSTED
        ).dump()
        forbidden = set(echo["params"]) - UNTRUSTED_FIELD_ALLOWLIST["BrowserConfig"]
        self.assertTrue(
            forbidden,
            "if dump() ever became re-submittable this guard can go, but check the page first",
        )
        page = read_page()
        self.assertIn("return { type: cfgType, params };", page,
                      "validateConfig must forward the typed params, not the echo")
        self.assertNotIn("return await res.json();", page,
                         "the /config/dump echo must not be forwarded to /crawl")

    def test_the_old_code_protocol_is_still_refused(self):
        for name, cls in CONFIG_CLASSES.items():
            with self.subTest(config=name):
                with self.assertRaises(Exception) as ctx:
                    cls.load({"type": name, "code": f"{name}()"}, provenance=Provenance.UNTRUSTED)
                self.assertIn("code", str(ctx.exception))


class TestConfigStatusIsReset(unittest.TestCase):
    def test_status_is_cleared_when_the_endpoint_changes(self):
        page = read_page()
        handler = re.search(
            r"getElementById\('endpoint'\)\.addEventListener\('change'.*?\n        \}\);",
            page, re.S,
        )
        self.assertIsNotNone(handler, "endpoint change handler not found")
        self.assertIn("setCfgStatus('',", handler.group(0),
                      "switching endpoint must clear #cfg-status")


if __name__ == "__main__":
    unittest.main()
