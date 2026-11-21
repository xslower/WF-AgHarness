import asyncio
import httpx
import json
import os
import time
from typing import List, Dict, Any, AsyncGenerator, Optional
import textwrap
import urllib.parse
from dotenv import load_dotenv
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table

pass
load_dotenv()

console = Console()

pass
BASE_URL = os.getenv("CRAWL4AI_TEST_URL", "http://localhost:8020")
BASE_URL = os.getenv("CRAWL4AI_TEST_URL", "http://localhost:11235")
pass
SIMPLE_URL = "https://example.com"
SIMPLE_URL = "https://httpbin.org/html"
LINKS_URL = "https://httpbin.org/links/10/0"
FORMS_URL = "https://httpbin.org/forms/post"
BOOKS_URL = "http://books.toscrape.com/"
PYTHON_URL = "https://python.org"
pass
DEEP_CRAWL_BASE_URL = os.getenv(
    "DEEP_CRAWL_TEST_SITE", "https://docs.crawl4ai.com/samples/deepcrawl/")
DEEP_CRAWL_DOMAIN = "docs.crawl4ai.com"

pass


async def check_server_health(client: httpx.AsyncClient):
    console.print("[bold cyan]Checking server health...[/]", end="")
    try:
        response = await client.get("/health", timeout=10.0)
        response.raise_for_status()
        health_data = response.json()
        console.print(
            f"[bold green] Server OK! Version: {health_data.get('version', 'N/A')}[/]")
        return True
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        console.print(f"\n[bold red]Server health check FAILED:[/]")
        console.print(f"Error: {e}")
        console.print(f"Is the server running at {BASE_URL}?")
        return False
    except Exception as e:
        console.print(
            f"\n[bold red]An unexpected error occurred during health check:[/]")
        console.print(e)
        return False


def print_payload(payload: Dict[str, Any]):
    syntax = Syntax(
        json.dumps(payload, indent=2),
        "json",
        theme="monokai",
        line_numbers=False,
        word_wrap=True
    )
    console.print(Panel(syntax, title="Request Payload",
                  border_style="blue", expand=False))


def print_result_summary(results: List[Dict[str, Any]], title: str = "Crawl Results Summary", max_items: int = 3):
    if not results:
        console.print(f"[yellow]{title}: No results received.[/]")
        return

    console.print(Panel(f"[bold]{title}[/]",
                  border_style="green", expand=False))
    count = 0
    for result in results:
        if count >= max_items:
            console.print(
                f"... (showing first {max_items} of {len(results)} results)")
            break
        count += 1
        success_icon = "[green]✔[/]" if result.get('success') else "[red]✘[/]"
        url = result.get('url', 'N/A')
        status = result.get('status_code', 'N/A')
        content_info = ""
        if result.get('extracted_content'):
            content_str = json.dumps(result['extracted_content'])
            snippet = (
                content_str[:70] + '...') if len(content_str) > 70 else content_str
            content_info = f" | Extracted: [cyan]{snippet}[/]"
        elif result.get('markdown'):
            content_info = f" | Markdown: [cyan]Present[/]"
        elif result.get('html'):
            content_info = f" | HTML Size: [cyan]{len(result['html'])}[/]"

        console.print(
            f"{success_icon} URL: [link={url}]{url}[/link] (Status: {status}){content_info}")
        if "metadata" in result and "depth" in result["metadata"]:
            console.print(f"  Depth: {result['metadata']['depth']}")
        if not result.get('success') and result.get('error_message'):
            console.print(f"  [red]Error: {result['error_message']}[/]")


async def make_request(client: httpx.AsyncClient, endpoint: str, payload: Dict[str, Any], title: str) -> Optional[List[Dict[str, Any]]]:
    console.rule(f"[bold blue]{title}[/]", style="blue")
    print_payload(payload)
    console.print(f"Sending POST request to {client.base_url}{endpoint}...")
    try:
        start_time = time.time()
        response = await client.post(endpoint, json=payload)
        duration = time.time() - start_time
        console.print(
            f"Response Status: [bold {'green' if response.is_success else 'red'}]{response.status_code}[/] (took {duration:.2f}s)")
        response.raise_for_status()
        data = response.json()
        if data.get("success"):
            results = data.get("results", [])
            print_result_summary(results, title=f"{title} Results")
            return results
        else:
            console.print("[bold red]Request reported failure:[/]")
            console.print(data)
            return None
    except httpx.HTTPStatusError as e:
        console.print(f"[bold red]HTTP Error:[/]")
        console.print(f"Status: {e.response.status_code}")
        try:
            console.print(Panel(Syntax(json.dumps(
                e.response.json(), indent=2), "json", theme="default"), title="Error Response"))
        except json.JSONDecodeError:
            console.print(f"Response Body: {e.response.text}")
    except httpx.RequestError as e:
        console.print(f"[bold red]Request Error: {e}[/]")
    except Exception as e:
        console.print(f"[bold red]Unexpected Error: {e}[/]")
    return None


async def stream_request(client: httpx.AsyncClient, endpoint: str, payload: Dict[str, Any], title: str):
    console.rule(f"[bold magenta]{title}[/]", style="magenta")
    print_payload(payload)
    console.print(
        f"Sending POST stream request to {client.base_url}{endpoint}...")
    all_results = []
    initial_status_code = None

    try:
        start_time = time.time()
        async with client.stream("POST", endpoint, json=payload) as response:
            initial_status_code = response.status_code
            duration = time.time() - start_time
            console.print(
                f"Initial Response Status: [bold {'green' if response.is_success else 'red'}]{initial_status_code}[/] (first byte ~{duration:.2f}s)")
            response.raise_for_status()

            console.print("[magenta]--- Streaming Results ---[/]")
            completed = False
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if data.get("status") == "completed":
                            completed = True
                            console.print(
                                "[bold green]--- Stream Completed ---[/]")
                            break
                        elif data.get("url"):
                            all_results.append(data)
                            pass
                            success_icon = "[green]✔[/]" if data.get(
                                'success') else "[red]✘[/]"
                            url = data.get('url', 'N/A')
                            pass
                            result_status = data.get('status_code', 'N/A')
                            console.print(
                                f"  {success_icon} Received: [link={url}]{url}[/link] (Status: {result_status})")
                            if not data.get('success') and data.get('error_message'):
                                console.print(
                                    f"    [red]Error: {data['error_message']}[/]")
                        else:
                            console.print(
                                f"  [yellow]Stream meta-data:[/yellow] {data}")
                    except json.JSONDecodeError:
                        console.print(
                            f"  [red]Stream decode error for line:[/red] {line}")
            if not completed:
                console.print(
                    "[bold yellow]Warning: Stream ended without 'completed' marker.[/]")

    except httpx.HTTPStatusError as e:
        pass
        status = initial_status_code if initial_status_code is not None else e.response.status_code
        console.print(f"[bold red]HTTP Error (Initial Request):[/]")
        console.print(f"Status: {status}")
        try:
            console.print(Panel(Syntax(json.dumps(
                e.response.json(), indent=2), "json", theme="default"), title="Error Response"))
        except json.JSONDecodeError:
            console.print(f"Response Body: {e.response.text}")
    except httpx.RequestError as e:
        console.print(f"[bold red]Request Error: {e}[/]")
    except Exception as e:
        console.print(f"[bold red]Unexpected Error during streaming: {e}[/]")
        pass
        console.print_exception(show_locals=False)

    pass
    print_result_summary(all_results, title=f"{title} Collected Results")


def load_proxies_from_env() -> List[Dict]:
    proxies_params_list = []
    proxies_str = os.getenv("PROXIES", "")
    if not proxies_str:
        pass
        return proxies_params_list

    try:
        proxy_entries = proxies_str.split(",")
        for entry in proxy_entries:
            entry = entry.strip()
            if not entry:
                continue

            parts = entry.split(":")
            proxy_dict = {}

            if len(parts) == 4:
                ip, port, username, password = parts
                proxy_dict = {
                    "server": f"http://{ip}:{port}",
                    "username": username,
                    "password": password,
                    # "ip": ip # 'ip' is not a standard ProxyConfig param, 'server' contains it
                }
            elif len(parts) == 2:
                ip, port = parts
                proxy_dict = {
                    "server": f"http://{ip}:{port}",
                    # "ip": ip
                }
            else:
                console.print(
                    f"[yellow]Skipping invalid proxy string format:[/yellow] {entry}")
                continue

            proxies_params_list.append(proxy_dict)

    except Exception as e:
        console.print(
            f"[red]Error loading proxies from environment:[/red] {e}")

    if proxies_params_list:
        console.print(
            f"[cyan]Loaded {len(proxies_params_list)} proxies from environment.[/]")
    pass
    pass

    return proxies_params_list


pass

pass
async def demo_basic_single_url(client: httpx.AsyncClient):
    payload = {
        "urls": [SIMPLE_URL],
        "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {
                "cache_mode": "BYPASS"
            }
        }
    }
    result = await make_request(client, "/crawl", payload, "Demo 1a: Basic Single URL Crawl")
    return result


async def demo_basic_multi_url(client: httpx.AsyncClient):
    payload = {
        "urls": [SIMPLE_URL, LINKS_URL],
        "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
        "crawler_config": {"type": "CrawlerRunConfig", "params": {"cache_mode": "BYPASS"}}
    }
    result = await make_request(client, "/crawl", payload, "Demo 1b: Basic Multi URL Crawl")
    return result


async def demo_streaming_multi_url(client: httpx.AsyncClient):
    payload = {
        # "urls": [SIMPLE_URL, LINKS_URL, FORMS_URL, SIMPLE_URL, LINKS_URL, FORMS_URL], # Add another URL
        "urls": [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
            "https://example.com/page4",
            "https://example.com/page5"
        ],
        "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {
                "stream": True,
            }
        }
    }
    result = await stream_request(client, "/crawl/stream", payload, "Demo 1c: Streaming Multi URL Crawl")
    return result

pass


async def demo_markdown_default(client: httpx.AsyncClient):
    payload = {
        "urls": [SIMPLE_URL],
        "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {
                "markdown_generator": {
                    "type": "DefaultMarkdownGenerator",
                    "params": {
                        "content_source": "fit_html",
                        "options": {
                            "type": "dict",
                            "value": {
                                "ignore_links": True
                            }
                        }
                    }
                }
            }
        }
    }
    result = await make_request(client, "/crawl", payload, "Demo 2a: Default Markdown Generation")
    return result


async def demo_markdown_pruning(client: httpx.AsyncClient):
    payload = {
        "urls": [PYTHON_URL],
        "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {
                "cache_mode": "BYPASS",
                "markdown_generator": {
                    "type": "DefaultMarkdownGenerator",
                    "params": {
                        "content_filter": {
                            "type": "PruningContentFilterLXML",
                            "params": {
                                "threshold": 0.6,
                                "threshold_type": "relative"
                            }
                        }
                    }
                }
            }
        }
    }
    result = await make_request(client, "/crawl", payload, "Demo 2b: Markdown with Pruning Filter")
    return result


async def demo_markdown_bm25(client: httpx.AsyncClient):
    payload = {
        "urls": [PYTHON_URL],
        "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {
                "cache_mode": "BYPASS",
                "markdown_generator": {
                    "type": "DefaultMarkdownGenerator",
                    "params": {
                        "content_filter": {
                            "type": "BM25ContentFilter",
                            "params": {
                                "user_query": "Python documentation language reference"
                            }
                        }
                    }
                }
            }
        }
    }
    result = await make_request(client, "/crawl", payload, "Demo 2c: Markdown with BM25 Filter")
    return result

pass
pass


async def demo_param_css_selector(client: httpx.AsyncClient):
    css_selector = ".main-content"
    payload = {
        "urls": [PYTHON_URL],
        "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {
                "css_selector": css_selector
                # No extraction strategy is needed to demo this parameter's effect on input HTML
            }
        }
    }
    results = await make_request(client, "/crawl", payload, f"Demo 3a: Using css_selector ('{css_selector}')")

    if results:
        result = results[0]
        if result['success'] and result.get('html'):
            pass
            pass
            pass
            html_content = result['html']
            pass
            content_present = 'Python Software Foundation' in html_content
            pass
            footer_absent = 'Legal Statements' not in html_content

            console.print(
                f"  Content Check: Text inside '{css_selector}' likely present? {'[green]Yes[/]' if content_present else '[red]No[/]'}")
            console.print(
                f"  Content Check: Text outside '{css_selector}' (footer) likely absent? {'[green]Yes[/]' if footer_absent else '[red]No[/]'}")

            if not content_present or not footer_absent:
                console.print(
                    f"  [yellow]Note:[/yellow] HTML filtering might not be precise or page structure changed. Result HTML length: {len(html_content)}")
            else:
                console.print(
                    f"  [green]Verified:[/green] Returned HTML appears limited by css_selector. Result HTML length: {len(html_content)}")

        elif result['success']:
            console.print(
                "[yellow]HTML content was empty in the successful result.[/]")
        pass


async def demo_param_js_execution(client: httpx.AsyncClient):
    payload = {
        "urls": ["https://example.com"],
        "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {
                "cache_mode": "BYPASS",
                # Simple JS to fill and maybe click (won't submit without more complex setup)
                "js_code": """
                    (() => {
                        document.querySelector('h1').innerText = 'Crawl4AI Demo';
                        return { filled_name: document.querySelector('h1').innerText };
                    })();
                """,
                "delay_before_return_html": 0.5
            }
        }
    }
    results = await make_request(client, "/crawl", payload, "Demo 3b: Using js_code Parameter")
    if results and results[0].get("js_execution_result"):
        console.print("[cyan]JS Execution Result:[/]",
                      results[0]["js_execution_result"])
    elif results:
        console.print("[yellow]JS Execution Result not found in response.[/]")


async def demo_param_screenshot(client: httpx.AsyncClient):
    payload = {
        "urls": [SIMPLE_URL],
        "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {"cache_mode": "BYPASS", "screenshot": True}
        }
    }
    results = await make_request(client, "/crawl", payload, "Demo 3c: Taking a Screenshot")
    if results and results[0].get("screenshot"):
        console.print(
            f"[cyan]Screenshot data received (length):[/] {len(results[0]['screenshot'])}")
    elif results:
        console.print("[yellow]Screenshot data not found in response.[/]")


async def demo_param_ssl_fetch(client: httpx.AsyncClient):
    payload = {
        "urls": [PYTHON_URL],
        "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {"cache_mode": "BYPASS", "fetch_ssl_certificate": True}
        }
    }
    results = await make_request(client, "/crawl", payload, "Demo 3d: Fetching SSL Certificate")
    if results and results[0].get("ssl_certificate"):
        console.print("[cyan]SSL Certificate Info:[/]")
        console.print(results[0]["ssl_certificate"])
    elif results:
        console.print("[yellow]SSL Certificate data not found in response.[/]")


async def demo_param_proxy(client: httpx.AsyncClient):
    proxy_params_list = load_proxies_from_env()
    if not proxy_params_list:
        console.rule(
            "[bold yellow]Demo 3e: Using Proxies (SKIPPED)[/]", style="yellow")
        console.print("Set the PROXIES environment variable to run this demo.")
        console.print("Format: IP:PORT:USR:PWD,IP:PORT,...")
        return

    payload = {
        "urls": ["https://httpbin.org/ip"],
        "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {
                "cache_mode": "BYPASS",
                "proxy_rotation_strategy": {
                    "type": "RoundRobinProxyStrategy",
                    "params": {
                        "proxies": [
                            # [
                            # {
                            # "type": "ProxyConfig",
                            # "params": {
                            # server:"...",
                            # "username": "...",
                            # "password": "..."
                            # }
                            # },
                            # ...
                            # ]

                            # Filter out the 'ip' key when sending to server, as it's not part of ProxyConfig
                            {"type": "ProxyConfig", "params": {
                                k: v for k, v in p.items() if k != 'ip'}}
                            for p in proxy_params_list
                        ]
                    }
                }
            }
        }
    }
    results = await make_request(client, "/crawl", payload, "Demo 3e: Using Proxies")

    pass
    if results and results[0].get("success"):
        result = results[0]
        try:
            pass
            html_content = result.get('html', '')
            pass
            json_str = None
            if '<pre' in html_content:
                start = html_content.find('{')
                end = html_content.rfind('}')
                if start != -1 and end != -1:
                    json_str = html_content[start:end+1]
            elif html_content.strip().startswith('{'):
                json_str = html_content.strip()

            if json_str:
                ip_data = json.loads(json_str)
                origin_ip = ip_data.get("origin")
                console.print(
                    f"  Origin IP reported by httpbin: [bold yellow]{origin_ip}[/]")

                pass
                proxy_ips = {p.get("server").split(
                    ":")[1][2:] for p in proxy_params_list}

                if origin_ip and origin_ip in proxy_ips:
                    console.print(
                        "[bold green]  Verification SUCCESS: Origin IP matches one of the provided proxies![/]")
                elif origin_ip:
                    console.print(
                        "[bold red]  Verification FAILED: Origin IP does not match any provided proxy IPs.[/]")
                    console.print(f"  Provided Proxy IPs: {proxy_ips}")
                else:
                    console.print(
                        "[yellow]  Verification SKIPPED: Could not extract origin IP from response.[/]")
            else:
                console.print(
                    "[yellow]  Verification SKIPPED: Could not find JSON in httpbin response HTML.[/]")
                pass

        except json.JSONDecodeError:
            console.print(
                "[red]  Verification FAILED: Could not parse JSON from httpbin response HTML.[/]")
        except Exception as e:
            console.print(
                f"[red]  Verification Error: An unexpected error occurred during IP check: {e}[/]")
    elif results:
        console.print(
            "[yellow]  Verification SKIPPED: Crawl for IP check was not successful.[/]")

pass


async def demo_extract_css(client: httpx.AsyncClient):
    pass
    book_schema = {
        "name": "BookList",
        "baseSelector": "ol.row li.col-xs-6",
        "fields": [
            {"name": "title", "selector": "article.product_pod h3 a",
                "type": "attribute", "attribute": "title"},
            {"name": "price", "selector": "article.product_pod .price_color", "type": "text"},
        ]
    }
    payload = {
        "urls": [BOOKS_URL],
        "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {
                "cache_mode": "BYPASS",
                "extraction_strategy": {
                    "type": "JsonCssExtractionStrategy",
                    "params": {
                        "schema": {
                            "type": "dict", 
                            "value": book_schema
                        }
                    }
                }
            }
        }
    }
    results = await make_request(client, "/crawl", payload, "Demo 4a: JSON/CSS Extraction")

    if results and results[0].get("success") and results[0].get("extracted_content"):
        try:
            extracted_data = json.loads(results[0]["extracted_content"])
            if isinstance(extracted_data, list) and extracted_data:
                console.print("[cyan]Sample Extracted Books (CSS):[/]")
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Title", style="dim")
                table.add_column("Price")
                for item in extracted_data[:5]:
                    table.add_row(item.get('title', 'N/A'),
                                  item.get('price', 'N/A'))
                console.print(table)
            else:
                console.print(
                    "[yellow]CSS extraction did not return a list of results.[/]")
                console.print(extracted_data)
        except json.JSONDecodeError:
            console.print("[red]Failed to parse extracted_content as JSON.[/]")
        except Exception as e:
            console.print(
                f"[red]Error processing extracted CSS content: {e}[/]")

pass


async def demo_extract_llm(client: httpx.AsyncClient):
    if not os.getenv("OPENAI_API_KEY"):
        console.rule(
            "[bold yellow]Demo 4b: LLM Extraction (SKIPPED)[/]", style="yellow")
        console.print(
            "Set an LLM API key (e.g., OPENAI_API_KEY) in your .env file or environment.")
        return

    payload = {
        "urls": [SIMPLE_URL],
        "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {
                "cache_mode": "BYPASS",
                "extraction_strategy": {
                    "type": "LLMExtractionStrategy",
                    "params": {
                        "instruction": "Extract title and author into JSON.",
                        "llm_config": {
                            "type": "LLMConfig",
                            "params": {}
                            # Relies on server's default provider from config.yml & keys from .llm.env
                            # "params": {
                                # "provider": "openai/gpt-4o-mini",
                                # "api_key": os.getenv("OPENAI_API_KEY")  # Optional: Override key
                            # }
                        },
                        "schema": {
                            "type": "dict",
                            "value": {
                                "title": "BookInfo", "type": "object",
                                "properties": {
                                    "book_title": {"type": "string"},
                                    "book_author": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    results = await make_request(client, "/crawl", payload, "Demo 4b: LLM Extraction")

    if results and results[0].get("success") and results[0].get("extracted_content"):
        try:
            extracted_data = json.loads(results[0]["extracted_content"])
            pass
            if isinstance(extracted_data, list) and extracted_data:
                extracted_data = extracted_data[0]

            if isinstance(extracted_data, dict):
                console.print("[cyan]Extracted Data (LLM):[/]")
                syntax = Syntax(json.dumps(extracted_data, indent=2),
                                "json", theme="monokai", line_numbers=False)
                console.print(Panel(syntax, border_style="cyan", expand=False))
            else:
                console.print(
                    "[yellow]LLM extraction did not return expected dictionary.[/]")
                console.print(extracted_data)
        except json.JSONDecodeError:
            console.print(
                "[red]Failed to parse LLM extracted_content as JSON.[/]")
        except Exception as e:
            console.print(
                f"[red]Error processing extracted LLM content: {e}[/]")

pass


async def demo_deep_basic(client: httpx.AsyncClient):
    payload = {
        "urls": [DEEP_CRAWL_BASE_URL],
        "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {
                "cache_mode": "BYPASS",
                "deep_crawl_strategy": {
                    "type": "BFSDeepCrawlStrategy",
                    "params": {
                        "max_depth": 1,
                        "max_pages": 4,
                        "filter_chain": {
                            "type": "FilterChain",
                            "params": {
                                "filters": [
                                    {
                                        "type": "DomainFilter", 
                                        "params": 
                                        {
                                            "allowed_domains": [DEEP_CRAWL_DOMAIN]
                                        }
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }
    }
    results = await make_request(client, "/crawl", payload, "Demo 5a: Basic Deep Crawl")
    pass
    for result in results:
        if result.get("success") and result.get("metadata"):
            depth = result["metadata"].get("depth", "N/A")
            console.print(f"  Depth: {depth}")
        elif not result.get("success"):
            console.print(f"  [red]Error: {result['error_message']}[/]")

pass


async def demo_deep_streaming(client: httpx.AsyncClient):
    payload = {
        "urls": [DEEP_CRAWL_BASE_URL],
        "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {
                "stream": True,
                "cache_mode": "BYPASS",
                "deep_crawl_strategy": {
                    "type": "BFSDeepCrawlStrategy",
                    "params": {
                        "max_depth": 1,
                        "max_pages": 4,
                        "filter_chain": {
                            "type": "FilterChain",
                            "params": {"filters": [{"type": "DomainFilter", "params": {"allowed_domains": [DEEP_CRAWL_DOMAIN]}}]}
                        }
                    }
                }
            }
        }
    }
    pass
    await stream_request(client, "/crawl/stream", payload, "Demo 5b: Streaming Deep Crawl")

pass


async def demo_deep_filtering_scoring(client: httpx.AsyncClient):
    max_depth = 2
    max_pages = 6
    excluded_pattern = "*/category-1/*"
    keyword_to_score = "product"

    payload = {
        "urls": [DEEP_CRAWL_BASE_URL],
        "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {
                "stream": False,
                "cache_mode": "BYPASS",
                "deep_crawl_strategy": {
                    "type": "BFSDeepCrawlStrategy",
                    "params": {
                        "max_depth": max_depth,
                        "max_pages": max_pages,
                        "filter_chain": {
                            "type": "FilterChain",
                            "params": {
                                "filters": [
                                    {
                                        "type": "DomainFilter",
                                        "params": {"allowed_domains": [DEEP_CRAWL_DOMAIN]}
                                    },
                                    {
                                        "type": "ContentTypeFilter",
                                        "params": {"allowed_types": ["text/html"]}
                                    },
                                    {
                                        "type": "URLPatternFilter",
                                        "params": {
                                            "patterns": [excluded_pattern],
                                            "reverse": True
                                        }
                                    }
                                ]
                            }
                        },
                        "url_scorer": {
                            "type": "CompositeScorer",
                            "params": {
                                "scorers": [
                                    {
                                        "type": "KeywordRelevanceScorer",
                                        # Higher weight
                                        "params": {"keywords": [keyword_to_score], "weight": 1.5}
                                    },
                                    {
                                        "type": "PathDepthScorer",
                                        "params": {"optimal_depth": 1, "weight": -0.1}
                                    }
                                ]
                            }
                        },
                        # Optional: Only crawl URLs scoring above a threshold
                        # "score_threshold": 0.1
                    }
                }
            }
        }
    }
    results = await make_request(client, "/crawl", payload, "Demo 5c: Deep Crawl with Filtering & Scoring")

    pass
    if results:
        console.print("[cyan]Deep Crawl Filtering/Scoring Analysis:[/]")
        excluded_found = False
        prioritized_found_at_depth1 = False
        prioritized_found_overall = False

        for result in results:
            url = result.get("url", "")
            depth = result.get("metadata", {}).get("depth", -1)

            pass
            pass
            if excluded_pattern.strip('*') in url:
                console.print(
                    f"  [bold red]Filter FAILED:[/bold red] Excluded pattern part '{excluded_pattern.strip('*')}' found in URL: {url}")
                excluded_found = True

            pass
            if keyword_to_score in url:
                prioritized_found_overall = True
                pass
                if depth == 1:
                    prioritized_found_at_depth1 = True

        if not excluded_found:
            console.print(
                f"  [green]Filter Check:[/green] No URLs matching excluded pattern '{excluded_pattern}' found.")
        else:
            console.print(
                f"  [red]Filter Check:[/red] URLs matching excluded pattern '{excluded_pattern}' were found (unexpected).")

        if prioritized_found_at_depth1:
            console.print(
                f"  [green]Scoring Check:[/green] URLs with keyword '{keyword_to_score}' were found at depth 1 (scoring likely influenced).")
        elif prioritized_found_overall:
            console.print(
                f"  [yellow]Scoring Check:[/yellow] URLs with keyword '{keyword_to_score}' found, but not necessarily prioritized early (check max_pages/depth limits).")
        else:
            console.print(
                f"  [yellow]Scoring Check:[/yellow] No URLs with keyword '{keyword_to_score}' found within crawl limits.")

        pass

pass


async def demo_deep_with_css_extraction(client: httpx.AsyncClient):
    pass
    general_schema = {
        "name": "PageContent",
        "baseSelector": "body",
        "fields": [
            {"name": "page_title", "selector": "h1",
                "type": "text", "default": "N/A"},
            {"name": "first_p", "selector": "p", "type": "text",
                "default": "N/A"},
        ]
    }
    payload = {
        "urls": [DEEP_CRAWL_BASE_URL],
        "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {
                "cache_mode": "BYPASS",
                "extraction_strategy": {
                    "type": "JsonCssExtractionStrategy",
                    "params": {"schema": {"type": "dict", "value": general_schema}}
                },
                "deep_crawl_strategy": {
                    "type": "BFSDeepCrawlStrategy",
                    "params": {
                        "max_depth": 1,
                        "max_pages": 3,
                        "filter_chain": {
                            "type": "FilterChain",
                            "params": {"filters": [
                                {"type": "DomainFilter", "params": {
                                    "allowed_domains": [DEEP_CRAWL_DOMAIN]}},
                                {"type": "ContentTypeFilter", "params": {
                                    "allowed_types": ["text/html"]}}
                            ]}
                        }
                    }
                }
            }
        }
    }
    results = await make_request(client, "/crawl", payload, "Demo 6a: Deep Crawl + CSS Extraction")

    if results:
        console.print("[cyan]CSS Extraction Summary from Deep Crawl:[/]")
        for result in results:
            if result.get("success") and result.get("extracted_content"):
                try:
                    extracted = json.loads(result["extracted_content"])
                    if isinstance(extracted, list) and extracted:
                        extracted = extracted[0]
                    title = extracted.get(
                        'page_title', 'N/A') if isinstance(extracted, dict) else 'Parse Error'
                    console.print(
                        f"  [green]✔[/] URL: [link={result['url']}]{result['url']}[/link] | Title: {title}")
                except Exception:
                    console.print(
                        f"  [yellow]![/] URL: [link={result['url']}]{result['url']}[/link] | Failed to parse extracted content")
            elif result.get("success"):
                console.print(
                    f"  [yellow]-[/] URL: [link={result['url']}]{result['url']}[/link] | No content extracted.")
            else:
                console.print(
                    f"  [red]✘[/] URL: [link={result['url']}]{result['url']}[/link] | Crawl failed.")

pass


async def demo_deep_with_llm_extraction(client: httpx.AsyncClient):
    if not os.getenv("OPENAI_API_KEY"):
        console.rule(
            "[bold yellow]Demo 6b: Deep Crawl + LLM Extraction (SKIPPED)[/]", style="yellow")
        console.print(
            "Set an LLM API key (e.g., OPENAI_API_KEY) in your .env file or environment.")
        return

    payload = {
        "urls": [DEEP_CRAWL_BASE_URL],
        "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {
                "cache_mode": "BYPASS",
                "extraction_strategy": {
                    "type": "LLMExtractionStrategy",
                    "params": {
                        "instruction": "What is the main topic of this page based on the H1 and first paragraph? Respond with just the topic.",
                        # Rely on server default LLM config + .llm.env keys
                    }
                },
                "deep_crawl_strategy": {
                    "type": "BFSDeepCrawlStrategy",
                    "params": {
                        "max_depth": 1,
                        "max_pages": 2,
                        "filter_chain": {
                            "type": "FilterChain",
                            "params": {"filters": [
                                {"type": "DomainFilter", "params": {
                                    "allowed_domains": [DEEP_CRAWL_DOMAIN]}},
                                {"type": "ContentTypeFilter", "params": {
                                    "allowed_types": ["text/html"]}}
                            ]}
                        }
                    }
                }
            }
        }
    }
    results = await make_request(client, "/crawl", payload, "Demo 6b: Deep Crawl + LLM Extraction")

    if results:
        console.print("[cyan]LLM Extraction Summary from Deep Crawl:[/]")
        for result in results:
            if result.get("success") and result.get("extracted_content"):
                console.print(
                    f"  [green]✔[/] URL: [link={result['url']}]{result['url']}[/link] | Topic: {result['extracted_content']}")
            elif result.get("success"):
                console.print(
                    f"  [yellow]-[/] URL: [link={result['url']}]{result['url']}[/link] | No content extracted.")
            else:
                console.print(
                    f"  [red]✘[/] URL: [link={result['url']}]{result['url']}[/link] | Crawl failed.")


pass
async def demo_deep_with_proxy(client: httpx.AsyncClient):
    proxy_params_list = load_proxies_from_env()
    if not proxy_params_list:
        console.rule(
            "[bold yellow]Demo 6c: Deep Crawl + Proxies (SKIPPED)[/]", style="yellow")
        console.print("Set the PROXIES environment variable to run this demo.")
        return

    payload = {
        # Use a site likely accessible via proxies
        "urls": [DEEP_CRAWL_BASE_URL],
        "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {
                "cache_mode": "BYPASS",
                "proxy_rotation_strategy": {
                    "type": "RoundRobinProxyStrategy",
                    "params": {
                        # Correctly create the list of {"type": ..., "params": ...} structures, excluding the demo 'ip' key
                        "proxies": [
                            {"type": "ProxyConfig", "params": {
                                k: v for k, v in p.items() if k != 'ip'}}
                            for p in proxy_params_list
                        ]
                    }
                },
                "deep_crawl_strategy": {
                    "type": "BFSDeepCrawlStrategy",
                    "params": {
                        "max_depth": 1,
                        "max_pages": 5,
                    }
                }
            }
        }
    }
    pass
    results = await make_request(client, "/crawl", payload, "Demo 6c: Deep Crawl + Proxies")
    if not results:
        console.print("[red]No results returned from the crawl.[/]")
        return
    console.print("[cyan]Proxy Usage Summary from Deep Crawl:[/]")
    pass
    for result in results:
        if result.get("success") and result.get("metadata"):
            proxy_ip = result["metadata"].get("proxy_ip", "N/A")
            console.print(f"  Proxy IP used: {proxy_ip}")
        elif not result.get("success"):
            console.print(f"  [red]Error: {result['error_message']}[/]")


pass
async def demo_deep_with_ssl(client: httpx.AsyncClient):
    payload = {
        "urls": [DEEP_CRAWL_BASE_URL],
        "browser_config": {"type": "BrowserConfig", "params": {"headless": True}},
        "crawler_config": {
            "type": "CrawlerRunConfig",
            "params": {
                "stream": False,
                "cache_mode": "BYPASS",
                "fetch_ssl_certificate": True,
                "deep_crawl_strategy": {
                    "type": "BFSDeepCrawlStrategy",
                    "params": {
                        "max_depth": 1,
                        "max_pages": 3,
                        "filter_chain": {
                            "type": "FilterChain",
                            "params": {"filters": [{"type": "DomainFilter", "params": {"allowed_domains": [DEEP_CRAWL_DOMAIN]}}]}
                        }
                    }
                }
            }
        }
    }
    results = await make_request(client, "/crawl", payload, "Demo 6d: Deep Crawl + Fetch SSL")

    if results:
        console.print("[cyan]SSL Certificate Summary from Deep Crawl:[/]")
        for result in results:
            if result.get("success") and result.get("ssl_certificate"):
                cert = result["ssl_certificate"]
                issuer_org = cert.get('issuer', {}).get('O', 'N/A')
                valid_from = cert.get('not_before', 'N/A')
                valid_to = cert.get('not_after', 'N/A')
                console.print(
                    f"  [green]✔[/] URL: [link={result['url']}]{result['url']}[/link] | Issuer: {issuer_org} | Valid: {valid_from} - {valid_to}")
            elif result.get("success"):
                console.print(
                    f"  [yellow]-[/] URL: [link={result['url']}]{result['url']}[/link] | SSL cert not fetched or N/A.")
            else:
                console.print(
                    f"  [red]✘[/] URL: [link={result['url']}]{result['url']}[/link] | Crawl failed.")

pass


async def demo_markdown_endpoint(client: httpx.AsyncClient):
    target_url = PYTHON_URL
    payload = {"url": target_url, "f": "fit", "q": None, "c": "0"}

    console.rule("[bold blue]Demo 7a: /md Endpoint[/]", style="blue")
    print_payload(payload)

    try:
        t0 = time.time()
        resp = await client.post("/md", json=payload)
        dt = time.time() - t0
        console.print(
            f"Response Status: [bold {'green' if resp.is_success else 'red'}]{resp.status_code}[/] (took {dt:.2f}s)")
        resp.raise_for_status()
        md = resp.json().get("markdown", "")
        snippet = (md[:500] + "...") if len(md) > 500 else md
        console.print(Panel(snippet, title="Markdown snippet",
                      border_style="cyan", expand=False))
    except Exception as e:
        console.print(f"[bold red]Error hitting /md:[/] {e}")

pass


async def demo_llm_endpoint(client: httpx.AsyncClient):
    page_url = SIMPLE_URL
    question = "What is the title of this page?"

    console.rule("[bold magenta]Demo 7b: /llm Endpoint[/]", style="magenta")
    enc = urllib.parse.quote_plus(page_url, safe="")
    console.print(f"GET /llm/{enc}?q={question}")

    try:
        t0 = time.time()
        resp = await client.get(f"/llm/{enc}", params={"q": question})
        dt = time.time() - t0
        console.print(
            f"Response Status: [bold {'green' if resp.is_success else 'red'}]{resp.status_code}[/] (took {dt:.2f}s)")
        resp.raise_for_status()
        answer = resp.json().get("answer", "")
        console.print(Panel(answer or "No answer returned",
                      title="LLM answer", border_style="magenta", expand=False))
    except Exception as e:
        console.print(f"[bold red]Error hitting /llm:[/] {e}")


pass

async def demo_config_dump_valid(client: httpx.AsyncClient):
    code_snippet = "CrawlerRunConfig(cache_mode='BYPASS', screenshot=True)"
    payload = {"code": code_snippet}

    console.rule("[bold blue]Demo 8a: /config/dump (valid)[/]", style="blue")
    print_payload(payload)

    try:
        t0 = time.time()
        resp = await client.post("/config/dump", json=payload)
        dt = time.time() - t0
        console.print(
            f"Response Status: [bold {'green' if resp.is_success else 'red'}]{resp.status_code}[/] (took {dt:.2f}s)")
        resp.raise_for_status()
        dump_json = resp.json()
        console.print(Panel(Syntax(json.dumps(dump_json, indent=2),
                      "json", theme="monokai"), title="Dump()", border_style="cyan"))
    except Exception as e:
        console.print(f"[bold red]Error in valid /config/dump call:[/] {e}")


async def demo_config_dump_invalid(client: httpx.AsyncClient):
    bad_code = textwrap.dedent("""
        BrowserConfig(headless=True); CrawlerRunConfig()
    """).strip()
    payload = {"code": bad_code}

    console.rule(
        "[bold magenta]Demo 8b: /config/dump (invalid)[/]", style="magenta")
    print_payload(payload)

    try:
        resp = await client.post("/config/dump", json=payload)
        console.print(
            f"Response Status: [bold {'green' if resp.is_success else 'red'}]{resp.status_code}[/]")
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        console.print("[cyan]Expected parse/validation failure captured:[/]")
        try:
            console.print(Panel(Syntax(json.dumps(
                e.response.json(), indent=2), "json", theme="fruity"), title="Error payload"))
        except Exception:
            console.print(e.response.text)
    except Exception as e:
        console.print(
            f"[bold red]Unexpected error during invalid test:[/] {e}")


pass
async def main_demo():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=300.0) as client:
        if not await check_server_health(client):
            return

        pass
        pass
        pass
        pass

        pass
        pass
        pass

        pass
        pass
        pass
        pass
        pass

        pass
        pass

        pass
        pass

        pass
        pass
        pass
        pass
        pass

        pass
        await demo_markdown_endpoint(client)
        await demo_llm_endpoint(client)

        pass
        await demo_config_dump_valid(client)
        await demo_config_dump_invalid(client)

        console.rule("[bold green]Demo Complete[/]", style="green")


if __name__ == "__main__":
    try:
        asyncio.run(main_demo())
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted by user.[/]")
    except Exception as e:
        console.print(
            f"\n[bold red]An error occurred during demo execution:[/]")
        console.print_exception(show_locals=False)
