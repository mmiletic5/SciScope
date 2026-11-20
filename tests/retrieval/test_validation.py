"""Behavior tests for private retrieval request/vector validation."""

from __future__ import annotations

import math

import pytest

from sciscope.retrieval._core import _effective_pool
from sciscope.retrieval._errors import RetrievalFailure
from sciscope.retrieval._validation import (
    validate_query_embedding,
    validate_request,
)
from tests.retrieval.conftest import FakeEmbedder


def request(**updates: object) -> dict[str, object]:
    """Build a minimal valid private-core request mapping."""
    value: dict[str, object] = {
        "contract_version": "retrieval.v1",
        "request_id": "offline-1",
        "query_text": " bee homing ",
        "mode": "hybrid",
        "top_k": 5,
    }
    value.update(updates)
    return value


def test_request_trims_text_and_rejects_explicit_pool_below_top_k() -> None:
    """Hybrid pool cannot silently truncate the requested result count."""
    validated = validate_request(request())
    assert validated.query_text == "bee homing"

    with pytest.raises(RetrievalFailure) as raised:
        validate_request(request(ranking={"candidate_pool_size": 4}))
    assert raised.value.code == "INVALID_REQUEST"


@pytest.mark.parametrize(
    "updates",
    [
        {"query_text": "   "},
        {"query_text": "x" * 2001},
        {"request_id": "bad id"},
        {"top_k": True},
        {"mode": "other"},
        {"mode": "dense", "ranking": {"candidate_pool_size": 5}},
        {"ranking": {"candidate_pool_size": 251}},
        {"unknown": "field"},
        {"filters": {"languages": []}},
    ],
)
def test_invalid_requests_fail_before_provider_or_database(updates) -> None:
    """Malformed and irrelevant request fields have one typed failure."""
    with pytest.raises(RetrievalFailure) as raised:
        validate_request(request(**updates))
    assert raised.value.code == "INVALID_REQUEST"


@pytest.mark.parametrize(
    "vector",
    [
        (0.0,) * 1536,
        (math.nan,) + (0.0,) * 1535,
        (math.inf,) + (0.0,) * 1535,
        (1.0,),
        (1e100,) + (0.0,) * 1535,
    ],
)
def test_invalid_query_vectors_are_rejected(vector) -> None:
    """Zero-norm, malformed, nonfinite, and non-float32 vectors fail."""
    with pytest.raises(RetrievalFailure) as raised:
        validate_query_embedding(
            vector, expected_dimensions=1536, request_id="vector-request"
        )
    assert raised.value.code == "EMBEDDING_CONFIGURATION_MISMATCH"
    assert raised.value.request_id == "vector-request"


def test_query_vector_is_converted_to_float32_safe_values() -> None:
    """A valid query vector is returned as finite Python floats."""
    result = validate_query_embedding(
        (1.0,) + (0.0,) * 1535, expected_dimensions=1536
    )
    assert len(result) == 1536
    assert result[0] == 1.0


def test_filters_canonicalize_only_request_values() -> None:
    """DOIs and languages canonicalize without changing stored values."""
    validated = validate_request(
        request(
            filters={
                "languages": [" EN "],
                "dois": ["https://doi.org/10.1371/JOURNAL.PONE.0077354."],
                "journals": [" PLOS ONE "],
                "normalized_types": ["results"],
                "publication_year_from": 2010,
                "publication_year_to": 2015,
            }
        )
    )
    assert validated.filters.languages == ("en",)
    assert validated.filters.dois == ("10.1371/journal.pone.0077354",)
    assert validated.filters.journals == ("PLOS ONE",)
    assert validated.filters.publication_year_from == 2010


@pytest.mark.parametrize(
    "filters",
    [
        {"publication_year_from": 2020, "publication_year_to": 2019},
        {"normalized_types": ["results", "results"]},
        {"journals": ["PLOS ONE", " PLOS ONE "]},
        {"languages": ["EN", " en "]},
        {
            "dois": [
                "10.1371/journal.pone.0077354",
                "doi:10.1371/JOURNAL.PONE.0077354",
            ]
        },
        {"dois": ["https://example.org/resolve?x=1"]},
        {"publication_year_from": None},
        {"journals": None},
    ],
)
def test_invalid_filter_values_are_rejected(filters) -> None:
    """Null, duplicate, malformed, and reversed filters are invalid."""
    with pytest.raises(RetrievalFailure) as raised:
        validate_request(request(filters=filters))
    assert raised.value.code == "INVALID_REQUEST"


def test_fake_embedder_returns_fixed_vector_and_records_config(fake_embedder):
    """Offline adapter fixture makes no provider call and is reproducible."""
    config = object()
    vector = fake_embedder.embed_query("bee homing", config=config)
    assert vector[0] == 1.0
    assert fake_embedder.calls == [("bee homing", config)]


def test_fake_embedder_class_accepts_explicit_vector():
    """Tests can inject an exact query vector into the core."""
    fake = FakeEmbedder((0.5, 0.5), [])
    assert fake.embed_query("query", config=None) == (0.5, 0.5)


def test_v2_contract_is_accepted_and_v1_defaults_remain_unchanged():
    """The opt-in v2 contract is distinct while modes remain compatible."""
    v2 = validate_request(request(contract_version="retrieval.v2"))
    v1 = validate_request(request(contract_version="retrieval.v1"))
    assert v2.contract_version == "retrieval.v2"
    assert v2.mode == "hybrid"
    assert v1.contract_version == "retrieval.v1"
    assert v1.mode == "hybrid"


def test_unsupported_contract_version_has_distinct_typed_error():
    """Unknown versions remain distinct from malformed requests."""
    with pytest.raises(RetrievalFailure) as raised:
        validate_request(request(contract_version="retrieval.v3"))
    assert raised.value.code == "UNSUPPORTED_CONTRACT_VERSION"
    assert raised.value.request_id == "offline-1"


def test_default_hybrid_pool_is_bounded_by_eligibility_and_cap():
    """Default branch pool follows the documented multiplier and hard cap."""
    request_value = validate_request(request(top_k=5))
    assert _effective_pool(request_value, 12) == 12
    assert _effective_pool(request_value, 1000) == 50
    max_request = validate_request(request(top_k=50))
    assert _effective_pool(max_request, 1000) == 250
    assert _effective_pool(max_request, 10) == 10
