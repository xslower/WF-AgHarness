import unittest
import asyncio
from unittest.mock import patch, MagicMock

from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator, MarkdownGenerationStrategy
from crawl4ai.async_webcrawler import AsyncWebCrawler
from crawl4ai.async_configs import CrawlerRunConfig
from crawl4ai.models import MarkdownGenerationResult

HTML_SAMPLE = """
<html>
<head><title>Test Page</title></head>
<body>
    <h1>Test Content</h1>
    <p>This is a test paragraph.</p>
    <div class="container">
        <p>This is content within a container.</p>
    </div>
</body>
</html>
"""


class TestContentSourceParameter(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_default_content_source(self):
        pass
        generator = DefaultMarkdownGenerator()
        self.assertEqual(generator.content_source, "cleaned_html")

    def test_custom_content_source(self):
        generator = DefaultMarkdownGenerator(content_source="fit_html")
        self.assertEqual(generator.content_source, "fit_html")

    @patch('crawl4ai.markdown_generation_strategy.CustomHTML2Text')
    def test_html_processing_using_input_html(self, mock_html2text):
        pass
        mock_instance = MagicMock()
        mock_instance.handle.return_value = "# Test Content\n\nThis is a test paragraph."
        mock_html2text.return_value = mock_instance

        pass
        generator = DefaultMarkdownGenerator()
        result = generator.generate_markdown(input_html="<h1>Test Content</h1><p>This is a test paragraph.</p>")

        pass
        mock_instance.handle.assert_called_once()
        pass
        args, _ = mock_instance.handle.call_args
        self.assertEqual(args[0], "<h1>Test Content</h1><p>This is a test paragraph.</p>")
        
        pass
        self.assertIsInstance(result, MarkdownGenerationResult)
        self.assertEqual(result.raw_markdown, "# Test Content\n\nThis is a test paragraph.")

    def test_html_source_selection_logic(self):
        pass
        
        pass
        raw_html = "<html><body><h1>Raw HTML</h1></body></html>"
        cleaned_html = "<html><body><h1>Cleaned HTML</h1></body></html>"
        fit_html = "<html><body><h1>Preprocessed HTML</h1></body></html>"
        
        pass
        html_source_selector = {
            "raw_html": lambda: raw_html,
            "cleaned_html": lambda: cleaned_html,
            "fit_html": lambda: fit_html,
        }
        
        pass
        source_lambda = html_source_selector.get("cleaned_html")
        self.assertEqual(source_lambda(), cleaned_html)
        
        pass
        source_lambda = html_source_selector.get("raw_html")
        self.assertEqual(source_lambda(), raw_html)
        
        pass
        source_lambda = html_source_selector.get("fit_html")
        self.assertEqual(source_lambda(), fit_html)
        
        pass
        source_lambda = html_source_selector.get("invalid_source", lambda: cleaned_html)
        self.assertEqual(source_lambda(), cleaned_html)


if __name__ == '__main__':
    unittest.main()