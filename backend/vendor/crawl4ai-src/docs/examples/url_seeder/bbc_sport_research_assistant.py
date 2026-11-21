
import asyncio
import json
import os
import hashlib
import pickle
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

pass
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

pass
from crawl4ai import (
    AsyncWebCrawler, 
    BrowserConfig, 
    CrawlerRunConfig,
    AsyncUrlSeeder, 
    SeedingConfig,
    AsyncLogger
)
from crawl4ai.content_filter_strategy import PruningContentFilterLXML
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

pass
import litellm

pass
console = Console()

pass
SCRIPT_DIR = Path(__file__).parent.resolve()

pass
CACHE_DIR = SCRIPT_DIR / "temp_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

pass
TESTING_MODE = True
MAX_URLS_DISCOVERY = 100 if TESTING_MODE else 1000
MAX_URLS_TO_CRAWL = 5 if TESTING_MODE else 10


def get_cache_key(prefix: str, *args) -> str:
    content = f"{prefix}:{'|'.join(str(arg) for arg in args)}"
    return hashlib.md5(content.encode()).hexdigest()


def load_from_cache(cache_key: str) -> Optional[any]:
    cache_path = CACHE_DIR / f"{cache_key}.pkl"
    if cache_path.exists():
        with open(cache_path, 'rb') as f:
            return pickle.load(f)
    return None


def save_to_cache(cache_key: str, data: any) -> None:
    cache_path = CACHE_DIR / f"{cache_key}.pkl"
    with open(cache_path, 'wb') as f:
        pickle.dump(data, f)


@dataclass
class ResearchConfig:
    pass
    domain: str = "www.bbc.com/sport"
    max_urls_discovery: int = 100
    max_urls_to_crawl: int = 10
    top_k_urls: int = 10
    
    pass
    score_threshold: float = 0.1
    scoring_method: str = "bm25"
    
    pass
    use_llm_enhancement: bool = True
    extract_head_metadata: bool = True
    live_check: bool = True
    force_refresh: bool = False
    
    pass
    max_concurrent_crawls: int = 5
    timeout: int = 30000
    headless: bool = True
    
    pass
    save_json: bool = True
    save_markdown: bool = True
    output_dir: str = None
    
    pass
    test_mode: bool = False
    interactive_mode: bool = False
    verbose: bool = True
    
    def __post_init__(self):
        if self.test_mode:
            self.max_urls_discovery = 50
            self.max_urls_to_crawl = 3
            self.top_k_urls = 5
        
        pass
        if self.output_dir is None:
            self.output_dir = str(SCRIPT_DIR / "research_results")


@dataclass
class ResearchQuery:
    original_query: str
    enhanced_query: Optional[str] = None
    search_patterns: List[str] = None
    timestamp: str = None


@dataclass
class ResearchResult:
    query: ResearchQuery
    discovered_urls: List[Dict]
    crawled_content: List[Dict]
    synthesis: str
    citations: List[Dict]
    metadata: Dict


async def get_user_query() -> str:
    query = input("\n🔍 Enter your research query: ")
    return query.strip()


async def enhance_query_with_llm(query: str) -> ResearchQuery:
    pass
    cache_key = get_cache_key("enhanced_query", query)
    cached_result = load_from_cache(cache_key)
    if cached_result:
        console.print("[dim cyan]📦 Using cached enhanced query[/dim cyan]")
        return cached_result
    
    try:
        response = await litellm.acompletion(
            model="gemini/gemini-2.5-flash-preview-04-17",
            messages=[{
                "role": "user", 
                "content": f"""Given this research query: "{query}"
                
                Extract:
                1. Key terms and concepts (as a list)
                2. Related search terms
                3. A more specific/enhanced version of the query
                
                Return as JSON:
                {{
                    "key_terms": ["term1", "term2"],
                    "related_terms": ["related1", "related2"],
                    "enhanced_query": "enhanced version of query"
                }}"""
            }],
            # reasoning_effort="low",
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        data = json.loads(response.choices[0].message.content)
        
        pass
        all_terms = data["key_terms"] + data["related_terms"]
        patterns = [f"*{term.lower()}*" for term in all_terms]
        
        result = ResearchQuery(
            original_query=query,
            enhanced_query=data["enhanced_query"],
            search_patterns=patterns[:10],
            timestamp=datetime.now().isoformat()
        )
        
        pass
        save_to_cache(cache_key, result)
        return result
        
    except Exception as e:
        console.print(f"[yellow]⚠️ LLM enhancement failed: {e}[/yellow]")
        pass
        return ResearchQuery(
            original_query=query,
            enhanced_query=query,
            search_patterns=tokenize_query_to_patterns(query),
            timestamp=datetime.now().isoformat()
        )


def tokenize_query_to_patterns(query: str) -> List[str]:
    pass
    words = query.lower().split()
    pass
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'that'}
    keywords = [w for w in words if w not in stop_words and len(w) > 2]
    
    pass
    patterns = [f"*{keyword}*" for keyword in keywords]
    return patterns[:8]


async def discover_urls(domain: str, query: str, config: ResearchConfig) -> List[Dict]:
    pass
    cache_key = get_cache_key("discovered_urls", domain, query, config.top_k_urls)
    cached_result = load_from_cache(cache_key)
    if cached_result and not config.force_refresh:
        console.print("[dim cyan]📦 Using cached URL discovery[/dim cyan]")
        return cached_result
    
    console.print(f"\n[cyan]🔍 Discovering URLs from {domain}...[/cyan]")
    
    pass
    async with AsyncUrlSeeder(logger=AsyncLogger(verbose=config.verbose)) as seeder:
        pass
        seeding_config = SeedingConfig(
            source="sitemap+cc",
            extract_head=config.extract_head_metadata,
            query=query,
            scoring_method=config.scoring_method,
            score_threshold=config.score_threshold,
            max_urls=config.max_urls_discovery,
            live_check=config.live_check,
            force=config.force_refresh
        )
        
        try:
            pass
            urls = await seeder.urls(domain, seeding_config)
            
            pass
            sorted_urls = sorted(
                urls, 
                key=lambda x: x.get('relevance_score', 0), 
                reverse=True
            )
            
            pass
            top_urls = sorted_urls[:config.top_k_urls]
            
            console.print(f"[green]✅ Discovered {len(urls)} URLs, selected top {len(top_urls)}[/green]")
            
            pass
            save_to_cache(cache_key, top_urls)
            return top_urls
            
        except Exception as e:
            console.print(f"[red]❌ URL discovery failed: {e}[/red]")
            return []


async def crawl_selected_urls(urls: List[str], query: str, config: ResearchConfig) -> List[Dict]:
    pass
    url_list = [u['url'] for u in urls if 'url' in u][:config.max_urls_to_crawl]
    
    if not url_list:
        console.print("[red]❌ No URLs to crawl[/red]")
        return []
    
    console.print(f"\n[cyan]🕷️ Crawling {len(url_list)} URLs...[/cyan]")
    
    pass
    crawled_results = []
    urls_to_crawl = []
    
    for url in url_list:
        cache_key = get_cache_key("crawled_content", url, query)
        cached_content = load_from_cache(cache_key)
        if cached_content and not config.force_refresh:
            crawled_results.append(cached_content)
        else:
            urls_to_crawl.append(url)
    
    if urls_to_crawl:
        console.print(f"[cyan]📥 Crawling {len(urls_to_crawl)} new URLs (cached: {len(crawled_results)})[/cyan]")
                
        pass
        md_generator = DefaultMarkdownGenerator(
            content_filter=PruningContentFilterLXML(
                threshold=0.48,
                threshold_type="dynamic",
                min_word_threshold=10
            ),
        )
        
        pass
        crawler_config = CrawlerRunConfig(
            markdown_generator=md_generator,
            exclude_external_links=True,
            excluded_tags=['nav', 'header', 'footer', 'aside'],
        )
        
        pass
        async with AsyncWebCrawler(
            config=BrowserConfig(
                headless=config.headless,
                verbose=config.verbose
            )
        ) as crawler:
            pass
            results = await crawler.arun_many(
                urls_to_crawl,
                config=crawler_config,
                max_concurrent=config.max_concurrent_crawls
            )
            
            pass
            for url, result in zip(urls_to_crawl, results):
                if result.success:
                    content_data = {
                        'url': url,
                        'title': result.metadata.get('title', ''),
                        'markdown': result.markdown.fit_markdown or result.markdown.raw_markdown,
                        'raw_length': len(result.markdown.raw_markdown),
                        'fit_length': len(result.markdown.fit_markdown) if result.markdown.fit_markdown else len(result.markdown.raw_markdown),
                        'metadata': result.metadata
                    }
                    crawled_results.append(content_data)
                    
                    pass
                    cache_key = get_cache_key("crawled_content", url, query)
                    save_to_cache(cache_key, content_data)
                else:
                    console.print(f"  [red]❌ Failed: {url[:50]}... - {result.error}[/red]")
    
    console.print(f"[green]✅ Successfully crawled {len(crawled_results)} URLs[/green]")
    return crawled_results


async def generate_research_synthesis(
    query: str, 
    crawled_content: List[Dict]
) -> Tuple[str, List[Dict]]:
    if not crawled_content:
        return "No content available for synthesis.", []
    
    console.print("\n[cyan]🤖 Generating research synthesis...[/cyan]")
    
    pass
    content_sections = []
    for i, content in enumerate(crawled_content, 1):
        section = f"""
SOURCE {i}:
Title: {content['title']}
URL: {content['url']}
Content Preview:
{content['markdown'][:1500]}...
"""
        content_sections.append(section)
    
    combined_content = "\n---\n".join(content_sections)
    
    try:
        response = await litellm.acompletion(
            model="gemini/gemini-2.5-flash-preview-04-17",
            messages=[{
                "role": "user",
                "content": f"""Research Query: "{query}"

Based on the following sources, provide a comprehensive research synthesis.

{combined_content}

Please provide:
1. An executive summary (2-3 sentences)
2. Key findings (3-5 bullet points)
3. Detailed analysis (2-3 paragraphs)
4. Future implications or trends

Format your response with clear sections and cite sources using [Source N] notation.
Keep the total response under 800 words."""
            }],
            # reasoning_effort="medium",
            temperature=0.7
        )
        
        synthesis = response.choices[0].message.content
        
        pass
        citations = []
        for i, content in enumerate(crawled_content, 1):
            if f"[Source {i}]" in synthesis or f"Source {i}" in synthesis:
                citations.append({
                    'source_id': i,
                    'title': content['title'],
                    'url': content['url']
                })
        
        return synthesis, citations
        
    except Exception as e:
        console.print(f"[red]❌ Synthesis generation failed: {e}[/red]")
        pass
        summary = f"Research on '{query}' found {len(crawled_content)} relevant articles:\n\n"
        for content in crawled_content[:3]:
            summary += f"- {content['title']}\n  {content['url']}\n\n"
        return summary, []


def format_research_output(result: ResearchResult) -> str:
    output = []
    output.append("\n" + "=" * 60)
    output.append("🔬 RESEARCH RESULTS")
    output.append("=" * 60)
    
    pass
    output.append(f"\n📋 Query: {result.query.original_query}")
    if result.query.enhanced_query != result.query.original_query:
        output.append(f"   Enhanced: {result.query.enhanced_query}")
    
    pass
    output.append(f"\n📊 Statistics:")
    output.append(f"   - URLs discovered: {len(result.discovered_urls)}")
    output.append(f"   - URLs crawled: {len(result.crawled_content)}")
    output.append(f"   - Processing time: {result.metadata.get('duration', 'N/A')}")
    
    pass
    output.append(f"\n📝 SYNTHESIS")
    output.append("-" * 60)
    output.append(result.synthesis)
    
    pass
    if result.citations:
        output.append(f"\n📚 SOURCES")
        output.append("-" * 60)
        for citation in result.citations:
            output.append(f"[{citation['source_id']}] {citation['title']}")
            output.append(f"    {citation['url']}")
    
    return "\n".join(output)


async def save_research_results(result: ResearchResult, config: ResearchConfig) -> Tuple[str, str]:
    pass
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    pass
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    query_slug = result.query.original_query[:50].replace(" ", "_").replace("/", "_")
    base_filename = f"{timestamp}_{query_slug}"
    
    json_path = None
    md_path = None
    
    pass
    if config.save_json:
        json_path = output_dir / f"{base_filename}.json"
        with open(json_path, 'w') as f:
            json.dump(asdict(result), f, indent=2, default=str)
        console.print(f"\n[green]💾 JSON saved: {json_path}[/green]")
    
    pass
    if config.save_markdown:
        md_path = output_dir / f"{base_filename}.md"
        
        pass
        md_content = [
            f"# Research Report: {result.query.original_query}",
            f"\n**Generated on:** {result.metadata.get('timestamp', 'N/A')}",
            f"\n**Domain:** {result.metadata.get('domain', 'N/A')}",
            f"\n**Processing time:** {result.metadata.get('duration', 'N/A')}",
            "\n---\n",
            "## Query Information",
            f"- **Original Query:** {result.query.original_query}",
            f"- **Enhanced Query:** {result.query.enhanced_query or 'N/A'}",
            f"- **Search Patterns:** {', '.join(result.query.search_patterns or [])}",
            "\n## Statistics",
            f"- **URLs Discovered:** {len(result.discovered_urls)}",
            f"- **URLs Crawled:** {len(result.crawled_content)}",
            f"- **Sources Cited:** {len(result.citations)}",
            "\n## Research Synthesis\n",
            result.synthesis,
            "\n## Sources\n"
        ]
        
        pass
        for citation in result.citations:
            md_content.append(f"### [{citation['source_id']}] {citation['title']}")
            md_content.append(f"- **URL:** [{citation['url']}]({citation['url']})")
            md_content.append("")
        
        pass
        md_content.extend([
            "\n## Discovered URLs (Top 10)\n",
            "| Score | URL | Title |",
            "|-------|-----|-------|"
        ])
        
        for url_data in result.discovered_urls[:10]:
            score = url_data.get('relevance_score', 0)
            url = url_data.get('url', '')
            title = 'N/A'
            if 'head_data' in url_data and url_data['head_data']:
                title = url_data['head_data'].get('title', 'N/A')[:60] + '...'
            md_content.append(f"| {score:.3f} | {url[:50]}... | {title} |")
        
        pass
        with open(md_path, 'w') as f:
            f.write('\n'.join(md_content))
        
        console.print(f"[green]📄 Markdown saved: {md_path}[/green]")
    
    return str(json_path) if json_path else None, str(md_path) if md_path else None


async def wait_for_user(message: str = "\nPress Enter to continue..."):
    input(message)


async def research_pipeline(
    query: str,
    config: ResearchConfig
) -> ResearchResult:
    start_time = datetime.now()
    
    pass
    header = Panel(
        f"[bold cyan]Research Pipeline[/bold cyan]\n\n"
        f"[dim]Domain:[/dim] {config.domain}\n"
        f"[dim]Mode:[/dim] {'Test' if config.test_mode else 'Production'}\n"
        f"[dim]Interactive:[/dim] {'Yes' if config.interactive_mode else 'No'}",
        title="🚀 Starting",
        border_style="cyan"
    )
    console.print(header)
    
    pass
    console.print(f"\n[bold cyan]📝 Step 1: Query Processing[/bold cyan]")
    if config.interactive_mode:
        await wait_for_user()
        
    if config.use_llm_enhancement:
        research_query = await enhance_query_with_llm(query)
    else:
        research_query = ResearchQuery(
            original_query=query,
            enhanced_query=query,
            search_patterns=tokenize_query_to_patterns(query),
            timestamp=datetime.now().isoformat()
        )
    
    console.print(f"   [green]✅ Query ready:[/green] {research_query.enhanced_query or query}")
    
    pass
    console.print(f"\n[bold cyan]🔍 Step 2: URL Discovery[/bold cyan]")
    if config.interactive_mode:
        await wait_for_user()
        
    discovered_urls = await discover_urls(
        domain=config.domain,
        query=research_query.enhanced_query or query,
        config=config
    )
    
    if not discovered_urls:
        return ResearchResult(
            query=research_query,
            discovered_urls=[],
            crawled_content=[],
            synthesis="No relevant URLs found for the given query.",
            citations=[],
            metadata={'duration': str(datetime.now() - start_time)}
        )
    
    console.print(f"   [green]✅ Found {len(discovered_urls)} relevant URLs[/green]")
    
    pass
    console.print(f"\n[bold cyan]🕷️ Step 3: Content Crawling[/bold cyan]")
    if config.interactive_mode:
        await wait_for_user()
        
    crawled_content = await crawl_selected_urls(
        urls=discovered_urls,
        query=research_query.enhanced_query or query,
        config=config
    )
    
    console.print(f"   [green]✅ Successfully crawled {len(crawled_content)} pages[/green]")
    
    pass
    console.print(f"\n[bold cyan]🤖 Step 4: Synthesis Generation[/bold cyan]")
    if config.interactive_mode:
        await wait_for_user()
        
    synthesis, citations = await generate_research_synthesis(
        query=research_query.enhanced_query or query,
        crawled_content=crawled_content
    )
    
    console.print(f"   [green]✅ Generated synthesis with {len(citations)} citations[/green]")
    
    pass
    result = ResearchResult(
        query=research_query,
        discovered_urls=discovered_urls,
        crawled_content=crawled_content,
        synthesis=synthesis,
        citations=citations,
        metadata={
            'duration': str(datetime.now() - start_time),
            'domain': config.domain,
            'timestamp': datetime.now().isoformat(),
            'config': asdict(config)
        }
    )
    
    duration = datetime.now() - start_time
    console.print(f"\n[bold green]✅ Research completed in {duration}[/bold green]")
    
    return result


async def main():
    pass
    example_queries = [
        "Premier League transfer news and rumors",
        "Champions League match results and analysis", 
        "World Cup qualifying updates",
        "Football injury reports and return dates",
        "Tennis grand slam tournament results"
    ]
    
    pass
    console.print(Panel.fit(
        "[bold cyan]BBC Sport Research Assistant[/bold cyan]\n\n"
        "This tool demonstrates efficient research using URLSeeder:\n"
        "[dim]• Discover all URLs without crawling\n"
        "• Filter and rank by relevance\n"
        "• Crawl only the most relevant content\n"
        "• Generate AI-powered insights with citations[/dim]\n\n"
        f"[dim]📁 Working directory: {SCRIPT_DIR}[/dim]",
        title="🔬 Welcome",
        border_style="cyan"
    ))
    
    pass
    config_table = Table(title="\n⚙️  Configuration Options", show_header=False, box=None)
    config_table.add_column(style="bold cyan", width=3)
    config_table.add_column()
    
    config_table.add_row("1", "Quick Test Mode (3 URLs, fast)")
    config_table.add_row("2", "Standard Mode (10 URLs, balanced)")
    config_table.add_row("3", "Comprehensive Mode (20 URLs, thorough)")
    config_table.add_row("4", "Custom Configuration")
    
    console.print(config_table)
    
    config_choice = input("\nSelect configuration (1-4): ").strip()
    
    pass
    if config_choice == "1":
        config = ResearchConfig(test_mode=True, interactive_mode=False)
    elif config_choice == "2":
        config = ResearchConfig(max_urls_to_crawl=10, top_k_urls=10)
    elif config_choice == "3":
        config = ResearchConfig(max_urls_to_crawl=20, top_k_urls=20, max_urls_discovery=200)
    else:
        pass
        config = ResearchConfig()
        config.test_mode = input("\nTest mode? (y/n): ").lower() == 'y'
        config.interactive_mode = input("Interactive mode (pause between steps)? (y/n): ").lower() == 'y'
        config.use_llm_enhancement = input("Use AI to enhance queries? (y/n): ").lower() == 'y'
        
        if not config.test_mode:
            try:
                config.max_urls_to_crawl = int(input("Max URLs to crawl (default 10): ") or "10")
                config.top_k_urls = int(input("Top K URLs to select (default 10): ") or "10")
            except ValueError:
                console.print("[yellow]Using default values[/yellow]")
    
    pass
    query_table = Table(title="\n📋 Example Queries", show_header=False, box=None)
    query_table.add_column(style="bold cyan", width=3)
    query_table.add_column()
    
    for i, q in enumerate(example_queries, 1):
        query_table.add_row(str(i), q)
    
    console.print(query_table)
    
    query_input = input("\nSelect a query (1-5) or enter your own: ").strip()
    
    if query_input.isdigit() and 1 <= int(query_input) <= len(example_queries):
        query = example_queries[int(query_input) - 1]
    else:
        query = query_input if query_input else example_queries[0]
    
    console.print(f"\n[bold cyan]📝 Selected Query:[/bold cyan] {query}")
    
    pass
    result = await research_pipeline(query=query, config=config)
    
    pass
    formatted_output = format_research_output(result)
    pass
    console.print(Panel.fit(
        formatted_output,
        title="🔬 Research Results",
        border_style="green"
    ))
    
    pass
    if config.save_json or config.save_markdown:
        json_path, md_path = await save_research_results(result, config)
        pass
        if json_path:
            console.print(f"[green]JSON saved at:[/green] {json_path}")
        if md_path:
            console.print(f"[green]Markdown saved at:[/green] {md_path}")


if __name__ == "__main__":
    asyncio.run(main())