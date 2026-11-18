"""Standalone delivery reader interfaces; Group F Phase 1 stubs only."""

from __future__ import annotations

import os
from collections.abc import Iterator


class DeliveryReadError(ValueError):
    """Expose a sanitized reader code without paths or record content."""

    code: str

    def __init__(self, code: str) -> None:
        """Declare the safe error interface for Phase 2 implementation."""
        raise NotImplementedError


def iter_jsonl(path: str | os.PathLike[str]) -> Iterator[dict[str, object]]:
    """Read ordered JSON objects using strict UTF-8 and LF-only boundaries."""
    raise NotImplementedError


def load_vectors(
    path: str | os.PathLike[str], *, dimensions: int, count: int
) -> tuple[tuple[float, ...], ...]:
    """Load an exactly sized finite little-endian float32 matrix."""
    raise NotImplementedError


def vectors_by_chunk_id(
    manifest_path: str | os.PathLike[str],
    vectors_path: str | os.PathLike[str],
    *,
    dimensions: int,
) -> dict[str, tuple[float, ...]]:
    """Associate vector rows exclusively with ordered manifest entry IDs."""
    raise NotImplementedError
