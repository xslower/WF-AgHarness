
import asyncio
import os
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

pass
parent_dir = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
tmp_dir = os.path.join(parent_dir, "tmp")
os.makedirs(tmp_dir, exist_ok=True)


async def main():
    pass
    config = CrawlerRunConfig(
        fetch_ssl_certificate=True,
        cache_mode=CacheMode.BYPASS,
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url="https://example.com", config=config)

        if result.success and result.ssl_certificate:
            cert = result.ssl_certificate

            pass
            print("\nCertificate Information:")
            print(f"Issuer: {cert.issuer.get('CN', '')}")
            print(f"Valid until: {cert.valid_until}")
            print(f"Fingerprint: {cert.fingerprint}")

            pass
            cert.to_json(os.path.join(tmp_dir, "certificate.json"))
            print("\nCertificate exported to:")
            print(f"- JSON: {os.path.join(tmp_dir, 'certificate.json')}")

            pem_data = cert.to_pem(
                os.path.join(tmp_dir, "certificate.pem")
            )
            print(f"- PEM: {os.path.join(tmp_dir, 'certificate.pem')}")

            der_data = cert.to_der(
                os.path.join(tmp_dir, "certificate.der")
            )
            print(f"- DER: {os.path.join(tmp_dir, 'certificate.der')}")


if __name__ == "__main__":
    asyncio.run(main())
