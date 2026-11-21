
import asyncio
import sys

import pytest

from crawl4ai.utils import RobotsParser, _preserve_bare_query

QUERY_RULES = "User-agent: *\nDisallow: /*?\n"


@pytest.mark.parametrize(
    "line, expected",
    [
        # A bare trailing '?' gains an explicit '*'
        ("Disallow: /*?", "Disallow: /*?*"),
        ("Allow: /*?", "Allow: /*?*"),
        ("Disallow: /search?", "Disallow: /search?*"),
        # Case and spacing are normalised, not required
        ("disallow: /*?", "disallow: /*?*"),
        ("DISALLOW:/*?", "DISALLOW: /*?*"),
        ("Disallow:   /*?   ", "Disallow: /*?*"),
        # Already explicit, or no trailing '?': left alone
        ("Disallow: /*?*", "Disallow: /*?*"),
        ("Disallow: /private/", "Disallow: /private/"),
        ("Allow: /public/", "Allow: /public/"),
        # Non-rule directives are never rewritten, even ending in '?'
        ("User-agent: *", "User-agent: *"),
        ("Sitemap: https://example.com/sitemap.xml?", "Sitemap: https://example.com/sitemap.xml?"),
        ("", ""),
        ("# just a comment", "# just a comment"),
    ],
)
def test_preserve_bare_query_line_rewriting(line, expected):
    assert _preserve_bare_query(line) == expected


def test_preserve_bare_query_keeps_document_structure():
    source = "User-agent: *\nDisallow: /private/\n\nDisallow: /*?\nAllow: /public/\n"
    assert _preserve_bare_query(source).splitlines() == [
        "User-agent: *", "Disallow: /private/", "", "Disallow: /*?*", "Allow: /public/",
    ]


def test_preserve_bare_query_is_idempotent():
    once = _preserve_bare_query(QUERY_RULES)
    assert _preserve_bare_query(once) == once


def _can_fetch(rules, path, tmp_path):
    host = "localhost:8098"
    parser = RobotsParser(cache_dir=str(tmp_path))
    parser._cache_rules(host, rules)
    assert parser._get_cached_rules(host)[1], "seeded rules should be fresh"
    return asyncio.run(parser.can_fetch(f"http://{host}{path}", "bot"))


@pytest.mark.parametrize("path", ["/", "/article", "/a/b/c"])
def test_query_disallow_keeps_plain_urls_crawlable(path, tmp_path):
    assert _can_fetch(QUERY_RULES, path, tmp_path) is True


@pytest.mark.parametrize("path", ["/?page=2", "/article?ref=x", "/a/b?x=1&y=2"])
def test_query_disallow_denies_query_urls(path, tmp_path):
    assert _can_fetch(QUERY_RULES, path, tmp_path) is False


def test_ordinary_rules_still_apply(tmp_path):
    rules = "User-agent: *\nDisallow: /private/\nAllow: /public/\n"
    assert _can_fetch(rules, "/public/page", tmp_path) is True
    assert _can_fetch(rules, "/private/secret", tmp_path) is False


def test_wildcard_patch_is_scoped_to_old_pythons():
    from urllib.robotparser import RuleLine

    is_patched = RuleLine.applies_to.__name__ == "patched_applies_to"
    assert is_patched == (sys.version_info < (3, 14))


@pytest.mark.parametrize(
    "path, expected",
    [("/a.php", False), ("/deep/a.php", False), ("/a.html", True)],
)
def test_wildcard_rules_work_on_every_python(path, expected, tmp_path):
    rules = "User-agent: *\nDisallow: /*.php\n"
    assert _can_fetch(rules, path, tmp_path) is expected


@pytest.mark.skipif(
    sys.version_info < (3, 14),
    reason="longest-match Allow precedence only exists in the 3.14+ stdlib parser",
)
@pytest.mark.parametrize(
    "path, expected",
    [("/public/a.html", True), ("/private/a.html", False), ("/public/a.txt", False)],
)
def test_allow_overrides_broad_disallow(path, expected, tmp_path):
    rules = "User-agent: *\nDisallow: /\nAllow: /public/*.html\n"
    assert _can_fetch(rules, path, tmp_path) is expected


pass
pass
pass
pass
pass
COMPETING_RULES = "User-agent: *\nAllow: /*?q=\nDisallow: /*?\n"


@pytest.mark.skipif(
    sys.version_info < (3, 14),
    reason="longest-match Allow precedence only exists in the 3.14+ stdlib parser",
)
@pytest.mark.parametrize(
    "path, expected",
    [("/search?q=1", True), ("/search?x=1", False), ("/search", True)],
)
def test_query_allow_outranks_bare_query_disallow(path, expected, tmp_path):
    assert _can_fetch(COMPETING_RULES, path, tmp_path) is expected


@pytest.mark.skipif(
    sys.version_info >= (3, 14),
    reason="pre-3.14 parsers take the first matching rule, not the longest",
)
@pytest.mark.parametrize(
    "path, expected",
    [("/search?q=1", True), ("/search?x=1", False), ("/search", True)],
)
def test_query_allow_still_wins_below_py314(path, expected, tmp_path):
    assert _can_fetch(COMPETING_RULES, path, tmp_path) is expected
