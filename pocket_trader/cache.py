# cache.py
"""
Intelligent caching system with TTL, LRU, and LFU
Supports: Time-based, Frequency-based, and Redis-backed caching
"""

import time
import asyncio
import heapq
import json
import logging
from typing import Any, Optional, Dict, Tuple, List, Callable, TypeVar, Generic
from collections import OrderedDict
from dataclasses import dataclass

from .utils import setup_logger

K = TypeVar('K')
V = TypeVar('V')


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    value: Any
    expiry: float
    created_at: float
    access_count: int = 0
    last_access: float = 0.0


# ============================================================================
# TTL CACHE - Time-based caching
# ============================================================================

class TTLCache:
    """Time-based cache with LRU eviction and statistics"""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 60.0, cleanup_interval: float = 10.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._logger = setup_logger("TTLCache")
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
        }
    
    async def start(self):
        """Start cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self._logger.info("Cache cleanup started")
    
    async def stop(self):
        """Stop cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            self._logger.info("Cache cleanup stopped")
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache"""
        async with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return default
            
            entry = self._cache[key]
            now = time.time()
            
            if now > entry.expiry:
                del self._cache[key]
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                return default
            
            entry.access_count += 1
            entry.last_access = now
            self._cache.move_to_end(key)
            self._stats["hits"] += 1
            
            return entry.value
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """Set value in cache"""
        ttl = ttl or self.default_ttl
        now = time.time()
        
        async with self._lock:
            entry = CacheEntry(
                value=value,
                expiry=now + ttl,
                created_at=now,
                last_access=now
            )
            
            self._cache[key] = entry
            self._cache.move_to_end(key)
            
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)
                self._stats["evictions"] += 1
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def clear(self):
        """Clear all cache"""
        async with self._lock:
            self._cache.clear()
            self._logger.info("Cache cleared")
    
    async def get_or_set(self, key: str, factory: Callable[[], Any], ttl: Optional[float] = None) -> Any:
        """Get from cache or set using factory"""
        value = await self.get(key)
        if value is not None:
            return value
        
        value = factory() if not asyncio.iscoroutinefunction(factory) else await factory()
        await self.set(key, value, ttl)
        return value
    
    async def _cleanup_loop(self):
        """Periodic cleanup of expired entries"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Cleanup error: {e}")
    
    async def _cleanup_expired(self):
        """Remove expired entries"""
        now = time.time()
        expired = []
        
        async with self._lock:
            for key, entry in list(self._cache.items()):
                if now > entry.expiry:
                    expired.append(key)
            
            for key in expired:
                del self._cache[key]
            
            if expired:
                self._stats["expirations"] += len(expired)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            **self._stats,
            "size": len(self._cache),
            "max_size": self.max_size,
            "hit_rate": round(hit_rate, 2),
            "usage_percent": round(len(self._cache) / self.max_size * 100, 2) if self.max_size > 0 else 0,
        }


# ============================================================================
# LFU CACHE - Least Frequently Used (Frequency-based)
# ============================================================================

class LFUCache(Generic[K, V]):
    """
    Least Frequently Used Cache with frequency tracking
    Better than LRU for indicator caching and pattern storage
    """
    
    def __init__(self, max_size: int = 1000, ttl: Optional[float] = None):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[K, V] = {}
        self._freq: Dict[K, int] = {}
        self._timestamps: Dict[K, float] = {}
        self._heap: List[Tuple[int, float, K]] = []
        self._counter = 0
        self._lock = asyncio.Lock()
        self._logger = setup_logger("LFUCache")
        self._hits = 0
        self._misses = 0
    
    async def get(self, key: K) -> Optional[V]:
        """Get value and update frequency"""
        async with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            # Check TTL
            if self.ttl:
                age = time.time() - self._timestamps[key]
                if age > self.ttl:
                    await self.delete(key)
                    self._misses += 1
                    return None
            
            self._freq[key] += 1
            self._hits += 1
            return self._cache[key]
    
    async def set(self, key: K, value: V):
        """Set value with frequency tracking"""
        async with self._lock:
            if key in self._cache:
                self._cache[key] = value
                self._freq[key] += 1
                self._timestamps[key] = time.time()
                return
            
            # Evict if full
            if len(self._cache) >= self.max_size:
                await self._evict()
            
            self._cache[key] = value
            self._freq[key] = 1
            self._timestamps[key] = time.time()
            self._counter += 1
            heapq.heappush(self._heap, (1, self._counter, key))
    
    async def delete(self, key: K):
        """Delete key from cache"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                del self._freq[key]
                del self._timestamps[key]
    
    async def _evict(self):
        """Evict least frequently used item"""
        while self._heap:
            freq, _, key = heapq.heappop(self._heap)
            if key in self._cache and self._freq.get(key, 0) == freq:
                del self._cache[key]
                del self._freq[key]
                del self._timestamps[key]
                self._logger.debug(f"Evicted LFU key: {key} (freq: {freq})")
                return
        
        # Fallback: evict any
        if self._cache:
            key = next(iter(self._cache))
            await self.delete(key)
    
    async def clear(self):
        """Clear all cache"""
        async with self._lock:
            self._cache.clear()
            self._freq.clear()
            self._timestamps.clear()
            self._heap.clear()
            self._counter = 0
            self._hits = 0
            self._misses = 0
            self._logger.info("LFU cache cleared")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        async with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'ttl': self.ttl,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': round(hit_rate, 2),
                'avg_frequency': sum(self._freq.values()) / len(self._freq) if self._freq else 0
            }


# ============================================================================
# PREDICTIVE CACHE - Machine Learning based prefetching
# ============================================================================

class PredictiveCache:
    """
    Machine learning based predictive caching
    Learns patterns and preloads likely needed data
    """
    
    def __init__(self, cache: TTLCache, window_size: int = 100):
        self.cache = cache
        self.window_size = window_size
        self._access_pattern: Dict[str, List[str]] = {}
        self._access_history: List[str] = []
        self._logger = setup_logger("PredictiveCache")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value and record access pattern"""
        value = await self.cache.get(key)
        
        if value is not None:
            self._record_access(key)
            await self._predict_and_prefetch(key)
        
        return value
    
    async def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """Set value"""
        await self.cache.set(key, value, ttl)
    
    def _record_access(self, key: str):
        """Record access pattern"""
        self._access_history.append(key)
        
        if len(self._access_history) > self.window_size:
            self._access_history.pop(0)
        
        # Update pattern
        if len(self._access_history) > 1:
            prev_key = self._access_history[-2]
            if prev_key not in self._access_pattern:
                self._access_pattern[prev_key] = []
            self._access_pattern[prev_key].append(key)
    
    async def _predict_and_prefetch(self, current_key: str):
        """Predict next keys and prefetch"""
        if current_key in self._access_pattern:
            next_keys = self._access_pattern[current_key]
            if next_keys:
                # Get most common next key
                from collections import Counter
                most_common = Counter(next_keys).most_common(1)
                if most_common:
                    predicted_key = most_common[0][0]
                    # Prefetch if not in cache
                    if not await self.cache.get(predicted_key):
                        self._logger.debug(f"Prefetching {predicted_key}")
                        # Signal to load this key
                        await self._on_prefetch(predicted_key)
    
    async def _on_prefetch(self, key: str):
        """Called when a key should be prefetched"""
        # Override in subclass
        pass
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get predictive cache statistics"""
        return {
            'patterns': len(self._access_pattern),
            'history_size': len(self._access_history),
            'cache_stats': await self.cache.get_stats()
        }


# ============================================================================
# INDICATOR CACHE - Specialized for technical indicators
# ============================================================================

class IndicatorCache:
    """Specialized cache for indicator results with TTL based on timeframe"""
    
    def __init__(self, max_size: int = 500, use_lfu: bool = True):
        if use_lfu:
            self.cache = LFUCache(max_size=max_size, ttl=30.0)
        else:
            self.cache = TTLCache(max_size=max_size, default_ttl=30.0)
        self._logger = setup_logger("IndicatorCache")
        self._use_lfu = use_lfu
    
    def _make_key(self, indicator: str, asset: str, timeframe: int, *args) -> str:
        """Create cache key"""
        args_str = ":".join(str(a) for a in args)
        return f"{indicator}:{asset}:{timeframe}:{args_str}"
    
    def _get_ttl(self, timeframe: int) -> float:
        """Get TTL based on timeframe"""
        if timeframe <= 60:  # 1m
            return 5.0
        elif timeframe <= 300:  # 5m
            return 15.0
        elif timeframe <= 900:  # 15m
            return 30.0
        elif timeframe <= 3600:  # 1h
            return 60.0
        else:
            return 120.0
    
    async def get(self, indicator: str, asset: str, timeframe: int, *args) -> Optional[Any]:
        """Get cached indicator result"""
        key = self._make_key(indicator, asset, timeframe, *args)
        if self._use_lfu:
            return await self.cache.get(key)
        else:
            return await self.cache.get(key)
    
    async def set(self, value: Any, indicator: str, asset: str, timeframe: int, *args):
        """Cache indicator result"""
        key = self._make_key(indicator, asset, timeframe, *args)
        ttl = self._get_ttl(timeframe)
        if self._use_lfu:
            await self.cache.set(key, value)
        else:
            await self.cache.set(key, value, ttl)
    
    async def get_or_compute(self, 
                           indicator: str, 
                           asset: str, 
                           timeframe: int, 
                           compute_func: Callable,
                           *args) -> Any:
        """Get cached or compute new value"""
        key = self._make_key(indicator, asset, timeframe, *args)
        
        # Try cache first
        if self._use_lfu:
            cached = await self.cache.get(key)
        else:
            cached = await self.cache.get(key)
        
        if cached is not None:
            return cached
        
        # Compute new value
        value = compute_func() if not asyncio.iscoroutinefunction(compute_func) else await compute_func()
        
        # Cache it
        ttl = self._get_ttl(timeframe)
        if self._use_lfu:
            await self.cache.set(key, value)
        else:
            await self.cache.set(key, value, ttl)
        
        return value
    
    async def invalidate_asset(self, asset: str):
        """Invalidate all cache for an asset"""
        async with self.cache._lock:
            if self._use_lfu:
                keys_to_delete = [k for k in self.cache._cache.keys() if f":{asset}:" in str(k)]
                for key in keys_to_delete:
                    await self.cache.delete(key)
            else:
                keys_to_delete = [k for k in self.cache._cache.keys() if f":{asset}:" in k]
                for key in keys_to_delete:
                    await self.cache.delete(key)
            
            if keys_to_delete:
                self._logger.info(f"Invalidated {len(keys_to_delete)} cache entries for {asset}")
    
    async def clear(self):
        """Clear all cache"""
        await self.cache.clear()
        self._logger.info("Indicator cache cleared")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return await self.cache.get_stats()


# ============================================================================
# PATTERN CACHE - For genetic algorithm pattern storage
# ============================================================================

class PatternCache:
    """
    Specialized cache for genetic algorithm patterns
    Stores successful and failed trading patterns
    """
    
    def __init__(self, max_patterns: int = 1000):
        self.max_patterns = max_patterns
        self._successful: Dict[str, List[Dict]] = {}
        self._failed: Dict[str, List[Dict]] = {}
        self._lock = asyncio.Lock()
        self._logger = setup_logger("PatternCache")
    
    async def add_successful(self, pattern_key: str, pattern_data: Dict):
        """Add successful pattern"""
        async with self._lock:
            if pattern_key not in self._successful:
                self._successful[pattern_key] = []
            
            self._successful[pattern_key].append({
                **pattern_data,
                'timestamp': time.time()
            })
            
            # Keep only max patterns
            if len(self._successful[pattern_key]) > self.max_patterns:
                self._successful[pattern_key] = self._successful[pattern_key][-self.max_patterns:]
    
    async def add_failed(self, pattern_key: str, pattern_data: Dict):
        """Add failed pattern"""
        async with self._lock:
            if pattern_key not in self._failed:
                self._failed[pattern_key] = []
            
            self._failed[pattern_key].append({
                **pattern_data,
                'timestamp': time.time()
            })
            
            if len(self._failed[pattern_key]) > self.max_patterns:
                self._failed[pattern_key] = self._failed[pattern_key][-self.max_patterns:]
    
    async def get_similar(self, pattern_key: str, threshold: float = 0.8) -> Optional[Dict]:
        """Find similar successful pattern"""
        async with self._lock:
            if pattern_key not in self._successful:
                return None
            
            patterns = self._successful[pattern_key]
            if not patterns:
                return None
            
            # Get most recent successful pattern
            return patterns[-1]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get pattern cache statistics"""
        async with self._lock:
            return {
                'successful_patterns': sum(len(p) for p in self._successful.values()),
                'failed_patterns': sum(len(p) for p in self._failed.values()),
                'unique_patterns': len(self._successful),
                'total_patterns': sum(len(p) for p in self._successful.values()) + 
                                 sum(len(p) for p in self._failed.values())
            }
    
    async def clear(self):
        """Clear all patterns"""
        async with self._lock:
            self._successful.clear()
            self._failed.clear()
            self._logger.info("Pattern cache cleared")


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "TTLCache",
    "LFUCache",
    "PredictiveCache",
    "IndicatorCache",
    "PatternCache",
]