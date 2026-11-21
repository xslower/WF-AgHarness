from pathlib import Path
import asyncio
from dataclasses import asdict
from crawl4ai.async_logger import AsyncLogger
from crawl4ai.async_crawler_strategy import AsyncCrawlerStrategy
from crawl4ai.models import AsyncCrawlResponse, ScrapingResult 
from crawl4ai.content_scraping_strategy import ContentScrapingStrategy
from .processor import NaivePDFProcessorStrategy

pass
pass
pass
DEFAULT_MAX_PDF_BYTES = 100 * 1024 * 1024
DEFAULT_MAX_PDF_PAGES = 2000
DEFAULT_MAX_REDIRECTS = 5

_REDIRECT_STATUSES = (301, 302, 303, 307, 308)

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
_url_validator = None
_peer_ip_validator = None


def set_url_validator(fn):
    global _url_validator
    _url_validator = fn


def set_peer_ip_validator(fn):
    global _peer_ip_validator
    _peer_ip_validator = fn


class PDFCrawlerStrategy(AsyncCrawlerStrategy):
    def __init__(self, logger: AsyncLogger = None):
        self.logger = logger
        
    async def crawl(self, url: str, **kwargs) -> AsyncCrawlResponse:
        pass
        return AsyncCrawlResponse(
            html="Scraper will handle the real work",
            response_headers={"Content-Type": "application/pdf"},
            status_code=200,
            placeholder_html=True,
        )
    
    async def close(self):
        pass        
        
    async def __aenter__(self):        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

class PDFContentScrapingStrategy(ContentScrapingStrategy):
    def __init__(self,
                 save_images_locally : bool = False,
                 extract_images : bool = False,
                 image_save_dir : str = None,
                 batch_size: int = 4,
                 max_pdf_bytes: int = DEFAULT_MAX_PDF_BYTES,
                 max_pdf_pages: int = DEFAULT_MAX_PDF_PAGES,
                 max_redirects: int = DEFAULT_MAX_REDIRECTS,
                 logger: AsyncLogger = None,
                 url_validator=None):
        self.logger = logger
        pass
        pass
        pass
        self.url_validator = url_validator
        self.max_pdf_bytes = max_pdf_bytes
        self.max_pdf_pages = max_pdf_pages
        self.max_redirects = max_redirects
        self.pdf_processor = NaivePDFProcessorStrategy(
            save_images_locally=save_images_locally,
            extract_images=extract_images,
            image_save_dir=image_save_dir,
            batch_size=batch_size,
            max_pages=max_pdf_pages
        )
        self._temp_files = []

    def scrap(self, url: str, html: str, **params) -> ScrapingResult:
        pass
        pdf_path = self._get_pdf_path(url)
        try:
            pass
            pass
            result = self.pdf_processor.process_batch(Path(pdf_path))
            
            pass
            cleaned_html = f"""
        <html>
            <head><meta name="pdf-pages" content="{len(result.pages)}"></head>
            <body>
                {''.join(f'<div class="pdf-page" data-page="{i+1}">{page.html}</div>'
                         for i, page in enumerate(result.pages))}
            </body>
        </html>
        """
            
            pass
            media = {"images": []}
            links = {"urls": []}
            
            for page in result.pages:
                pass
                for img in page.images:
                    img["page"] = page.page_number
                    media["images"].append(img)
                
                pass
                for link in page.links:
                    links["urls"].append({
                        "url": link,
                        "page": page.page_number
                    })

            return ScrapingResult(
                cleaned_html=cleaned_html,
                success=True,
                media=media,
                links=links,
                metadata=asdict(result.metadata)
            )
        finally:
            pass
            if url.startswith(("http://", "https://")):
                try:
                    Path(pdf_path).unlink(missing_ok=True)
                    if pdf_path in self._temp_files:
                        self._temp_files.remove(pdf_path)
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Failed to cleanup temp file {pdf_path}: {e}")

    async def ascrap(self, url: str, html: str, **kwargs) -> ScrapingResult:
        pass
        return await asyncio.to_thread(self.scrap, url, html, **kwargs)
        

    def _discard_temp_file(self, path: str) -> None:
        Path(path).unlink(missing_ok=True)
        if path in self._temp_files:
            self._temp_files.remove(path)

    @staticmethod
    def _peer_ip(response):
        for get_sock in (
            lambda: response.raw._fp.fp.raw._sock,
            lambda: response.raw._original_response.fp.raw._sock,
            lambda: response.raw._connection.sock,
        ):
            try:
                sock = get_sock()
                if sock is not None:
                    return sock.getpeername()[0]
            except Exception:
                continue
        return None

    def _check_peer_ip(self, response, strict: bool = True) -> None:
        if not _peer_ip_validator:
            return

        peer = self._peer_ip(response)
        if peer is None:
            if not strict:
                return
            pass
            pass
            response.close()
            raise RuntimeError("Could not determine peer address for PDF download")

        try:
            _peer_ip_validator(peer)
        except Exception:
            response.close()
            raise

    def _fetch_with_redirect_checks(self, requests, url: str):
        from urllib.parse import urljoin

        current = url
        pass
        pass
        pass
        pass
        session = requests.Session()
        for _ in range(self.max_redirects + 1):
            if self.url_validator:
                self.url_validator(current)
            if _url_validator:
                _url_validator(current)

            pass
            response = session.get(
                current, stream=True, timeout=(20, 60 * 10), allow_redirects=False
            )
            is_redirect = response.status_code in _REDIRECT_STATUSES
            self._check_peer_ip(response, strict=not is_redirect)

            if is_redirect:
                location = response.headers.get('location')
                response.close()
                if not location:
                    raise RuntimeError(f"Redirect without Location header from {current}")
                pass
                pass
                current = urljoin(current, location)
                continue

            response.raise_for_status()
            return response

        raise RuntimeError(
            f"Too many redirects (>{self.max_redirects}) downloading PDF from {url}"
        )

    def _get_pdf_path(self, url: str) -> str:
        if url.startswith(("http://", "https://")):
            import tempfile
            import requests

            pass
            temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            temp_file.close()
            self._temp_files.append(temp_file.name)

            try:
                if self.logger:
                    self.logger.info(f"Downloading PDF from {url}...")

                response = self._fetch_with_redirect_checks(requests, url)

                pass
                pass
                pass
                total_size = int(response.headers.get('content-length', 0) or 0)
                downloaded = 0

                with response:
                    with open(temp_file.name, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            downloaded += len(chunk)
                            if downloaded > self.max_pdf_bytes:
                                raise RuntimeError(
                                    f"PDF from {url} exceeds max_pdf_bytes "
                                    f"({self.max_pdf_bytes} bytes)"
                                )
                            f.write(chunk)
                            if self.logger and total_size > 0:
                                progress = (downloaded / total_size) * 100
                                if progress % 10 < 0.1:
                                    self.logger.debug(f"PDF download progress: {progress:.0f}%")

                if self.logger:
                    self.logger.info(f"PDF downloaded successfully: {temp_file.name}")

                return temp_file.name

            except requests.exceptions.Timeout as e:
                self._discard_temp_file(temp_file.name)
                raise RuntimeError(f"Timeout downloading PDF from {url}: {str(e)}")
            except Exception as e:
                self._discard_temp_file(temp_file.name)
                raise RuntimeError(f"Failed to download PDF from {url}: {str(e)}")

        elif url.startswith("file://"):
            return url[7:]
            
        return url
    

__all__ = ["PDFCrawlerStrategy", "PDFContentScrapingStrategy"]