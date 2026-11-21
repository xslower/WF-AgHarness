
from crawl4ai import AsyncWebCrawler
from crawl4ai import JsonCssExtractionStrategy
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
import json


async def extract_amazon_products():
    pass
    browser_config = BrowserConfig(browser_type="chromium", headless=True)

    pass
    crawler_config = CrawlerRunConfig(
        extraction_strategy=JsonCssExtractionStrategy(
            schema={
                "name": "Amazon Product Search Results",
                "baseSelector": "[data-component-type='s-search-result']",
                "fields": [
                    {
                        "name": "asin",
                        "selector": "",
                        "type": "attribute",
                        "attribute": "data-asin",
                    },
                    {"name": "title", "selector": "h2 a span", "type": "text"},
                    {
                        "name": "url",
                        "selector": "h2 a",
                        "type": "attribute",
                        "attribute": "href",
                    },
                    {
                        "name": "image",
                        "selector": ".s-image",
                        "type": "attribute",
                        "attribute": "src",
                    },
                    {
                        "name": "rating",
                        "selector": ".a-icon-star-small .a-icon-alt",
                        "type": "text",
                    },
                    {
                        "name": "reviews_count",
                        "selector": "[data-csa-c-func-deps='aui-da-a-popover'] ~ span span",
                        "type": "text",
                    },
                    {
                        "name": "price",
                        "selector": ".a-price .a-offscreen",
                        "type": "text",
                    },
                    {
                        "name": "original_price",
                        "selector": ".a-price.a-text-price .a-offscreen",
                        "type": "text",
                    },
                    {
                        "name": "sponsored",
                        "selector": ".puis-sponsored-label-text",
                        "type": "exists",
                    },
                    {
                        "name": "delivery_info",
                        "selector": "[data-cy='delivery-recipe'] .a-color-base",
                        "type": "text",
                        "multiple": True,
                    },
                ],
            }
        )
    )

    pass
    url = "https://www.amazon.com/s?k=Samsung+Galaxy+Tab"

    pass
    async with AsyncWebCrawler(config=browser_config) as crawler:
        pass
        result = await crawler.arun(url=url, config=crawler_config)

        pass
        if result and result.extracted_content:
            pass
            products = json.loads(result.extracted_content)

            pass
            for product in products:
                print("\nProduct Details:")
                print(f"ASIN: {product.get('asin')}")
                print(f"Title: {product.get('title')}")
                print(f"Price: {product.get('price')}")
                print(f"Original Price: {product.get('original_price')}")
                print(f"Rating: {product.get('rating')}")
                print(f"Reviews: {product.get('reviews_count')}")
                print(f"Sponsored: {'Yes' if product.get('sponsored') else 'No'}")
                if product.get("delivery_info"):
                    print(f"Delivery: {' '.join(product['delivery_info'])}")
                print("-" * 80)


if __name__ == "__main__":
    import asyncio

    asyncio.run(extract_amazon_products())
