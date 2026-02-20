"""
TTL-based caching layer for frequently accessed data.
Caches model library, agent definitions, prompt templates, and other
read-heavy data with configurable TTL per namespace.

Uses Redis when available, falls back to in-memory LRU cache.
"""

import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional
from functools import wraps

logger = logging.getLogger(__name__)


# Default TTLs per data type (seconds)
DEFAULT_TTLS = {
    "models": 300,          # 5 min — model library rarely changes
    "agents": 60,           # 1 min — agent definitions change more often
    "agent_detail": 30,     # 30s — single agent detail
    "prompts": 120,         # 2 min — prompt templates
    "tools": 120,           # 2 min — tool definitions
    "environments": 60,     # 1 min — environment configs
    "groups": 120,          # 2 min — group configs
    "metering": 30,         # 30s — metering data (near real-time)
    "default": 60,          # 1 min — fallback
}


class _CacheEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.expires_at = time.monotonic() + ttl

    @property
    def expired(self) -> bool:
        return time.monotonic() > self.expires_at


class CacheLayer:
    """
    Two-tier cache: Redis (shared across replicas) → In-memory (per-process).

    Usage:
        cache = CacheLayer(redis_url="redis://localhost:6379/0")
        await cache.connect()

        # Manual get/set
        await cache.set("models", "all", model_list, ttl=300)
        models = await cache.get("models", "all")

        # Decorator
        @cache.cached("models", ttl=300)
        async def list_models():
            return expensive_call()
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0",
                 max_memory_entries: int = 1000):
        self._redis_url = redis_url
        self._redis = None
        self._connected = False
        self._max_entries = max_memory_entries
        # In-memory L1 cache (per-process, fast)
        self._l1: Dict[str, _CacheEntry] = {}
        # Stats
        self._hits = 0
        self._misses = 0
        self._redis_hits = 0

    async def connect(self) -> bool:
        """Connect to Redis for L2 cache."""
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            await self._redis.ping()
            self._connected = True
            logger.info("[CACHE] Redis L2 cache connected")
            return True
        except Exception as e:
            logger.warning(f"[CACHE] Redis unavailable ({e}). L1-only mode.")
            self._connected = False
            self._redis = None
            return False

    async def disconnect(self):
        if self._redis:
            try:
                await self._redis.close()
            except Exception:
                pass
        self._connected = False

    def _cache_key(self, namespace: str, key: str) -> str:
        return f"{namespace}:{key}"

    def _redis_key(self, namespace: str, key: str) -> str:
        return f"jai:cache:{namespace}:{key}"

    def _ttl_for(self, namespace: str, ttl: Optional[int] = None) -> int:
        if ttl is not None:
            return ttl
        return DEFAULT_TTLS.get(namespace, DEFAULT_TTLS["default"])

    # ── Core Operations ──────────────────────────────────────────

    async def get(self, namespace: str, key: str) -> Optional[Any]:
        """Get from cache. Checks L1 (memory) first, then L2 (Redis)."""
        ck = self._cache_key(namespace, key)

        # L1: in-memory
        entry = self._l1.get(ck)
        if entry and not entry.expired:
            self._hits += 1
            return entry.value
        elif entry:
            del self._l1[ck]  # expired

        # L2: Redis
        if self._connected and self._redis:
            try:
                raw = await self._redis.get(self._redis_key(namespace, key))
                if raw:
                    value = json.loads(raw)
                    # Promote to L1
                    ttl = self._ttl_for(namespace)
                    self._l1[ck] = _CacheEntry(value, ttl)
                    self._evict_if_needed()
                    self._redis_hits += 1
                    self._hits += 1
                    return value
            except Exception as e:
                logger.debug(f"[CACHE] Redis get failed: {e}")

        self._misses += 1
        return None

    async def set(self, namespace: str, key: str, value: Any,
                  ttl: Optional[int] = None) -> bool:
        """Set in both L1 and L2 cache."""
        actual_ttl = self._ttl_for(namespace, ttl)
        ck = self._cache_key(namespace, key)

        # L1
        self._l1[ck] = _CacheEntry(value, actual_ttl)
        self._evict_if_needed()

        # L2
        if self._connected and self._redis:
            try:
                serialized = json.dumps(value, default=str)
                await self._redis.setex(
                    self._redis_key(namespace, key),
                    actual_ttl,
                    serialized,
                )
            except Exception as e:
                logger.debug(f"[CACHE] Redis set failed: {e}")

        return True

    async def invalidate(self, namespace: str, key: str) -> bool:
        """Remove a specific key from both cache tiers."""
        ck = self._cache_key(namespace, key)
        self._l1.pop(ck, None)
        if self._connected and self._redis:
            try:
                await self._redis.delete(self._redis_key(namespace, key))
            except Exception:
                pass
        return True

    async def invalidate_namespace(self, namespace: str) -> int:
        """Invalidate all keys in a namespace."""
        # L1
        prefix = f"{namespace}:"
        to_remove = [k for k in self._l1 if k.startswith(prefix)]
        for k in to_remove:
            del self._l1[k]

        # L2
        count = len(to_remove)
        if self._connected and self._redis:
            try:
                pattern = f"jai:cache:{namespace}:*"
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                    if keys:
                        await self._redis.delete(*keys)
                        count += len(keys)
                    if cursor == 0:
                        break
            except Exception:
                pass
        return count

    async def invalidate_all(self) -> int:
        """Flush entire cache."""
        count = len(self._l1)
        self._l1.clear()
        if self._connected and self._redis:
            try:
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(cursor, match="jai:cache:*", count=100)
                    if keys:
                        await self._redis.delete(*keys)
                        count += len(keys)
                    if cursor == 0:
                        break
            except Exception:
                pass
        return count

    # ── Decorator ────────────────────────────────────────────────

    def cached(self, namespace: str, key_fn: Optional[Callable] = None,
               ttl: Optional[int] = None):
        """
        Decorator for caching async function results.

        @cache.cached("models")
        async def list_models():
            ...

        @cache.cached("agents", key_fn=lambda agent_id: agent_id)
        async def get_agent(agent_id: str):
            ...
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Compute cache key
                if key_fn:
                    cache_key = str(key_fn(*args, **kwargs))
                else:
                    cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"

                # Try cache
                cached_val = await self.get(namespace, cache_key)
                if cached_val is not None:
                    return cached_val

                # Execute and cache
                result = await func(*args, **kwargs)
                if result is not None:
                    await self.set(namespace, cache_key, result, ttl)
                return result
            wrapper.invalidate = lambda: self.invalidate_namespace(namespace)
            return wrapper
        return decorator

    # ── Eviction ─────────────────────────────────────────────────

    def _evict_if_needed(self):
        """Evict expired entries and oldest entries if over limit."""
        # Remove expired
        now = time.monotonic()
        expired = [k for k, v in self._l1.items() if v.expires_at <= now]
        for k in expired:
            del self._l1[k]

        # If still over limit, remove oldest (by expiry)
        if len(self._l1) > self._max_entries:
            sorted_keys = sorted(self._l1.keys(), key=lambda k: self._l1[k].expires_at)
            excess = len(self._l1) - self._max_entries
            for k in sorted_keys[:excess]:
                del self._l1[k]

    # ── Stats ────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "l1_entries": len(self._l1),
            "l2_connected": self._connected,
            "hits": self._hits,
            "misses": self._misses,
            "redis_hits": self._redis_hits,
            "hit_rate": round(self._hits / total, 4) if total > 0 else 0.0,
            "namespaces": list(set(k.split(":")[0] for k in self._l1.keys())),
        }

    # ── Sync Wrappers ────────────────────────────────────────────

    def get_sync(self, namespace: str, key: str) -> Optional[Any]:
        """Synchronous L1-only get."""
        ck = self._cache_key(namespace, key)
        entry = self._l1.get(ck)
        if entry and not entry.expired:
            self._hits += 1
            return entry.value
        if entry:
            del self._l1[ck]
        self._misses += 1
        return None

    def set_sync(self, namespace: str, key: str, value: Any,
                 ttl: Optional[int] = None) -> bool:
        """Synchronous L1-only set (Redis write is async-queued)."""
        actual_ttl = self._ttl_for(namespace, ttl)
        ck = self._cache_key(namespace, key)
        self._l1[ck] = _CacheEntry(value, actual_ttl)
        self._evict_if_needed()

        if self._connected and self._redis:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.set(namespace, key, value, ttl))
            except Exception:
                pass
        return True

    def invalidate_sync(self, namespace: str, key: str):
        """Synchronous L1 invalidation."""
        ck = self._cache_key(namespace, key)
        self._l1.pop(ck, None)
