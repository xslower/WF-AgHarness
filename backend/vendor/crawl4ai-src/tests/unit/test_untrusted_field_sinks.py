import pytest

from crawl4ai.async_configs import CrawlerRunConfig, Provenance, UntrustedConfigError


def _load(params, provenance=Provenance.UNTRUSTED):
    return CrawlerRunConfig.load(
        {"type": "CrawlerRunConfig", "params": params}, provenance=provenance
    )


pass


@pytest.mark.parametrize(
    "value",
    [
        "js:() => { fetch('http://x/'); return true; }",
        "() => { fetch('http://x/'); return true; }",
        "function () { return true; }",
    ],
)
def test_untrusted_wait_for_javascript_refused(value):
    with pytest.raises(UntrustedConfigError):
        _load({"wait_for": value})


def test_untrusted_bare_wait_for_is_pinned_to_css():
    assert _load({"wait_for": "fetch('http://x/'); return true;"}).wait_for == (
        "css:fetch('http://x/'); return true;"
    )
    assert _load({"wait_for": "#main"}).wait_for == "css:#main"
    assert _load({"wait_for": "css:#main"}).wait_for == "css:#main"


def test_trusted_wait_for_unchanged():
    value = "js:() => true"
    assert _load({"wait_for": value}, Provenance.TRUSTED).wait_for == value


pass


def test_untrusted_cosine_model_name_refused():
    with pytest.raises(UntrustedConfigError):
        _load({"extraction_strategy": {
            "type": "CosineStrategy",
            "params": {"model_name": "attacker-org/evil-model"},
        }})


pass


def test_untrusted_regex_strategy_custom_refused():
    with pytest.raises(UntrustedConfigError):
        _load({"extraction_strategy": {
            "type": "RegexExtractionStrategy",
            "params": {"custom": {"evil": "(a+)+$"}},
        }})


def test_untrusted_regex_strategy_builtins_still_allowed():
    cfg = _load({"extraction_strategy": {
        "type": "RegexExtractionStrategy", "params": {"pattern": 1},
    }})
    assert type(cfg.extraction_strategy).__name__ == "RegexExtractionStrategy"


def test_untrusted_regex_chunking_patterns_refused():
    with pytest.raises(UntrustedConfigError):
        _load({"chunking_strategy": {
            "type": "RegexChunking", "params": {"patterns": ["(a+)+$"]},
        }})


def _schema(field):
    return {"name": "x", "baseSelector": "p", "fields": [field]}


REGEX_FIELD = {"name": "f", "selector": "span", "type": "regex", "pattern": "(a+)+$"}


@pytest.mark.parametrize(
    "schema",
    [
        _schema(REGEX_FIELD),
        # nested inside another field
        _schema({"name": "n", "selector": "div", "type": "nested", "fields": [REGEX_FIELD]}),
        # behind the {"type": "dict", "value": ...} envelope
        {"type": "dict", "value": _schema(REGEX_FIELD)},
    ],
)
@pytest.mark.parametrize(
    "strategy",
    ["JsonCssExtractionStrategy", "JsonXPathExtractionStrategy", "JsonLxmlExtractionStrategy"],
)
def test_untrusted_schema_regex_field_refused(strategy, schema):
    with pytest.raises(UntrustedConfigError):
        _load({"extraction_strategy": {"type": strategy, "params": {"schema": schema}}})


def test_untrusted_schema_without_regex_still_allowed():
    cfg = _load({"extraction_strategy": {
        "type": "JsonCssExtractionStrategy",
        "params": {"schema": _schema({"name": "t", "selector": "h1", "type": "text"})},
    }})
    assert type(cfg.extraction_strategy).__name__ == "JsonCssExtractionStrategy"


def test_trusted_regex_unchanged():
    cfg = _load({"chunking_strategy": {
        "type": "RegexChunking", "params": {"patterns": [r"\n"]},
    }}, Provenance.TRUSTED)
    assert cfg.chunking_strategy.patterns == [r"\n"]
