"""Safety tests for the native read-only Phase D database preflight."""

from __future__ import annotations

import pytest
from sqlalchemy.engine import make_url

from scripts.phase_d_readonly_db_preflight import derive_test_database_url


def test_preflight_retargets_only_approved_local_database() -> None:
    """A local source URL is always retargeted to sciscope_test_005."""
    target = derive_test_database_url(
        "postgresql+psycopg://sciscope:secret@localhost:5432/sciscope"
    )

    parsed = make_url(target)
    assert parsed.database == "sciscope_test_005"
    assert parsed.host == "localhost"


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://sciscope:secret@remote.example:5432/sciscope",
        "postgresql+psycopg://sciscope:secret@localhost:5432/sciscope_prod",
        "postgresql+psycopg://sciscope:secret@localhost:5433/sciscope",
    ],
)
def test_preflight_rejects_unapproved_url_source(url: str) -> None:
    """Remote, unexpected, or nonstandard endpoints fail before connecting."""
    with pytest.raises(ValueError, match="local target guard"):
        derive_test_database_url(url)
