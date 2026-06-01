# Copyright © 2026 Network Logic Limited. All rights reserved.
# Reads/writes app configuration from the database.
# Uses synchronous SQLAlchemy in asyncio.to_thread to avoid greenlet on Windows.

import asyncio
import base64
import hashlib
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

ENCRYPTED_KEYS = {"anthropic_api_key", "smtp_password", "linkedin_client_secret"}

_cache: dict[str, str] = {}
_cache_loaded = False


def _get_db_url() -> str:
    url = settings.DATABASE_URL
    return (
        url
        .replace("sqlite+aiosqlite:///", "sqlite:///")
        .replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        .replace("postgres+asyncpg://", "postgresql+psycopg2://")
    )


def _get_cipher():
    from cryptography.fernet import Fernet
    raw = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(raw))


def _encrypt(value: str) -> str:
    return _get_cipher().encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    try:
        return _get_cipher().decrypt(value.encode()).decode()
    except Exception:
        return value


def _sync_load_all() -> dict:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    engine = create_engine(_get_db_url(), echo=False)
    try:
        with Session(engine) as session:
            rows = session.execute(text("SELECT key, value FROM app_settings")).fetchall()
            result = {}
            for key, value in rows:
                if key in ENCRYPTED_KEYS and value:
                    result[key] = _decrypt(value)
                else:
                    result[key] = value or ""
            return result
    except Exception as e:
        logger.warning(f"settings load failed: {e}")
        return {}
    finally:
        engine.dispose()


def _sync_set_many(data: dict) -> None:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    engine = create_engine(_get_db_url(), echo=False)
    try:
        with Session(engine) as session:
            for key, value in data.items():
                stored = _encrypt(value) if key in ENCRYPTED_KEYS else value
                existing = session.execute(
                    text("SELECT id FROM app_settings WHERE key = :k"), {"k": key}
                ).fetchone()
                if existing:
                    session.execute(
                        text("UPDATE app_settings SET value = :v, updated_at = CURRENT_TIMESTAMP WHERE key = :k"),
                        {"v": stored, "k": key}
                    )
                else:
                    import uuid
                    session.execute(
                        text("INSERT INTO app_settings (id, key, value, updated_at) VALUES (:id, :k, :v, CURRENT_TIMESTAMP)"),
                        {"id": str(uuid.uuid4()), "k": key, "v": stored}
                    )
            session.commit()
    finally:
        engine.dispose()


async def load_all() -> None:
    global _cache, _cache_loaded
    try:
        _cache = await asyncio.to_thread(_sync_load_all)
    except Exception as e:
        logger.warning(f"settings_service.load_all failed: {e}")
    _cache_loaded = True


async def get(key: str) -> Optional[str]:
    if not _cache_loaded:
        await load_all()
    return _cache.get(key) or None


async def set(key: str, value: str) -> None:
    await set_many({key: value})


async def set_many(data: dict[str, str]) -> None:
    await asyncio.to_thread(_sync_set_many, data)
    _cache.update(data)


async def is_setup_complete() -> bool:
    try:
        val = await asyncio.to_thread(_sync_load_all)
        return val.get("setup_complete") == "true"
    except Exception:
        return False
