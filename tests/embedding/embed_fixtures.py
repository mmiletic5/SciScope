"""Synthetic offline helpers shared only by embedding contract tests."""

from __future__ import annotations

import hashlib
import io
import json
import struct
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self
from urllib.request import Request

from sciscope.chunking.config import TEMPLATE_VERSION
from sciscope.chunking.counter import Utf8BytesDiv3Counter
from sciscope.chunking.output import CHUNK_RECORD_FIELDS
from sciscope.embedding.config import DEFAULT_MODEL
from sciscope.embedding.openai_client import (
    TransportRequest,
    TransportResponse,
)

FAKE_KEY = "FAKEKEY_" + "z" * 105
FAKE_ENV = {"OPENAI_API_KEY": FAKE_KEY}
FIXED_DATE = "2026-11-17"


def response_body(
    vectors: Sequence[Sequence[object]] = ((1.0, 0.0),),
    *,
    prompt_tokens: int = 7,
    total_tokens: int = 7,
    model: str = DEFAULT_MODEL,
) -> dict[str, object]:
    """Build an indexed synthetic API response with declared usage."""
    return {
        "model": model,
        "data": [
            {"index": index, "embedding": list(vector)}
            for index, vector in enumerate(vectors)
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "total_tokens": total_tokens,
        },
    }


def response(
    status: int = 200,
    *,
    headers: Mapping[str, str] | None = None,
    body: object = None,
) -> TransportResponse:
    """Build a scripted response, using valid synthetic JSON by default."""
    return TransportResponse(
        status, headers or {}, response_body() if body is None else body
    )


@dataclass
class ScriptedTransport:
    """Record requests and consume explicit offline responses or failures."""

    script: list[TransportResponse | Exception]
    calls: list[TransportRequest] = field(default_factory=list)

    def post_json(self, request: TransportRequest) -> TransportResponse:
        """Return the next response or raise the next scripted failure."""
        self.calls.append(request)
        assert self.script, "Unexpected transport call"
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@dataclass
class RetryClock:
    """Record sleeps and jitter bounds with a controllable monotonic clock."""

    now: float = 0.0
    use_maximum_jitter: bool = False
    sleeps: list[float] = field(default_factory=list)
    jitter_bounds: list[tuple[float, float]] = field(default_factory=list)

    def sleep(self, seconds: float) -> None:
        """Advance the clock without waiting."""
        self.sleeps.append(seconds)
        self.now += seconds

    def monotonic(self) -> float:
        """Return the synthetic elapsed time."""
        return self.now

    def uniform(self, low: float, high: float) -> float:
        """Select an endpoint of the requested jitter interval."""
        self.jitter_bounds.append((low, high))
        return high if self.use_maximum_jitter else low


class FakeHttpResponse:
    """Expose bounded reads from synthetic bytes without a socket."""

    def __init__(
        self,
        body: bytes,
        status: int = 200,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """Keep response bytes, status, and synthetic HTTP headers."""
        self.stream = io.BytesIO(body)
        self.status = status
        self.headers = headers or {}
        self.read_sizes: list[int] = []

    def read(self, size: int = -1) -> bytes:
        """Record read bounds before consuming bytes."""
        self.read_sizes.append(size)
        return self.stream.read(size)

    def __enter__(self) -> Self:
        """Enter the fake response context."""
        return self

    def __exit__(self, *args: object) -> None:
        """Close the synthetic response body."""
        self.close()

    def close(self) -> None:
        """Support cleanup when this response is wrapped in HTTPError."""
        self.stream.close()


@dataclass
class FakeOpenUrl:
    """Record an injected urllib request without opening a connection."""

    outcome: FakeHttpResponse | Exception
    calls: list[tuple[Request, float]] = field(default_factory=list)

    def __call__(self, request: Request, *, timeout: float) -> FakeHttpResponse:
        """Return or raise the configured outcome."""
        self.calls.append((request, timeout))
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def json_bytes(value: object) -> bytes:
    """Serialize synthetic values using the transport's ASCII default."""
    return json.dumps(value).encode("utf-8")


def assert_sanitized(error: BaseException) -> None:
    """Check exception values and chains for the distinctive fake secret."""
    rendered = " ".join((str(error), repr(error), repr(error.args)))
    for forbidden in (FAKE_KEY, FAKE_KEY[:8], str(len(FAKE_KEY))):
        assert forbidden not in rendered
    assert error.__cause__ is None
    assert error.__context__ is None


def synthetic_record(
    index: int = 0, text: str | None = None
) -> dict[str, object]:
    """Build one complete chunk record containing invented sentences only."""
    text = text if text is not None else f"Synthetic sentence number {index}."
    record: dict[str, object] = {
        "chunk_id": hashlib.sha256(f"synthetic-{index}".encode()).hexdigest(),
        "doi": "10.0000/synthetic.offline",
        "xml_sha256": "a" * 64,
        "section_id": "synthetic-section",
        "ordinal": index + 1,
        "chunk_kind": "paragraph",
        "normalized_type": "methods",
        "section_path": ["(untitled)", "Synthetic heading"],
        "text": text,
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "spans": [
            {
                "source_locator": "synthetic-locator",
                "paragraph_index": index + 1,
                "start": 0,
                "end": len(text),
            }
        ],
        "source_locator": "synthetic-locator",
        "content_tokens": Utf8BytesDiv3Counter().count(text),
        "hard_split": False,
        "omitted": [],
        "chunking_version": "chunking-v1",
        "token_counter_id": "utf8-bytes-div3-v1",
        "template_version": TEMPLATE_VERSION,
    }
    assert tuple(record) == CHUNK_RECORD_FIELDS
    return record


def write_chunks(
    directory: Path, records: Sequence[Mapping[str, object]]
) -> Path:
    """Write synthetic LF-delimited chunks in explicitly supplied order."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "chunks.jsonl"
    path.write_bytes(
        "".join(
            json.dumps(row, ensure_ascii=False) + "\n" for row in records
        ).encode("utf-8")
    )
    return path


@dataclass
class AdditiveTransport:
    """Return deterministic vectors and additive or scripted batch usage."""

    fail_on_call: int | None = None
    reversed_indices: bool = False
    usage_values: list[tuple[int, int]] = field(default_factory=list)
    calls: list[TransportRequest] = field(default_factory=list)

    def post_json(self, request: TransportRequest) -> TransportResponse:
        """Embed text-derived synthetic vectors or fail the selected call."""
        self.calls.append(request)
        if self.fail_on_call == len(self.calls):
            return TransportResponse(401, {}, {"error": {"code": "offline"}})
        texts = request.payload["input"]
        assert isinstance(texts, list) and all(
            isinstance(t, str) for t in texts
        )
        dimensions = request.payload["dimensions"]
        assert isinstance(dimensions, int)
        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.encode()).digest()
            vector = [0.0] * dimensions
            vector[digest[0] % dimensions] = 1.0
            vectors.append(vector)
        prompt, total = (
            self.usage_values.pop(0)
            if self.usage_values
            else (len(texts) * 2, len(texts) * 3)
        )
        body = response_body(vectors, prompt_tokens=prompt, total_tokens=total)
        if self.reversed_indices:
            data = body["data"]
            assert isinstance(data, list)
            body["data"] = list(reversed(data))
        return TransportResponse(
            200, {"x-ratelimit-remaining-tokens": "99"}, body
        )


def f32_bytes(values: Sequence[float]) -> bytes:
    """Produce independently specified little-endian float32 bytes."""
    return struct.pack("<" + "f" * len(values), *values)
