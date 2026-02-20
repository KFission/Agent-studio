"""
Async SQLAlchemy engine and session factory.
Uses asyncpg driver for PostgreSQL.
Engine is lazily created on first use to avoid import-time connection failures.
"""
import logging
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.config.settings import settings

logger = logging.getLogger(__name__)

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker] = None


def get_engine() -> AsyncEngine:
    """Lazily create and return the async engine singleton."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.environment == "dev",
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,
            connect_args={"ssl": "disable"},
        )
        logger.info(f"Created async engine for {settings.database_url.split('@')[-1]}")
    return _engine


def get_session_factory() -> async_sessionmaker:
    """Lazily create and return the session factory singleton."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def dispose_engine() -> None:
    """Dispose the engine on shutdown (call from lifespan)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Async engine disposed")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async DB session per request."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
