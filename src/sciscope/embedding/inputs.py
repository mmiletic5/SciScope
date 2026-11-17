"""Reusable strict chunk loading and exact-byte embedding provenance."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from sciscope.chunking.config import TEMPLATE_VERSION
from sciscope.chunking.counter import TokenCounter
from sciscope.chunking.output import CHUNK_RECORD_FIELDS
from sciscope.embedding.config import EmbeddingInputError


@dataclass(frozen=True, slots=True)
class ChunkInput:
    """A validated raw chunk preserving its original heading path."""

    chunk_id: str
    doi: str
    section_path: tuple[str, ...]
    text: str
    chunking_version: str
    token_counter_id: str
    template_version: str


@dataclass(frozen=True, slots=True)
class LoadedChunks:
    """File-ordered validated chunks and exact-byte source provenance."""

    chunks: tuple[ChunkInput, ...]
    chunks_sha256: str
    chunking_version: str
    token_counter_id: str
    template_version: str


def load_chunk_inputs(path: Path, counter: TokenCounter) -> LoadedChunks:
    """Read strict UTF-8 JSONL using only LF as a record delimiter."""
    raw: bytes | None = None
    try:
        raw = path.read_bytes()
    except OSError:
        pass
    if raw is None:
        raise EmbeddingInputError("chunks-unreadable")
    text: str | None = None
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        pass
    if text is None:
        raise EmbeddingInputError("chunks-invalid-utf8")
    if not text:
        raise EmbeddingInputError("chunks-empty")
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    chunks: list[ChunkInput] = []
    seen: set[str] = set()
    for line in lines:
        value: object = None
        valid_json = False
        try:
            value = json.loads(line, parse_constant=_reject_constant)
            valid_json = True
        except (ValueError, RecursionError):
            pass
        if not valid_json:
            raise EmbeddingInputError("chunks-invalid-json")
        chunk = _chunk_input(value)
        if chunk.chunk_id in seen:
            raise EmbeddingInputError("chunks-duplicate-id")
        seen.add(chunk.chunk_id)
        chunks.append(chunk)
    if len({chunk.chunking_version for chunk in chunks}) != 1:
        raise EmbeddingInputError("chunks-mixed-versions")
    if any(chunk.token_counter_id != counter.counter_id for chunk in chunks):
        raise EmbeddingInputError("counter-mismatch")
    if any(chunk.template_version != TEMPLATE_VERSION for chunk in chunks):
        raise EmbeddingInputError("template-mismatch")
    return LoadedChunks(
        tuple(chunks),
        hashlib.sha256(raw).hexdigest(),
        chunks[0].chunking_version,
        counter.counter_id,
        TEMPLATE_VERSION,
    )


def _reject_constant(value: str) -> object:
    """Reject NaN/Infinity without disclosing input content."""
    raise ValueError("invalid-json-constant")


def _chunk_input(value: object) -> ChunkInput:
    """Validate the exact chunk field set and required embedding primitives."""
    if not isinstance(value, dict) or set(value) != set(CHUNK_RECORD_FIELDS):
        raise EmbeddingInputError("chunks-bad-record")
    row = cast(dict[str, object], value)
    strings = (
        "chunk_id",
        "doi",
        "text",
        "text_sha256",
        "chunking_version",
        "token_counter_id",
        "template_version",
    )
    if any(not isinstance(row[name], str) for name in strings):
        raise EmbeddingInputError("chunks-bad-record")
    if any(_has_surrogate(cast(str, row[name])) for name in strings):
        raise EmbeddingInputError("chunks-bad-record")
    chunk_id = cast(str, row["chunk_id"])
    text = cast(str, row["text"])
    path = row["section_path"]
    if (
        re.fullmatch("[0-9a-f]{64}", chunk_id) is None
        or not text.strip()
        or row["text_sha256"] != hashlib.sha256(text.encode()).hexdigest()
        or not isinstance(path, list)
        or any(not isinstance(heading, str) for heading in path)
        or any(_has_surrogate(heading) for heading in cast(list[str], path))
        or not cast(str, row["chunking_version"]).strip()
    ):
        raise EmbeddingInputError("chunks-bad-record")
    return ChunkInput(
        chunk_id,
        cast(str, row["doi"]),
        tuple(cast(list[str], path)),
        text,
        cast(str, row["chunking_version"]),
        cast(str, row["token_counter_id"]),
        cast(str, row["template_version"]),
    )


def _has_surrogate(text: str) -> bool:
    """Detect JSON escape values that cannot be encoded as strict UTF-8."""
    return any(0xD800 <= ord(char) <= 0xDFFF for char in text)
