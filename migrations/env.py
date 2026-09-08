"""Alembic environment configuration for HealthFlow."""

import os
from logging.config import fileConfig

# Import models to ensure all tables are registered on Base.metadata
import healthflow_infrastructure.models  # noqa: F401
from alembic import context
from healthflow_infrastructure.database import DEFAULT_DATABASE_URL, Base
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Retrieve database URL from alembic config, environment, or the default.

    Config takes priority over the DATABASE_URL environment variable so that programmatic callers
    (e.g. tests isolating themselves to a separate database via
    `Config.set_main_option("sqlalchemy.url", ...)`) are never silently overridden by whatever
    DATABASE_URL happens to be set in the ambient shell — see
    docs/phases/PHASE_06_WALKTHROUGH.md for the bug this previously caused (the migration test
    always operated on the real dev database instead of its isolated test database whenever a
    developer had DATABASE_URL exported, which is the project's own documented normal workflow).
    """
    url = (
        config.get_main_option("sqlalchemy.url")
        or os.getenv("DATABASE_URL")
        or DEFAULT_DATABASE_URL
    )
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
