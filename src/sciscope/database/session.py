"""Synchronous SQLAlchemy engine construction."""

from __future__ import annotations

from typing import Any, cast

from pgvector.psycopg import register_vector
from psycopg import Connection as PsycopgConnection
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.pool import ConnectionPoolEntry

from sciscope.database.config import DatabaseSettings


def create_database_engine(settings: DatabaseSettings) -> Engine:
    """Create a synchronous engine and register pgvector per connection."""
    engine = create_engine(settings.url, pool_pre_ping=True)

    @event.listens_for(engine, "connect")
    def register_vector_type(
        dbapi_connection: object,
        connection_record: ConnectionPoolEntry,
    ) -> None:
        del connection_record
        register_vector(cast(PsycopgConnection[Any], dbapi_connection))

    return engine
