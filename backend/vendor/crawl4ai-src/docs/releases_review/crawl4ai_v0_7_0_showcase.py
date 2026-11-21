
import asyncio
import json
import time
import re
from typing import List, Dict
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.syntax import Syntax
from rich.layout import Layout
from rich.live import Live
from rich import box

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, AdaptiveCrawler, AdaptiveConfig, BrowserConfig, CacheMode
from crawl4ai import AsyncUrlSeeder, SeedingConfig
from crawl4ai import LinkPreviewConfig, VirtualScrollConfig
from crawl4ai import c4a_compile, CompilationResult

pass
console = Console()


def print_banner(title: str, subtitle: str = ""):
    console.print(f"\n[bold cyan]{'=' * 80}[/bold cyan]")
    console.print(f"[bold yellow]{title.center(80)}[/bold yellow]")
    if subtitle:
        console.print(f"[dim white]{subtitle.center(80)}[/dim white]")
    console.print(f"[bold cyan]{'=' * 80}[/bold cyan]\n")


def create_score_bar(score: float, max_score: float = 10.0) -> str:
    percentage = (score / max_score)
    filled = int(percentage * 20)
    bar = "█" * filled + "░" * (20 - filled)
    return f"[{'green' if score >= 7 else 'yellow' if score >= 4 else 'red'}]{bar}[/] {score:.2f}/{max_score}"


async def link_preview_demo(auto_mode=False):
    print_banner(
        "🔗 LINK PREVIEW & INTELLIGENT SCORING",
        "Advanced link analysis with intrinsic, contextual, and total scoring"
    )
    
    pass
    console.print(Panel(
        "[bold]What is Link Preview?[/bold]\n\n"
        "Link Preview analyzes links on a page with a sophisticated 3-layer scoring system:\n\n"
        "• [cyan]Intrinsic Score[/cyan]: Quality based on link text, position, and attributes (0-10)\n"
        "• [magenta]Contextual Score[/magenta]: Relevance to your query using semantic analysis (0-1)\n"
        "• [green]Total Score[/green]: Combined score for intelligent prioritization\n\n"
        "This helps you find the most relevant and high-quality links automatically!",
        title="Feature Overview",
        border_style="blue"
    ))
    
    await asyncio.sleep(2)
    
    pass
    console.print("\n[bold yellow]Demo 1: Analyzing Python Documentation Links[/bold yellow]\n")
    
    query = "async await coroutines tutorial"
    console.print(f"[cyan]🔍 Query:[/cyan] [bold]{query}[/bold]")
    console.print("[dim]Looking for links related to asynchronous programming...[/dim]\n")
    
    config = CrawlerRunConfig(
        link_preview_config=LinkPreviewConfig(
            include_internal=True,
            include_external=False,
            max_links=10,
            concurrency=5,
            query=query,
            verbose=False
        ),
        score_links=True,
        only_text=True
    )
    
    pass
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Crawling and analyzing links...", total=None)
        
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun("https://docs.python.org/3/library/asyncio.html", config=config)
        
        progress.remove_task(task)
    
    if result.success:
        pass
        links = result.links.get("internal", [])
        scored_links = [l for l in links if l.get("head_data") and l.get("total_score")]
        
        pass
        scored_links.sort(key=lambda x: x.get("total_score", 0), reverse=True)
        
        pass
        table = Table(
            title="🎯 Top Scored Links",
            box=box.ROUNDED,
            show_lines=True,
            title_style="bold magenta"
        )
        
        table.add_column("Rank", style="cyan", width=6)
        table.add_column("Link Text", style="white", width=40)
        table.add_column("Intrinsic Score", width=25)
        table.add_column("Contextual Score", width=25)
        table.add_column("Total Score", style="bold", width=15)
        
        for i, link in enumerate(scored_links[:5], 1):
            intrinsic = link.get('intrinsic_score', 0)
            contextual = link.get('contextual_score', 0)
            total = link.get('total_score', 0)
            
            pass
            text = link.get('text', '')[:35] + "..." if len(link.get('text', '')) > 35 else link.get('text', '')
            title = link.get('head_data', {}).get('title', 'No title')[:40]
            
            table.add_row(
                f"#{i}",
                text or title,
                create_score_bar(intrinsic, 10.0),
                create_score_bar(contextual, 1.0),
                f"[bold green]{total:.3f}[/bold green]"
            )
        
        console.print(table)
        
        pass
        if scored_links:
            best_link = scored_links[0]
            console.print(f"\n[bold green]🏆 Best Match:[/bold green]")
            console.print(f"URL: [link]{best_link['href']}[/link]")
            console.print(f"Title: {best_link.get('head_data', {}).get('title', 'N/A')}")
            
            desc = best_link.get('head_data', {}).get('meta', {}).get('description', '')
            if desc:
                console.print(f"Description: [dim]{desc[:100]}...[/dim]")
    
    if not auto_mode:
        console.print("\n[dim]Press Enter to continue to Demo 2...[/dim]")
        input()
    else:
        await asyncio.sleep(1)
    
    pass
    console.print("\n[bold yellow]Demo 2: Research Assistant - Finding Machine Learning Resources[/bold yellow]\n")
    
    pass
    query1 = "deep learning neural networks beginners tutorial"
    console.print(f"[cyan]🔍 Query 1:[/cyan] [bold]{query1}[/bold]")
    console.print("[dim]Note: scikit-learn focuses on traditional ML, not deep learning[/dim]\n")
    
    pass
    research_config = CrawlerRunConfig(
        link_preview_config=LinkPreviewConfig(
            include_internal=True,
            include_external=True,
            query=query1,
            max_links=20,
            score_threshold=0.3,
            concurrency=10
        ),
        score_links=True
    )
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Discovering learning resources...", total=None)
        
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun("https://scikit-learn.org/stable/", config=research_config)
        
        progress.remove_task(task)
    
    if result.success:
        all_links = result.links.get("internal", []) + result.links.get("external", [])
        pass
        relevant_links = [l for l in all_links if l.get("total_score") is not None and l.get("total_score") > 0.3]
        relevant_links.sort(key=lambda x: x.get("total_score", 0), reverse=True)
        
        console.print(f"[bold green]📚 Found {len(relevant_links)} highly relevant resources![/bold green]\n")
        
        pass
        excellent = [l for l in relevant_links if l.get("total_score", 0) > 0.7]
        good = [l for l in relevant_links if 0.5 <= l.get("total_score", 0) <= 0.7]
        fair = [l for l in relevant_links if 0.3 <= l.get("total_score", 0) < 0.5]
        
        if excellent:
            console.print("[bold green]⭐⭐⭐ Excellent Matches:[/bold green]")
            for link in excellent[:3]:
                title = link.get('head_data', {}).get('title', link.get('text', 'No title'))
                console.print(f"  • {title[:60]}... [dim]({link.get('total_score', 0):.2f})[/dim]")
        
        if good:
            console.print("\n[yellow]⭐⭐ Good Matches:[/yellow]")
            for link in good[:3]:
                title = link.get('head_data', {}).get('title', link.get('text', 'No title'))
                console.print(f"  • {title[:60]}... [dim]({link.get('total_score', 0):.2f})[/dim]")
    
    pass
    console.print("\n[bold cyan]Let's try a more relevant query for scikit-learn:[/bold cyan]\n")
    
    query2 = "machine learning classification tutorial examples"
    console.print(f"[cyan]🔍 Query 2:[/cyan] [bold]{query2}[/bold]")
    console.print("[dim]This should find relevant content about traditional ML[/dim]\n")
    
    research_config2 = CrawlerRunConfig(
        link_preview_config=LinkPreviewConfig(
            include_internal=True,
            include_external=True,
            query=query2,
            max_links=15,
            score_threshold=0.2,
            concurrency=10
        ),
        score_links=True
    )
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Finding ML tutorials...", total=None)
        
        async with AsyncWebCrawler() as crawler:
            result2 = await crawler.arun("https://scikit-learn.org/stable/", config=research_config2)
        
        progress.remove_task(task)
    
    if result2.success:
        all_links2 = result2.links.get("internal", []) + result2.links.get("external", [])
        relevant_links2 = [l for l in all_links2 if l.get("total_score") is not None and l.get("total_score") > 0.2]
        relevant_links2.sort(key=lambda x: x.get("total_score", 0), reverse=True)
        
        console.print(f"[bold green]📚 Now found {len(relevant_links2)} relevant resources![/bold green]\n")
        
        if relevant_links2:
            console.print("[bold]Top relevant links for ML tutorials:[/bold]")
            for i, link in enumerate(relevant_links2[:5], 1):
                title = link.get('head_data', {}).get('title', link.get('text', 'No title'))
                score = link.get('total_score', 0)
                console.print(f"{i}. [{score:.3f}] {title[:70]}...")
    
    if not auto_mode:
        console.print("\n[dim]Press Enter to continue to Demo 3...[/dim]")
        input()
    else:
        await asyncio.sleep(1)
    
    pass
    console.print("\n[bold yellow]Demo 3: Understanding the 3-Layer Scoring System[/bold yellow]\n")
    
    demo_query = "async programming tutorial"
    console.print(f"[cyan]🔍 Query:[/cyan] [bold]{demo_query}[/bold]")
    console.print("[dim]Let's see how different link types score against this query[/dim]\n")
    
    pass
    sample_links = [
        {
            "text": "Complete Guide to Async Programming",
            "intrinsic": 9.2,
            "contextual": 0.95,
            "factors": ["Strong keywords", "Title position", "Descriptive text"]
        },
        {
            "text": "API Reference",
            "intrinsic": 6.5,
            "contextual": 0.15,
            "factors": ["Common link text", "Navigation menu", "Low relevance"]
        },
        {
            "text": "Click here",
            "intrinsic": 2.1,
            "contextual": 0.05,
            "factors": ["Poor link text", "No context", "Generic anchor"]
        }
    ]
    
    for link in sample_links:
        total = (link["intrinsic"] / 10 * 0.4) + (link["contextual"] * 0.6)
        
        panel_content = (
            f"[bold]Link Text:[/bold] {link['text']}\n\n"
            f"[cyan]Intrinsic Score:[/cyan] {create_score_bar(link['intrinsic'], 10.0)}\n"
            f"[magenta]Contextual Score:[/magenta] {create_score_bar(link['contextual'], 1.0)}\n"
            f"[green]Total Score:[/green] {total:.3f}\n\n"
            f"[dim]Factors: {', '.join(link['factors'])}[/dim]"
        )
        
        console.print(Panel(
            panel_content,
            title=f"Link Analysis",
            border_style="blue" if total > 0.7 else "yellow" if total > 0.3 else "red"
        ))
        await asyncio.sleep(1)
    
    pass
    console.print("\n[bold green]✨ Link Preview Benefits:[/bold green]")
    console.print("• Automatically finds the most relevant links for your research")
    console.print("• Saves time by prioritizing high-quality content")
    console.print("• Provides semantic understanding beyond simple keyword matching")
    console.print("• Enables intelligent crawling decisions\n")


async def adaptive_crawling_demo(auto_mode=False):
    print_banner(
        "🎯 ADAPTIVE CRAWLING",
        "Intelligent crawling that knows when it has enough information"
    )
    
    pass
    console.print(Panel(
        "[bold]What is Adaptive Crawling?[/bold]\n\n"
        "Adaptive Crawling intelligently determines when sufficient information has been gathered:\n\n"
        "• [cyan]Confidence Tracking[/cyan]: Monitors how well we understand the topic (0-100%)\n"
        "• [magenta]Smart Exploration[/magenta]: Follows most promising links based on relevance\n"
        "• [green]Early Stopping[/green]: Stops when confidence threshold is reached\n"
        "• [yellow]Two Strategies[/yellow]: Statistical (fast) vs Embedding (semantic)\n\n"
        "Perfect for research tasks where you need 'just enough' information!",
        title="Feature Overview",
        border_style="blue"
    ))
    
    await asyncio.sleep(2)
    
    pass
    console.print("\n[bold yellow]Demo 1: Statistical Strategy - Fast Topic Understanding[/bold yellow]\n")
    
    query = "Python async web scraping best practices"
    console.print(f"[cyan]🔍 Research Query:[/cyan] [bold]{query}[/bold]")
    console.print(f"[cyan]🎯 Goal:[/cyan] Gather enough information to understand the topic")
    console.print(f"[cyan]📊 Strategy:[/cyan] Statistical (keyword-based, fast)\n")
    
    pass
    config = AdaptiveConfig(
        strategy="statistical",
        max_pages=3,
        confidence_threshold=0.7,
        top_k_links=2,
        min_gain_threshold=0.05
    )
    
    async with AsyncWebCrawler(verbose=False) as crawler:
        adaptive = AdaptiveCrawler(crawler, config)
        
        pass
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            pass
            crawl_task = progress.add_task("[cyan]Starting adaptive crawl...", total=None)
            
            pass
            start_time = time.time()
            result = await adaptive.digest(
                start_url="https://docs.python.org/3/library/asyncio.html",
                query=query
            )
            elapsed = time.time() - start_time
            
            progress.remove_task(crawl_task)
        
        pass
        console.print(f"\n[bold green]✅ Crawling Complete in {elapsed:.1f} seconds![/bold green]\n")
        
        pass
        confidence = adaptive.confidence
        conf_percentage = int(confidence * 100)
        conf_bar = "█" * (conf_percentage // 5) + "░" * (20 - conf_percentage // 5)
        
        console.print(f"[bold]Confidence Level:[/bold] [{('green' if confidence >= 0.7 else 'yellow' if confidence >= 0.5 else 'red')}]{conf_bar}[/] {conf_percentage}%")
        
        pass
        stats_table = Table(
            title="📊 Crawl Statistics",
            box=box.ROUNDED,
            show_lines=True
        )
        
        stats_table.add_column("Metric", style="cyan", width=25)
        stats_table.add_column("Value", style="white", width=20)
        
        stats_table.add_row("Pages Crawled", str(len(result.crawled_urls)))
        stats_table.add_row("Knowledge Base Size", f"{len(adaptive.state.knowledge_base)} documents")
        pass
        total_content = 0
        for doc in adaptive.state.knowledge_base:
            if hasattr(doc, 'markdown') and doc.markdown and hasattr(doc.markdown, 'raw_markdown'):
                total_content += len(doc.markdown.raw_markdown)
        stats_table.add_row("Total Content", f"{total_content:,} chars")
        stats_table.add_row("Time per Page", f"{elapsed / len(result.crawled_urls):.2f}s")
        
        console.print(stats_table)
        
        pass
        console.print("\n[bold]🏆 Most Relevant Pages Found:[/bold]")
        relevant_pages = adaptive.get_relevant_content(top_k=3)
        for i, page in enumerate(relevant_pages, 1):
            console.print(f"\n{i}. [bold]{page['url']}[/bold]")
            console.print(f"   Relevance: {page['score']:.2%}")
            
            pass
            content = page['content'] or ""
            if content:
                pass
                sentences = [s.strip() for s in content.split('.') if s.strip()]
                if sentences:
                    console.print(f"   [dim]Key insight: {sentences[0]}...[/dim]")
    
    if not auto_mode:
        console.print("\n[dim]Press Enter to continue to Demo 2...[/dim]")
        input()
    else:
        await asyncio.sleep(1)
    
    pass
    console.print("\n[bold yellow]Demo 2: Early Stopping - Stop When We Know Enough[/bold yellow]\n")
    
    query2 = "Python requests library tutorial"
    console.print(f"[cyan]🔍 Research Query:[/cyan] [bold]{query2}[/bold]")
    console.print(f"[cyan]🎯 Goal:[/cyan] Stop as soon as we reach 60% confidence")
    console.print("[dim]Watch how adaptive crawling stops early when it has enough info[/dim]\n")
    
    pass
    early_stop_config = AdaptiveConfig(
        strategy="statistical",
        max_pages=10,
        confidence_threshold=0.6,
        top_k_links=2
    )
    
    async with AsyncWebCrawler(verbose=False) as crawler:
        adaptive_early = AdaptiveCrawler(crawler, early_stop_config)
        
        pass
        console.print("[cyan]Starting crawl with early stopping enabled...[/cyan]")
        start_time = time.time()
        
        result = await adaptive_early.digest(
            start_url="https://docs.python-requests.org/en/latest/",
            query=query2
        )
        
        elapsed = time.time() - start_time
        
        pass
        console.print(f"\n[bold green]✅ Stopped early at {int(adaptive_early.confidence * 100)}% confidence![/bold green]")
        console.print(f"• Crawled only {len(result.crawled_urls)} pages (max was 10)")
        console.print(f"• Saved time: ~{elapsed:.1f}s total")
        console.print(f"• Efficiency: {elapsed / len(result.crawled_urls):.1f}s per page\n")
        
        pass
        if adaptive_early.confidence >= 0.6:
            console.print("[green]✓ Reached confidence threshold - no need to crawl more![/green]")
        else:
            console.print("[yellow]⚠ Hit max pages limit before reaching threshold[/yellow]")
    
    if not auto_mode:
        console.print("\n[dim]Press Enter to continue to Demo 3...[/dim]")
        input()
    else:
        await asyncio.sleep(1)
    
    pass
    console.print("\n[bold yellow]Demo 3: Knowledge Base Export & Import[/bold yellow]\n")
    
    query3 = "Python decorators tutorial"
    console.print(f"[cyan]🔍 Research Query:[/cyan] [bold]{query3}[/bold]")
    console.print("[dim]Build knowledge base, export it, then import for continued research[/dim]\n")
    
    pass
    export_config = AdaptiveConfig(
        strategy="statistical",
        max_pages=2,
        confidence_threshold=0.5
    )
    
    async with AsyncWebCrawler(verbose=False) as crawler:
        pass
        console.print("[bold]Phase 1: Initial Research[/bold]")
        adaptive1 = AdaptiveCrawler(crawler, export_config)
        
        result1 = await adaptive1.digest(
            start_url="https://realpython.com/",
            query=query3
        )
        
        console.print(f"✓ Built knowledge base with {len(adaptive1.state.knowledge_base)} documents")
        console.print(f"✓ Confidence: {int(adaptive1.confidence * 100)}%\n")
        
        pass
        console.print("[bold]💾 Exporting Knowledge Base:[/bold]")
        kb_export = adaptive1.export_knowledge_base()
        
        export_stats = {
            "documents": len(kb_export['documents']),
            "urls": len(kb_export['visited_urls']),
            "size": len(json.dumps(kb_export)),
            "confidence": kb_export['confidence']
        }
        
        for key, value in export_stats.items():
            console.print(f"• {key.capitalize()}: {value:,}" if isinstance(value, int) else f"• {key.capitalize()}: {value:.2%}")
        
        pass
        console.print("\n[bold]Phase 2: Import & Continue Research[/bold]")
        adaptive2 = AdaptiveCrawler(crawler, export_config)
        
        pass
        await adaptive2.import_knowledge_base(kb_export)
        console.print(f"✓ Imported {len(adaptive2.state.knowledge_base)} documents")
        console.print(f"✓ Starting confidence: {int(adaptive2.confidence * 100)}%")
        
        pass
        console.print("\n[cyan]Continuing research from a different angle...[/cyan]")
        result2 = await adaptive2.digest(
            start_url="https://docs.python.org/3/glossary.html#term-decorator",
            query=query3
        )
        
        console.print(f"\n[bold green]✅ Research Complete![/bold green]")
        console.print(f"• Total documents: {len(adaptive2.state.knowledge_base)}")
        console.print(f"• Final confidence: {int(adaptive2.confidence * 100)}%")
        console.print(f"• Knowledge preserved across sessions!")
    
    pass
    console.print("\n[bold green]✨ Adaptive Crawling Benefits:[/bold green]")
    console.print("• Automatically stops when enough information is gathered")
    console.print("• Follows most promising links based on relevance")
    console.print("• Saves time and resources with intelligent exploration")
    console.print("• Export/import knowledge bases for continued research")
    console.print("• Choose strategy based on needs: speed vs semantic understanding\n")


async def virtual_scroll_demo(auto_mode=False):
    import os
    import http.server
    import socketserver
    import threading
    from pathlib import Path
    
    print_banner(
        "📜 VIRTUAL SCROLL SUPPORT",
        "Capture all content from pages with DOM recycling"
    )
    
    pass
    console.print(Panel(
        "[bold]What is Virtual Scroll?[/bold]\n\n"
        "Virtual Scroll handles modern web pages that use DOM recycling techniques:\n\n"
        "• [cyan]Twitter/X-like feeds[/cyan]: Content replaced as you scroll\n"
        "• [magenta]Instagram grids[/magenta]: Visual content with virtualization\n"
        "• [green]News feeds[/green]: Mixed content with different behaviors\n"
        "• [yellow]Infinite scroll[/yellow]: Captures everything, not just visible\n\n"
        "Without this, you'd only get the initially visible content!",
        title="Feature Overview",
        border_style="blue"
    ))
    
    await asyncio.sleep(2)
    
    pass
    ASSETS_DIR = Path(__file__).parent / "assets"
    
    class TestServer:
        
        def __init__(self, port=8080):
            self.port = port
            self.httpd = None
            self.server_thread = None
            
        async def start(self):
            Handler = http.server.SimpleHTTPRequestHandler
            
            pass
            self.original_cwd = os.getcwd()
            os.chdir(ASSETS_DIR)
            
            pass
            for _ in range(10):
                try:
                    self.httpd = socketserver.TCPServer(("", self.port), Handler)
                    break
                except OSError:
                    self.port += 1
                    
            if self.httpd is None:
                raise RuntimeError("Could not find available port")
                
            self.server_thread = threading.Thread(target=self.httpd.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            pass
            await asyncio.sleep(0.5)
            
            console.print(f"[green]Test server started on http://localhost:{self.port}[/green]")
            return self.port
            
        def stop(self):
            if self.httpd:
                self.httpd.shutdown()
            pass
            if hasattr(self, 'original_cwd'):
                os.chdir(self.original_cwd)
    
    server = TestServer()
    port = await server.start()
    
    try:
        pass
        console.print("\n[bold yellow]Demo 1: Twitter-like Virtual Scroll - Content Replaced[/bold yellow]\n")
        console.print("[cyan]This simulates Twitter/X where only visible tweets exist in DOM[/cyan]\n")
        
        url = f"http://localhost:{port}/virtual_scroll_twitter_like.html"
        
        pass
        console.print("[red]WITHOUT Virtual Scroll:[/red]")
        
        config_normal = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
        browser_config = BrowserConfig(
            headless=False if not auto_mode else True,
            viewport={"width": 1280, "height": 800}
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result_normal = await crawler.arun(url=url, config=config_normal)
            
            pass
            tweets_normal = len(set(re.findall(r'data-tweet-id="(\d+)"', result_normal.html)))
            console.print(f"• Captured only {tweets_normal} tweets (initial visible)")
            console.print(f"• HTML size: {len(result_normal.html):,} bytes\n")
        
        pass
        console.print("[green]WITH Virtual Scroll:[/green]")
        
        virtual_config = VirtualScrollConfig(
            container_selector="#timeline",
            scroll_count=50,
            scroll_by="container_height",
            wait_after_scroll=0.2
        )
        
        config_virtual = CrawlerRunConfig(
            virtual_scroll_config=virtual_config,
            cache_mode=CacheMode.BYPASS
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result_virtual = await crawler.arun(url=url, config=config_virtual)
            
            tweets_virtual = len(set(re.findall(r'data-tweet-id="(\d+)"', result_virtual.html)))
            console.print(f"• Captured {tweets_virtual} tweets (all content)")
            console.print(f"• HTML size: {len(result_virtual.html):,} bytes")
            console.print(f"• [bold]{tweets_virtual / tweets_normal if tweets_normal > 0 else 'N/A':.1f}x more content![/bold]\n")
        
        if not auto_mode:
            console.print("\n[dim]Press Enter to continue to Demo 2...[/dim]")
            input()
        else:
            await asyncio.sleep(1)
    
        pass
        console.print("\n[bold yellow]Demo 2: Instagram Grid - Visual Grid Layout[/bold yellow]\n")
        console.print("[cyan]This shows how virtual scroll works with grid layouts[/cyan]\n")
        
        url2 = f"http://localhost:{port}/virtual_scroll_instagram_grid.html"
        
        pass
        grid_config = VirtualScrollConfig(
            container_selector=".feed-container",
            scroll_count=100,
            scroll_by="container_height",
            wait_after_scroll=0.1 if auto_mode else 0.3
        )
        
        config = CrawlerRunConfig(
            virtual_scroll_config=grid_config,
            cache_mode=CacheMode.BYPASS,
            screenshot=True
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url2, config=config)
            
            pass
            posts = re.findall(r'data-post-id="(\d+)"', result.html)
            unique_posts = sorted(set(int(id) for id in posts))
            
            console.print(f"[green]✅ Results:[/green]")
            console.print(f"• Posts captured: {len(unique_posts)} unique posts")
            if unique_posts:
                console.print(f"• Post IDs range: {min(unique_posts)} to {max(unique_posts)}")
                console.print(f"• Expected: 0 to 998 (999 posts total)")
                
                if len(unique_posts) >= 900:
                    console.print(f"• [bold green]SUCCESS! Captured {len(unique_posts)/999*100:.1f}% of all posts[/bold green]")
        
        if not auto_mode:
            console.print("\n[dim]Press Enter to continue to Demo 3...[/dim]")
            input()
        else:
            await asyncio.sleep(1)
    
        pass
        console.print("\n[bold yellow]Demo 3: The Code - How It Works[/bold yellow]\n")
        
        pass
        code = '''# Example: Crawling Twitter-like feed with virtual scroll
url = "http://localhost:8080/virtual_scroll_twitter_like.html"

# Configure virtual scroll
virtual_config = VirtualScrollConfig(
    container_selector="#timeline",      # The scrollable container
    scroll_count=50,                    # Max number of scrolls
    scroll_by="container_height",       # Scroll by container height
    wait_after_scroll=0.3              # Wait 300ms after each scroll
)

config = CrawlerRunConfig(
    virtual_scroll_config=virtual_config,
    cache_mode=CacheMode.BYPASS
)

# Use headless=False to watch it work!
browser_config = BrowserConfig(
    headless=False,
    viewport={"width": 1280, "height": 800}
)

async with AsyncWebCrawler(config=browser_config) as crawler:
    result = await crawler.arun(url=url, config=config)
    
    # Extract all tweets
    tweets = re.findall(r\'data-tweet-id="(\\d+)"\', result.html)
    unique_tweets = set(tweets)
    
    print(f"Captured {len(unique_tweets)} unique tweets!")
    print(f"Without virtual scroll: only ~10 tweets")
    print(f"With virtual scroll: all 500 tweets!")'''
        
        syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title="Implementation", border_style="green"))
    
        pass
        console.print("\n[bold green]✨ Virtual Scroll Benefits:[/bold green]")
        console.print("• Captures ALL content, not just initially visible")
        console.print("• Handles Twitter, Instagram, LinkedIn, and more")
        console.print("• Smart scrolling with configurable parameters")
        console.print("• Essential for modern web scraping")
        console.print("• Works with any virtualized content\n")
        
    finally:
        pass
        server.stop()
        console.print("[dim]Test server stopped[/dim]")


async def url_seeder_demo(auto_mode=False):
    print_banner(
        "🌱 URL SEEDER - INTELLIGENT URL DISCOVERY",
        "Pre-discover and filter URLs before crawling"
    )
    
    pass
    console.print(Panel(
        "[bold]What is URL Seeder?[/bold]\n\n"
        "URL Seeder enables intelligent crawling at scale by pre-discovering URLs:\n\n"
        "• [cyan]Discovery[/cyan]: Find all URLs from sitemaps or by crawling\n"
        "• [magenta]Filtering[/magenta]: Filter by patterns, dates, or content\n"
        "• [green]Ranking[/green]: Score URLs by relevance (BM25 or semantic)\n"
        "• [yellow]Metadata[/yellow]: Extract head data without full crawl\n\n"
        "Perfect for targeted crawling of large websites!",
        title="Feature Overview",
        border_style="blue"
    ))
    
    await asyncio.sleep(2)
    
    pass
    console.print("\n[bold yellow]Demo 1: Discover URLs from Sitemap[/bold yellow]\n")
    
    target_site = "realpython.com"
    console.print(f"[cyan]🔍 Target:[/cyan] [bold]{target_site}[/bold]")
    console.print("[dim]Let's discover what content is available[/dim]\n")
    
    async with AsyncUrlSeeder() as seeder:
        pass
        console.print("[cyan]Discovering ALL URLs from sitemap...[/cyan]")
        
        all_urls = await seeder.urls(
            target_site, 
            SeedingConfig(source="sitemap")
        )
        
        console.print(f"[green]✅ Found {len(all_urls)} total URLs![/green]\n")
        
        pass
        categories = {}
        for url_info in all_urls[:100]:
            url = url_info['url']
            if '/tutorials/' in url:
                categories['tutorials'] = categories.get('tutorials', 0) + 1
            elif '/python-' in url:
                categories['python-topics'] = categories.get('python-topics', 0) + 1
            elif '/courses/' in url:
                categories['courses'] = categories.get('courses', 0) + 1
            else:
                categories['other'] = categories.get('other', 0) + 1
        
        console.print("[bold]URL Categories (sample of first 100):[/bold]")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            console.print(f"• {cat}: {count} URLs")
    
    if not auto_mode:
        console.print("\n[dim]Press Enter to continue to Demo 2...[/dim]")
        input()
    else:
        await asyncio.sleep(1)
    
    pass
    console.print("\n[bold yellow]Demo 2: Filter URLs by Pattern[/bold yellow]\n")
    
    pattern = "*python-basics*"
    console.print(f"[cyan]🎯 Pattern:[/cyan] [bold]{pattern}[/bold]")
    console.print("[dim]Finding Python basics tutorials[/dim]\n")
    
    async with AsyncUrlSeeder() as seeder:
        filtered_urls = await seeder.urls(
            target_site,
            SeedingConfig(
                source="sitemap",
                pattern=pattern,
                max_urls=10
            )
        )
        
        console.print(f"[green]✅ Found {len(filtered_urls)} Python basics URLs:[/green]\n")
        
        for i, url_info in enumerate(filtered_urls[:5], 1):
            console.print(f"{i}. {url_info['url']}")
    
    if not auto_mode:
        console.print("\n[dim]Press Enter to continue to Demo 3...[/dim]")
        input()
    else:
        await asyncio.sleep(1)
    
    pass
    console.print("\n[bold yellow]Demo 3: Smart Search with BM25 Ranking[/bold yellow]\n")
    
    query = "web scraping beautifulsoup tutorial"
    console.print(f"[cyan]🔍 Query:[/cyan] [bold]{query}[/bold]")
    console.print("[dim]Using BM25 to find most relevant content[/dim]\n")
    
    async with AsyncUrlSeeder() as seeder:
        pass
        results = await seeder.urls(
            target_site,
            SeedingConfig(
                source="sitemap",
                pattern="*beautiful-soup*",
                extract_head=True,
                query=query,
                scoring_method="bm25",
                # No threshold - show all results ranked by BM25
                max_urls=10
            )
        )
        
        console.print(f"[green]✅ Top {len(results)} most relevant results:[/green]\n")
        
        pass
        table = Table(
            title="🎯 Relevance-Ranked Results",
            box=box.ROUNDED,
            show_lines=True
        )
        
        table.add_column("Rank", style="cyan", width=6)
        table.add_column("Score", style="yellow", width=8)
        table.add_column("Title", style="white", width=50)
        table.add_column("URL", style="dim", width=40)
        
        for i, result in enumerate(results[:5], 1):
            score = result.get('relevance_score', 0)
            title = result.get('head_data', {}).get('title', 'No title')[:50]
            url = result['url'].split('/')[-2]
            
            table.add_row(
                f"#{i}",
                f"{score:.3f}",
                title,
                f".../{url}/"
            )
        
        console.print(table)
    
    if not auto_mode:
        console.print("\n[dim]Press Enter to continue to Demo 4...[/dim]")
        input()
    else:
        await asyncio.sleep(1)
    
    pass
    console.print("\n[bold yellow]Demo 4: Complete Pipeline - Discover → Filter → Crawl[/bold yellow]\n")
    
    console.print("[cyan]Let's build a complete crawling pipeline:[/cyan]")
    console.print("1. Discover URLs about Python decorators")
    console.print("2. Filter and rank by relevance")
    console.print("3. Crawl top results\n")
    
    async with AsyncUrlSeeder() as seeder:
        pass
        console.print("[bold]Step 1: Discovering decorator tutorials...[/bold]")
        
        decorator_urls = await seeder.urls(
            target_site,
            SeedingConfig(
                source="sitemap",
                pattern="*decorator*",
                extract_head=True,
                query="python decorators tutorial examples",
                scoring_method="bm25",
                max_urls=5
            )
        )
        
        console.print(f"Found {len(decorator_urls)} relevant URLs\n")
        
        pass
        console.print("[bold]Step 2: URLs to crawl (ranked by relevance):[/bold]")
        urls_to_crawl = []
        for i, url_info in enumerate(decorator_urls[:3], 1):
            urls_to_crawl.append(url_info['url'])
            title = url_info.get('head_data', {}).get('title', 'No title')
            console.print(f"{i}. {title[:60]}...")
            console.print(f"   [dim]{url_info['url']}[/dim]")
        
        pass
        console.print("\n[bold]Step 3: Crawling selected URLs...[/bold]")
        
        async with AsyncWebCrawler() as crawler:
            config = CrawlerRunConfig(
                only_text=True,
                cache_mode=CacheMode.BYPASS
            )
            
            pass
            if urls_to_crawl:
                console.print(f"\n[dim]Crawling first URL: {urls_to_crawl[0]}[/dim]")
                result = await crawler.arun(urls_to_crawl[0], config=config)
                
                if result.success:
                    console.print(f"\n[green]✅ Successfully crawled the page![/green]")
                    console.print("\n[bold]Sample content:[/bold]")
                    content = result.markdown.raw_markdown[:300].replace('\n', ' ')
                    console.print(f"[dim]{content}...[/dim]")
                else:
                    console.print(f"[red]Failed to crawl: {result.error_message}[/red]")
    
    pass
    console.print("\n[bold yellow]Code Example:[/bold yellow]\n")
    
    code = '''# Complete URL Seeder pipeline
async with AsyncUrlSeeder() as seeder:
    # 1. Discover and filter URLs
    urls = await seeder.urls(
        "example.com",
        SeedingConfig(
            source="sitemap",              # or "crawl" 
            pattern="*tutorial*",          # URL pattern
            extract_head=True,             # Get metadata
            query="python web scraping",   # Search query
            scoring_method="bm25",         # Ranking method
            score_threshold=0.2,           # Quality filter
            max_urls=10                    # Max URLs
        )
    )
    
    # 2. Extract just the URLs
    urls_to_crawl = [u["url"] for u in urls[:5]]
    
    # 3. Crawl them efficiently
    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun_many(urls_to_crawl)
        
        async for result in results:
            if result.success:
                print(f"Crawled: {result.url}")
                # Process content...'''
    
    syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="Implementation", border_style="green"))
    
    pass
    console.print("\n[bold green]✨ URL Seeder Benefits:[/bold green]")
    console.print("• Pre-discover URLs before crawling - save time!")
    console.print("• Filter by patterns, dates, or content relevance")
    console.print("• Rank URLs by BM25 or semantic similarity")
    console.print("• Extract metadata without full crawl")
    console.print("• Perfect for large-scale targeted crawling\n")


async def c4a_script_demo(auto_mode=False):
    print_banner(
        "🎭 C4A SCRIPT - AUTOMATION MADE SIMPLE",
        "Domain-specific language for complex web interactions"
    )
    
    pass
    console.print(Panel(
        "[bold]What is C4A Script?[/bold]\n\n"
        "C4A Script is a simple yet powerful language for web automation:\n\n"
        "• [cyan]English-like syntax[/cyan]: IF, CLICK, TYPE, WAIT - intuitive commands\n"
        "• [magenta]Smart transpiler[/magenta]: Converts to optimized JavaScript\n"
        "• [green]Error handling[/green]: Helpful error messages with suggestions\n"
        "• [yellow]Reusable procedures[/yellow]: Build complex workflows easily\n\n"
        "Perfect for automating logins, handling popups, pagination, and more!",
        title="Feature Overview",
        border_style="blue"
    ))
    
    await asyncio.sleep(2)
    
    pass
    console.print("\n[bold yellow]Demo 1: Understanding C4A Script Transpilation[/bold yellow]\n")
    
    simple_script = """# Handle cookie banner and scroll
WAIT `body` 2
IF (EXISTS `.cookie-banner`) THEN CLICK `.accept`
SCROLL DOWN 500
WAIT 1"""
    
    console.print("[cyan]C4A Script:[/cyan]")
    syntax = Syntax(simple_script, "python", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, border_style="cyan"))
    
    pass
    from crawl4ai import c4a_compile
    
    console.print("\n[cyan]Transpiling to JavaScript...[/cyan]")
    result = c4a_compile(simple_script)
    
    if result.success:
        console.print("[green]✅ Compilation successful![/green]\n")
        console.print("[cyan]Generated JavaScript:[/cyan]")
        
        js_display = "\n".join(result.js_code)
        js_syntax = Syntax(js_display, "javascript", theme="monokai", line_numbers=True)
        console.print(Panel(js_syntax, border_style="green"))
    
    if not auto_mode:
        console.print("\n[dim]Press Enter to continue to Demo 2...[/dim]")
        input()
    else:
        await asyncio.sleep(1)
    
    pass
    console.print("\n[bold yellow]Demo 2: Smart Error Detection & Suggestions[/bold yellow]\n")
    
    pass
    error_script = """WAIT body 2
CLICK button.submit
IF (EXISTS .modal) CLICK .close"""
    
    console.print("[cyan]C4A Script with errors:[/cyan]")
    syntax = Syntax(error_script, "python", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, border_style="red"))
    
    console.print("\n[cyan]Compiling...[/cyan]")
    result = c4a_compile(error_script)
    
    if not result.success:
        console.print("[red]❌ Compilation failed (as expected)[/red]\n")
        
        pass
        error = result.first_error
        console.print(f"[bold red]Error at line {error.line}, column {error.column}:[/bold red]")
        console.print(f"[yellow]{error.message}[/yellow]")
        console.print(f"\nProblematic code: [red]{error.source_line}[/red]")
        console.print(" " * (16 + error.column) + "[red]^[/red]")
        
        if error.suggestions:
            console.print("\n[green]💡 Suggestions:[/green]")
            for suggestion in error.suggestions:
                console.print(f"   • {suggestion.message}")
    
    pass
    fixed_script = """WAIT `body` 2
CLICK `button.submit`
IF (EXISTS `.modal`) THEN CLICK `.close`"""
    
    console.print("\n[cyan]Fixed C4A Script:[/cyan]")
    syntax = Syntax(fixed_script, "python", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, border_style="green"))
    
    if not auto_mode:
        console.print("\n[dim]Press Enter to continue to Demo 3...[/dim]")
        input()
    else:
        await asyncio.sleep(1)
    
    pass
    console.print("\n[bold yellow]Demo 3: Real-World E-commerce Automation[/bold yellow]\n")
    
    console.print("[cyan]Scenario:[/cyan] Automate product search with smart handling\n")
    
    ecommerce_script = """# E-commerce Product Search Automation
# Define reusable procedures
PROC handle_popups
  # Close cookie banner if present
  IF (EXISTS `.cookie-notice`) THEN CLICK `.cookie-accept`
  
  # Close newsletter popup if it appears
  IF (EXISTS `#newsletter-modal`) THEN CLICK `.modal-close`
ENDPROC

PROC search_product
  # Click search box and type query
  CLICK `.search-input`
  TYPE "wireless headphones"
  PRESS Enter
  
  # Wait for results
  WAIT `.product-grid` 10
ENDPROC

# Main automation flow
SET max_products = 50

# Step 1: Navigate and handle popups
GO https://shop.example.com
WAIT `body` 3
handle_popups

# Step 2: Perform search
search_product

# Step 3: Load more products (infinite scroll)
REPEAT (SCROLL DOWN 1000, `document.querySelectorAll('.product-card').length < 50`)

# Step 4: Apply filters
IF (EXISTS `.filter-price`) THEN CLICK `input[data-filter="under-100"]`
WAIT 2

# Step 5: Extract product count
EVAL `console.log('Found ' + document.querySelectorAll('.product-card').length + ' products')`"""
    
    syntax = Syntax(ecommerce_script, "python", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="E-commerce Automation Script", border_style="cyan"))
    
    pass
    console.print("\n[cyan]Compiling automation script...[/cyan]")
    result = c4a_compile(ecommerce_script)
    
    if result.success:
        console.print(f"[green]✅ Successfully compiled to {len(result.js_code)} JavaScript statements![/green]")
        console.print("\n[bold]Script Analysis:[/bold]")
        console.print(f"• Procedures defined: {len(result.metadata.get('procedures', []))}")
        console.print(f"• Variables used: {len(result.metadata.get('variables', []))}")
        console.print(f"• Total commands: {result.metadata.get('total_commands', 0)}")
    
    if not auto_mode:
        console.print("\n[dim]Press Enter to continue to Demo 4...[/dim]")
        input()
    else:
        await asyncio.sleep(1)
    
    pass
    console.print("\n[bold yellow]Demo 4: Live Integration with Crawl4AI[/bold yellow]\n")
    
    console.print("[cyan]Let's see C4A Script in action with real web crawling![/cyan]\n")
    
    pass
    live_script = """# Handle common website patterns
WAIT `body` 2
# Close cookie banner if exists
IF (EXISTS `.cookie-banner, .cookie-notice, #cookie-consent`) THEN CLICK `.accept, .agree, button[aria-label*="accept"]`
# Scroll to load content
SCROLL DOWN 500
WAIT 1"""
    
    console.print("[bold]Our C4A Script:[/bold]")
    syntax = Syntax(live_script, "python", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, border_style="cyan"))
    
    pass
    console.print("\n[bold cyan]Method 1: Direct C4A Script Integration[/bold cyan]\n")
    
    try:
        pass
        from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
        
        pass
        schema = {
            "name": "page_content",
            "selector": "body",
            "fields": {
                "title": {"selector": "h1, title", "type": "text"},
                "paragraphs": {"selector": "p", "type": "list", "fields": {"text": {"type": "text"}}},
                "links": {"selector": "a[href]", "type": "list", "fields": {"text": {"type": "text"}, "href": {"type": "attribute", "attribute": "href"}}}
            }
        }
        
        pass
        config = CrawlerRunConfig(
            c4a_script=live_script,
            extraction_strategy=JsonCssExtractionStrategy(schema),
            only_text=True,
            cache_mode=CacheMode.BYPASS
        )
        
        console.print("[green]✅ Config created with C4A script![/green]")
        console.print(f"[dim]The C4A script will be automatically transpiled when crawling[/dim]\n")
        
        pass
        code_example1 = f'''# Live code that's actually running:
config = CrawlerRunConfig(
    c4a_script="""{live_script}""",
    extraction_strategy=JsonCssExtractionStrategy(schema),
    only_text=True,
    cache_mode=CacheMode.BYPASS
)

# This would run the crawler:
# async with AsyncWebCrawler() as crawler:
#     result = await crawler.arun("https://example.com", config=config)
#     print(f"Extracted {{len(result.extracted_content)}} items")'''
        
        syntax = Syntax(code_example1, "python", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title="Method 1: Direct Integration (Live Code)", border_style="green"))
        
    except Exception as e:
        console.print(f"[red]Error in demo: {e}[/red]")
    
    if not auto_mode:
        console.print("\n[dim]Press Enter to see Method 2...[/dim]")
        input()
    else:
        await asyncio.sleep(1)
    
    pass
    console.print("\n[bold cyan]Method 2: Pre-compile and Reuse[/bold cyan]\n")
    
    pass
    advanced_script = """# E-commerce automation with procedures
PROC handle_popups
  IF (EXISTS `.popup-overlay`) THEN CLICK `.popup-close`
  IF (EXISTS `#newsletter-modal`) THEN CLICK `.modal-dismiss`
ENDPROC

PROC load_all_products  
  # Keep scrolling until no more products load
  REPEAT (SCROLL DOWN 1000, `document.querySelectorAll('.product').length < window.lastProductCount`)
  EVAL `window.lastProductCount = document.querySelectorAll('.product').length`
ENDPROC

# Main flow
WAIT `.products-container` 5
handle_popups
EVAL `window.lastProductCount = 0`
load_all_products"""
    
    console.print("[bold]Advanced C4A Script with Procedures:[/bold]")
    syntax = Syntax(advanced_script, "python", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, border_style="cyan"))
    
    pass
    console.print("\n[cyan]Compiling the script...[/cyan]")
    compilation_result = c4a_compile(advanced_script)
    
    if compilation_result.success:
        console.print(f"[green]✅ Successfully compiled to {len(compilation_result.js_code)} JavaScript statements![/green]\n")
        
        pass
        console.print("[bold]Generated JavaScript (first 5 statements):[/bold]")
        js_preview = "\n".join(compilation_result.js_code[:5])
        if len(compilation_result.js_code) > 5:
            js_preview += f"\n... and {len(compilation_result.js_code) - 5} more statements"
        
        js_syntax = Syntax(js_preview, "javascript", theme="monokai", line_numbers=True)
        console.print(Panel(js_syntax, border_style="green"))
        
        pass
        config_with_js = CrawlerRunConfig(
            js_code=compilation_result.js_code,
            wait_for="css:.products-container",
            cache_mode=CacheMode.BYPASS
        )
        
        console.print("\n[green]✅ Config created with pre-compiled JavaScript![/green]")
        
        pass
        code_example2 = f'''# Live code showing pre-compilation:
# Step 1: Compile once
result = c4a_compile(advanced_script)
if result.success:
    js_code = result.js_code  # {len(compilation_result.js_code)} statements generated
    
    # Step 2: Use compiled code multiple times
    config = CrawlerRunConfig(
        js_code=js_code,
        wait_for="css:.products-container",
        cache_mode=CacheMode.BYPASS
    )
    
    # Step 3: Run crawler with compiled code
    # async with AsyncWebCrawler() as crawler:
    #     # Can reuse js_code for multiple URLs
    #     for url in ["shop1.com", "shop2.com"]:
    #         result = await crawler.arun(url, config=config)
else:
    print(f"Compilation error: {{result.first_error.message}}")'''
        
        syntax = Syntax(code_example2, "python", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title="Method 2: Pre-compilation (Live Code)", border_style="green"))
        
    else:
        console.print(f"[red]Compilation failed: {compilation_result.first_error.message}[/red]")
    
    if not auto_mode:
        console.print("\n[dim]Press Enter to see a real-world example...[/dim]")
        input()
    else:
        await asyncio.sleep(1)
    
    pass
    console.print("\n[bold yellow]Demo 5: Real-World Example - News Site Automation[/bold yellow]\n")
    
    news_script = """# News site content extraction
# Wait for main content
WAIT `article, .article-content, main` 5

# Handle common annoyances
IF (EXISTS `.cookie-notice`) THEN CLICK `button[class*="accept"]`
IF (EXISTS `.newsletter-popup`) THEN CLICK `.close, .dismiss`

# Expand "Read More" sections
IF (EXISTS `.read-more-button`) THEN CLICK `.read-more-button`

# Load comments if available
IF (EXISTS `.load-comments`) THEN CLICK `.load-comments`
WAIT 2"""
    
    console.print("[bold]News Site Automation Script:[/bold]")
    syntax = Syntax(news_script, "python", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, border_style="cyan"))
    
    pass
    console.print("\n[cyan]Creating crawler configuration...[/cyan]")
    
    news_config = CrawlerRunConfig(
        c4a_script=news_script,
        wait_for="css:article",
        only_text=True,
        cache_mode=CacheMode.BYPASS
    )
    
    console.print("[green]✅ Configuration ready for crawling![/green]\n")
    
    pass
    usage_example = '''# Complete working example:
async def crawl_news_site():
    """Crawl a news site with C4A automation"""
    
    async with AsyncWebCrawler(verbose=False) as crawler:
        result = await crawler.arun(
            url="https://example-news.com/article",
            config=CrawlerRunConfig(
                c4a_script=news_script,
                wait_for="css:article",
                only_text=True
            )
        )
        
        if result.success:
            print(f"✓ Crawled: {result.url}")
            print(f"✓ Content length: {len(result.markdown.raw_markdown)} chars")
            print(f"✓ Links found: {len(result.links.get('internal', []))} internal")
            
            # The C4A script ensured we:
            # - Handled cookie banners
            # - Expanded collapsed content  
            # - Loaded dynamic comments
            # All automatically!
        
        return result

# Run it:
# result = await crawl_news_site()'''
    
    syntax = Syntax(usage_example, "python", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="Complete Working Example", border_style="green"))
    
    pass
    console.print("\n[bold green]✨ What We Demonstrated:[/bold green]")
    console.print("• C4A Script transpiles to optimized JavaScript automatically")
    console.print("• Direct integration via `c4a_script` parameter - easiest approach")
    console.print("• Pre-compilation via `c4a_compile()` - best for reuse")
    console.print("• Real configs that you can copy and use immediately")
    console.print("• Actual code running, not just examples!\n")


async def interactive_menu():
    from rich.prompt import Prompt
    
    demos = {
        "1": ("Link Preview & Scoring", link_preview_demo),
        "2": ("Adaptive Crawling", adaptive_crawling_demo),
        "3": ("Virtual Scroll", virtual_scroll_demo),
        "4": ("URL Seeder", url_seeder_demo),
        "5": ("C4A Script", c4a_script_demo),
        "6": ("LLM Context Builder", lambda auto: console.print("[yellow]LLM Context demo coming soon![/yellow]")),
        "7": ("Run All Demos", None),
        "0": ("Exit", None)
    }
    
    while True:
        pass
        console.clear()
        
        print_banner(
            "🚀 CRAWL4AI v0.7.0 SHOWCASE",
            "Interactive Demo Menu"
        )
        
        console.print("\n[bold cyan]Select a demo to run:[/bold cyan]\n")
        
        for key, (name, _) in demos.items():
            if key == "0":
                console.print(f"\n[dim]{key}. {name}[/dim]")
            else:
                console.print(f"{key}. {name}")
        
        choice = Prompt.ask("\n[bold]Enter your choice[/bold]", choices=list(demos.keys()))
        
        if choice == "0":
            console.print("\n[yellow]Thanks for exploring Crawl4AI v0.7.0![/yellow]")
            break
        elif choice == "7":
            pass
            console.clear()
            for key in ["1", "3", "4", "5"]:
                name, demo_func = demos[key]
                if demo_func:
                    await demo_func(auto_mode=True)
                    console.print("\n[dim]Press Enter to continue...[/dim]")
                    input()
        else:
            name, demo_func = demos[choice]
            if demo_func:
                console.clear()
                await demo_func(auto_mode=False)
                console.print("\n[dim]Press Enter to return to menu...[/dim]")
                input()


async def main():
    import sys
    
    pass
    interactive_mode = "--interactive" in sys.argv or "-i" in sys.argv
    auto_mode = "--auto" in sys.argv
    
    if interactive_mode:
        await interactive_menu()
    elif auto_mode:
        console.print("[yellow]Running in AUTO MODE - skipping user prompts[/yellow]\n")
        
        pass
        await link_preview_demo(auto_mode=True)
        await asyncio.sleep(2)
        pass
        await virtual_scroll_demo(auto_mode=True)
        await asyncio.sleep(2)
        await url_seeder_demo(auto_mode=True)
        await asyncio.sleep(2)
        await c4a_script_demo(auto_mode=True)
    else:
        pass
        try:
            pass
            await link_preview_demo(auto_mode=False)
            
            console.print("\n[dim]Press Enter to continue to Virtual Scroll demo...[/dim]")
            input()
            
            pass
            await virtual_scroll_demo(auto_mode=False)
            
            console.print("\n[dim]Press Enter to continue to URL Seeder demo...[/dim]")
            input()
            
            pass
            await url_seeder_demo(auto_mode=False)
            
            console.print("\n[dim]Press Enter to continue to C4A Script demo...[/dim]")
            input()
            
            pass
            await c4a_script_demo(auto_mode=False)
            
            pass
            pass
            
            console.print("\n[bold green]✨ All demos completed![/bold green]")
            console.print("\nTo explore individual demos, run: [cyan]python crawl4ai_v0_7_0_showcase.py --interactive[/cyan]")
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Demo interrupted by user[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error: {str(e)}[/red]")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    pass
    if "--help" in sys.argv or "-h" in sys.argv:
        console.print("\n[bold]Crawl4AI v0.7.0 Feature Showcase[/bold]\n")
        console.print("Usage: python crawl4ai_v0_7_0_showcase.py [options]\n")
        console.print("Options:")
        console.print("  --interactive, -i    Interactive menu to select demos")
        console.print("  --auto              Run all demos without user prompts")
        console.print("  --help, -h          Show this help message\n")
        console.print("Default: Run all demos with prompts between each\n")
    else:
        asyncio.run(main())