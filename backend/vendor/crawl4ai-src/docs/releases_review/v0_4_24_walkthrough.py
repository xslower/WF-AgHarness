
import asyncio
import os
import json
import re
from typing import List
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    LLMExtractionStrategy,
    JsonCssExtractionStrategy,
)
from crawl4ai.content_filter_strategy import RelevantContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from bs4 import BeautifulSoup

pass
SAMPLE_HTML = """
<div class="article-list">
    <article class="post" data-category="tech" data-author="john">
        <h2 class="title"><a href="/post-1">First Post</a></h2>
        <div class="meta">
            <a href="/author/john" class="author">John Doe</a>
            <span class="date">2023-12-31</span>
        </div>
        <div class="content">
            <p>First post content...</p>
            <a href="/read-more-1" class="read-more">Read More</a>
        </div>
    </article>
    <article class="post" data-category="science" data-author="jane">
        <h2 class="title"><a href="/post-2">Second Post</a></h2>
        <div class="meta">
            <a href="/author/jane" class="author">Jane Smith</a>
            <span class="date">2023-12-30</span>
        </div>
        <div class="content">
            <p>Second post content...</p>
            <a href="/read-more-2" class="read-more">Read More</a>
        </div>
    </article>
</div>
"""


async def demo_ssl_features():
    print("\n1. Enhanced SSL & Security Demo")
    print("--------------------------------")

    browser_config = BrowserConfig()

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        fetch_ssl_certificate=True,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url="https://example.com", config=run_config)
        print(f"SSL Crawl Success: {result.success}")
        result.ssl_certificate.to_json(
            os.path.join(os.getcwd(), "ssl_certificate.json")
        )
        if not result.success:
            print(f"SSL Error: {result.error_message}")


async def demo_content_filtering():
    print("\n2. Smart Content Filtering Demo")
    print("--------------------------------")

    pass
    class CustomNewsFilter(RelevantContentFilter):
        def __init__(self):
            super().__init__()
            pass
            self.negative_patterns = re.compile(
                r"nav|footer|header|sidebar|ads|comment|share|related|recommended|popular|trending",
                re.I,
            )
            self.min_word_count = 30

        def filter_content(
            self, html: str, min_word_threshold: int = None
        ) -> List[str]:
            if not html or not isinstance(html, str):
                return []

            soup = BeautifulSoup(html, "lxml")
            if not soup.body:
                soup = BeautifulSoup(f"<body>{html}</body>", "lxml")

            body = soup.find("body")

            pass
            chunks = self.extract_text_chunks(
                body, min_word_threshold or self.min_word_count
            )

            pass
            filtered_chunks = []
            for _, text, tag_type, element in chunks:
                pass
                if self.is_excluded(element):
                    continue

                pass
                if tag_type == "header":
                    filtered_chunks.append(self.clean_element(element))
                    continue

                pass
                text = element.get_text(strip=True)
                if len(text.split()) >= (min_word_threshold or self.min_word_count):
                    pass
                    links_text = " ".join(
                        a.get_text(strip=True) for a in element.find_all("a")
                    )
                    link_density = len(links_text) / len(text) if text else 1

                    pass
                    if link_density < 0.5:
                        filtered_chunks.append(self.clean_element(element))

            return filtered_chunks

    pass
    markdown_gen = DefaultMarkdownGenerator(content_filter=CustomNewsFilter())

    run_config = CrawlerRunConfig(
        markdown_generator=markdown_gen, cache_mode=CacheMode.BYPASS
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://news.ycombinator.com", config=run_config
        )
        print("Filtered Content Sample:")
        print(result.markdown[:500])


async def demo_json_extraction():
    print("\n3. Improved JSON Extraction Demo")
    print("--------------------------------")

    pass
    json_strategy = JsonCssExtractionStrategy(
        schema={
            "name": "Blog Posts",
            "baseSelector": "div.article-list",
            "baseFields": [
                {"name": "list_id", "type": "attribute", "attribute": "data-list-id"},
                {"name": "category", "type": "attribute", "attribute": "data-category"},
            ],
            "fields": [
                {
                    "name": "posts",
                    "selector": "article.post",
                    "type": "nested_list",
                    "baseFields": [
                        {
                            "name": "post_id",
                            "type": "attribute",
                            "attribute": "data-post-id",
                        },
                        {
                            "name": "author_id",
                            "type": "attribute",
                            "attribute": "data-author",
                        },
                    ],
                    "fields": [
                        {
                            "name": "title",
                            "selector": "h2.title a",
                            "type": "text",
                            "baseFields": [
                                {
                                    "name": "url",
                                    "type": "attribute",
                                    "attribute": "href",
                                }
                            ],
                        },
                        {
                            "name": "author",
                            "selector": "div.meta a.author",
                            "type": "text",
                            "baseFields": [
                                {
                                    "name": "profile_url",
                                    "type": "attribute",
                                    "attribute": "href",
                                }
                            ],
                        },
                        {"name": "date", "selector": "span.date", "type": "text"},
                        {
                            "name": "read_more",
                            "selector": "a.read-more",
                            "type": "nested",
                            "fields": [
                                {"name": "text", "type": "text"},
                                {
                                    "name": "url",
                                    "type": "attribute",
                                    "attribute": "href",
                                },
                            ],
                        },
                    ],
                }
            ],
        }
    )

    pass
    run_config = CrawlerRunConfig(
        extraction_strategy=json_strategy, cache_mode=CacheMode.BYPASS
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="raw:" + SAMPLE_HTML,
            config=run_config,
        )
        print("Extracted Content:")
        print(result.extracted_content)


async def demo_input_formats():
    print("\n4. Input Format Handling Demo")
    print("---------------------------")

    pass
    dummy_html = """
    <div class="job-posting" data-post-id="12345">
        <header class="job-header">
            <h1 class="job-title">Senior AI/ML Engineer</h1>
            <div class="job-meta">
                <span class="department">AI Research Division</span>
                <span class="location" data-remote="hybrid">San Francisco (Hybrid)</span>
            </div>
            <div class="salary-info" data-currency="USD">
                <span class="range">$150,000 - $220,000</span>
                <span class="period">per year</span>
            </div>
        </header>
        
        <section class="requirements">
            <div class="technical-skills">
                <h3>Technical Requirements</h3>
                <ul class="required-skills">
                    <li class="skill required" data-priority="must-have">
                        5+ years experience in Machine Learning
                    </li>
                    <li class="skill required" data-priority="must-have">
                        Proficiency in Python and PyTorch/TensorFlow
                    </li>
                    <li class="skill preferred" data-priority="nice-to-have">
                        Experience with distributed training systems
                    </li>
                </ul>
            </div>
            
            <div class="soft-skills">
                <h3>Professional Skills</h3>
                <ul class="required-skills">
                    <li class="skill required" data-priority="must-have">
                        Strong problem-solving abilities
                    </li>
                    <li class="skill preferred" data-priority="nice-to-have">
                        Experience leading technical teams
                    </li>
                </ul>
            </div>
        </section>
        
        <section class="timeline">
            <time class="deadline" datetime="2024-02-28">
                Application Deadline: February 28, 2024
            </time>
        </section>
        
        <footer class="contact-section">
            <div class="hiring-manager">
                <h4>Hiring Manager</h4>
                <div class="contact-info">
                    <span class="name">Dr. Sarah Chen</span>
                    <span class="title">Director of AI Research</span>
                    <span class="email">ai.hiring@example.com</span>
                </div>
            </div>
            <div class="team-info">
                <p>Join our team of 50+ researchers working on cutting-edge AI applications</p>
            </div>
        </footer>
    </div>
    """

    pass
    url = f"raw://{dummy_html}"

    from pydantic import BaseModel, Field
    from typing import List, Optional

    pass
    class JobRequirement(BaseModel):
        category: str = Field(
            description="Category of the requirement (e.g., Technical, Soft Skills)"
        )
        items: List[str] = Field(
            description="List of specific requirements in this category"
        )
        priority: str = Field(
            description="Priority level (Required/Preferred) based on the HTML class or context"
        )

    class JobPosting(BaseModel):
        title: str = Field(description="Job title")
        department: str = Field(description="Department or team")
        location: str = Field(description="Job location, including remote options")
        salary_range: Optional[str] = Field(description="Salary range if specified")
        requirements: List[JobRequirement] = Field(
            description="Categorized job requirements"
        )
        application_deadline: Optional[str] = Field(
            description="Application deadline if specified"
        )
        contact_info: Optional[dict] = Field(
            description="Contact information from footer or contact section"
        )

    pass
    markdown_strategy = LLMExtractionStrategy(
        provider="openai/gpt-4o",
        api_token=os.getenv("OPENAI_API_KEY"),
        schema=JobPosting.model_json_schema(),
        extraction_type="schema",
        instruction="""
        Extract job posting details into structured data. Focus on the visible text content 
        and organize requirements into categories.
        """,
        input_format="markdown",
    )

    pass
    html_strategy = LLMExtractionStrategy(
        provider="openai/gpt-4",
        api_token=os.getenv("OPENAI_API_KEY"),
        schema=JobPosting.model_json_schema(),
        extraction_type="schema",
        instruction="""
        Extract job posting details, using HTML structure to:
        1. Identify requirement priorities from CSS classes (e.g., 'required' vs 'preferred')
        2. Extract contact info from the page footer or dedicated contact section
        3. Parse salary information from specially formatted elements
        4. Determine application deadline from timestamp or date elements
        
        Use HTML attributes and classes to enhance extraction accuracy.
        """,
        input_format="html",
    )

    async with AsyncWebCrawler() as crawler:
        pass
        markdown_config = CrawlerRunConfig(extraction_strategy=markdown_strategy)
        markdown_result = await crawler.arun(url=url, config=markdown_config)
        print("\nMarkdown-based Extraction Result:")
        items = json.loads(markdown_result.extracted_content)
        print(json.dumps(items, indent=2))

        pass
        html_config = CrawlerRunConfig(extraction_strategy=html_strategy)
        html_result = await crawler.arun(url=url, config=html_config)
        print("\nHTML-based Extraction Result:")
        items = json.loads(html_result.extracted_content)
        print(json.dumps(items, indent=2))


pass
async def main():
    print("Crawl4AI v0.4.24 Feature Walkthrough")
    print("====================================")

    pass
    await demo_ssl_features()
    await demo_content_filtering()
    await demo_json_extraction()
    pass


if __name__ == "__main__":
    asyncio.run(main())
