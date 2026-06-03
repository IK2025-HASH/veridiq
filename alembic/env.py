import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so their metadata is registered for autogenerate
from app.database import Base  # noqa: E402
from app.models import generation, settings, user  # noqa: E402, F401

target_metadata = Base.metadata


def get_url() -> str:
    """Sync DB URL for Alembic — strips async driver prefix."""
    url = os.getenv("DATABASE_URL", "sqlite:///./veridiq.db")
    return (
        url
        .replace("sqlite+aiosqlite:///", "sqlite:///")
        .replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        .replace("postgres+asyncpg://", "postgresql+psycopg2://")
        .replace("postgres://", "postgresql+psycopg2://")
    )


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
