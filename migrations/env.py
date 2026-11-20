"""Alembic environment with secret-safe application configuration."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

from sciscope.database.config import DatabaseSettings
from sciscope.database.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run SQL generation without opening a database connection."""
    settings = DatabaseSettings.from_environment()
    context.configure(
        url=settings.url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def preflight(connection: Connection) -> None:
    """Require PostgreSQL 17 before the revision starts its transaction."""
    version = connection.execute(text("SHOW server_version_num")).scalar_one()
    if not str(version).startswith("17"):
        raise RuntimeError("SciScope requires PostgreSQL major version 17")


def configure_and_run(connection: Connection) -> None:
    """Run the migration environment on a caller-owned connection."""
    preflight(connection)
    connection.commit()
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using the configured synchronous engine."""
    supplied_connection = config.attributes.get("connection")
    if supplied_connection is not None:
        configure_and_run(supplied_connection)
        return

    settings = DatabaseSettings.from_environment()
    # Migrations must connect before `vector` exists in a clean database.
    engine = create_engine(settings.url, pool_pre_ping=True)
    with engine.connect() as connection:
        configure_and_run(connection)
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
