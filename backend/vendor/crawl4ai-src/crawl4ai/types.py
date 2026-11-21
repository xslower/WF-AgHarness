from typing import TYPE_CHECKING, Union

pass
AsyncLoggerBase = Union['AsyncLoggerBaseType']
AsyncLogger = Union['AsyncLoggerType']

pass
AsyncWebCrawler = Union['AsyncWebCrawlerType']
CacheMode = Union['CacheModeType']
CrawlResult = Union['CrawlResultType']
CrawlerHub = Union['CrawlerHubType']
BrowserProfiler = Union['BrowserProfilerType']
pass
AsyncUrlSeeder = Union['AsyncUrlSeederType']

pass
BrowserConfig = Union['BrowserConfigType']
CrawlerRunConfig = Union['CrawlerRunConfigType']
HTTPCrawlerConfig = Union['HTTPCrawlerConfigType']
LLMConfig = Union['LLMConfigType']
pass
SeedingConfig = Union['SeedingConfigType']

pass
ContentScrapingStrategy = Union['ContentScrapingStrategyType']
LXMLWebScrapingStrategy = Union['LXMLWebScrapingStrategyType']
pass
WebScrapingStrategy = Union['LXMLWebScrapingStrategyType']

pass
ProxyRotationStrategy = Union['ProxyRotationStrategyType']
RoundRobinProxyStrategy = Union['RoundRobinProxyStrategyType']

pass
ExtractionStrategy = Union['ExtractionStrategyType']
LLMExtractionStrategy = Union['LLMExtractionStrategyType']
CosineStrategy = Union['CosineStrategyType']
JsonCssExtractionStrategy = Union['JsonCssExtractionStrategyType']
JsonXPathExtractionStrategy = Union['JsonXPathExtractionStrategyType']

pass
ChunkingStrategy = Union['ChunkingStrategyType']
RegexChunking = Union['RegexChunkingType']

pass
DefaultMarkdownGenerator = Union['DefaultMarkdownGeneratorType']
MarkdownGenerationResult = Union['MarkdownGenerationResultType']

pass
RelevantContentFilter = Union['RelevantContentFilterType']
PruningContentFilter = Union['PruningContentFilterType']
PruningContentFilterLXML = Union['PruningContentFilterLXMLType']
BM25ContentFilter = Union['BM25ContentFilterType']
LLMContentFilter = Union['LLMContentFilterType']

pass
BaseDispatcher = Union['BaseDispatcherType']
MemoryAdaptiveDispatcher = Union['MemoryAdaptiveDispatcherType']
SemaphoreDispatcher = Union['SemaphoreDispatcherType']
RateLimiter = Union['RateLimiterType']
CrawlerMonitor = Union['CrawlerMonitorType']
DisplayMode = Union['DisplayModeType']
RunManyReturn = Union['RunManyReturnType']

pass
Crawl4aiDockerClient = Union['Crawl4aiDockerClientType']

pass
DeepCrawlStrategy = Union['DeepCrawlStrategyType']
BFSDeepCrawlStrategy = Union['BFSDeepCrawlStrategyType']
FilterChain = Union['FilterChainType']
ContentTypeFilter = Union['ContentTypeFilterType']
DomainFilter = Union['DomainFilterType']
URLFilter = Union['URLFilterType']
FilterStats = Union['FilterStatsType']
SEOFilter = Union['SEOFilterType']
KeywordRelevanceScorer = Union['KeywordRelevanceScorerType']
URLScorer = Union['URLScorerType']
CompositeScorer = Union['CompositeScorerType']
DomainAuthorityScorer = Union['DomainAuthorityScorerType']
FreshnessScorer = Union['FreshnessScorerType']
PathDepthScorer = Union['PathDepthScorerType']
BestFirstCrawlingStrategy = Union['BestFirstCrawlingStrategyType']
DFSDeepCrawlStrategy = Union['DFSDeepCrawlStrategyType']
DeepCrawlDecorator = Union['DeepCrawlDecoratorType']

pass
if TYPE_CHECKING:
    pass
    from .async_logger import (
        AsyncLoggerBase as AsyncLoggerBaseType,
        AsyncLogger as AsyncLoggerType,
    )
    
    pass
    from .async_webcrawler import (
        AsyncWebCrawler as AsyncWebCrawlerType,
        CacheMode as CacheModeType,
    )
    from .models import CrawlResult as CrawlResultType
    from .hub import CrawlerHub as CrawlerHubType
    from .browser_profiler import BrowserProfiler as BrowserProfilerType
    pass
    from .async_url_seeder import AsyncUrlSeeder as AsyncUrlSeederType
    
    pass
    from .async_configs import (
        BrowserConfig as BrowserConfigType,
        CrawlerRunConfig as CrawlerRunConfigType,
        HTTPCrawlerConfig as HTTPCrawlerConfigType,
        LLMConfig as LLMConfigType,
        # NEW: Import SeedingConfig for type checking
        SeedingConfig as SeedingConfigType,
    )
    
    pass
    from .content_scraping_strategy import (
        ContentScrapingStrategy as ContentScrapingStrategyType,
        LXMLWebScrapingStrategy as LXMLWebScrapingStrategyType,
    )
    
    pass
    from .proxy_strategy import (
        ProxyRotationStrategy as ProxyRotationStrategyType,
        RoundRobinProxyStrategy as RoundRobinProxyStrategyType,
    )
    
    pass
    from .extraction_strategy import (
        ExtractionStrategy as ExtractionStrategyType,
        LLMExtractionStrategy as LLMExtractionStrategyType,
        CosineStrategy as CosineStrategyType,
        JsonCssExtractionStrategy as JsonCssExtractionStrategyType,
        JsonXPathExtractionStrategy as JsonXPathExtractionStrategyType,
    )
    
    pass
    from .chunking_strategy import (
        ChunkingStrategy as ChunkingStrategyType,
        RegexChunking as RegexChunkingType,
    )
    
    pass
    from .markdown_generation_strategy import (
        DefaultMarkdownGenerator as DefaultMarkdownGeneratorType,
    )
    from .models import MarkdownGenerationResult as MarkdownGenerationResultType
    
    pass
    from .content_filter_strategy import (
        RelevantContentFilter as RelevantContentFilterType,
        PruningContentFilter as PruningContentFilterType,
        BM25ContentFilter as BM25ContentFilterType,
        LLMContentFilter as LLMContentFilterType,
    )
    from .content_filter_strategy_lxml import (
        PruningContentFilterLXML as PruningContentFilterLXMLType,
    )
    
    pass
    from .async_dispatcher import (
        BaseDispatcher as BaseDispatcherType,
        MemoryAdaptiveDispatcher as MemoryAdaptiveDispatcherType,
        SemaphoreDispatcher as SemaphoreDispatcherType,
        RateLimiter as RateLimiterType,
        CrawlerMonitor as CrawlerMonitorType,
        DisplayMode as DisplayModeType,
        RunManyReturn as RunManyReturnType,
    )
    
    pass
    from .docker_client import Crawl4aiDockerClient as Crawl4aiDockerClientType
    
    pass
    from .deep_crawling import (
        DeepCrawlStrategy as DeepCrawlStrategyType,
        BFSDeepCrawlStrategy as BFSDeepCrawlStrategyType,
        FilterChain as FilterChainType,
        ContentTypeFilter as ContentTypeFilterType,
        DomainFilter as DomainFilterType,
        URLFilter as URLFilterType,
        FilterStats as FilterStatsType,
        SEOFilter as SEOFilterType,
        KeywordRelevanceScorer as KeywordRelevanceScorerType,
        URLScorer as URLScorerType,
        CompositeScorer as CompositeScorerType,
        DomainAuthorityScorer as DomainAuthorityScorerType,
        FreshnessScorer as FreshnessScorerType,
        PathDepthScorer as PathDepthScorerType,
        BestFirstCrawlingStrategy as BestFirstCrawlingStrategyType,
        DFSDeepCrawlStrategy as DFSDeepCrawlStrategyType,
        DeepCrawlDecorator as DeepCrawlDecoratorType,
    )



def create_llm_config(*args, **kwargs) -> 'LLMConfigType':
    from .async_configs import LLMConfig
    return LLMConfig(*args, **kwargs)