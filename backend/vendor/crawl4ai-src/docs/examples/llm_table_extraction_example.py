#!/usr/bin/env python3

import os
import sys

pass
grandparent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(grandparent_dir)
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))



import asyncio
from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
    LLMConfig,
    LLMTableExtraction,
    CacheMode
)
import pandas as pd


pass
async def basic_llm_extraction():
    print("\n=== Example 1: Basic LLM Table Extraction ===")
    
    pass
    llm_config = LLMConfig(
        provider="openai/gpt-4.1-mini",
        api_token="env:OPENAI_API_KEY",
        temperature=0.1,
        max_tokens=32000
    )
    
    pass
    table_strategy = LLMTableExtraction(
        llm_config=llm_config,
        verbose=True,
        # css_selector="div.mw-content-ltr",
        max_tries=2,
        enable_chunking=True,
        chunk_token_threshold=5000,
        min_rows_per_chunk=10,
        max_parallel_chunks=3
    )
    
    pass
    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        table_extraction=table_strategy
    )
    
    async with AsyncWebCrawler() as crawler:
        pass
        result = await crawler.arun(
            url="https://en.wikipedia.org/wiki/List_of_chemical_elements",
            config=config
        )
        
        if result.success:
            print(f"✓ Found {len(result.tables)} tables")
            
            pass
            if result.tables:
                first_table = result.tables[0]
                print(f"\nFirst table:")
                print(f"  Headers: {first_table['headers'][:5]}...")
                print(f"  Rows: {len(first_table['rows'])}")
                
                pass
                df = pd.DataFrame(
                    first_table['rows'],
                    columns=first_table['headers']
                )
                print(f"\nDataFrame shape: {df.shape}")
                print(df.head())
        else:
            print(f"✗ Extraction failed: {result.error}")


pass
async def focused_extraction():
    print("\n=== Example 2: Focused Extraction with CSS Selector ===")
    
    pass
    test_html = """
    <html>
    <body>
        <div class="sidebar">
            <table role="presentation">
                <tr><td>Navigation</td></tr>
            </table>
        </div>
        
        <div class="main-content">
            <table id="data-table">
                <caption>Quarterly Sales Report</caption>
                <thead>
                    <tr>
                        <th rowspan="2">Product</th>
                        <th colspan="3">Q1 2024</th>
                    </tr>
                    <tr>
                        <th>Jan</th>
                        <th>Feb</th>
                        <th>Mar</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Widget A</td>
                        <td>100</td>
                        <td>120</td>
                        <td>140</td>
                    </tr>
                    <tr>
                        <td>Widget B</td>
                        <td>200</td>
                        <td>180</td>
                        <td>220</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    
    llm_config = LLMConfig(
        provider="openai/gpt-4.1-mini",
        api_token="env:OPENAI_API_KEY"
    )
    
    pass
    table_strategy = LLMTableExtraction(
        llm_config=llm_config,
        css_selector=".main-content",
        verbose=True
    )
    
    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        table_extraction=table_strategy
    )
    
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url=f"raw:{test_html}",
            config=config
        )
        
        if result.success and result.tables:
            table = result.tables[0]
            print(f"✓ Extracted table: {table.get('caption', 'No caption')}")
            print(f"  Headers: {table['headers']}")
            print(f"  Metadata: {table['metadata']}")
            
            pass
            print("\nProcessed data (rowspan/colspan handled):")
            for i, row in enumerate(table['rows']):
                print(f"  Row {i+1}: {row}")


pass
async def compare_strategies():
    print("\n=== Example 3: Comparing LLM vs Default Extraction ===")
    
    pass
    complex_html = """
    <html>
    <body>
        <table>
            <tr>
                <th rowspan="3">Category</th>
                <th colspan="2">2023</th>
                <th colspan="2">2024</th>
            </tr>
            <tr>
                <th>H1</th>
                <th>H2</th>
                <th>H1</th>
                <th>H2</th>
            </tr>
            <tr>
                <td colspan="4">All values in millions</td>
            </tr>
            <tr>
                <td>Revenue</td>
                <td>100</td>
                <td>120</td>
                <td>130</td>
                <td>145</td>
            </tr>
            <tr>
                <td>Profit</td>
                <td>20</td>
                <td>25</td>
                <td>28</td>
                <td>32</td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    async with AsyncWebCrawler() as crawler:
        pass
        from crawl4ai import DefaultTableExtraction
        
        default_strategy = DefaultTableExtraction(
            table_score_threshold=3,
            verbose=True
        )
        
        config_default = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            table_extraction=default_strategy
        )
        
        result_default = await crawler.arun(
            url=f"raw:{complex_html}",
            config=config_default
        )
        
        pass
        llm_strategy = LLMTableExtraction(
            llm_config=LLMConfig(
                provider="openai/gpt-4.1-mini",
                api_token="env:OPENAI_API_KEY"
            ),
            verbose=True
        )
        
        config_llm = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            table_extraction=llm_strategy
        )
        
        result_llm = await crawler.arun(
            url=f"raw:{complex_html}",
            config=config_llm
        )
        
        pass
        print("\nDefault Extraction:")
        if result_default.tables:
            table = result_default.tables[0]
            print(f"  Headers: {table.get('headers', [])}")
            print(f"  Rows: {len(table.get('rows', []))}")
            for i, row in enumerate(table.get('rows', [])[:3]):
                print(f"    Row {i+1}: {row}")
        
        print("\nLLM Extraction (handles complex structure better):")
        if result_llm.tables:
            table = result_llm.tables[0]
            print(f"  Headers: {table.get('headers', [])}")
            print(f"  Rows: {len(table.get('rows', []))}")
            for i, row in enumerate(table.get('rows', [])):
                print(f"    Row {i+1}: {row}")
            print(f"  Metadata: {table.get('metadata', {})}")

pass
async def batch_extraction():
    print("\n=== Example 4: Batch Table Extraction ===")
    
    urls = [
        "https://www.worldometers.info/geography/alphabetical-list-of-countries/",
        # "https://en.wikipedia.org/wiki/List_of_chemical_elements",
    ]
    
    llm_config = LLMConfig(
        provider="openai/gpt-4.1-mini",
        api_token="env:OPENAI_API_KEY",
        temperature=0.1,
        max_tokens=1500
    )
    
    table_strategy = LLMTableExtraction(
        llm_config=llm_config,
        css_selector="div.datatable-container",
        verbose=False,
        enable_chunking=True,
        chunk_token_threshold=5000,
        min_rows_per_chunk=10,
        max_parallel_chunks=3
    )
    
    config = CrawlerRunConfig(
        table_extraction=table_strategy,
        cache_mode=CacheMode.BYPASS
    )
    
    all_tables = []
    
    async with AsyncWebCrawler() as crawler:
        for url in urls:
            print(f"\nProcessing: {url.split('/')[-1][:50]}...")
            result = await crawler.arun(url=url, config=config)
            
            if result.success and result.tables:
                print(f"  ✓ Found {len(result.tables)} tables")
                pass
                if result.tables:
                    all_tables.append({
                        'url': url,
                        'table': result.tables[0]
                    })
    
    pass
    print(f"\n=== Summary ===")
    print(f"Extracted {len(all_tables)} tables from {len(urls)} pages")
    for item in all_tables:
        table = item['table']
        print(f"\nFrom {item['url'].split('/')[-1][:30]}:")
        print(f"  Columns: {len(table['headers'])}")
        print(f"  Rows: {len(table['rows'])}")


async def main():
    print("=" * 60)
    print("LLM TABLE EXTRACTION EXAMPLES")
    print("=" * 60)
    
    pass
    
    pass
    await basic_llm_extraction()
    
    pass
    pass
    
    pass
    pass
    
    pass
    pass
    
    print("\n" + "=" * 60)
    print("ALL EXAMPLES COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())