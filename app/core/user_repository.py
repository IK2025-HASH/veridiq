# Copyright © 2026 Network Logic Limited. All rights reserved.
# DB persistence for user accounts.
# Follows the same sync-in-thread pattern as settings_service.py
# to avoid greenlet on Windows.

import asyncio
import logging
import uuid
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)


def _get_sync_url() -> str:
    url = settings.DATABASE_URL
    return (
        url
        .replace("sqlite+aiosqlite:///", "sqlite:///")
        .replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        .replace("postgres+asyncpg://", "postgresql+psycopg2://")
        .replace("postgres://", "postgresql+psycopg2://")
    )


def _row_to_dict(row) -> dict:
    """Convert a UserAccount ORM row to the dict format used by USERS."""
    return {
        "id":                  str(row.id),
        "email":               row.email,
        "hashed_password":     row.hashed_password,
        "display_name":        row.display_name,
        "avatar_url":          row.avatar_url,
        "phone":               row.phone,
        "account_type":        row.account_type,
        "tier":                row.tier,
        "credit_balance":      row.credit_balance,
        "credits_used_month":  row.credits_used_month,
        "credits_used_total":  row.credits_used_total,
        "team_id":             str(row.team_id) if row.team_id else None,
        "team_role":           row.team_role,
        "email_verified":      row.email_verified,
        "is_active":           row.is_active,
        "is_admin":            row.is_admin,
        "classified_mode":     row.classified_mode,
        "billing_name":        row.billing_name,
        "billing_address":     row.billing_address,
        "billing_vat":         row.billing_vat,
        "company_name":        row.company_name,
        "two_fa_enabled":      False,   # stored in settings table for now
        "created_at":          row.created_at.isoformat() if row.created_at else None,
        "last_login":          row.last_login.isoformat() if row.last_login else None,
    }


async def save(user_dict: dict) -> None:
    """Insert or update a user in user_accounts.

    Upserts by user id — safe to call on re-registration or after profile update.
    """
    def _sync():
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import Session

        from app.models.user import UserAccount

        engine = create_engine(_get_sync_url(), echo=False)
        with Session(engine) as session:
            uid = uuid.UUID(user_dict["id"]) if isinstance(user_dict["id"], str) else user_dict["id"]
            existing = session.get(UserAccount, uid)
            if existing:
                # Update mutable fields only
                existing.email            = user_dict.get("email", existing.email)
                existing.hashed_password  = user_dict.get("hashed_password", existing.hashed_password) or existing.hashed_password
                existing.display_name     = user_dict.get("display_name", existing.display_name)
                existing.avatar_url       = user_dict.get("avatar_url")
                existing.phone            = user_dict.get("phone")
                existing.account_type     = user_dict.get("account_type", existing.account_type)
                existing.tier             = user_dict.get("tier", existing.tier)
                existing.credit_balance   = user_dict.get("credit_balance", existing.credit_balance)
                existing.is_active        = user_dict.get("is_active", existing.is_active)
                existing.is_admin         = user_dict.get("is_admin", existing.is_admin)
                existing.classified_mode  = user_dict.get("classified_mode", existing.classified_mode)
                existing.billing_name     = user_dict.get("billing_name")
                existing.billing_address  = user_dict.get("billing_address")
                existing.billing_vat      = user_dict.get("billing_vat")
                existing.company_name     = user_dict.get("company_name")
                existing.email_verified   = user_dict.get("email_verified", existing.email_verified)
            else:
                row = UserAccount(
                    id=uid,
                    email=user_dict["email"],
                    hashed_password=user_dict.get("hashed_password") or "",
                    display_name=user_dict.get("display_name", ""),
                    avatar_url=user_dict.get("avatar_url"),
                    phone=user_dict.get("phone"),
                    account_type=user_dict.get("account_type", "individual"),
                    tier=user_dict.get("tier", "free"),
                    credit_balance=user_dict.get("credit_balance", 50),
                    credits_used_month=user_dict.get("credits_used_month", 0),
                    credits_used_total=user_dict.get("credits_used_total", 0),
                    email_verified=user_dict.get("email_verified", False),
                    is_active=user_dict.get("is_active", True),
                    is_admin=user_dict.get("is_admin", False),
                    classified_mode=user_dict.get("classified_mode", False),
                    billing_name=user_dict.get("billing_name"),
                    billing_address=user_dict.get("billing_address"),
                    billing_vat=user_dict.get("billing_vat"),
                    company_name=user_dict.get("company_name"),
                    created_at=datetime.utcnow(),
                )
                session.add(row)
            session.commit()
        engine.dispose()

    try:
        await asyncio.to_thread(_sync)
    except Exception as exc:
        logger.warning(f"user_repository.save failed for {user_dict.get('email')}: {exc}")


async def load_all() -> list[dict]:
    """Return all active users from user_accounts as dicts."""
    def _sync() -> list[dict]:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from app.models.user import UserAccount

        engine = create_engine(_get_sync_url(), echo=False)
        with Session(engine) as session:
            rows = session.query(UserAccount).filter(UserAccount.is_active == True).all()  # noqa: E712
            result = [_row_to_dict(r) for r in rows]
        engine.dispose()
        return result

    try:
        return await asyncio.to_thread(_sync)
    except Exception as exc:
        logger.warning(f"user_repository.load_all failed: {exc}")
        return []


async def update_last_login(user_id: str) -> None:
    """Stamp last_login timestamp on a user row."""
    def _sync():
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from app.models.user import UserAccount

        engine = create_engine(_get_sync_url(), echo=False)
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        with Session(engine) as session:
            row = session.get(UserAccount, uid)
            if row:
                row.last_login = datetime.utcnow()
                session.commit()
        engine.dispose()

    try:
        await asyncio.to_thread(_sync)
    except Exception as exc:
        logger.warning(f"user_repository.update_last_login failed: {exc}")
