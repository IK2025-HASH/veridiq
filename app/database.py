# Copyright © 2026 Network Logic Limited. All rights reserved.

import asyncio
from sqlalchemy import create_engine as _create_sync_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    # pool_pre_ping not supported on SQLite
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


async def create_tables():
    from app.models.settings import AppSetting  # noqa: F401

    # Always use a sync engine in a thread — avoids greenlet entirely on all platforms.
    def _sync_create():
        sync_url = (
            settings.DATABASE_URL
            .replace("sqlite+aiosqlite:///", "sqlite:///")
            .replace("postgresql+asyncpg://", "postgresql+psycopg2://")
            .replace("postgres+asyncpg://", "postgresql+psycopg2://")
        )
        sync_engine = _create_sync_engine(sync_url, echo=False)
        Base.metadata.create_all(sync_engine, tables=[AppSetting.__table__])
        sync_engine.dispose()

    await asyncio.to_thread(_sync_create)
