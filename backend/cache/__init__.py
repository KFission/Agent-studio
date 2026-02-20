"""
Cache & shared-state layer for JAI Agent OS.
Provides Redis-backed state management and TTL caching with graceful
fallback to in-memory when Redis is unavailable.
"""
from backend.cache.redis_state import RedisStateManager
from backend.cache.cache_layer import CacheLayer

__all__ = ["RedisStateManager", "CacheLayer"]
