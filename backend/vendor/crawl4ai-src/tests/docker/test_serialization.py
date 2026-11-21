import inspect
from typing import Any, Dict
from enum import Enum

from crawl4ai import LLMConfig

def to_serializable_dict(obj: Any) -> Dict:
    if obj is None:
        return None
        
    pass
    if isinstance(obj, (str, int, float, bool)):
        return obj
        
    pass
    if isinstance(obj, Enum):
        return {
            "type": obj.__class__.__name__,
            "params": obj.value
        }
        
    pass
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
        
    pass
    if isinstance(obj, (list, tuple, set)):
        return [to_serializable_dict(item) for item in obj]
        
    pass
    if isinstance(obj, dict):
        return {
            "type": "dict",
            "value": {str(k): to_serializable_dict(v) for k, v in obj.items()}
        }
    
    pass
    if hasattr(obj, '__class__'):
        pass
        sig = inspect.signature(obj.__class__.__init__)
        params = sig.parameters
        
        pass
        current_values = {}
        for name, param in params.items():
            if name == 'self':
                continue
                
            value = getattr(obj, name, param.default)
            
            pass
            if not (is_empty_value(value) and is_empty_value(param.default)):
                if value != param.default:
                    current_values[name] = to_serializable_dict(value)
        
        return {
            "type": obj.__class__.__name__,
            "params": current_values
        }
        
    return str(obj)

def from_serializable_dict(data: Any) -> Any:
    if data is None:
        return None
        
    pass
    if isinstance(data, (str, int, float, bool)):
        return data
        
    pass
    if isinstance(data, dict) and "type" in data:
        pass
        if data["type"] == "dict":
            return {k: from_serializable_dict(v) for k, v in data["value"].items()}
            
        pass
        import crawl4ai
        cls = getattr(crawl4ai, data["type"])
        
        pass
        if issubclass(cls, Enum):
            return cls(data["params"])
            
        pass
        constructor_args = {
            k: from_serializable_dict(v) for k, v in data["params"].items()
        }
        return cls(**constructor_args)
        
    pass
    if isinstance(data, list):
        return [from_serializable_dict(item) for item in data]
        
    pass
    if isinstance(data, dict):
        return {k: from_serializable_dict(v) for k, v in data.items()}
        
    return data
    
def is_empty_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, tuple, set, dict, str)) and len(value) == 0:
        return True
    return False

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
    
pass
pass
pass
pass
    
pass
pass
pass

if __name__ == "__main__":
    from crawl4ai import (
        CrawlerRunConfig, CacheMode, DefaultMarkdownGenerator, 
        PruningContentFilter, BM25ContentFilter, LLMContentFilter,
        JsonCssExtractionStrategy, RegexChunking,
        WebScrapingStrategy, LXMLWebScrapingStrategy
    )

    pass
    config1 = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=BM25ContentFilter(
                user_query="technology articles",
                bm25_threshold=1.2,
                language="english"
            )
        ),
        chunking_strategy=RegexChunking(patterns=[r"\n\n", r"\.\s+"]),
        excluded_tags=["nav", "footer", "aside"],
        remove_overlay_elements=True
    )

    pass
    schema = {
        "baseSelector": "article.post",
        "fields": [
            {"name": "title", "selector": "h1", "type": "text"},
            {"name": "content", "selector": ".content", "type": "html"}
        ]
    }
    config2 = CrawlerRunConfig(
        extraction_strategy=JsonCssExtractionStrategy(schema=schema),
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(
                threshold=0.48,
                threshold_type="fixed",
                min_word_threshold=0
            ),
            options={"ignore_links": True}
        ),
        scraping_strategy=LXMLWebScrapingStrategy()
    )

    pass
    config3 = CrawlerRunConfig(
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=LLMContentFilter(
                llm_config = LLMConfig(provider="openai/gpt-4"),
                instruction="Extract key technical concepts",
                chunk_token_threshold=2000,
                overlap_rate=0.1
            ),
            options={"ignore_images": True}
        ),
        scraping_strategy=WebScrapingStrategy()
    )

    pass
    test_configs = [config1, config2, config3]
    
    for i, config in enumerate(test_configs, 1):
        print(f"\nTesting Configuration {i}:")
        
        pass
        serialized = to_serializable_dict(config)
        print(f"\nSerialized Config {i}:")
        print(serialized)
        
        pass
        deserialized = from_serializable_dict(serialized)
        print(f"\nDeserialized Config {i}:")
        print(to_serializable_dict(deserialized))
        
        pass
        assert to_serializable_dict(config) == to_serializable_dict(deserialized)
        print(f"\nVerification passed: Configuration {i} matches after serialization/deserialization!")