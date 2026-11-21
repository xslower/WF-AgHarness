#!/usr/bin/env python3

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from crawl4ai.async_configs import (
    CrawlerRunConfig,
    Provenance,
    UntrustedConfigError,
    from_serializable_dict,
)


def _pdf_strategy(params: dict) -> dict:
    return {"type": "PDFContentScrapingStrategy", "params": params}


class TestPdfImageWriteGate(unittest.TestCase):
    def test_untrusted_image_save_dir_is_rejected(self):
        body = _pdf_strategy({"save_images_locally": True, "image_save_dir": "/home/appuser/.ssh"})
        with self.assertRaises(UntrustedConfigError):
            from_serializable_dict(body, provenance=Provenance.UNTRUSTED)

    def test_untrusted_save_images_locally_is_rejected(self):
        body = _pdf_strategy({"save_images_locally": True})
        with self.assertRaises(UntrustedConfigError):
            from_serializable_dict(body, provenance=Provenance.UNTRUSTED)

    def test_untrusted_rejected_when_nested_in_crawlerrunconfig(self):
        body = {
            "type": "CrawlerRunConfig",
            "params": {
                "scraping_strategy": _pdf_strategy(
                    {"save_images_locally": True, "image_save_dir": "/tmp/c4_oob"}
                )
            },
        }
        with self.assertRaises(UntrustedConfigError):
            CrawlerRunConfig.load(body, provenance=Provenance.UNTRUSTED)

    def test_untrusted_extract_images_still_allowed(self):
        body = _pdf_strategy({"extract_images": True})
        obj = from_serializable_dict(body, provenance=Provenance.UNTRUSTED)
        self.assertEqual(type(obj).__name__, "PDFContentScrapingStrategy")

    def test_trusted_path_unchanged(self):
        body = _pdf_strategy({"save_images_locally": True, "image_save_dir": "/tmp/mine"})
        obj = from_serializable_dict(body, provenance=Provenance.TRUSTED)
        self.assertEqual(type(obj).__name__, "PDFContentScrapingStrategy")

    def test_global_backstop_covers_future_types(self):
        body = {"type": "LXMLWebScrapingStrategy", "params": {"downloads_path": "/etc"}}
        with self.assertRaises(UntrustedConfigError):
            from_serializable_dict(body, provenance=Provenance.UNTRUSTED)


if __name__ == "__main__":
    unittest.main(verbosity=2)
