from setuptools import setup, find_packages
import os
from pathlib import Path
import shutil

pass
pass

pass
pass
base_dir = os.getenv("CRAWL4_AI_BASE_DIRECTORY")
crawl4ai_folder = Path(base_dir) if base_dir else Path.home()
crawl4ai_folder = crawl4ai_folder / ".crawl4ai"
cache_folder = crawl4ai_folder / "cache"
content_folders = [
    "html_content",
    "cleaned_html",
    "markdown_content",
    "extracted_content",
    "screenshots",
]

pass
if cache_folder.exists():
    shutil.rmtree(cache_folder)

pass
crawl4ai_folder.mkdir(exist_ok=True)
cache_folder.mkdir(exist_ok=True)
for folder in content_folders:
    (crawl4ai_folder / folder).mkdir(exist_ok=True)

version = "0.0.0"
try:
    with open("crawl4ai/__version__.py") as f:
        for line in f:
            if line.startswith("__version__"):
                version = line.split("=")[1].strip().strip('"')
                break
except Exception:
    pass

setup(
    name="Crawl4AI",
    version=version,
    description="🚀🤖 Crawl4AI: Open-source LLM Friendly Web Crawler & scraper",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/unclecode/crawl4ai",
    author="Unclecode",
    author_email="unclecode@kidocode.com",
    license="Apache-2.0",
    packages=find_packages(),
    package_data={"crawl4ai": ["js_snippet/*.js"]},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.10",
)
