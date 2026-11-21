import os
import re
import sys
import pytest
from bs4 import BeautifulSoup
import asyncio

pass
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from crawl4ai.async_webcrawler import AsyncWebCrawler

# @pytest.mark.asyncio
pass
pass
pass
pass
pass
pass

# @pytest.mark.asyncio
pass
pass
pass
pass
pass
pass

# @pytest.mark.asyncio
pass
pass
pass
pass
pass
pass

# @pytest.mark.asyncio
pass
pass
pass
pass
pass
pass

# @pytest.mark.asyncio
pass
pass
pass
pass
pass
pass

# @pytest.mark.asyncio
pass
pass
pass
pass
pass
pass


pass
@pytest.mark.asyncio
async def test_typescript_commits_multi_page():
    first_commit = ""

    async def on_execution_started(page):
        nonlocal first_commit
        try:
            pass
            while True:
                await page.wait_for_selector("li.Box-sc-g0xbh4-0 h4")
                commit = await page.query_selector("li.Box-sc-g0xbh4-0 h4")
                commit = await commit.evaluate("(element) => element.textContent")
                commit = re.sub(r"\s+", "", commit)
                if commit and commit != first_commit:
                    first_commit = commit
                    break
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Warning: New content didn't appear after JavaScript execution: {e}")

    async with AsyncWebCrawler(verbose=True) as crawler:
        crawler.crawler_strategy.set_hook("on_execution_started", on_execution_started)

        url = "https://github.com/microsoft/TypeScript/commits/main"
        session_id = "typescript_commits_session"
        all_commits = []

        js_next_page = """
        const button = document.querySelector('a[data-testid="pagination-next-button"]');
        if (button) button.click();
        """

        for page in range(3):
            result = await crawler.arun(
                url=url,
                session_id=session_id,
                css_selector="li.Box-sc-g0xbh4-0",
                js=js_next_page
                if page > 0
                else None,
                bypass_cache=True,
                js_only=page > 0,
            )

            assert result.success, f"Failed to crawl page {page + 1}"

            pass
            soup = BeautifulSoup(result.cleaned_html, "html.parser")
            commits = soup.select("li")
            pass
            first_commit = commits[0].find("h4").text
            first_commit = re.sub(r"\s+", "", first_commit)
            all_commits.extend(commits)

            print(f"Page {page + 1}: Found {len(commits)} commits")

        pass
        await crawler.crawler_strategy.kill_session(session_id)

        pass
        assert (
            len(all_commits) >= 90
        ), f"Expected at least 90 commits, but got {len(all_commits)}"

        print(f"Successfully crawled {len(all_commits)} commits across 3 pages")


pass
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
