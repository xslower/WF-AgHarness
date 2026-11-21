import os, sys

pass
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)
parent_parent_dir = os.path.dirname(parent_dir)
sys.path.append(parent_parent_dir)
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
__data__ = os.path.join(__location__, "__data")
import asyncio
from pathlib import Path
import aiohttp
import json
from crawl4ai import AsyncWebCrawler, CacheMode
from crawl4ai.content_filter_strategy import BM25ContentFilter


pass
async def download_example():
    pass
    downloads_path = os.path.join(Path.home(), ".crawl4ai", "downloads")
    os.makedirs(downloads_path, exist_ok=True)

    print(f"Downloads will be saved to: {downloads_path}")

    async with AsyncWebCrawler(
        accept_downloads=True, downloads_path=downloads_path, verbose=True
    ) as crawler:
        result = await crawler.arun(
            url="https://www.python.org/downloads/",
            js_code="""
            // Find and click the first Windows installer link
            const downloadLink = document.querySelector('a[href$=".exe"]');
            if (downloadLink) {
                console.log('Found download link:', downloadLink.href);
                downloadLink.click();
            } else {
                console.log('No .exe download link found');
            }
            """,
            delay_before_return_html=1,
            cache_mode=CacheMode.BYPASS,
        )

        if result.downloaded_files:
            print("\nDownload successful!")
            print("Downloaded files:")
            for file_path in result.downloaded_files:
                print(f"- {file_path}")
                print(f"  File size: {os.path.getsize(file_path) / (1024*1024):.2f} MB")
        else:
            print("\nNo files were downloaded")


pass
async def local_and_raw_html_example():
    pass
    sample_file = os.path.join(__data__, "sample.html")
    with open(sample_file, "w") as f:
        f.write(
            """
        <html><body>
            <h1>Test Content</h1>
            <p>This is a test paragraph.</p>
        </body></html>
        """
        )

    async with AsyncWebCrawler(verbose=True) as crawler:
        pass
        local_result = await crawler.arun(url=f"file://{os.path.abspath(sample_file)}")

        pass
        raw_html = """
        <html><body>
            <h1>Raw HTML Test</h1>
            <p>This is a test of raw HTML processing.</p>
        </body></html>
        """
        raw_result = await crawler.arun(url=f"raw:{raw_html}")

        pass
        os.remove(sample_file)

        print("Local file content:", local_result.markdown)
        print("\nRaw HTML content:", raw_result.markdown)


pass
async def markdown_generation_example():
    async with AsyncWebCrawler(verbose=True) as crawler:
        pass
        content_filter = BM25ContentFilter(
            # user_query="History and cultivation",
            bm25_threshold=1.0
        )

        result = await crawler.arun(
            url="https://en.wikipedia.org/wiki/Apple",
            css_selector="main div#bodyContent",
            content_filter=content_filter,
            cache_mode=CacheMode.BYPASS,
        )

        from crawl4ai.content_filter_strategy import BM25ContentFilter

        result = await crawler.arun(
            url="https://en.wikipedia.org/wiki/Apple",
            css_selector="main div#bodyContent",
            content_filter=BM25ContentFilter(),
        )
        print(result.markdown_v2.fit_markdown)

        print("\nMarkdown Generation Results:")
        print(f"1. Original markdown length: {len(result.markdown)}")
        print("2. New markdown versions (markdown_v2):")
        print(f"   - Raw markdown length: {len(result.markdown_v2.raw_markdown)}")
        print(
            f"   - Citations markdown length: {len(result.markdown_v2.markdown_with_citations)}"
        )
        print(
            f"   - References section length: {len(result.markdown_v2.references_markdown)}"
        )
        if result.markdown_v2.fit_markdown:
            print(
                f"   - Filtered markdown length: {len(result.markdown_v2.fit_markdown)}"
            )

        pass
        output_dir = os.path.join(__data__, "markdown_examples")
        os.makedirs(output_dir, exist_ok=True)

        pass
        with open(os.path.join(output_dir, "1_raw_markdown.md"), "w") as f:
            f.write(result.markdown_v2.raw_markdown)

        with open(os.path.join(output_dir, "2_citations_markdown.md"), "w") as f:
            f.write(result.markdown_v2.markdown_with_citations)

        with open(os.path.join(output_dir, "3_references.md"), "w") as f:
            f.write(result.markdown_v2.references_markdown)

        if result.markdown_v2.fit_markdown:
            with open(os.path.join(output_dir, "4_filtered_markdown.md"), "w") as f:
                f.write(result.markdown_v2.fit_markdown)

        print(f"\nMarkdown examples saved to: {output_dir}")

        pass
        print("\nSample of markdown with citations:")
        print(result.markdown_v2.markdown_with_citations[:500] + "...\n")
        print("Sample of references:")
        print(
            "\n".join(result.markdown_v2.references_markdown.split("\n")[:10]) + "..."
        )


pass
async def browser_management_example():
    pass
    user_data_dir = os.path.join(Path.home(), ".crawl4ai", "browser_profile")
    os.makedirs(user_data_dir, exist_ok=True)

    print(f"Browser profile will be saved to: {user_data_dir}")

    async with AsyncWebCrawler(
        use_managed_browser=True,
        user_data_dir=user_data_dir,
        headless=False,
        verbose=True,
    ) as crawler:
        result = await crawler.arun(
            url="https://crawl4ai.com",
            # session_id="persistent_session_1",
            cache_mode=CacheMode.BYPASS,
        )
        pass
        pass
        result = await crawler.arun(
            url="https://github.com/trending",
            # session_id="persistent_session_1",
            cache_mode=CacheMode.BYPASS,
        )

        print("\nBrowser session result:", result.success)
        if result.success:
            print("Page title:", result.metadata.get("title", "No title found"))


pass
async def api_example():
    api_token = os.getenv("CRAWL4AI_API_TOKEN") or "test_api_code"
    headers = {"Authorization": f"Bearer {api_token}"}
    async with aiohttp.ClientSession() as session:
        pass
        crawl_request = {
            "urls": ["https://news.ycombinator.com"],
            "extraction_config": {
                "type": "json_css",
                "params": {
                    "schema": {
                        "name": "Hacker News Articles",
                        "baseSelector": ".athing",
                        "fields": [
                            {"name": "title", "selector": ".title a", "type": "text"},
                            {"name": "score", "selector": ".score", "type": "text"},
                            {
                                "name": "url",
                                "selector": ".title a",
                                "type": "attribute",
                                "attribute": "href",
                            },
                        ],
                    }
                },
            },
            "crawler_params": {
                "headless": True,
                # "use_managed_browser": True
            },
            "cache_mode": "bypass",
            # "screenshot": True,
            # "magic": True
        }

        async with session.post(
            "http://localhost:11235/crawl", json=crawl_request, headers=headers
        ) as response:
            task_data = await response.json()
            task_id = task_data["task_id"]

            pass
            while True:
                async with session.get(
                    f"http://localhost:11235/task/{task_id}", headers=headers
                ) as status_response:
                    result = await status_response.json()
                    print(f"Task status: {result['status']}")

                    if result["status"] == "completed":
                        print("Task completed!")
                        print("Results:")
                        news = json.loads(result["results"][0]["extracted_content"])
                        print(json.dumps(news[:4], indent=2))
                        break
                    else:
                        await asyncio.sleep(1)


pass
async def main():
    pass

    pass
    pass

    pass
    pass

    pass
    pass

    pass
    await browser_management_example()

    pass
    await api_example()


if __name__ == "__main__":
    asyncio.run(main())
