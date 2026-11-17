"""Bounded sanitized OpenAI transport and sequential retrying client."""

from __future__ import annotations

import json
import math
import random
import re
import time
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from email.message import Message
from types import TracebackType
from typing import IO, Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request

from sciscope.embedding.config import (
    DEFAULT_BASE_URL,
    EmbeddingConfig,
    EmbeddingConfigError,
    EmbeddingProviderError,
)
from sciscope.embedding.provider import (
    EmbeddingResult,
    EmbeddingUsage,
    _validate_inputs,
)


@dataclass(frozen=True, slots=True)
class TransportRequest:
    """A JSON payload and timeout without connection credentials or URL."""

    payload: Mapping[str, object]
    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class TransportResponse:
    """HTTP status, sanitized allowlisted headers, and parsed JSON or None."""

    status: int
    headers: Mapping[str, str]
    body: object


class Transport(Protocol):
    """Post one JSON request through an owned connection."""

    def post_json(self, request: TransportRequest) -> TransportResponse:
        """Return a sanitized response or raise a sanitized transport error."""
        ...


class TransportTimeout(Exception):
    """A sanitized timeout without a message or exception chain."""


class TransportConnectionError(Exception):
    """A sanitized connection failure without a message or exception chain."""


class HttpResponse(Protocol):
    """Minimal context-managed urllib response used by the injected opener."""

    status: int
    headers: Mapping[str, str]

    def read(self, size: int = -1) -> bytes:
        """Read at most the specified number of bytes."""
        ...

    def __enter__(self) -> HttpResponse:
        """Enter the response context."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the response context."""
        ...


class OpenUrl(Protocol):
    """Inject a request opener without permitting implicit test networking."""

    def __call__(self, request: Request, *, timeout: float) -> HttpResponse:
        """Open a request with an explicit timeout."""
        ...


@dataclass(frozen=True, slots=True)
class OpenAIConnection:
    """Private connection data excluded from object representations."""

    api_key: str = field(repr=False)
    url: str = field(repr=False)
    custom_base_url_used: bool = False


class UrllibTransport:
    """Own a connection and bound reads while refusing all redirects."""

    def __init__(
        self,
        connection: OpenAIConnection,
        *,
        open_url: OpenUrl | None = None,
        max_response_bytes: int = 16 * 1024 * 1024,
    ) -> None:
        """Configure the connection and an optional injected offline opener."""
        self._connection = connection
        self._open_url = open_url or _default_open_url
        self._max_response_bytes = max_response_bytes

    def __repr__(self) -> str:
        """Describe the transport without connection data or addresses."""
        return "UrllibTransport()"

    def post_json(self, request: TransportRequest) -> TransportResponse:
        """Post bounded JSON with sanitized headers and errors."""
        failure: type[TransportTimeout] | type[TransportConnectionError]
        try:
            sent = Request(
                self._connection.url,
                data=json.dumps(dict(request.payload)).encode("utf-8"),
                headers={
                    "Authorization": "Bearer " + self._connection.api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "sciscope-embed/0",
                },
                method="POST",
            )
            try:
                with self._open_url(
                    sent, timeout=request.timeout_seconds
                ) as result:
                    return TransportResponse(
                        result.status,
                        _safe_headers(result.headers),
                        _read_body(result.read, self._max_response_bytes),
                    )
            except HTTPError as error:
                try:
                    body = _read_body(error.read, self._max_response_bytes)
                    return TransportResponse(
                        error.code,
                        _safe_headers(dict(error.headers.items())),
                        _error_discriminators(body),
                    )
                finally:
                    error.close()
        except TimeoutError:
            failure = TransportTimeout
        except URLError as error:
            failure = (
                TransportTimeout
                if isinstance(error.reason, TimeoutError)
                else TransportConnectionError
            )
        except Exception:
            failure = TransportConnectionError
        raise failure() from None


class _RefuseRedirects(urllib.request.HTTPRedirectHandler):
    """Keep Authorization on the configured endpoint by refusing redirects."""

    def redirect_request(
        self,
        req: Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: Message,
        newurl: str,
    ) -> None:
        """Refuse every redirect before a second request can be constructed."""
        return None


def _default_open_url(request: Request, *, timeout: float) -> HttpResponse:
    """Open with redirect refusal, without using global urllib opener state."""
    opener = urllib.request.build_opener(_RefuseRedirects())
    return cast(HttpResponse, opener.open(request, timeout=timeout))


def _safe_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Return only allowlisted names and short printable ASCII values."""
    return {
        name.lower(): value
        for name, value in headers.items()
        if (
            name.lower() == "retry-after"
            or name.lower().startswith("x-ratelimit-")
        )
        and len(value) <= 64
        and all(0x20 <= ord(char) <= 0x7E for char in value)
    }


def _reject_constant(value: str) -> object:
    """Reject nonstandard JSON numbers without echoing the input."""
    raise ValueError("invalid-json-constant")


def _read_body(read: Callable[[int], bytes], maximum: int) -> object:
    """Read bounded response bytes and parse strict JSON without raw errors."""
    raw = read(maximum + 1)
    if len(raw) > maximum:
        return None
    try:
        value: object = json.loads(
            raw.decode("utf-8"), parse_constant=_reject_constant
        )
        return value
    except (ValueError, UnicodeError, RecursionError):
        return None


def _object(value: object) -> dict[str, object] | None:
    """Narrow a parsed JSON object without propagating dynamic JSON types."""
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return None


def _error_discriminators(body: object) -> object:
    """Discard HTTP error prose and retain only code/type discriminators."""
    obj = _object(body)
    error = _object(obj.get("error")) if obj is not None else None
    if error is None:
        return None
    return {
        "error": {
            name: error[name]
            for name in ("code", "type")
            if isinstance(error.get(name), str)
        }
    }


class OpenAIEmbedder:
    """Validate indexed embeddings and apply bounded injectable retries."""

    provider_id: str = "openai"
    model: str
    dimensions: int

    def __init__(
        self,
        config: EmbeddingConfig,
        transport: Transport,
        *,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        uniform: Callable[[float, float], float] = random.uniform,
    ) -> None:
        """Configure a client without reading any environment variables."""
        self._config = config
        self._transport = transport
        self._sleep = sleep
        self._monotonic = monotonic
        self._uniform = uniform
        self.model = config.model
        self.dimensions = config.dimensions

    def embed_passages(self, texts: Sequence[str]) -> EmbeddingResult:
        """Embed final passages unchanged and validate before returning."""
        _validate_inputs(texts, self._config.max_inputs_per_request)
        request = TransportRequest(
            {
                "model": self.model,
                "input": list(texts),
                "dimensions": self.dimensions,
                "encoding_format": "float",
            },
            self._config.request_timeout_seconds,
        )
        start = self._monotonic()
        base = min(
            self._config.initial_backoff_seconds,
            self._config.max_backoff_seconds,
        )
        for attempt in range(1, self._config.max_attempts + 1):
            response: TransportResponse | None = None
            try:
                response = self._transport.post_json(request)
            except (TransportTimeout, TransportConnectionError):
                pass
            if response is not None:
                if 200 <= response.status < 300:
                    return self._validate_response(
                        response, len(texts), attempt
                    )
                self._classify_status(response)
            if attempt == self._config.max_attempts:
                raise EmbeddingProviderError("retry-exhausted")
            retry_after = _retry_after(response.headers) if response else 0.0
            delay = max(retry_after, base + self._uniform(0, base * 0.25))
            if (
                self._monotonic() - start + delay
                > self._config.max_total_retry_seconds
            ):
                raise EmbeddingProviderError("retry-budget-exceeded")
            self._sleep(delay)
            base = min(self._config.max_backoff_seconds, base * 2)
        raise AssertionError("unreachable-attempt-loop")

    def embed_queries(self, queries: Sequence[str]) -> EmbeddingResult:
        """Prepend the query prefix once and embed validated inputs."""
        _validate_inputs(queries, self._config.max_inputs_per_request)
        return self.embed_passages(
            [self._config.query_prefix + query for query in queries]
        )

    def _classify_status(self, response: TransportResponse) -> None:
        """Raise for permanent HTTP failures and return for retryable ones."""
        status = response.status
        if status == 429:
            obj = _object(response.body)
            error = _object(obj.get("error")) if obj is not None else None
            if error is not None and "insufficient_quota" in (
                error.get("code"),
                error.get("type"),
            ):
                raise EmbeddingProviderError("quota-exceeded")
            return
        if 500 <= status < 600:
            return
        codes = {
            400: "request-rejected",
            401: "authentication-failed",
            403: "permission-denied",
            404: "endpoint-or-model-not-found",
        }
        code = (
            "unexpected-redirect"
            if 300 <= status < 400
            else codes.get(status, f"http-{status}")
        )
        raise EmbeddingProviderError(code)

    def _validate_response(
        self, response: TransportResponse, count: int, attempts: int
    ) -> EmbeddingResult:
        """Validate response shape, model, indexed vectors, and usage."""
        if response.body is None:
            raise EmbeddingProviderError("response-not-json")
        obj = _object(response.body)
        if (
            obj is None
            or not isinstance(obj.get("model"), str)
            or not isinstance(obj.get("data"), list)
        ):
            raise EmbeddingProviderError("response-shape")
        if obj["model"] != self.model:
            raise EmbeddingProviderError("response-model-mismatch")
        data = cast(list[object], obj["data"])
        items: list[tuple[int, list[object]]] = []
        for value in data:
            item = _object(value)
            if (
                item is None
                or type(item.get("index")) is not int
                or not isinstance(item.get("embedding"), list)
            ):
                raise EmbeddingProviderError("response-shape")
            items.append(
                (
                    cast(int, item["index"]),
                    cast(list[object], item["embedding"]),
                )
            )
        if len(items) != count:
            raise EmbeddingProviderError("response-count")
        items.sort(key=lambda item: item[0])
        if [index for index, _ in items] != list(range(count)):
            raise EmbeddingProviderError("response-index")
        vectors: list[tuple[float, ...]] = []
        for _, values in items:
            if len(values) != self.dimensions:
                raise EmbeddingProviderError("response-dimensions")
            vector: list[float] = []
            for element in values:
                if type(element) not in (int, float):
                    raise EmbeddingProviderError("response-nonfinite")
                numeric = cast(float | int, element)
                finite = False
                try:
                    finite = math.isfinite(numeric)
                except OverflowError:
                    pass
                if not finite:
                    raise EmbeddingProviderError("response-nonfinite")
                vector.append(float(numeric))
            vectors.append(tuple(vector))
        usage = _object(obj.get("usage"))
        if usage is None or any(
            type(usage.get(key)) is not int or cast(int, usage[key]) < 0
            for key in ("prompt_tokens", "total_tokens")
        ):
            raise EmbeddingProviderError("response-usage")
        return EmbeddingResult(
            tuple(vectors),
            EmbeddingUsage(
                cast(int, usage["prompt_tokens"]),
                cast(int, usage["total_tokens"]),
            ),
            _safe_headers(response.headers),
            attempts,
        )


def _retry_after(headers: Mapping[str, str]) -> float:
    """Accept bounded plain decimal Retry-After seconds only."""
    value = _safe_headers(headers).get("retry-after", "")
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value) is None:
        return 0.0
    seconds = float(value)
    return seconds if math.isfinite(seconds) and seconds <= 3600 else 0.0


def read_api_key(environ: Mapping[str, str]) -> str:
    """Read and validate a key only from the injected process mapping."""
    key = environ.get("OPENAI_API_KEY", "")
    if not key.strip():
        raise EmbeddingConfigError("missing-api-key")
    if any(not 0x21 <= ord(char) <= 0x7E for char in key):
        raise EmbeddingConfigError("invalid-api-key")
    return key


def read_base_url(environ: Mapping[str, str]) -> tuple[str, bool]:
    """Read a safe normalized HTTPS base and report custom-base use."""
    base = environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL)
    normalized: str | None = None
    try:
        parts = urlsplit(base)
        if (
            parts.scheme == "https"
            and parts.hostname
            and parts.netloc
            and parts.username is None
            and parts.password is None
            and not parts.query
            and not parts.fragment
            and "?" not in base
            and "#" not in base
            and all(0x21 <= ord(char) <= 0x7E for char in base)
        ):
            port = parts.port
            host = parts.hostname.lower()
            if ":" in host:
                host = "[" + host + "]"
            authority = host + (f":{port}" if port not in (None, 443) else "")
            normalized = urlunsplit(
                ("https", authority, parts.path.rstrip("/"), "", "")
            )
    except ValueError:
        pass
    if normalized is None:
        raise EmbeddingConfigError("invalid-base-url")
    return normalized, normalized != DEFAULT_BASE_URL


def embeddings_url(base: str) -> str:
    """Compose the embeddings endpoint without duplicating a v1 suffix."""
    base = base.rstrip("/")
    return base + (
        "/embeddings"
        if urlsplit(base).path.endswith("/v1")
        else "/v1/embeddings"
    )
