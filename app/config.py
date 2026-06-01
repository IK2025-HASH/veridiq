# Copyright © 2026 Network Logic Limited. All rights reserved.

from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "Verid-iq"
    APP_TAGLINE: str = "AI-Powered Test Intelligence for Jira"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "change-me-in-production"

    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    MAX_TOKENS: int = 4096

    # SQLite by default (local) — Railway injects a real PostgreSQL URL automatically
    DATABASE_URL: str = "sqlite+aiosqlite:///./veridiq.db"

    RATE_LIMIT_PER_DAY: int = 5

    KNOWLEDGE_DIR: Path = Path(__file__).parent.parent / "knowledge_volumes"

    # LinkedIn OAuth
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""
    LINKEDIN_REDIRECT_URI: str = "https://veridiq.networklogic.uk/auth/linkedin/callback"

    BASE_URL: str = "https://veridiq.networklogic.uk"

    # Email (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "no-reply@networklogic.uk"

    model_config = {"env_file": ".env", "case_sensitive": True}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
