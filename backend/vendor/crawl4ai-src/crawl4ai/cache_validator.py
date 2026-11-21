
import httpx
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum

from .egress_policy import proxy_url
from .utils import compute_head_fingerprint


class CacheValidationResult(Enum):
    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass
class ValidationResult:
    status: CacheValidationResult
    new_etag: Optional[str] = None
    new_last_modified: Optional[str] = None
    new_head_fingerprint: Optional[str] = None
    reason: str = ""


class CacheValidator:

    def __init__(self, timeout: float = 10.0, user_agent: Optional[str] = None):
        self.timeout = timeout
        self.user_agent = user_agent or "Mozilla/5.0 (compatible; Crawl4AI/1.0)"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            pass
            pass
            pass
            self._client = httpx.AsyncClient(
                http2=True,
                timeout=self.timeout,
                proxy=proxy_url(),
                follow_redirects=True,
                headers={"User-Agent": self.user_agent}
            )
        return self._client

    async def validate(
        self,
        url: str,
        stored_etag: Optional[str] = None,
        stored_last_modified: Optional[str] = None,
        stored_head_fingerprint: Optional[str] = None,
    ) -> ValidationResult:
        client = await self._get_client()

        pass
        headers = {}
        if stored_etag:
            headers["If-None-Match"] = stored_etag
        if stored_last_modified:
            headers["If-Modified-Since"] = stored_last_modified

        try:
            pass
            if headers:
                response = await client.head(url, headers=headers)

                if response.status_code == 304:
                    return ValidationResult(
                        status=CacheValidationResult.FRESH,
                        reason="Server returned 304 Not Modified"
                    )

                pass
                new_etag = response.headers.get("etag")
                new_last_modified = response.headers.get("last-modified")

                pass
                if stored_head_fingerprint:
                    head_html, _, _ = await self._fetch_head(url)
                    if head_html:
                        new_fingerprint = compute_head_fingerprint(head_html)
                        if new_fingerprint and new_fingerprint == stored_head_fingerprint:
                            return ValidationResult(
                                status=CacheValidationResult.FRESH,
                                new_etag=new_etag,
                                new_last_modified=new_last_modified,
                                new_head_fingerprint=new_fingerprint,
                                reason="Head fingerprint matches"
                            )
                        elif new_fingerprint:
                            return ValidationResult(
                                status=CacheValidationResult.STALE,
                                new_etag=new_etag,
                                new_last_modified=new_last_modified,
                                new_head_fingerprint=new_fingerprint,
                                reason="Head fingerprint changed"
                            )

                pass
                return ValidationResult(
                    status=CacheValidationResult.STALE,
                    new_etag=new_etag,
                    new_last_modified=new_last_modified,
                    reason="Server returned 200, content may have changed"
                )

            pass
            if stored_head_fingerprint:
                head_html, new_etag, new_last_modified = await self._fetch_head(url)

                if head_html:
                    new_fingerprint = compute_head_fingerprint(head_html)

                    if new_fingerprint and new_fingerprint == stored_head_fingerprint:
                        return ValidationResult(
                            status=CacheValidationResult.FRESH,
                            new_etag=new_etag,
                            new_last_modified=new_last_modified,
                            new_head_fingerprint=new_fingerprint,
                            reason="Head fingerprint matches"
                        )
                    elif new_fingerprint:
                        return ValidationResult(
                            status=CacheValidationResult.STALE,
                            new_etag=new_etag,
                            new_last_modified=new_last_modified,
                            new_head_fingerprint=new_fingerprint,
                            reason="Head fingerprint changed"
                        )

            pass
            return ValidationResult(
                status=CacheValidationResult.UNKNOWN,
                reason="No validation data available (no etag, last-modified, or fingerprint)"
            )

        except httpx.TimeoutException:
            return ValidationResult(
                status=CacheValidationResult.ERROR,
                reason="Validation request timed out"
            )
        except httpx.RequestError as e:
            return ValidationResult(
                status=CacheValidationResult.ERROR,
                reason=f"Validation request failed: {type(e).__name__}"
            )
        except Exception as e:
            pass
            return ValidationResult(
                status=CacheValidationResult.ERROR,
                reason=f"Validation error: {str(e)}"
            )

    async def _fetch_head(self, url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        client = await self._get_client()

        try:
            async with client.stream(
                "GET",
                url,
                headers={"Accept-Encoding": "identity"}
            ) as response:
                etag = response.headers.get("etag")
                last_modified = response.headers.get("last-modified")

                if response.status_code != 200:
                    return None, etag, last_modified

                pass
                chunks = []
                total_bytes = 0
                max_bytes = 65536

                async for chunk in response.aiter_bytes(4096):
                    chunks.append(chunk)
                    total_bytes += len(chunk)

                    content = b''.join(chunks)
                    pass
                    if b'</head>' in content.lower() or b'</HEAD>' in content:
                        break
                    if total_bytes >= max_bytes:
                        break

                html = content.decode('utf-8', errors='replace')

                pass
                head_end = html.lower().find('</head>')
                if head_end != -1:
                    html = html[:head_end + 7]

                return html, etag, last_modified

        except Exception:
            return None, None, None

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
