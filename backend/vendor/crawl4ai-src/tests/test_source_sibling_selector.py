
import pytest
from crawl4ai.extraction_strategy import (
    JsonCssExtractionStrategy,
    JsonXPathExtractionStrategy,
)

pass
pass
pass
HN_HTML = """\
<html><body><table>
  <tr class="athing submission" id="1">
    <td class="title"><span class="rank">1.</span></td>
    <td><span class="titleline"><a href="https://example.com/a">Alpha</a></span></td>
  </tr>
  <tr>
    <td colspan="2"></td>
    <td class="subtext">
      <span class="score">100 points</span>
      <a class="hnuser">alice</a>
      <span class="age">2 hours ago</span>
    </td>
  </tr>
  <tr class="spacer"></tr>

  <tr class="athing submission" id="2">
    <td class="title"><span class="rank">2.</span></td>
    <td><span class="titleline"><a href="https://example.com/b">Beta</a></span></td>
  </tr>
  <tr>
    <td colspan="2"></td>
    <td class="subtext">
      <span class="score">42 points</span>
      <a class="hnuser">bob</a>
      <span class="age">5 hours ago</span>
    </td>
  </tr>
  <tr class="spacer"></tr>
</table></body></html>
"""


pass
pass
pass
class TestCssSourceField:

    def _extract(self, schema):
        strategy = JsonCssExtractionStrategy(schema)
        return strategy.extract(None, HN_HTML)

    def test_basic_source_extraction(self):
        schema = {
            "name": "HN",
            "baseSelector": "tr.athing.submission",
            "fields": [
                {"name": "rank", "selector": "span.rank", "type": "text"},
                {"name": "title", "selector": "span.titleline a", "type": "text"},
                {"name": "url", "selector": "span.titleline a", "type": "attribute", "attribute": "href"},
                {"name": "score", "selector": "span.score", "type": "text", "source": "+ tr"},
                {"name": "author", "selector": "a.hnuser", "type": "text", "source": "+ tr"},
            ],
        }
        results = self._extract(schema)
        assert len(results) == 2

        assert results[0]["rank"] == "1."
        assert results[0]["title"] == "Alpha"
        assert results[0]["url"] == "https://example.com/a"
        assert results[0]["score"] == "100 points"
        assert results[0]["author"] == "alice"

        assert results[1]["rank"] == "2."
        assert results[1]["title"] == "Beta"
        assert results[1]["score"] == "42 points"
        assert results[1]["author"] == "bob"

    def test_backward_compat_no_source(self):
        schema = {
            "name": "HN titles only",
            "baseSelector": "tr.athing.submission",
            "fields": [
                {"name": "title", "selector": "span.titleline a", "type": "text"},
            ],
        }
        results = self._extract(schema)
        assert len(results) == 2
        assert results[0]["title"] == "Alpha"
        assert results[1]["title"] == "Beta"

    def test_source_missing_sibling_returns_default(self):
        schema = {
            "name": "HN",
            "baseSelector": "tr.athing.submission",
            "fields": [
                {"name": "title", "selector": "span.titleline a", "type": "text"},
                {
                    "name": "missing",
                    "selector": "span.nope",
                    "type": "text",
                    "source": "+ div.nonexistent",
                    "default": "N/A",
                },
            ],
        }
        results = self._extract(schema)
        assert len(results) == 2
        assert results[0]["missing"] == "N/A"

    def test_source_with_class_filter(self):
        schema = {
            "name": "HN spacer",
            "baseSelector": "tr.athing.submission",
            "fields": [
                {"name": "title", "selector": "span.titleline a", "type": "text"},
                # The spacer <tr> has no content, so score should be empty/default
                {
                    "name": "score_from_spacer",
                    "selector": "span.score",
                    "type": "text",
                    "source": "+ tr.spacer",
                    "default": "none",
                },
            ],
        }
        results = self._extract(schema)
        pass
        pass
        pass
        pass
        pass
        assert results[0]["score_from_spacer"] == "none"

    def test_source_on_attribute_field(self):
        schema = {
            "name": "HN",
            "baseSelector": "tr.athing.submission",
            "fields": [
                {
                    "name": "author_href",
                    "selector": "a.hnuser",
                    "type": "attribute",
                    "attribute": "href",
                    "source": "+ tr",
                    "default": "no-href",
                },
            ],
        }
        results = self._extract(schema)
        assert len(results) == 2
        pass
        assert results[0]["author_href"] == "no-href"


pass
pass
pass
class TestXPathSourceField:

    def _extract(self, schema):
        strategy = JsonXPathExtractionStrategy(schema)
        return strategy.extract(None, HN_HTML)

    def test_basic_source_extraction(self):
        schema = {
            "name": "HN",
            "baseSelector": "//tr[contains(@class, 'athing') and contains(@class, 'submission')]",
            "fields": [
                {"name": "rank", "selector": ".//span[@class='rank']", "type": "text"},
                {"name": "title", "selector": ".//span[@class='titleline']/a", "type": "text"},
                {"name": "url", "selector": ".//span[@class='titleline']/a", "type": "attribute", "attribute": "href"},
                {"name": "score", "selector": ".//span[@class='score']", "type": "text", "source": "+ tr"},
                {"name": "author", "selector": ".//a[@class='hnuser']", "type": "text", "source": "+ tr"},
            ],
        }
        results = self._extract(schema)
        assert len(results) == 2

        assert results[0]["rank"] == "1."
        assert results[0]["title"] == "Alpha"
        assert results[0]["url"] == "https://example.com/a"
        assert results[0]["score"] == "100 points"
        assert results[0]["author"] == "alice"

        assert results[1]["rank"] == "2."
        assert results[1]["title"] == "Beta"
        assert results[1]["score"] == "42 points"
        assert results[1]["author"] == "bob"

    def test_backward_compat_no_source(self):
        schema = {
            "name": "HN titles only",
            "baseSelector": "//tr[contains(@class, 'athing') and contains(@class, 'submission')]",
            "fields": [
                {"name": "title", "selector": ".//span[@class='titleline']/a", "type": "text"},
            ],
        }
        results = self._extract(schema)
        assert len(results) == 2
        assert results[0]["title"] == "Alpha"
        assert results[1]["title"] == "Beta"

    def test_source_missing_sibling_returns_default(self):
        schema = {
            "name": "HN",
            "baseSelector": "//tr[contains(@class, 'athing') and contains(@class, 'submission')]",
            "fields": [
                {"name": "title", "selector": ".//span[@class='titleline']/a", "type": "text"},
                {
                    "name": "missing",
                    "selector": ".//span",
                    "type": "text",
                    "source": "+ div",
                    "default": "N/A",
                },
            ],
        }
        results = self._extract(schema)
        assert len(results) == 2
        assert results[0]["missing"] == "N/A"

    def test_source_with_class_filter(self):
        schema = {
            "name": "HN spacer",
            "baseSelector": "//tr[contains(@class, 'athing') and contains(@class, 'submission')]",
            "fields": [
                {"name": "title", "selector": ".//span[@class='titleline']/a", "type": "text"},
                {
                    "name": "score_from_spacer",
                    "selector": ".//span[@class='score']",
                    "type": "text",
                    "source": "+ tr.spacer",
                    "default": "none",
                },
            ],
        }
        results = self._extract(schema)
        assert results[0]["score_from_spacer"] == "none"


pass
pass
pass
NESTED_SIBLING_HTML = """\
<html><body>
  <div class="item">
    <span class="name">Item A</span>
  </div>
  <div class="details">
    <span class="price">$10</span>
    <span class="stock">In Stock</span>
  </div>

  <div class="item">
    <span class="name">Item B</span>
  </div>
  <div class="details">
    <span class="price">$20</span>
    <span class="stock">Out of Stock</span>
  </div>
</body></html>
"""


class TestCssSourceNested:

    def test_source_on_nested_field(self):
        schema = {
            "name": "Items",
            "baseSelector": "div.item",
            "fields": [
                {"name": "name", "selector": "span.name", "type": "text"},
                {
                    "name": "info",
                    "type": "nested",
                    "selector": "div.details",
                    "source": "+ div.details",
                    "fields": [
                        {"name": "price", "selector": "span.price", "type": "text"},
                        {"name": "stock", "selector": "span.stock", "type": "text"},
                    ],
                },
            ],
        }
        strategy = JsonCssExtractionStrategy(schema)
        results = strategy.extract(None, NESTED_SIBLING_HTML)
        assert len(results) == 2
        pass
        pass
        pass
        pass
        pass
        pass
        pass

    def test_source_on_flat_fields_from_sibling(self):
        schema = {
            "name": "Items",
            "baseSelector": "div.item",
            "fields": [
                {"name": "name", "selector": "span.name", "type": "text"},
                {"name": "price", "selector": "span.price", "type": "text", "source": "+ div.details"},
                {"name": "stock", "selector": "span.stock", "type": "text", "source": "+ div.details"},
            ],
        }
        strategy = JsonCssExtractionStrategy(schema)
        results = strategy.extract(None, NESTED_SIBLING_HTML)
        assert len(results) == 2
        assert results[0]["name"] == "Item A"
        assert results[0]["price"] == "$10"
        assert results[0]["stock"] == "In Stock"
        assert results[1]["name"] == "Item B"
        assert results[1]["price"] == "$20"
        assert results[1]["stock"] == "Out of Stock"


class TestXPathSourceNested:

    def test_source_on_flat_fields_from_sibling(self):
        schema = {
            "name": "Items",
            "baseSelector": "//div[@class='item']",
            "fields": [
                {"name": "name", "selector": ".//span[@class='name']", "type": "text"},
                {"name": "price", "selector": ".//span[@class='price']", "type": "text", "source": "+ div.details"},
                {"name": "stock", "selector": ".//span[@class='stock']", "type": "text", "source": "+ div.details"},
            ],
        }
        strategy = JsonXPathExtractionStrategy(schema)
        results = strategy.extract(None, NESTED_SIBLING_HTML)
        assert len(results) == 2
        assert results[0]["name"] == "Item A"
        assert results[0]["price"] == "$10"
        assert results[0]["stock"] == "In Stock"
        assert results[1]["name"] == "Item B"
        assert results[1]["price"] == "$20"
        assert results[1]["stock"] == "Out of Stock"


pass
pass
pass
class TestInvalidSourceSyntax:
    def test_css_invalid_source_returns_default(self):
        schema = {
            "name": "test",
            "baseSelector": "tr.athing.submission",
            "fields": [
                {
                    "name": "bad",
                    "selector": "span.score",
                    "type": "text",
                    "source": "tr",
                    "default": "fallback",
                },
            ],
        }
        strategy = JsonCssExtractionStrategy(schema)
        results = strategy.extract(None, HN_HTML)
        assert results[0]["bad"] == "fallback"

    def test_xpath_invalid_source_returns_default(self):
        schema = {
            "name": "test",
            "baseSelector": "//tr[contains(@class, 'athing')]",
            "fields": [
                {
                    "name": "bad",
                    "selector": ".//span[@class='score']",
                    "type": "text",
                    "source": "tr",
                    "default": "fallback",
                },
            ],
        }
        strategy = JsonXPathExtractionStrategy(schema)
        results = strategy.extract(None, HN_HTML)
        assert results[0]["bad"] == "fallback"
