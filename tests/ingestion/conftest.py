"""Rollback-scoped real PostgreSQL fixtures for importer integration tests."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Connection, Engine, text
from sqlalchemy.engine import make_url

from sciscope.database.config import DatabaseSettings
from sciscope.database.session import create_database_engine


@pytest.fixture(scope="session")
def database_engine() -> Iterator[Engine]:
    """Connect only to the already-migrated authorized Feature 005 test DB."""
    url = os.environ.get("SCISCOPE_TEST_DATABASE_URL")
    if not url or make_url(url).database != "sciscope_test_005":
        pytest.fail(
            "Ingestion tests require SCISCOPE_TEST_DATABASE_URL targeting "
            "sciscope_test_005",
            pytrace=False,
        )
    engine = create_database_engine(DatabaseSettings(url=url))
    try:
        with engine.connect() as connection:
            identity = connection.execute(
                text(
                    "SELECT current_database() AS database_name, "
                    "current_user AS role_name, "
                    "current_setting('server_version_num') AS server_version"
                )
            ).one()
            extension = connection.execute(
                text(
                    "SELECT extversion FROM pg_extension WHERE extname='vector'"
                )
            ).scalar_one_or_none()
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one_or_none()
            if (
                identity.database_name != "sciscope_test_005"
                or identity.role_name != "sciscope"
                or not str(identity.server_version).startswith("17")
                or extension != "0.8.7"
                or revision != "f005_pgvector_foundation"
            ):
                pytest.fail(
                    "Ingestion database preflight did not match Feature 005",
                    pytrace=False,
                )
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def ingestion_connection(database_engine: Engine) -> Iterator[Connection]:
    """Yield only a confirmed sciscope_test_005 transaction, then roll back."""
    with database_engine.connect() as connection:
        transaction = connection.begin()
        try:
            database = connection.execute(
                text("SELECT current_database()")
            ).scalar_one()
            if database != "sciscope_test_005":
                pytest.fail(
                    "Ingestion integration tests require sciscope_test_005",
                    pytrace=False,
                )
            yield connection
        finally:
            transaction.rollback()
