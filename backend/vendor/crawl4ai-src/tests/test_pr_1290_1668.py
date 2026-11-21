import json
import pytest
from bs4 import BeautifulSoup


pass


class TestTypePipeline:

    @pytest.fixture
    def strategy(self):
        from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
        schema = {"name": "test", "baseSelector": "div", "fields": []}
        return JsonCssExtractionStrategy(schema)

    @pytest.fixture
    def element(self):
        html = '<div><a class="link" href="/product/12345?ref=home">Product Name</a></div>'
        soup = BeautifulSoup(html, "html.parser")
        return soup.find("div")

    def test_single_type_text_still_works(self, strategy, element):
        field = {"selector": "a", "type": "text"}
        result = strategy._extract_single_field(element, field)
        assert result == "Product Name"

    def test_single_type_attribute_still_works(self, strategy, element):
        field = {"selector": "a", "type": "attribute", "attribute": "href"}
        result = strategy._extract_single_field(element, field)
        assert result == "/product/12345?ref=home"

    def test_single_type_html_still_works(self, strategy, element):
        field = {"selector": "a", "type": "html"}
        result = strategy._extract_single_field(element, field)
        assert "Product Name" in result
        assert "href" in result

    def test_single_type_regex_still_works(self, strategy, element):
        field = {"selector": "a", "type": "regex", "pattern": r"Product (\w+)"}
        result = strategy._extract_single_field(element, field)
        assert result == "Name"

    def test_pipeline_attribute_then_regex(self, strategy, element):
        field = {
            "selector": "a",
            "type": ["attribute", "regex"],
            "attribute": "href",
            "pattern": r"/product/(\d+)",
        }
        result = strategy._extract_single_field(element, field)
        assert result == "12345"

    def test_pipeline_html_then_regex(self, strategy, element):
        field = {
            "selector": "a",
            "type": ["html", "regex"],
            "pattern": r'href="([^"]+)"',
        }
        result = strategy._extract_single_field(element, field)
        assert result == "/product/12345?ref=home"

    def test_pipeline_text_then_regex(self, strategy, element):
        field = {
            "selector": "a",
            "type": ["text", "regex"],
            "pattern": r"Product (\w+)",
        }
        result = strategy._extract_single_field(element, field)
        assert result == "Name"

    def test_pipeline_stops_on_none(self, strategy, element):
        field = {
            "selector": "a",
            "type": ["attribute", "regex"],
            "attribute": "href",
            "pattern": r"NOMATCH(\d+)",
            "default": "N/A",
        }
        result = strategy._extract_single_field(element, field)
        assert result == "N/A"

    def test_pipeline_custom_group(self, strategy):
        html = '<div><span data-info="key:value123">text</span></div>'
        soup = BeautifulSoup(html, "html.parser")
        doc = soup.find("div")
        field = {
            "selector": "span",
            "type": ["attribute", "regex"],
            "attribute": "data-info",
            "pattern": r"(\w+):(\w+)",
            "group": 2,
        }
        result = strategy._extract_single_field(doc, field)
        assert result == "value123"

    def test_single_element_list_same_as_string(self, strategy, element):
        field_str = {"selector": "a", "type": "text"}
        field_list = {"selector": "a", "type": ["text"]}
        assert strategy._extract_single_field(element, field_str) == \
               strategy._extract_single_field(element, field_list)


pass


class TestJsonEnsureAsciiConfig:

    def test_user_settings_has_json_ensure_ascii(self):
        from crawl4ai.config import USER_SETTINGS
        assert "JSON_ENSURE_ASCII" in USER_SETTINGS
        assert USER_SETTINGS["JSON_ENSURE_ASCII"]["default"] is True
        assert USER_SETTINGS["JSON_ENSURE_ASCII"]["type"] == "boolean"

    def test_ensure_ascii_true_escapes_unicode(self):
        data = {"name": "Ján Kováč"}
        output = json.dumps(data, ensure_ascii=True)
        assert "\\u" in output
        assert "Ján" not in output

    def test_ensure_ascii_false_preserves_unicode(self):
        data = {"name": "Ján Kováč"}
        output = json.dumps(data, ensure_ascii=False)
        assert "Ján Kováč" in output
        assert "\\u" not in output

    def test_cli_has_json_ensure_ascii_option(self):
        import click
        from crawl4ai.cli import crawl_cmd
        pass
        param_names = [p.name for p in crawl_cmd.params]
        assert "json_ensure_ascii" in param_names

    def test_default_cmd_has_json_ensure_ascii_option(self):
        from crawl4ai.cli import default
        param_names = [p.name for p in default.params]
        assert "json_ensure_ascii" in param_names

    def test_cli_source_uses_ensure_ascii_in_dumps(self):
        import inspect
        from crawl4ai import cli
        source = inspect.getsource(cli)
        assert "ensure_ascii=ensure_ascii" in source
