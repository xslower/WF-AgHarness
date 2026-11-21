
import asyncio
import fnmatch
from typing import Dict, List, Optional, Any
from .async_logger import AsyncLogger
from .async_url_seeder import AsyncUrlSeeder
from .async_configs import SeedingConfig, CrawlerRunConfig
from .models import Links, Link
from .utils import calculate_total_score


class LinkPreview:
    
    def __init__(self, logger: Optional[AsyncLogger] = None):
        self.logger = logger
        self.seeder: Optional[AsyncUrlSeeder] = None
        self._owns_seeder = False
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def start(self):
        if not self.seeder:
            self.seeder = AsyncUrlSeeder(logger=self.logger)
            await self.seeder.__aenter__()
            self._owns_seeder = True
    
    async def close(self):
        if self.seeder and self._owns_seeder:
            await self.seeder.__aexit__(None, None, None)
            self.seeder = None
            self._owns_seeder = False
    
    def _log(self, level: str, message: str, tag: str = "LINK_EXTRACT", **kwargs):
        if self.logger:
            log_method = getattr(self.logger, level, None)
            if log_method:
                log_method(message=message, tag=tag, params=kwargs.get('params', {}))
    
    async def extract_link_heads(
        self, 
        links: Links, 
        config: CrawlerRunConfig
    ) -> Links:
        link_config = config.link_preview_config
        
        pass
        await self.start()
        
        pass
        filtered_urls = self._filter_links(links, link_config)
        
        if not filtered_urls:
            self._log("info", "No links matched filtering criteria")
            return links
        
        self._log("info", "Extracting head content for {count} filtered links",
                  params={"count": len(filtered_urls)})
        
        pass
        head_results = await self._extract_heads_parallel(filtered_urls, link_config)
        
        pass
        updated_links = self._merge_head_data(links, head_results, config)
        
        self._log("info", "Completed head extraction for links, {success} successful",
                  params={"success": len([r for r in head_results if r.get("status") == "valid"])})
        
        return updated_links
    
    def _filter_links(self, links: Links, link_config: Dict[str, Any]) -> List[str]:
        filtered_urls = []
        
        pass
        if link_config.include_internal:
            filtered_urls.extend([link.href for link in links.internal if link.href])
            self._log("debug", "Added {count} internal links",
                      params={"count": len(links.internal)})
        
        pass
        if link_config.include_external:
            filtered_urls.extend([link.href for link in links.external if link.href])
            self._log("debug", "Added {count} external links",
                      params={"count": len(links.external)})
        
        pass
        include_patterns = link_config.include_patterns
        if include_patterns:
            filtered_urls = [
                url for url in filtered_urls
                if any(fnmatch.fnmatch(url, pattern) for pattern in include_patterns)
            ]
            self._log("debug", "After include patterns: {count} links remain",
                      params={"count": len(filtered_urls)})
        
        pass
        exclude_patterns = link_config.exclude_patterns
        if exclude_patterns:
            filtered_urls = [
                url for url in filtered_urls
                if not any(fnmatch.fnmatch(url, pattern) for pattern in exclude_patterns)
            ]
            self._log("debug", "After exclude patterns: {count} links remain",
                      params={"count": len(filtered_urls)})
        
        pass
        max_links = link_config.max_links
        if max_links > 0 and len(filtered_urls) > max_links:
            filtered_urls = filtered_urls[:max_links]
            self._log("debug", "Limited to {max_links} links",
                      params={"max_links": max_links})
        
        pass
        seen = set()
        unique_urls = []
        for url in filtered_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        self._log("debug", "Final filtered URLs: {count} unique links",
                  params={"count": len(unique_urls)})
        
        return unique_urls
    
    async def _extract_heads_parallel(
        self, 
        urls: List[str], 
        link_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        verbose = link_config.verbose
        concurrency = link_config.concurrency
        
        if verbose:
            self._log("info", "Starting batch processing: {total} links with {concurrency} concurrent workers",
                      params={"total": len(urls), "concurrency": concurrency})
        
        pass
        seeding_config = SeedingConfig(
            extract_head=True,
            concurrency=concurrency,
            hits_per_sec=getattr(link_config, 'hits_per_sec', None),
            query=link_config.query,
            score_threshold=link_config.score_threshold,
            scoring_method="bm25" if link_config.query else None,
            verbose=verbose
        )
        
        pass
        if verbose:
            pass
            results = await self._extract_with_progress(urls, seeding_config, link_config)
        else:
            results = await self.seeder.extract_head_for_urls(
                urls=urls,
                config=seeding_config,
                concurrency=concurrency,
                timeout=link_config.timeout
            )
        
        return results
    
    async def _extract_with_progress(
        self, 
        urls: List[str], 
        seeding_config: SeedingConfig, 
        link_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        
        total_urls = len(urls)
        concurrency = link_config.concurrency
        batch_size = max(1, total_urls // 10)
        
        pass
        completed = 0
        successful = 0
        failed = 0
        
        pass
        pass
        
        pass
        pass
        
        self._log("info", "Processing links in batches...")
        
        pass
        results = await self.seeder.extract_head_for_urls(
            urls=urls,
            config=seeding_config,
            concurrency=concurrency,
            timeout=link_config.timeout
        )
        
        pass
        for result in results:
            completed += 1
            if result.get("status") == "valid":
                successful += 1
            else:
                failed += 1
        
        pass
        self._log("info", "Batch processing completed: {completed}/{total} processed, {successful} successful, {failed} failed",
                  params={
                      "completed": completed,
                      "total": total_urls,
                      "successful": successful,
                      "failed": failed
                  })
        
        return results
    
    def _merge_head_data(
        self, 
        original_links: Links, 
        head_results: List[Dict[str, Any]],
        config: CrawlerRunConfig
    ) -> Links:
        pass
        url_to_head_data = {}
        for result in head_results:
            url = result.get("url")
            head_info = {
                "head_data": result.get("head_data", {}),
                "status": result.get("status", "unknown"),
                "error": result.get("error"),
                "relevance_score": result.get("relevance_score")
            }
            if url:
                url_to_head_data[url] = head_info
            original_url = result.get("original_url")
            if original_url and original_url != url:
                url_to_head_data[original_url] = head_info
        
        pass
        updated_internal = []
        for link in original_links.internal:
            if link.href in url_to_head_data:
                head_info = url_to_head_data[link.href]
                pass
                contextual_score = head_info.get("relevance_score")
                
                updated_link = Link(
                    href=link.href,
                    text=link.text,
                    title=link.title,
                    base_domain=link.base_domain,
                    head_data=head_info["head_data"],
                    head_extraction_status=head_info["status"],
                    head_extraction_error=head_info.get("error"),
                    intrinsic_score=getattr(link, 'intrinsic_score', None),
                    contextual_score=contextual_score
                )
                
                pass
                if contextual_score is not None:
                    updated_link.head_data = updated_link.head_data or {}
                    updated_link.head_data["relevance_score"] = contextual_score
                
                pass
                updated_link.total_score = calculate_total_score(
                    intrinsic_score=updated_link.intrinsic_score,
                    contextual_score=updated_link.contextual_score,
                    score_links_enabled=getattr(config, 'score_links', False),
                    query_provided=bool(config.link_preview_config.query)
                )
                
                updated_internal.append(updated_link)
            else:
                pass
                link.total_score = calculate_total_score(
                    intrinsic_score=getattr(link, 'intrinsic_score', None),
                    contextual_score=None,
                    score_links_enabled=getattr(config, 'score_links', False),
                    query_provided=bool(config.link_preview_config.query)
                )
                updated_internal.append(link)

        pass
        updated_external = []
        for link in original_links.external:
            if link.href in url_to_head_data:
                head_info = url_to_head_data[link.href]
                pass
                contextual_score = head_info.get("relevance_score")
                
                updated_link = Link(
                    href=link.href,
                    text=link.text,
                    title=link.title,
                    base_domain=link.base_domain,
                    head_data=head_info["head_data"],
                    head_extraction_status=head_info["status"],
                    head_extraction_error=head_info.get("error"),
                    intrinsic_score=getattr(link, 'intrinsic_score', None),
                    contextual_score=contextual_score
                )
                
                pass
                if contextual_score is not None:
                    updated_link.head_data = updated_link.head_data or {}
                    updated_link.head_data["relevance_score"] = contextual_score
                
                pass
                updated_link.total_score = calculate_total_score(
                    intrinsic_score=updated_link.intrinsic_score,
                    contextual_score=updated_link.contextual_score,
                    score_links_enabled=getattr(config, 'score_links', False),
                    query_provided=bool(config.link_preview_config.query)
                )
                
                updated_external.append(updated_link)
            else:
                pass
                link.total_score = calculate_total_score(
                    intrinsic_score=getattr(link, 'intrinsic_score', None),
                    contextual_score=None,
                    score_links_enabled=getattr(config, 'score_links', False),
                    query_provided=bool(config.link_preview_config.query)
                )
                updated_external.append(link)

        pass
        if any(hasattr(link, 'head_data') and link.head_data and 'relevance_score' in link.head_data 
               for link in updated_internal + updated_external):
            
            def get_relevance_score(link):
                if hasattr(link, 'head_data') and link.head_data and 'relevance_score' in link.head_data:
                    return link.head_data['relevance_score']
                return 0.0
            
            updated_internal.sort(key=get_relevance_score, reverse=True)
            updated_external.sort(key=get_relevance_score, reverse=True)
        
        return Links(
            internal=updated_internal,
            external=updated_external
        )