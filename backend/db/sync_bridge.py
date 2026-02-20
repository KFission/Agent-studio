"""
Shared async-to-sync bridge for DB-backed managers.
Avoids duplicating the ThreadPoolExecutor + asyncio.run pattern in every manager.
"""
import asyncio
import concurrent.futures
from typing import TypeVar, Coroutine, Any

T = TypeVar("T")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run an async coroutine from synchronous code.
    Handles both cases:
    - No running event loop → asyncio.run()
    - Inside a running event loop → offload to a thread pool
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


def get_session_factory():
    """Get the async session factory, returning None if unavailable."""
    try:
        from backend.db.engine import get_session_factory
        return get_session_factory()
    except Exception:
        return None
