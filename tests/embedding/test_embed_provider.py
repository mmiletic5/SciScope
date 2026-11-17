"""T005 synthetic offline RED contracts for configuration and providers."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import replace
from typing import cast

import pytest
from embed_fixtures import (
    FAKE_ENV,
    FAKE_KEY,
    RetryClock,
    ScriptedTransport,
    assert_sanitized,
    response,
    response_body,
)

from sciscope.embedding.config import (
    API_MAX_INPUTS_PER_REQUEST,
    API_MAX_TOKENS_PER_REQUEST,
    EmbeddingConfig,
    EmbeddingConfigError,
    EmbeddingInputError,
    EmbeddingProviderError,
)
from sciscope.embedding.openai_client import (
    OpenAIConnection,
    OpenAIEmbedder,
    TransportConnectionError,
    TransportRequest,
    TransportResponse,
    TransportTimeout,
    UrllibTransport,
    read_api_key,
)
from sciscope.embedding.provider import Embedder, EmbeddingUsage, FakeEmbedder


def client(
    transport: ScriptedTransport,
    clock: RetryClock,
    config: EmbeddingConfig | None = None,
) -> OpenAIEmbedder:
    """Build a client whose transport, time, and jitter are entirely fake."""
    return OpenAIEmbedder(
        config or EmbeddingConfig(dimensions=2),
        transport,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        uniform=clock.uniform,
    )


def test_config_defaults() -> None:
    """T005-P01: retain every approved default and API ceiling."""
    config = EmbeddingConfig()
    assert config.provider == "openai"
    assert config.model == "text-embedding-3-small"
    assert config.dimensions == 1536
    assert config.passage_prefix == config.query_prefix == ""
    assert config.operational_cap_tokens == 384
    assert config.max_inputs_per_request == 8
    assert config.max_tokens_per_request == 2048
    assert config.max_attempts == 3
    assert config.request_timeout_seconds == 30.0
    assert config.initial_backoff_seconds == 1.0
    assert config.max_backoff_seconds == 30.0
    assert config.max_total_retry_seconds == 120.0
    assert API_MAX_INPUTS_PER_REQUEST == 2048
    assert API_MAX_TOKENS_PER_REQUEST == 300000


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("provider", "fake"),
        ("provider", "other"),
        ("model", ""),
        ("model", " \t"),
        ("dimensions", 0),
        ("dimensions", -1),
        ("dimensions", True),
        ("dimensions", 1.5),
        ("max_inputs_per_request", 0),
        ("max_inputs_per_request", -1),
        ("max_inputs_per_request", 1.5),
        ("max_inputs_per_request", 2049),
        ("max_inputs_per_request", True),
        ("max_tokens_per_request", 0),
        ("max_tokens_per_request", -1),
        ("max_tokens_per_request", 1.5),
        ("max_tokens_per_request", 300001),
        ("max_tokens_per_request", True),
        ("max_attempts", 0),
        ("max_attempts", -1),
        ("max_attempts", 1.5),
        ("max_attempts", True),
        ("request_timeout_seconds", -1.0),
        ("initial_backoff_seconds", -1.0),
        ("max_backoff_seconds", -1.0),
        ("max_total_retry_seconds", -1.0),
        ("request_timeout_seconds", float("nan")),
        ("initial_backoff_seconds", float("inf")),
        ("max_backoff_seconds", float("nan")),
        ("max_total_retry_seconds", float("inf")),
        ("operational_cap_tokens", 0),
        ("operational_cap_tokens", -1),
        ("operational_cap_tokens", 1.5),
        ("operational_cap_tokens", 513),
        ("operational_cap_tokens", True),
    ],
)
def test_config_rejects_invalid_values(field: str, value: object) -> None:
    """T005-P02: reject invalid config values without external effects."""
    with pytest.raises(EmbeddingConfigError) as caught:
        EmbeddingConfig(**{field: value})
    assert_sanitized(caught.value)


def test_config_accepts_api_boundaries() -> None:
    """T005-P03: accept positive dimensions, API maxima, and both caps."""
    for cap in (1, 512):
        config = EmbeddingConfig(
            dimensions=1,
            operational_cap_tokens=cap,
            max_inputs_per_request=2048,
            max_tokens_per_request=300000,
            max_attempts=1,
            initial_backoff_seconds=0.0,
        )
        assert config.operational_cap_tokens == cap


@pytest.mark.parametrize("method", ["embed_passages", "embed_queries"])
@pytest.mark.parametrize("fake", [False, True])
@pytest.mark.parametrize(
    ("texts", "code"),
    [
        ([], "empty-input-list"),
        ([""], "blank-input"),
        ([" \t\n"], "blank-input"),
        (["Synthetic input."] * 9, "too-many-inputs"),
    ],
)
def test_rejects_input_before_transport(
    method: str, fake: bool, texts: list[str], code: str
) -> None:
    """T005-P04: reject bad inputs for both methods before any request."""
    transport = ScriptedTransport([])
    config = EmbeddingConfig(dimensions=2)
    embedder = (
        FakeEmbedder(config)
        if fake
        else client(transport, RetryClock(), config)
    )
    with pytest.raises(EmbeddingInputError) as caught:
        getattr(embedder, method)(texts)
    assert caught.value.code == code
    assert_sanitized(caught.value)
    assert transport.calls == []


def test_fake_determinism_order_normalization_and_usage() -> None:
    """T005-P05: fake vectors depend only on final text and dimensions."""
    config = EmbeddingConfig(dimensions=8, query_prefix="query: ")
    calls: list[tuple[str, ...]] = []

    def count_usage(texts: Sequence[str]) -> EmbeddingUsage:
        calls.append(tuple(texts))
        return EmbeddingUsage(19, 23)

    fake = FakeEmbedder(config, usage_counter=count_usage)
    assert isinstance(fake, Embedder)
    first = fake.embed_passages(["Synthetic alpha.", "Synthetic beta."])
    again = fake.embed_passages(["Synthetic alpha.", "Synthetic beta."])
    reverse = fake.embed_passages(["Synthetic beta.", "Synthetic alpha."])
    assert first.vectors == again.vectors == tuple(reversed(reverse.vectors))
    assert first.vectors[0] != first.vectors[1]
    assert first.usage == EmbeddingUsage(19, 23)
    for vector in first.vectors:
        assert len(vector) == 8
        assert math.sqrt(math.fsum(v * v for v in vector)) == pytest.approx(1)
    query = fake.embed_queries(["Synthetic alpha."])
    final = fake.embed_passages(["query: Synthetic alpha."])
    assert query.vectors == final.vectors
    assert calls[-2:] == [("query: Synthetic alpha.",)] * 2
    other = FakeEmbedder(replace(config, model="synthetic-model"))
    assert (
        other.embed_passages(["Synthetic alpha."]).vectors[0]
        == (first.vectors[0])
    )


def test_request_payload_order_usage_headers_and_protocol() -> None:
    """T005-P06: send final passages unchanged and return indexed results."""
    body = response_body(((0.0, 1.0), (1.0, 0.0)))
    data = cast(list[object], body["data"])
    body["data"] = list(reversed(data))
    transport = ScriptedTransport(
        [
            response(
                body=body,
                headers={
                    "X-RateLimit-Remaining-Tokens": "100",
                    "Retry-After": "2",
                    "authorization": FAKE_KEY,
                    "x-ratelimit-bad": "unsafe\nvalue",
                    "x-ratelimit-long": "x" * 65,
                    "x-ratelimit-unicode": "é",
                },
            )
        ]
    )
    embedder = client(
        transport,
        RetryClock(),
        EmbeddingConfig(dimensions=2, passage_prefix="passage: "),
    )
    assert isinstance(embedder, Embedder)
    result = embedder.embed_passages(["final beta", "final alpha"])
    assert transport.calls[0].payload == {
        "model": "text-embedding-3-small",
        "input": ["final beta", "final alpha"],
        "dimensions": 2,
        "encoding_format": "float",
    }
    assert transport.calls[0].timeout_seconds == 30.0
    assert result.vectors == ((0.0, 1.0), (1.0, 0.0))
    assert result.usage == EmbeddingUsage(7, 7)
    assert result.attempts == 1
    assert dict(result.rate_limit_headers) == {
        "x-ratelimit-remaining-tokens": "100",
        "retry-after": "2",
    }


def test_openai_query_prefix_applied_exactly_once() -> None:
    """T005-P07: OpenAI queries receive exactly the configured prefix."""
    transport = ScriptedTransport([response()])
    client(
        transport,
        RetryClock(),
        EmbeddingConfig(dimensions=2, query_prefix="query: "),
    ).embed_queries(["Synthetic query."])
    assert transport.calls[0].payload["input"] == ["query: Synthetic query."]


@pytest.mark.parametrize(
    ("defect", "code"),
    [
        ("not-object", "response-shape"),
        ("no-data", "response-shape"),
        ("data-not-list", "response-shape"),
        ("item-not-object", "response-shape"),
        ("no-index", "response-shape"),
        ("bool-index", "response-shape"),
        ("str-index", "response-shape"),
        ("no-embedding", "response-shape"),
        ("vector-not-list", "response-shape"),
        ("short", "response-count"),
        ("long", "response-count"),
        ("duplicate-index", "response-index"),
        ("negative-index", "response-index"),
        ("outside-index", "response-index"),
        ("dimensions", "response-dimensions"),
        ("nan", "response-nonfinite"),
        ("inf", "response-nonfinite"),
        ("bool-vector", "response-nonfinite"),
        ("str-vector", "response-nonfinite"),
        ("no-usage", "response-usage"),
        ("no-prompt", "response-usage"),
        ("no-total", "response-usage"),
        ("negative-prompt", "response-usage"),
        ("negative-total", "response-usage"),
        ("bool-prompt", "response-usage"),
        ("bool-total", "response-usage"),
        ("float-prompt", "response-usage"),
        ("str-total", "response-usage"),
        ("model-mismatch", "response-model-mismatch"),
        ("no-model", "response-shape"),
        ("model-not-string", "response-shape"),
        ("not-json", "response-not-json"),
    ],
)
def test_malformed_response_is_not_retried(defect: str, code: str) -> None:
    """T005-P08: each invalid response has a sanitized permanent code."""
    body: object = response_body(((1.0, 0.0), (0.0, 1.0)))
    obj = cast(dict[str, object], body)
    data = cast(list[dict[str, object]], obj["data"])
    usage = cast(dict[str, object], obj["usage"])
    if defect == "not-object":
        body = []
    elif defect in ("no-data", "no-usage", "no-model"):
        del obj[defect.removeprefix("no-")]
    elif defect == "data-not-list":
        obj["data"] = {}
    elif defect == "item-not-object":
        obj["data"] = [None, data[1]]
    elif defect in ("no-index", "no-embedding"):
        del data[0][defect.removeprefix("no-")]
    elif defect in ("bool-index", "str-index"):
        data[0]["index"] = True if defect == "bool-index" else "0"
    elif defect == "vector-not-list":
        data[0]["embedding"] = {}
    elif defect == "short":
        obj["data"] = data[:1]
    elif defect == "long":
        obj["data"] = data + [{"index": 2, "embedding": [1.0, 0.0]}]
    elif defect.endswith("index"):
        data[0]["index"] = {
            "duplicate-index": 1,
            "negative-index": -1,
            "outside-index": 2,
        }[defect]
    elif defect == "dimensions":
        data[0]["embedding"] = [1.0]
    elif defect in ("nan", "inf", "bool-vector", "str-vector"):
        bad = {
            "nan": math.nan,
            "inf": math.inf,
            "bool-vector": True,
            "str-vector": "1",
        }[defect]
        data[0]["embedding"] = [bad, 0.0]
    elif defect in ("no-prompt", "no-total"):
        del usage[defect.removeprefix("no-") + "_tokens"]
    elif defect in (
        "negative-prompt",
        "negative-total",
        "bool-prompt",
        "bool-total",
        "float-prompt",
        "str-total",
    ):
        kind, field = defect.split("-")
        usage[field + "_tokens"] = {
            "negative": -1,
            "bool": True,
            "float": 1.5,
            "str": "1",
        }[kind]
    elif defect == "model-mismatch":
        obj["model"] = "different-model"
    elif defect == "model-not-string":
        obj["model"] = 3
    elif defect == "not-json":
        body = None
    transport = ScriptedTransport([TransportResponse(200, {}, body)])
    clock = RetryClock()
    with pytest.raises(EmbeddingProviderError) as caught:
        client(transport, clock).embed_passages(
            ["Synthetic A.", "Synthetic B."]
        )
    assert caught.value.code == code
    assert_sanitized(caught.value)
    assert len(transport.calls) == 1
    assert clock.sleeps == []


@pytest.mark.parametrize(
    "failure",
    [
        response(429),
        response(500),
        response(503),
        TransportTimeout(),
        TransportConnectionError(),
    ],
)
def test_transient_failure_then_success(
    failure: TransportResponse | Exception,
) -> None:
    """T005-P09: retry eligible failures and retain only successful usage."""
    clock = RetryClock()
    transport = ScriptedTransport([failure, response()])
    result = client(transport, clock).embed_passages(["Synthetic input."])
    assert result.attempts == 2
    assert result.usage == EmbeddingUsage(7, 7)
    assert len(transport.calls) == 2
    assert clock.sleeps == [1.0]


def test_retry_after_is_a_minimum_and_last_headers_win() -> None:
    """T005-P10: honor decimal Retry-After and expose last-response headers."""
    transport = ScriptedTransport(
        [
            response(429, headers={"retry-after": "4.5"}),
            response(headers={"x-ratelimit-remaining-tokens": "90"}),
        ]
    )
    clock = RetryClock()
    result = client(transport, clock).embed_passages(["Synthetic input."])
    assert clock.sleeps == [4.5]
    assert result.attempts == 2
    assert dict(result.rate_limit_headers) == {
        "x-ratelimit-remaining-tokens": "90"
    }


@pytest.mark.parametrize("maximum", [False, True])
def test_exact_capped_backoff_and_jitter(maximum: bool) -> None:
    """T005-P11: cap the base before adding the specified 25% jitter."""
    clock = RetryClock(use_maximum_jitter=maximum)
    transport = ScriptedTransport([response(429)] * 3 + [response()])
    config = EmbeddingConfig(
        dimensions=2, max_attempts=4, max_backoff_seconds=2.0
    )
    result = client(transport, clock, config).embed_passages(["Synthetic."])
    scale = 1.25 if maximum else 1.0
    assert clock.sleeps == [base * scale for base in (1.0, 2.0, 2.0)]
    assert clock.jitter_bounds == [(0, 0.25), (0, 0.5), (0, 0.5)]
    assert result.attempts == 4


@pytest.mark.parametrize(
    "header",
    [
        "-1",
        "NaN",
        "Infinity",
        "3601",
        "9999999999999",
        "Tue, 17 Nov 2026 12:00:00 GMT",
        "later",
        "1e1",
        "+2",
    ],
)
def test_invalid_retry_after_is_ignored(header: str) -> None:
    """T005-P12: accept only bounded plain nonnegative decimal seconds."""
    clock = RetryClock()
    transport = ScriptedTransport(
        [response(429, headers={"retry-after": header}), response()]
    )
    client(transport, clock).embed_passages(["Synthetic input."])
    assert clock.sleeps == [1.0]


@pytest.mark.parametrize("attempts", [1, 3])
def test_exhaustion_counts_total_attempts(attempts: int) -> None:
    """T005-P13: stop at max_attempts and never sleep after the last."""
    clock = RetryClock()
    transport = ScriptedTransport([response(503)] * attempts)
    with pytest.raises(EmbeddingProviderError) as caught:
        client(
            transport,
            clock,
            EmbeddingConfig(dimensions=2, max_attempts=attempts),
        ).embed_passages(["Synthetic input."])
    assert caught.value.code == "retry-exhausted"
    assert len(transport.calls) == attempts
    assert len(clock.sleeps) == attempts - 1
    assert_sanitized(caught.value)


def test_retry_budget_prevents_sleep() -> None:
    """T005-P14: reject delays exceeding the remaining retry budget."""
    clock = RetryClock()
    transport = ScriptedTransport([response(429, headers={"retry-after": "9"})])
    with pytest.raises(EmbeddingProviderError) as caught:
        client(
            transport,
            clock,
            EmbeddingConfig(dimensions=2, max_total_retry_seconds=8.0),
        ).embed_passages(["Synthetic input."])
    assert caught.value.code == "retry-budget-exceeded"
    assert_sanitized(caught.value)
    assert clock.sleeps == []
    assert len(transport.calls) == 1


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (400, "request-rejected"),
        (401, "authentication-failed"),
        (403, "permission-denied"),
        (404, "endpoint-or-model-not-found"),
        (418, "http-418"),
        (301, "unexpected-redirect"),
        (307, "unexpected-redirect"),
    ],
)
def test_permanent_status_is_not_retried(status: int, code: str) -> None:
    """T005-P15: classify permanent statuses without body or secret leakage."""
    clock = RetryClock()
    transport = ScriptedTransport([response(status, body={"error": FAKE_KEY})])
    with pytest.raises(EmbeddingProviderError) as caught:
        client(transport, clock).embed_passages(["Synthetic input."])
    assert caught.value.code == code
    assert len(transport.calls) == 1
    assert clock.sleeps == []
    assert_sanitized(caught.value)


@pytest.mark.parametrize("field", ["code", "type"])
def test_quota_429_is_not_retried(field: str) -> None:
    """T005-P16: either quota discriminator requires action without retry."""
    clock = RetryClock()
    transport = ScriptedTransport(
        [response(429, body={"error": {field: "insufficient_quota"}})]
    )
    with pytest.raises(EmbeddingProviderError) as caught:
        client(transport, clock).embed_passages(["Synthetic input."])
    assert caught.value.code == "quota-exceeded"
    assert len(transport.calls) == 1
    assert clock.sleeps == []
    assert_sanitized(caught.value)


def test_nonquota_error_code_429_retries() -> None:
    """T005-P17: another error code remains a transient 429."""
    transport = ScriptedTransport(
        [
            response(429, body={"error": {"code": "rate_limit_exceeded"}}),
            response(),
        ]
    )
    assert (
        client(transport, RetryClock()).embed_passages(["Synthetic."]).attempts
        == 2
    )


@pytest.mark.parametrize(
    ("environ", "code"),
    [
        ({}, "missing-api-key"),
        ({"OPENAI_API_KEY": " \t"}, "missing-api-key"),
        ({"OPENAI_API_KEY": FAKE_KEY + "\n"}, "invalid-api-key"),
        ({"OPENAI_API_KEY": FAKE_KEY + "é"}, "invalid-api-key"),
    ],
)
def test_key_errors_and_object_reprs_are_sanitized(
    environ: dict[str, str], code: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """T005-P18: reject unsafe keys without exposing key, prefix, or length."""
    with pytest.raises(EmbeddingConfigError) as caught:
        read_api_key(environ)
    assert caught.value.code == code
    assert_sanitized(caught.value)
    connection = OpenAIConnection(
        FAKE_KEY, "https://example.invalid/v1/embeddings"
    )
    transport = UrllibTransport(connection)
    for value in (EmbeddingConfig(), connection, transport):
        for secret in (FAKE_KEY, FAKE_KEY[:8], str(len(FAKE_KEY))):
            assert secret not in repr(value)
    assert read_api_key(FAKE_ENV) == FAKE_KEY
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


@pytest.mark.parametrize(("header", "delay"), [("0", 1.0), ("3600", 3600.0)])
def test_retry_after_accepts_decimal_boundaries(
    header: str, delay: float
) -> None:
    """T005-P19: include zero and the inclusive Retry-After ceiling."""
    clock = RetryClock()
    transport = ScriptedTransport(
        [response(429, headers={"retry-after": header}), response()]
    )
    client(
        transport,
        clock,
        EmbeddingConfig(dimensions=2, max_total_retry_seconds=4000.0),
    ).embed_passages(["Synthetic input."])
    assert clock.sleeps == [delay]


def test_elapsed_request_time_counts_toward_retry_budget() -> None:
    """T005-P20: request duration consumes the retry budget before sleeping."""
    clock = RetryClock(now=100.0)
    transport = ScriptedTransport([response(429, headers={"retry-after": "2"})])

    class TimedTransport:
        """Advance synthetic time while delivering a transient response."""

        def post_json(self, request: TransportRequest) -> TransportResponse:
            """Consume nine elapsed seconds without sleeping or networking."""
            clock.now += 9.0
            return transport.post_json(request)

    embedder = OpenAIEmbedder(
        EmbeddingConfig(dimensions=2, max_total_retry_seconds=10.0),
        TimedTransport(),
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        uniform=clock.uniform,
    )
    with pytest.raises(EmbeddingProviderError) as caught:
        embedder.embed_passages(["Synthetic input."])
    assert caught.value.code == "retry-budget-exceeded"
    assert_sanitized(caught.value)
    assert clock.sleeps == [] and len(transport.calls) == 1


def test_delay_equal_to_retry_budget_is_allowed() -> None:
    """T005-P21: allow elapsed time plus delay exactly equal to the budget."""
    clock = RetryClock()
    transport = ScriptedTransport([response(429), response()])
    result = client(
        transport,
        clock,
        EmbeddingConfig(dimensions=2, max_total_retry_seconds=1.0),
    ).embed_passages(["Synthetic input."])
    assert result.attempts == 2 and clock.sleeps == [1.0]
