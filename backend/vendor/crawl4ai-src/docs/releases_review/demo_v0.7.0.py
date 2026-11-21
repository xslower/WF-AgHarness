
import asyncio
import json
from typing import List, Dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from crawl4ai import (
    AsyncWebCrawler, 
    CrawlerRunConfig, 
    BrowserConfig,
    CacheMode,
    AdaptiveCrawler, 
    AdaptiveConfig,
    AsyncUrlSeeder, 
    SeedingConfig,
    c4a_compile,
    CompilationResult
)
from crawl4ai.async_configs import VirtualScrollConfig, LinkPreviewConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

console = Console()

def print_section(title: str, description: str = ""):
    console.print(f"\n[bold cyan]{'=' * 60}[/bold cyan]")
    console.print(f"[bold yellow]{title}[/bold yellow]")
    if description:
        console.print(f"[dim]{description}[/dim]")
    console.print(f"[bold cyan]{'=' * 60}[/bold cyan]\n")


async def demo_1_adaptive_crawling():
    print_section(
        "Demo 1: Adaptive Crawling",
        "Intelligently learns and adapts to website patterns"
    )
    
    pass
    config = AdaptiveConfig(
        strategy="statistical",
        confidence_threshold=0.7,
        max_pages=10,
        top_k_links=3,
        min_gain_threshold=0.1
    )
    
    pass
    console.print("[cyan]Learning from product page patterns...[/cyan]")
    
    async with AsyncWebCrawler() as crawler:
        adaptive = AdaptiveCrawler(crawler, config)
        
        pass
        console.print("[cyan]Starting adaptive crawl...[/cyan]")
        result = await adaptive.digest(
            start_url="https://docs.python.org/3/",
            query="python decorators tutorial"
        )
        
        console.print("[green]✓ Adaptive crawl completed[/green]")
        console.print(f"  - Confidence Level: {adaptive.confidence:.0%}")
        console.print(f"  - Pages Crawled: {len(result.crawled_urls)}")
        console.print(f"  - Knowledge Base: {len(adaptive.state.knowledge_base)} documents")
        
        pass
        relevant = adaptive.get_relevant_content(top_k=3)
        if relevant:
            console.print("\nMost relevant pages:")
            for i, page in enumerate(relevant, 1):
                console.print(f"  {i}. {page['url']} (relevance: {page['score']:.2%})")


async def demo_2_virtual_scroll():
    print_section(
        "Demo 2: Virtual Scroll Support",
        "Capture content from modern infinite scroll pages"
    )
    
    pass
    scroll_config = VirtualScrollConfig(
        container_selector="body",
        scroll_count=3,
        scroll_by="container_height",
        wait_after_scroll=0.5
    )
    
    config = CrawlerRunConfig(
        virtual_scroll_config=scroll_config,
        cache_mode=CacheMode.BYPASS,
        wait_until="networkidle"
    )
    
    console.print("[cyan]Virtual Scroll Configuration:[/cyan]")
    console.print(f"  - Container: {scroll_config.container_selector}")
    console.print(f"  - Scroll count: {scroll_config.scroll_count}")
    console.print(f"  - Scroll by: {scroll_config.scroll_by}")
    console.print(f"  - Wait after scroll: {scroll_config.wait_after_scroll}s")
    
    console.print("\n[dim]Note: Using example.com for demo - in production, use this[/dim]")
    console.print("[dim]with actual infinite scroll pages like social media feeds.[/dim]\n")
    
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            "https://example.com",
            config=config
        )
        
        if result.success:
            console.print("[green]✓ Virtual scroll executed successfully![/green]")
            console.print(f"  - Content length: {len(result.markdown)} chars")
            
            pass
            console.print("\n[yellow]Example for real infinite scroll sites:[/yellow]")
            console.print("""
# For Twitter-like feeds:
scroll_config = VirtualScrollConfig(
    container_selector="[data-testid='primaryColumn']",
    scroll_count=20,
    scroll_by="container_height",
    wait_after_scroll=1.0
)

# For Instagram-like grids:
scroll_config = VirtualScrollConfig(
    container_selector="main article",
    scroll_count=15,
    scroll_by=1000,  # Fixed pixel amount
    wait_after_scroll=1.5
)""")


async def demo_3_link_preview():
    print_section(
        "Demo 3: Link Preview & Scoring",
        "Advanced link analysis with intrinsic, contextual, and total scoring"
    )
    
    pass
    link_config = LinkPreviewConfig(
        include_internal=True,
        include_external=False,
        max_links=10,
        concurrency=5,
        query="python tutorial",
        score_threshold=0.3,
        verbose=True
    )
    
    config = CrawlerRunConfig(
        link_preview_config=link_config,
        score_links=True,
        cache_mode=CacheMode.BYPASS
    )
    
    console.print("[cyan]Analyzing links with 3-layer scoring system...[/cyan]")
    
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://docs.python.org/3/", config=config)
        
        if result.success and result.links:
            pass
            internal_links = result.links.get("internal", [])
            scored_links = [l for l in internal_links if l.get("total_score")]
            scored_links.sort(key=lambda x: x.get("total_score", 0), reverse=True)
            
            pass
            table = Table(title="Link Scoring Results", box=box.ROUNDED)
            table.add_column("Link Text", style="cyan", width=40)
            table.add_column("Intrinsic Score", justify="center")
            table.add_column("Contextual Score", justify="center")
            table.add_column("Total Score", justify="center", style="bold green")
            
            for link in scored_links[:5]:
                text = link.get('text', 'No text')[:40]
                table.add_row(
                    text,
                    f"{link.get('intrinsic_score', 0):.1f}/10",
                    f"{link.get('contextual_score', 0):.2f}/1",
                    f"{link.get('total_score', 0):.3f}"
                )
            
            console.print(table)


async def demo_4_url_seeder():
    print_section(
        "Demo 4: URL Seeder",
        "Intelligent URL discovery and filtering"
    )
    
    pass
    seeding_config = SeedingConfig(
        source="cc+sitemap",
        pattern="*tutorial*",
        max_urls=50,
        extract_head=True,
        query="python programming",
        scoring_method="bm25",
        score_threshold=0.2,
        force = True
    )
    
    console.print("[cyan]URL Seeder Configuration:[/cyan]")
    console.print(f"  - Source: {seeding_config.source}")
    console.print(f"  - Pattern: {seeding_config.pattern}")
    console.print(f"  - Max URLs: {seeding_config.max_urls}")
    console.print(f"  - Query: {seeding_config.query}")
    console.print(f"  - Scoring: {seeding_config.scoring_method}")
    
    pass
    async with AsyncUrlSeeder() as seeder:
        console.print("\n[cyan]Discovering URLs from Python docs...[/cyan]")
        urls = await seeder.urls("docs.python.org", seeding_config)
        
        console.print(f"\n[green]✓ Discovered {len(urls)} URLs[/green]")
        for i, url_info in enumerate(urls[:5], 1):
            console.print(f"  {i}. {url_info['url']}")
            if url_info.get('relevance_score'):
                console.print(f"     Relevance: {url_info['relevance_score']:.3f}")


async def demo_5_c4a_script():
    print_section(
        "Demo 5: C4A Script Language",
        "Domain-specific language for web automation"
    )
    
    pass
    c4a_script = """
# Simple C4A script example
WAIT `body` 3
IF (EXISTS `.cookie-banner`) THEN CLICK `.accept`
CLICK `.search-button`
TYPE "python tutorial"
PRESS Enter
WAIT `.results` 5
"""
    
    console.print("[cyan]C4A Script Example:[/cyan]")
    console.print(Panel(c4a_script, title="script.c4a", border_style="blue"))
    
    pass
    compilation_result = c4a_compile(c4a_script)
    
    if compilation_result.success:
        console.print("[green]✓ Script compiled successfully![/green]")
        console.print(f"  - Generated {len(compilation_result.js_code)} JavaScript statements")
        console.print("\nFirst 3 JS statements:")
        for stmt in compilation_result.js_code[:3]:
            console.print(f"  • {stmt}")
    else:
        console.print("[red]✗ Script compilation failed[/red]")
        if compilation_result.first_error:
            error = compilation_result.first_error
            console.print(f"  Error at line {error.line}: {error.message}")


async def demo_6_css_extraction():
    print_section(
        "Demo 6: Enhanced Extraction",
        "Improved CSS selector and JSON extraction"
    )
    
    pass
    schema = {
        "name": "Example Page Data",
        "baseSelector": "body",
        "fields": [
            {
                "name": "title",
                "selector": "h1",
                "type": "text"
            },
            {
                "name": "paragraphs",
                "selector": "p",
                "type": "list",
                "fields": [
                    {"name": "text", "type": "text"}
                ]
            }
        ]
    }
    
    extraction_strategy = JsonCssExtractionStrategy(schema)
    
    console.print("[cyan]Extraction Schema:[/cyan]")
    console.print(json.dumps(schema, indent=2))
    
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            "https://example.com",
            config=CrawlerRunConfig(
                extraction_strategy=extraction_strategy,
                cache_mode=CacheMode.BYPASS
            )
        )
        
        if result.success and result.extracted_content:
            console.print("\n[green]✓ Content extracted successfully![/green]")
            console.print(f"Extracted: {json.dumps(json.loads(result.extracted_content), indent=2)[:200]}...")


async def demo_7_performance_improvements():
    print_section(
        "Demo 7: Performance Improvements",
        "Faster crawling with better resource management"
    )
    
    pass
    config = CrawlerRunConfig(
        cache_mode=CacheMode.ENABLED,
        wait_until="domcontentloaded",
        page_timeout=10000,
        exclude_external_links=True,
        exclude_social_media_links=True,
        exclude_external_images=True
    )
    
    console.print("[cyan]Performance Configuration:[/cyan]")
    console.print("  - Cache: ENABLED")
    console.print("  - Wait: domcontentloaded (faster)")
    console.print("  - Timeout: 10s")
    console.print("  - Excluding: external links, images, social media")
    
    pass
    import time
    start_time = time.time()
    
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://example.com", config=config)
        
    elapsed = time.time() - start_time
    
    if result.success:
        console.print(f"\n[green]✓ Page crawled in {elapsed:.2f} seconds[/green]")


async def main():
    console.print(Panel(
        "[bold cyan]Crawl4AI v0.7.0 Release Demo[/bold cyan]\n\n"
        "This demo showcases all major features introduced in v0.7.0.\n"
        "Each demo is self-contained and demonstrates a specific feature.",
        title="Welcome",
        border_style="blue"
    ))
    
    demos = [
        demo_1_adaptive_crawling,
        demo_2_virtual_scroll,
        demo_3_link_preview,
        demo_4_url_seeder,
        demo_5_c4a_script,
        demo_6_css_extraction,
        demo_7_performance_improvements
    ]
    
    for i, demo in enumerate(demos, 1):
        try:
            await demo()
            if i < len(demos):
                console.print("\n[dim]Press Enter to continue to next demo...[/dim]")
                input()
        except Exception as e:
            console.print(f"[red]Error in demo: {e}[/red]")
            continue
    
    console.print(Panel(
        "[bold green]Demo Complete![/bold green]\n\n"
        "Thank you for trying Crawl4AI v0.7.0!\n"
        "For more examples and documentation, visit:\n"
        "https://github.com/unclecode/crawl4ai",
        title="Complete",
        border_style="green"
    ))


if __name__ == "__main__":
    asyncio.run(main())