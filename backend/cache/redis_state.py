"""
Redis-backed shared state manager for horizontal scaling.
All registries (agents, tools, environments, etc.) can use this to store
state in Redis instead of Python dicts, enabling multi-replica deployments.

Falls back gracefully to in-memory dicts when Redis is unavailable.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RedisStateManager:
    """
    Shared state backend that stores data in Redis hashes.
    Each registry gets its own namespace (hash key prefix).

    Usage:
        state = RedisStateManager(redis_url="redis://localhost:6379/0")
        await state.connect()
        state.hset("agents", "agt-001", {"name": "Bot", ...})
        agent = state.hget("agents", "agt-001")
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self._redis_url = redis_url
        self._redis = None
        self._connected = False
        # In-memory fallback when Redis is unavailable
        self._fallback: Dict[str, Dict[str, Any]] = {}

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        """Attempt to connect to Redis. Returns True if successful."""
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
                retry_on_timeout=True,
            )
            await self._redis.ping()
            self._connected = True
            logger.info(f"[REDIS] Connected to {self._redis_url}")
            return True
        except Exception as e:
            logger.warning(f"[REDIS] Connection failed ({e}). Using in-memory fallback.")
            self._connected = False
            self._redis = None
            return False

    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            try:
                await self._redis.close()
            except Exception:
                pass
        self._connected = False

    # ── Hash Operations (primary state storage) ──────────────────

    def _ns(self, namespace: str) -> str:
        """Prefix namespace for Redis keys."""
        return f"jai:{namespace}"

    async def hset(self, namespace: str, key: str, value: Any) -> bool:
        """Set a value in a namespaced hash."""
        serialized = json.dumps(value, default=str)
        if self._connected and self._redis:
            try:
                await self._redis.hset(self._ns(namespace), key, serialized)
                return True
            except Exception as e:
                logger.warning(f"[REDIS] hset failed: {e}")
        # Fallback
        self._fallback.setdefault(namespace, {})[key] = value
        return True

    async def hget(self, namespace: str, key: str) -> Optional[Any]:
        """Get a value from a namespaced hash."""
        if self._connected and self._redis:
            try:
                raw = await self._redis.hget(self._ns(namespace), key)
                return json.loads(raw) if raw else None
            except Exception as e:
                logger.warning(f"[REDIS] hget failed: {e}")
        # Fallback
        return self._fallback.get(namespace, {}).get(key)

    async def hdel(self, namespace: str, key: str) -> bool:
        """Delete a key from a namespaced hash."""
        if self._connected and self._redis:
            try:
                await self._redis.hdel(self._ns(namespace), key)
                return True
            except Exception as e:
                logger.warning(f"[REDIS] hdel failed: {e}")
        # Fallback
        self._fallback.get(namespace, {}).pop(key, None)
        return True

    async def hgetall(self, namespace: str) -> Dict[str, Any]:
        """Get all key-value pairs from a namespaced hash."""
        if self._connected and self._redis:
            try:
                raw = await self._redis.hgetall(self._ns(namespace))
                return {k: json.loads(v) for k, v in raw.items()}
            except Exception as e:
                logger.warning(f"[REDIS] hgetall failed: {e}")
        # Fallback
        return dict(self._fallback.get(namespace, {}))

    async def hkeys(self, namespace: str) -> List[str]:
        """Get all keys in a namespaced hash."""
        if self._connected and self._redis:
            try:
                return await self._redis.hkeys(self._ns(namespace))
            except Exception as e:
                logger.warning(f"[REDIS] hkeys failed: {e}")
        return list(self._fallback.get(namespace, {}).keys())

    async def hlen(self, namespace: str) -> int:
        """Get count of entries in a namespaced hash."""
        if self._connected and self._redis:
            try:
                return await self._redis.hlen(self._ns(namespace))
            except Exception as e:
                logger.warning(f"[REDIS] hlen failed: {e}")
        return len(self._fallback.get(namespace, {}))

    async def hexists(self, namespace: str, key: str) -> bool:
        """Check if a key exists in a namespaced hash."""
        if self._connected and self._redis:
            try:
                return await self._redis.hexists(self._ns(namespace), key)
            except Exception as e:
                logger.warning(f"[REDIS] hexists failed: {e}")
        return key in self._fallback.get(namespace, {})

    # ── Bulk Operations ──────────────────────────────────────────

    async def hset_many(self, namespace: str, items: Dict[str, Any]) -> int:
        """Set multiple key-value pairs in a hash."""
        if self._connected and self._redis:
            try:
                pipe = self._redis.pipeline()
                ns = self._ns(namespace)
                for k, v in items.items():
                    pipe.hset(ns, k, json.dumps(v, default=str))
                await pipe.execute()
                return len(items)
            except Exception as e:
                logger.warning(f"[REDIS] hset_many failed: {e}")
        # Fallback
        self._fallback.setdefault(namespace, {}).update(items)
        return len(items)

    async def flush_namespace(self, namespace: str) -> bool:
        """Delete an entire namespace."""
        if self._connected and self._redis:
            try:
                await self._redis.delete(self._ns(namespace))
                return True
            except Exception as e:
                logger.warning(f"[REDIS] flush failed: {e}")
        self._fallback.pop(namespace, None)
        return True

    # ── Sync Wrappers (for non-async registry methods) ───────────

    def hset_sync(self, namespace: str, key: str, value: Any) -> bool:
        """Synchronous hset — writes to fallback dict immediately,
        queues Redis write for next async cycle."""
        self._fallback.setdefault(namespace, {})[key] = value
        if self._connected and self._redis:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.hset(namespace, key, value))
                else:
                    loop.run_until_complete(self.hset(namespace, key, value))
            except Exception:
                pass
        return True

    def hget_sync(self, namespace: str, key: str) -> Optional[Any]:
        """Synchronous hget — reads from fallback dict (always up-to-date)."""
        return self._fallback.get(namespace, {}).get(key)

    def hdel_sync(self, namespace: str, key: str) -> bool:
        """Synchronous hdel."""
        self._fallback.get(namespace, {}).pop(key, None)
        if self._connected and self._redis:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.hdel(namespace, key))
                else:
                    loop.run_until_complete(self.hdel(namespace, key))
            except Exception:
                pass
        return True

    def hgetall_sync(self, namespace: str) -> Dict[str, Any]:
        """Synchronous hgetall."""
        return dict(self._fallback.get(namespace, {}))

    # ── Info ─────────────────────────────────────────────────────

    async def info(self) -> Dict[str, Any]:
        """Get Redis connection info and stats."""
        result = {
            "connected": self._connected,
            "url": self._redis_url,
            "fallback_namespaces": list(self._fallback.keys()),
            "fallback_total_keys": sum(len(v) for v in self._fallback.values()),
        }
        if self._connected and self._redis:
            try:
                info = await self._redis.info("memory")
                result["redis_memory_used"] = info.get("used_memory_human", "unknown")
                result["redis_memory_peak"] = info.get("used_memory_peak_human", "unknown")
            except Exception:
                pass
        return result
