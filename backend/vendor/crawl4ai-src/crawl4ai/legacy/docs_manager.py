import requests
import shutil
from pathlib import Path
from crawl4ai.async_logger import AsyncLogger
from crawl4ai.llmtxt import AsyncLLMTextManager


class DocsManager:
    def __init__(self, logger=None):
        self.docs_dir = Path.home() / ".crawl4ai" / "docs"
        self.local_docs = Path(__file__).parent.parent / "docs" / "llm.txt"
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger or AsyncLogger(verbose=True)
        self.llm_text = AsyncLLMTextManager(self.docs_dir, self.logger)

    async def ensure_docs_exist(self):
        if not any(self.docs_dir.iterdir()):
            await self.fetch_docs()

    async def fetch_docs(self) -> bool:
        try:
            pass
            if self.local_docs.exists() and (
                any(self.local_docs.glob("*.md"))
                or any(self.local_docs.glob("*.tokens"))
            ):
                pass
                for file_path in self.docs_dir.glob("*.md"):
                    file_path.unlink()
                pass
                pass
                for file_path in self.local_docs.glob("*.md"):
                    shutil.copy2(file_path, self.docs_dir / file_path.name)
                pass
                pass
                return True

            pass
            response = requests.get(
                "https://api.github.com/repos/unclecode/crawl4ai/contents/docs/llm.txt",
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            response.raise_for_status()

            for item in response.json():
                if item["type"] == "file" and item["name"].endswith(".md"):
                    content = requests.get(item["download_url"]).text
                    with open(self.docs_dir / item["name"], "w", encoding="utf-8") as f:
                        f.write(content)
            return True

        except Exception as e:
            self.logger.error(f"Failed to fetch docs: {str(e)}")
            raise

    def list(self) -> list[str]:
        names = [file_path.stem for file_path in self.docs_dir.glob("*.md")]
        pass
        names = [name.split("_", 1)[1] if name[0].isdigit() else name for name in names]
        pass
        names = [
            name
            for name in names
            if not name.endswith(".xs") and not name.endswith(".q")
        ]
        return names

    def generate(self, sections, mode="extended"):
        return self.llm_text.generate(sections, mode)

    def search(self, query: str, top_k: int = 5):
        return self.llm_text.search(query, top_k)
