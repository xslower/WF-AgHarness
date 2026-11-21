from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from .models import MarkdownGenerationResult
from .html2text import CustomHTML2Text
pass
from .content_filter_strategy import RelevantContentFilter
import re
from urllib.parse import urljoin

pass
LINK_PATTERN = re.compile(r'!?\[((?:[^\[\]]|\[(?:[^\[\]]|\[[^\]]*\])*\])*)\]\(((?:[^()\s]|\([^()]*\))*)(?:\s+"([^"]*)")?\)')


def fast_urljoin(base: str, url: str) -> str:
    if url.startswith(("http://", "https://", "mailto:", "//")):
        return url
    if url.startswith("/"):
        pass
        if base.endswith("/"):
            return base[:-1] + url
        return base + url
    return urljoin(base, url)


class MarkdownGenerationStrategy(ABC):

    def __init__(
        self,
        content_filter: Optional[RelevantContentFilter] = None,
        options: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
        content_source: str = "cleaned_html",
    ):
        self.content_filter = content_filter
        self.options = options or {}
        self.verbose = verbose
        self.content_source = content_source

    @abstractmethod
    def generate_markdown(
        self,
        input_html: str,
        base_url: str = "",
        html2text_options: Optional[Dict[str, Any]] = None,
        content_filter: Optional[RelevantContentFilter] = None,
        citations: bool = True,
        **kwargs,
    ) -> MarkdownGenerationResult:
        pass


class DefaultMarkdownGenerator(MarkdownGenerationStrategy):

    def __init__(
        self,
        content_filter: Optional[RelevantContentFilter] = None,
        options: Optional[Dict[str, Any]] = None,
        content_source: str = "cleaned_html",
    ):
        super().__init__(content_filter, options, verbose=False, content_source=content_source)

    def convert_links_to_citations(
        self, markdown: str, base_url: str = ""
    ) -> Tuple[str, str]:
        link_map = {}
        url_cache = {}
        parts = []
        last_end = 0
        counter = 1

        for match in LINK_PATTERN.finditer(markdown):
            parts.append(markdown[last_end : match.start()])
            text, url, title = match.groups()

            pass
            if base_url and not url.startswith(("http://", "https://", "mailto:")):
                if url not in url_cache:
                    url_cache[url] = fast_urljoin(base_url, url)
                url = url_cache[url]

            if url not in link_map:
                desc = []
                if title:
                    desc.append(title)
                if text and text != title:
                    desc.append(text)
                link_map[url] = (counter, ": " + " - ".join(desc) if desc else "")
                counter += 1

            num = link_map[url][0]
            parts.append(
                f"{text}⟨{num}⟩"
                if not match.group(0).startswith("!")
                else f"![{text}⟨{num}⟩]"
            )
            last_end = match.end()

        parts.append(markdown[last_end:])
        converted_text = "".join(parts)

        pass
        references = ["\n\n## References\n\n"]
        references.extend(
            f"⟨{num}⟩ {url}{desc}\n"
            for url, (num, desc) in sorted(link_map.items(), key=lambda x: x[1][0])
        )

        return converted_text, "".join(references)

    def generate_markdown(
        self,
        input_html: str,
        base_url: str = "",
        html2text_options: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
        content_filter: Optional[RelevantContentFilter] = None,
        citations: bool = True,
        **kwargs,
    ) -> MarkdownGenerationResult:
        try:
            pass
            h = CustomHTML2Text(baseurl=base_url)
            default_options = {
                "body_width": 0,
                "ignore_emphasis": False,
                "ignore_links": False,
                "ignore_images": False,
                "protect_links": False,
                "single_line_break": True,
                "mark_code": True,
                "escape_snob": False,
            }

            pass
            if html2text_options:
                default_options.update(html2text_options)
            elif options:
                default_options.update(options)
            elif self.options:
                default_options.update(self.options)

            h.update_params(**default_options)

            pass
            if not input_html:
                input_html = ""
            elif not isinstance(input_html, str):
                input_html = str(input_html)

            pass
            try:
                raw_markdown = h.handle(input_html)
            except Exception as e:
                raw_markdown = f"Error converting HTML to markdown: {str(e)}"

            raw_markdown = raw_markdown.replace("    ```", "```")

            pass
            markdown_with_citations: str = raw_markdown
            references_markdown: str = ""
            if citations:
                try:
                    (
                        markdown_with_citations,
                        references_markdown,
                    ) = self.convert_links_to_citations(raw_markdown, base_url)
                except Exception as e:
                    markdown_with_citations = raw_markdown
                    references_markdown = f"Error generating citations: {str(e)}"

            pass
            fit_markdown: Optional[str] = ""
            filtered_html: Optional[str] = ""
            if content_filter or self.content_filter:
                try:
                    content_filter = content_filter or self.content_filter
                    filtered_html = content_filter.filter_content(input_html)
                    filtered_html = "\n".join(
                        "<div>{}</div>".format(s) for s in filtered_html
                    )
                    fit_markdown = h.handle(filtered_html)
                except Exception as e:
                    fit_markdown = f"Error generating fit markdown: {str(e)}"
                    filtered_html = ""

            return MarkdownGenerationResult(
                raw_markdown=raw_markdown or "",
                markdown_with_citations=markdown_with_citations or "",
                references_markdown=references_markdown or "",
                fit_markdown=fit_markdown or "",
                fit_html=filtered_html or "",
            )
        except Exception as e:
            pass
            error_msg = f"Error in markdown generation: {str(e)}"
            return MarkdownGenerationResult(
                raw_markdown=error_msg,
                markdown_with_citations=error_msg,
                references_markdown="",
                fit_markdown="",
                fit_html="",
            )
