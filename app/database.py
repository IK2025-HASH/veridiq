# Copyright © 2026 Network Logic Limited. All rights reserved.

import asyncio
import logging

from sqlalchemy import create_engine as _create_sync_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    pool_pre_ping=not _is_sqlite,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def _sync_url(async_url: str) -> str:
    return (
        async_url
        .replace("sqlite+aiosqlite:///", "sqlite:///")
        .replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        .replace("postgres+asyncpg://", "postgresql+psycopg2://")
        # Railway sometimes provides plain postgres:// URLs
        .replace("postgres://", "postgresql+psycopg2://")
    )


async def create_tables():
    """Create all tables. Used on startup and in tests.

    Runs via a sync engine in a thread to avoid greenlet on Windows.
    On Railway (PostgreSQL) prefer running Alembic migrations instead —
    this function is the fallback for SQLite dev and CI.
    """
    # Import all models so their tables are registered on Base.metadata
    from app.models import generation, user  # noqa: F401
    from app.models import settings as _s

    def _sync_create():
        sync_engine = _create_sync_engine(_sync_url(settings.DATABASE_URL), echo=False)
        Base.metadata.create_all(sync_engine)
        sync_engine.dispose()

    await asyncio.to_thread(_sync_create)
    logger.info("Database tables ensured.")
