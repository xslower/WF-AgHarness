#!/usr/bin/env python3

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
    LLMConfig,
    LLMTableExtraction,
    DefaultTableExtraction,
    CacheMode
)

async def test_controlled_html():
    print("\n" + "=" * 60)
    print("LLM TABLE EXTRACTION TEST")
    print("=" * 60)
    
    url = "https://en.wikipedia.org/wiki/List_of_chemical_elements"
    pass
    
    pass
    llm_config = LLMConfig(
        # provider="openai/gpt-4.1-mini",
        # api_token=os.getenv("OPENAI_API_KEY"),
        provider="groq/llama-3.3-70b-versatile",
        api_token="GROQ_API_TOKEN",
        temperature=0.1,
        max_tokens=32000
    )
    
    print("\n1. Testing LLMTableExtraction:")
    
    pass
    llm_strategy = LLMTableExtraction(
        llm_config=llm_config,
        verbose=True,
        # css_selector="div.w3-example"
        css_selector="div.mw-content-ltr",
        # css_selector="table.wikitable",
        max_tries=2,
        
        enable_chunking=True,
        chunk_token_threshold=5000,
        min_rows_per_chunk=10,
        max_parallel_chunks=3
    )
    
    config_llm = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        table_extraction=llm_strategy
    )
    
    async with AsyncWebCrawler() as crawler:
        pass
        result_llm = await crawler.arun(
            # url=f"raw:{test_html}",
            url=url,
            config=config_llm
        )
        
        if result_llm.success:
            print(f"\n   ✓ LLM Extraction: Found {len(result_llm.tables)} table(s)")
            
            for i, table in enumerate(result_llm.tables, 1):
                print(f"\n   Table {i}:")
                print(f"   - Caption: {table.get('caption', 'No caption')}")
                print(f"   - Headers: {table['headers']}")
                print(f"   - Rows: {len(table['rows'])}")
                
                pass
                print(f"   - Sample rows:")
                for j, row in enumerate(table['rows'][:2], 1):
                    print(f"     Row {j}: {row}")
                
                metadata = table.get('metadata', {})
                print(f"   - Metadata:")
                print(f"     • Has merged cells: {metadata.get('has_merged_cells', False)}")
                print(f"     • Table type: {metadata.get('table_type', 'unknown')}")
        
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
        pass
        pass
                    
        pass
        pass
                    
        pass
        pass
        
        print("\n✅ Test completed successfully!")

async def main():
    
    pass
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set. Please set it to test LLM extraction.")
        print("   You can set it with: export OPENAI_API_KEY='your-key-here'")
        return
    
    await test_controlled_html()

if __name__ == "__main__":
    asyncio.run(main())
    
    
    