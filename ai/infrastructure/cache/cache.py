"""Cache Layer - Infrastructure"""

import os
import time
import threading
from typing import Any, Optional, Dict, Callable
from functools import wraps
from dataclasses import dataclass

CACHE_ENABLED = True
CACHE_TTL_SECONDS = 300

@dataclass
class CacheEntry:
    value: Any
    expires_at: float

class MemoryCache:
    """Thread-safe in-memory cache with TTL."""
    
    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            if time.time() > entry.expires_at:
                del self._cache[key]
                self._misses += 1
                return None
            self._hits += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            ttl = ttl or self._default_ttl
            self._cache[key] = CacheEntry(
                value=value,
                expires_at=time.time() + ttl
            )
    
    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)
    
    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self) -> int:
        with self._lock:
            now = time.time()
            expired = [k for k, v in self._cache.items() if now > v.expires_at]
            for k in expired:
                del self._cache[k]
            return len(expired)
    
    @property
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "size": len(self._cache)
            }

_cache: Optional[MemoryCache] = None

def get_cache() -> MemoryCache:
    global _cache
    if _cache is None:
        _cache = MemoryCache(default_ttl=CACHE_TTL_SECONDS)
    return _cache

def cached(key_prefix: str, ttl: Optional[int] = None):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not CACHE_ENABLED:
                return func(*args, **kwargs)
            
            cache = get_cache()
            cache_key = f"{key_prefix}:{args}:{kwargs}"
            result = cache.get(cache_key)
            
            if result is not None:
                return result
            
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)
            return result
        
        wrapper.cache_clear = lambda: get_cache().clear()
        return wrapper
    return decorator

class CacheKeys:
    VN_PRICE = "vn:price"
    VN_HISTORY = "vn:history"
    CRYPTO_PRICE = "crypto:price"
    CRYPTO_HISTORY = "crypto:history"
    PORTFOLIO = "portfolio"
    SNAPSHOT = "snapshot"
    FINANCIAL = "financial"
    QUOTE = "quote"

def cache_key(prefix: str, *args) -> str:
    parts = [prefix] + [str(a) for a in args]
    return ":".join(parts)
