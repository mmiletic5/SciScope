"""Deterministic retrieval test helpers with no external provider calls."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.engine import make_url


@dataclass
class FakeEmbedder:
    """Return a fixed vector and record requested text/configuration."""

    vector: Sequence[float]
    calls: list[tuple[str, object]]

    def embed_query(self, text: str, *, config: object) -> Sequence[float]:
        """Record a call and return the configured deterministic vector."""
        self.calls.append((text, config))
        return self.vector


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    """Provide a fixed nonzero vector without network access."""
    return FakeEmbedder((1.0,) + (0.0,) * 1535, [])


def independent_rrf_oracle(
    dense_ids: Sequence[str], lexical_ids: Sequence[str], constant: int = 60
) -> list[tuple[str, float, int]]:
    """Compute an independent expected RRF order from one-based ranks."""
    scores: dict[str, float] = {}
    best_ranks: dict[str, int] = {}
    for ids in (dense_ids, lexical_ids):
        for rank, chunk_id in enumerate(ids, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (constant + rank)
            best_ranks[chunk_id] = min(best_ranks.get(chunk_id, rank), rank)
    return sorted(
        (
            (chunk_id, score, best_ranks[chunk_id])
            for chunk_id, score in scores.items()
        ),
        key=lambda row: (-row[1], row[2], row[0]),
    )


@pytest.fixture(scope="session")
def retrieval_engine() -> Iterator[Engine]:
    """Provide read-only integration access to the explicitly authorized DB."""
    import os

    from sciscope.database.config import DatabaseSettings
    from sciscope.database.session import create_database_engine

    url = os.environ.get("SCISCOPE_TEST_DATABASE_URL", "")
    if not url or make_url(url).database != "sciscope_test_005":
        pytest.fail(
            "Retrieval integration tests require SCISCOPE_TEST_DATABASE_URL "
            "targeting sciscope_test_005",
            pytrace=False,
        )
    engine = create_database_engine(DatabaseSettings(url=url))
    try:
        with engine.connect() as connection:
            identity = connection.execute(
                text(
                    "SELECT current_database(), current_user, "
                    "current_setting('server_version_num')"
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
                identity[0] != "sciscope_test_005"
                or identity[1] != "sciscope"
                or not str(identity[2]).startswith("17")
                or extension != "0.8.7"
                or revision != "f005_pgvector_foundation"
            ):
                pytest.fail(
                    "Retrieval database preflight did not match Phase A test "
                    "database; no migration was attempted",
                    pytrace=False,
                )
            active_count = connection.execute(
                text("SELECT count(*) FROM delivery_imports WHERE is_active")
            ).scalar_one()
            if active_count != 1:
                pytest.fail(
                    "Retrieval integration tests require the preserved active "
                    "Phase A pilot snapshot; no database writes were attempted",
                    pytrace=False,
                )
        yield engine
    finally:
        engine.dispose()
