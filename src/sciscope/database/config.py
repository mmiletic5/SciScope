"""Secret-safe database settings."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True, repr=False)
class DatabaseSettings:
    """Connection settings for the synchronous PostgreSQL engine."""

    url: str = field(repr=False)

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> DatabaseSettings:
        """Load the database URL without exposing it in errors or repr."""
        environment = os.environ if environ is None else environ
        url = environment.get("DATABASE_URL", "").strip()
        if not url:
            raise ValueError("DATABASE_URL must be configured")
        if "@" in url and "://" in url:
            authority = url.split("://", 1)[1].split("/", 1)[0]
            if "@" in authority and ":" not in authority.rsplit("@", 1)[0]:
                raise ValueError(
                    "DATABASE_URL must include a valid credential format"
                )
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
        elif not url.startswith("postgresql+psycopg://"):
            raise ValueError(
                "DATABASE_URL must use the PostgreSQL psycopg driver"
            )
        return cls(url=url)
