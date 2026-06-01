# Copyright © 2026 Network Logic Limited. All rights reserved.
# Reads/writes app configuration from the database.
# Sensitive values are encrypted at rest using a key derived from SECRET_KEY.

import base64
import hashlib
import logging
from typing import Optional
from sqlalchemy import select
from cryptography.fernet import Fernet

from app.config import settings
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

ENCRYPTED_KEYS = {"anthropic_api_key", "smtp_password", "linkedin_client_secret"}

_cache: dict[str, str] = {}
_cache_loaded = False


def _get_cipher() -> Fernet:
    raw = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(raw))


def _encrypt(value: str) -> str:
    return _get_cipher().encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    try:
        return _get_cipher().decrypt(value.encode()).decode()
    except Exception:
        return value


async def load_all() -> None:
    """Load all settings from DB into the in-memory cache."""
    global _cache, _cache_loaded
    from app.models.settings import AppSetting
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(AppSetting))
            rows = result.scalars().all()
            _cache = {}
            for row in rows:
                if row.key in ENCRYPTED_KEYS and row.value:
                    _cache[row.key] = _decrypt(row.value)
                else:
                    _cache[row.key] = row.value or ""
        _cache_loaded = True
    except Exception as e:
        logger.warning(f"settings_service.load_all failed: {e}")
        _cache_loaded = True


async def get(key: str) -> Optional[str]:
    if not _cache_loaded:
        await load_all()
    return _cache.get(key) or None


async def set(key: str, value: str) -> None:
    from app.models.settings import AppSetting
    async with AsyncSessionLocal() as db:
        stored = _encrypt(value) if key in ENCRYPTED_KEYS else value
        result = await db.execute(select(AppSetting).where(AppSetting.key == key))
        row = result.scalar_one_or_none()
        if row:
            row.value = stored
        else:
            db.add(AppSetting(key=key, value=stored))
        await db.commit()
    _cache[key] = value


async def set_many(data: dict[str, str]) -> None:
    from app.models.settings import AppSetting
    async with AsyncSessionLocal() as db:
        for key, value in data.items():
            stored = _encrypt(value) if key in ENCRYPTED_KEYS else value
            result = await db.execute(select(AppSetting).where(AppSetting.key == key))
            row = result.scalar_one_or_none()
            if row:
                row.value = stored
            else:
                db.add(AppSetting(key=key, value=stored))
        await db.commit()
    _cache.update(data)


async def is_setup_complete() -> bool:
    from app.models.settings import AppSetting
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AppSetting).where(AppSetting.key == "setup_complete")
            )
            row = result.scalar_one_or_none()
            return row is not None and row.value == "true"
    except Exception:
        return False
