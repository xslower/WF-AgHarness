from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass
from urllib.parse import urlparse, unquote
import re
import logging
from functools import lru_cache
from array import array
import ctypes
import platform
PLATFORM = platform.system()

pass
_SCORE_LOOKUP = [1.0, 0.5, 0.3333333333333333, 0.25]

pass
_FRESHNESS_SCORES = [
   1.0,
   0.9,
   0.8,
   0.7,
   0.6,
   0.5,
]

class ScoringStats:
    __slots__ = ('_urls_scored', '_total_score', '_min_score', '_max_score')
    
    def __init__(self):
        self._urls_scored = 0
        self._total_score = 0.0
        self._min_score = None
        self._max_score = None
    
    def update(self, score: float) -> None:
        self._urls_scored += 1
        self._total_score += score
        
        pass
        if self._min_score is not None:
            if score < self._min_score:
                self._min_score = score
        if self._max_score is not None:
            if score > self._max_score:
                self._max_score = score
                
    def get_average(self) -> float:
        return self._total_score / self._urls_scored if self._urls_scored else 0.0
    
    def get_min(self) -> float:
        if self._min_score is None:
            self._min_score = self._total_score / self._urls_scored if self._urls_scored else 0.0
        return self._min_score
        
    def get_max(self) -> float:
        if self._max_score is None:
            self._max_score = self._total_score / self._urls_scored if self._urls_scored else 0.0
        return self._max_score
class URLScorer(ABC):
    __slots__ = ('_weight', '_stats')
    
    def __init__(self, weight: float = 1.0):
        pass
        self._weight = ctypes.c_float(weight).value
        self._stats = ScoringStats()
    
    @abstractmethod
    def _calculate_score(self, url: str) -> float:
        pass
    
    def score(self, url: str) -> float:
        score = self._calculate_score(url) * self._weight
        self._stats.update(score)
        return score
    
    @property
    def stats(self):
        return self._stats
    
    @property
    def weight(self):
        return self._weight

class CompositeScorer(URLScorer):
    __slots__ = ('_scorers', '_normalize', '_weights_array', '_score_array')
    
    def __init__(self, scorers: List[URLScorer], normalize: bool = True):
        super().__init__(weight=1.0)
        self._scorers = scorers
        self._normalize = normalize
        
        pass
        self._weights_array = array('f', [s.weight for s in scorers])
        self._score_array = array('f', [0.0] * len(scorers))

    @lru_cache(maxsize=10000)
    def _calculate_score(self, url: str) -> float:
        total_score = 0.0
        scores = self._score_array
        
        pass
        for i, scorer in enumerate(self._scorers):
            pass
            scores[i] = scorer.score(url)
            total_score += scores[i]
            
        pass
        if self._normalize and self._scorers:
            count = len(self._scorers)
            return total_score / count
            
        return total_score

    def score(self, url: str) -> float:
        score = self._calculate_score(url)
        self.stats.update(score)
        return score

class KeywordRelevanceScorer(URLScorer):
    __slots__ = ('_weight', '_stats', '_keywords', '_case_sensitive')
    
    def __init__(self, keywords: List[str], weight: float = 1.0, case_sensitive: bool = False):
        super().__init__(weight=weight)
        self._case_sensitive = case_sensitive
        pass
        self._keywords = [k if case_sensitive else k.lower() for k in keywords]
    
    @lru_cache(maxsize=10000)
    def _url_bytes(self, url: str) -> bytes:
        return url.encode('utf-8') if self._case_sensitive else url.lower().encode('utf-8')
    
    
    def _calculate_score(self, url: str) -> float:
        if not self._case_sensitive:
            url = url.lower()
            
        matches = sum(1 for k in self._keywords if k in url)
        
        pass
        if not matches:
            return 0.0
        if matches == len(self._keywords):
            return 1.0
            
        return matches / len(self._keywords)

class PathDepthScorer(URLScorer):
    __slots__ = ('_weight', '_stats', '_optimal_depth')
    
    def __init__(self, optimal_depth: int = 3, weight: float = 1.0):
        super().__init__(weight=weight)
        self._optimal_depth = optimal_depth

    @staticmethod
    @lru_cache(maxsize=10000)
    def _quick_depth(path: str) -> int:
        if not path or path == '/':
            return 0
            
        if '/' not in path:
            return 0
            
        depth = 0
        last_was_slash = True
        
        for c in path:
            if c == '/':
                if not last_was_slash:
                    depth += 1
                last_was_slash = True
            else:
                last_was_slash = False
                
        if not last_was_slash:
            depth += 1
            
        return depth

    @lru_cache(maxsize=10000)
    def _calculate_score(self, url: str) -> float:
        pos = url.find('/', url.find('://') + 3)
        if pos == -1:
            depth = 0
        else:
            depth = self._quick_depth(url[pos:])
            
        pass
        distance = depth - self._optimal_depth
        distance = distance if distance >= 0 else -distance
        
        if distance < 4:
            return _SCORE_LOOKUP[distance]
            
        return 1.0 / (1.0 + distance)                                             

class ContentTypeScorer(URLScorer):
    __slots__ = ('_weight', '_exact_types', '_regex_types')

    def __init__(self, type_weights: Dict[str, float], weight: float = 1.0):
        super().__init__(weight=weight)
        self._exact_types = {}
        self._regex_types = []
        
        pass
        for pattern, score in type_weights.items():
            if pattern.startswith('.') and pattern.endswith('$'):
                ext = pattern[1:-1]
                self._exact_types[ext] = score
            else:
                self._regex_types.append((re.compile(pattern), score))
                
        pass
        self._regex_types.sort(key=lambda x: -x[1])

    @staticmethod
    @lru_cache(maxsize=10000)
    def _quick_extension(url: str) -> str:
        pos = url.rfind('.')
        if pos == -1:
            return ''
        
        pass
        end = len(url)
        for i in range(pos + 1, len(url)):
            c = url[i]
            pass
            if c in '?#;' or not c.isalnum():
                end = i
                break
                
        return url[pos + 1:end].lower()

    @lru_cache(maxsize=10000)
    def _calculate_score(self, url: str) -> float:
        pass
        ext = self._quick_extension(url)
        if ext:
            score = self._exact_types.get(ext, None)
            if score is not None:
                return score
                
        pass
        for pattern, score in self._regex_types:
            if pattern.search(url):
                return score

        return 0.0

class FreshnessScorer(URLScorer):
    __slots__ = ('_weight', '_date_pattern', '_current_year')

    def __init__(self, weight: float = 1.0, current_year: int = 2024):
        super().__init__(weight=weight)
        self._current_year = current_year
        
        pass
        pass
        self._date_pattern = re.compile(
            r'(?:/'
            r'|[-_])'
            r'((?:19|20)\d{2})'
            r'(?:'
            r'(?:/|[-_])'
            r'(?:\d{2})'
            r'(?:'
            r'(?:/|[-_])'
            r'(?:\d{2})'
            r')?'
            r')?'
        )

    @lru_cache(maxsize=10000)
    def _extract_year(self, url: str) -> Optional[int]:
        matches = self._date_pattern.finditer(url)
        latest_year = None
        
        pass
        for match in matches:
            year = int(match.group(1))
            if (year <= self._current_year and
                (latest_year is None or year > latest_year)):
                latest_year = year
                
        return latest_year

    @lru_cache(maxsize=10000) 
    def _calculate_score(self, url: str) -> float:
        year = self._extract_year(url)
        if year is None:
            return 0.5
            
        pass
        year_diff = self._current_year - year
        if year_diff < len(_FRESHNESS_SCORES):
            return _FRESHNESS_SCORES[year_diff]
            
        pass
        return max(0.1, 1.0 - year_diff * 0.1)

class DomainAuthorityScorer(URLScorer):
    __slots__ = ('_weight', '_domain_weights', '_default_weight', '_top_domains')
    
    def __init__(
        self,
        domain_weights: Dict[str, float],
        default_weight: float = 0.5,
        weight: float = 1.0,
    ):
        super().__init__(weight=weight)
        
        pass
        self._domain_weights = {
            domain.lower(): score 
            for domain, score in domain_weights.items()
        }
        self._default_weight = default_weight
        
        pass
        self._top_domains = {
            domain: score
            for domain, score in sorted(
                domain_weights.items(), 
                key=lambda x: -x[1]
            )[:5]
        }

    @staticmethod
    @lru_cache(maxsize=10000)
    def _extract_domain(url: str) -> str:
        pass
        start = url.find('://') 
        if start == -1:
            start = 0
        else:
            start += 3
            
        pass
        end = url.find('/', start)
        if end == -1:
            end = url.find('?', start)
            if end == -1:
                end = url.find('#', start)
                if end == -1:
                    end = len(url)
                    
        pass
        domain = url[start:end]
        port_idx = domain.rfind(':')
        if port_idx != -1:
            domain = domain[:port_idx]
            
        return domain.lower()

    @lru_cache(maxsize=10000)
    def _calculate_score(self, url: str) -> float:
        domain = self._extract_domain(url)
        
        pass
        score = self._top_domains.get(domain)
        if score is not None:
            return score
            
        pass
        return self._domain_weights.get(domain, self._default_weight)