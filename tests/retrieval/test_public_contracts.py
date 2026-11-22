"""RED contract tests for the public versioned retrieval boundary."""

from __future__ import annotations

import importlib
import subprocess
import sys
from dataclasses import FrozenInstanceError
from types import ModuleType
from typing import Any

import pytest

_PUBLIC_EXPORTS = (
    "Author",
    "CorpusIdentity",
    "EmbeddingConfig",
    "NormalizedType",
    "PaperMetadata",
    "RankingOptions",
    "RetrievalErrorCode",
    "RetrievalException",
    "RetrievalFilters",
    "RetrievalMetadata",
    "RetrievalRequest",
    "RetrievalMode",
    "RetrievalResponse",
    "RetrievalResult",
    "RetrievalScore",
)


def _public_api() -> ModuleType:
    """Return the public retrieval package after requiring supported exports."""
    module = importlib.import_module("sciscope.retrieval")
    missing = [name for name in _PUBLIC_EXPORTS if not hasattr(module, name)]
    assert not missing, f"Missing public retrieval exports: {missing}"
    return module


def _public_type(module: ModuleType, name: str) -> Any:
    """Return one required public type after export validation."""
    return getattr(module, name)


def _valid_request(module: ModuleType, **updates: object) -> Any:
    """Construct a minimal valid hybrid request with optional updates."""
    values: dict[str, object] = {
        "contract_version": "retrieval.v1",
        "request_id": "public-contract-1",
        "query_text": " honey bee homing ",
        "mode": "hybrid",
        "top_k": 5,
    }
    values.update(updates)
    return _public_type(module, "RetrievalRequest")(**values)


def _assert_invalid_request(
    module: ModuleType,
    *,
    expected_request_id: str | None = "public-contract-1",
    **updates: object,
) -> None:
    """Assert that one invalid public request raises the typed error."""
    error_type = _public_type(module, "RetrievalException")
    error_code = _public_type(module, "RetrievalErrorCode")
    with pytest.raises(error_type) as raised:
        _valid_request(module, **updates)
    assert raised.value.code is error_code.INVALID_REQUEST
    assert raised.value.request_id == expected_request_id
    assert raised.value.retryable is False


def _valid_response_values(module: ModuleType) -> dict[str, Any]:
    """Construct valid public response values with exact source provenance."""
    author_type = _public_type(module, "Author")
    paper_type = _public_type(module, "PaperMetadata")
    score_type = _public_type(module, "RetrievalScore")
    result_type = _public_type(module, "RetrievalResult")
    corpus_type = _public_type(module, "CorpusIdentity")
    metadata_type = _public_type(module, "RetrievalMetadata")
    response_type = _public_type(module, "RetrievalResponse")
    author = author_type(surname="Example", given_names="A.")
    paper = paper_type(
        title="Example title",
        authors=(author,),
        journal="PLOS ONE",
        publication_year=2013,
        language="EN",
        license="CC BY 4.0",
        source_url="https://doi.org/10.1371/journal.pone.0077354",
    )
    result = result_type(
        rank=1,
        chunk_id="a" * 64,
        text="Exact preserved chunk text.",
        doi="10.1371/journal.pone.0077354",
        source_locator="jats:v1:xml-sha256:/article[1]/body[1]/sec[1]/p[1]",
        section_id="10.1371/journal.pone.0077354#sec-1",
        section_path=("Results",),
        normalized_type="results",
        paper=paper,
        scores=score_type(0.8, 1, 0.2, 1, 0.03),
    )
    return {
        "author": author,
        "paper": paper,
        "result": result,
        "paper_type": paper_type,
        "result_type": result_type,
        "response_type": response_type,
        "response_values": {
            "contract_version": "retrieval.v1",
            "request_id": "public-contract-1",
            "corpus": corpus_type(
                delivery_digest="sha256:" + "b" * 64,
                source_contract_version="0.3.0",
                corpus_version="pilot17-xml-1fff1573b610",
            ),
            "embedding": None,
            "retrieval": metadata_type("lexical", 5, None, None, None),
            "results": (result,),
            "warnings": (),
        },
    }


def _assert_invalid_dto_collection(module: ModuleType, callback: Any) -> None:
    """Assert that one mutable public DTO collection fails safely."""
    error_type = _public_type(module, "RetrievalException")
    error_code = _public_type(module, "RetrievalErrorCode")
    with pytest.raises(error_type) as raised:
        callback()
    assert raised.value.code is error_code.INVALID_REQUEST
    assert raised.value.request_id is None
    assert raised.value.retryable is False


def test_public_root_exports_supported_contract_types() -> None:
    """The root package exposes only the approved public contract types."""
    module = _public_api()
    assert all(hasattr(module, name) for name in _PUBLIC_EXPORTS)


def test_v1_request_construction_trims_query_and_is_immutable() -> None:
    """A valid v1 request preserves its version and canonical query text."""
    module = _public_api()
    request = _valid_request(module)

    assert request.contract_version == "retrieval.v1"
    assert request.request_id == "public-contract-1"
    assert request.query_text == "honey bee homing"
    assert request.top_k == 5
    with pytest.raises(FrozenInstanceError):
        request.top_k = 6
    assert not hasattr(request, "__dict__")


def test_explicit_v2_request_preserves_selected_version() -> None:
    """A v2 request uses the unchanged v1 DTO shape and keeps v2 selected."""
    module = _public_api()
    request = _valid_request(
        module,
        contract_version="retrieval.v2",
        request_id="public-contract-v2",
    )

    assert request.contract_version == "retrieval.v2"
    assert request.request_id == "public-contract-v2"


def test_unsupported_contract_version_fails_closed() -> None:
    """Unsupported contract versions raise the documented typed public error."""
    module = _public_api()
    error_type = _public_type(module, "RetrievalException")
    error_code = _public_type(module, "RetrievalErrorCode")

    with pytest.raises(error_type) as raised:
        _valid_request(module, contract_version="retrieval.v3")

    assert raised.value.code is error_code.UNSUPPORTED_CONTRACT_VERSION
    assert raised.value.request_id == "public-contract-1"
    assert raised.value.retryable is False
    assert raised.value.public_message == (
        "The retrieval contract version is unsupported."
    )


@pytest.mark.parametrize(
    "request_id",
    ["A-z_9.:", "x", "x" * 128],
)
def test_request_id_accepts_documented_ascii_boundaries(
    request_id: str,
) -> None:
    """Request IDs accept only the documented ASCII alphabet and bounds."""
    module = _public_api()
    request = _valid_request(module, request_id=request_id)

    assert request.request_id == request_id


@pytest.mark.parametrize(
    "request_id",
    ["", "x" * 129, "bad id", "über"],
)
def test_request_id_rejects_invalid_values(request_id: str) -> None:
    """Request IDs fail with INVALID_REQUEST outside the public grammar."""
    module = _public_api()
    _assert_invalid_request(
        module,
        request_id=request_id,
        expected_request_id=None,
    )


@pytest.mark.parametrize(
    ("query_text", "expected"),
    [("x", "x"), (" x ", "x"), ("x" * 2000, "x" * 2000)],
)
def test_query_accepts_and_canonicalizes_documented_boundaries(
    query_text: str, expected: str
) -> None:
    """Queries trim whitespace and permit at most 2,000 characters."""
    module = _public_api()
    request = _valid_request(module, query_text=query_text)

    assert request.query_text == expected


@pytest.mark.parametrize("query_text", ["   ", "x" * 2001])
def test_query_rejects_blank_or_oversized_values(query_text: str) -> None:
    """Blank and oversized queries fail before any service dependency exists."""
    module = _public_api()
    _assert_invalid_request(module, query_text=query_text)


@pytest.mark.parametrize("top_k", [1, 50])
def test_top_k_accepts_documented_integer_boundaries(top_k: int) -> None:
    """Top-k accepts the inclusive public range of one through fifty."""
    module = _public_api()
    request = _valid_request(module, top_k=top_k)

    assert request.top_k == top_k


@pytest.mark.parametrize("top_k", [True, 0, 51, 1.0])
def test_top_k_rejects_boolean_and_out_of_range_values(top_k: object) -> None:
    """Top-k rejects booleans and values outside the documented range."""
    module = _public_api()
    _assert_invalid_request(module, top_k=top_k)


def test_filters_canonicalize_values_and_reject_invalid_combinations() -> None:
    """Filters canonicalize request values without changing source metadata."""
    module = _public_api()
    filters_type = _public_type(module, "RetrievalFilters")
    filters = filters_type(
        publication_year_from=2010,
        publication_year_to=2015,
        normalized_types=("results",),
        journals=(" PLOS ONE ",),
        languages=(" EN ",),
        dois=("https://doi.org/10.1371/JOURNAL.PONE.0077354.",),
    )
    request = _valid_request(module, filters=filters)

    assert request.filters == filters
    assert filters.journals == ("PLOS ONE",)
    assert filters.languages == ("en",)
    assert filters.dois == ("10.1371/journal.pone.0077354",)

    error_type = _public_type(module, "RetrievalException")
    error_code = _public_type(module, "RetrievalErrorCode")
    with pytest.raises(error_type) as raised:
        filters_type(
            publication_year_from=2020,
            publication_year_to=2019,
        )
    assert raised.value.code is error_code.INVALID_REQUEST


def test_hybrid_ranking_pool_is_validated_by_mode_and_top_k() -> None:
    """Candidate pools are hybrid-only and cannot be smaller than top-k."""
    module = _public_api()
    ranking_type = _public_type(module, "RankingOptions")
    ranking = ranking_type(candidate_pool_size=5)
    request = _valid_request(module, ranking=ranking)

    assert request.ranking == ranking
    _assert_invalid_request(
        module,
        ranking=ranking_type(candidate_pool_size=4),
    )
    _assert_invalid_request(
        module,
        mode="dense",
        ranking=ranking_type(candidate_pool_size=5),
    )


def test_typed_error_has_only_stable_sanitized_public_fields() -> None:
    """Public errors retain the approved code, ID, retry, and message."""
    module = _public_api()
    error_type = _public_type(module, "RetrievalException")
    error_code = _public_type(module, "RetrievalErrorCode")
    error = error_type(
        code=error_code.EMBEDDING_UNAVAILABLE,
        request_id="public-contract-1",
        retryable=True,
        public_message=(
            "The query embedding service is temporarily unavailable."
        ),
    )

    assert error.code is error_code.EMBEDDING_UNAVAILABLE
    assert error.request_id == "public-contract-1"
    assert error.retryable is True
    assert error.public_message == (
        "The query embedding service is temporarily unavailable."
    )
    assert not hasattr(error, "cause")


def test_response_preserves_exact_source_identity_and_corpus_provenance() -> (
    None
):
    """Public result DTOs retain exact stable identities and corpus metadata."""
    module = _public_api()
    author_type = _public_type(module, "Author")
    paper_type = _public_type(module, "PaperMetadata")
    score_type = _public_type(module, "RetrievalScore")
    result_type = _public_type(module, "RetrievalResult")
    corpus_type = _public_type(module, "CorpusIdentity")
    metadata_type = _public_type(module, "RetrievalMetadata")
    response_type = _public_type(module, "RetrievalResponse")

    chunk_id = "a" * 64
    locator = "jats:v1:xml-sha256:/article[1]/body[1]/sec[1]/p[1]"
    result = result_type(
        rank=1,
        chunk_id=chunk_id,
        text="Exact preserved chunk text.",
        doi="10.1371/journal.pone.0077354",
        source_locator=locator,
        section_id="10.1371/journal.pone.0077354#sec-1",
        section_path=("Results",),
        normalized_type="results",
        paper=paper_type(
            title="Example title",
            authors=(author_type(surname="Example", given_names="A."),),
            journal="PLOS ONE",
            publication_year=2013,
            language="EN",
            license="CC BY 4.0",
            source_url="https://doi.org/10.1371/journal.pone.0077354",
        ),
        scores=score_type(0.8, 1, 0.2, 1, 0.03),
    )
    corpus = corpus_type(
        delivery_digest="sha256:" + "b" * 64,
        source_contract_version="0.3.0",
        corpus_version="pilot17-xml-1fff1573b610",
    )
    response = response_type(
        contract_version="retrieval.v1",
        request_id="public-contract-1",
        corpus=corpus,
        embedding=None,
        retrieval=metadata_type("lexical", 5, None, None, None),
        results=(result,),
        warnings=(),
    )

    assert response.corpus.delivery_digest == "sha256:" + "b" * 64
    assert response.results[0].chunk_id == chunk_id
    assert response.results[0].source_locator == locator
    assert response.results[0].section_path == ("Results",)


@pytest.mark.parametrize(
    "collection_name",
    ["authors", "section_path", "results", "warnings"],
)
def test_response_dtos_preserve_immutable_tuple_collections(
    collection_name: str,
) -> None:
    """Tuple collections retain source values without mutable references."""
    module = _public_api()
    values = _valid_response_values(module)
    response = values["response_type"](**values["response_values"])
    collections = {
        "authors": values["paper"].authors,
        "section_path": values["result"].section_path,
        "results": response.results,
        "warnings": response.warnings,
    }

    assert isinstance(collections[collection_name], tuple)
    assert (
        collections[collection_name]
        == {
            "authors": (values["author"],),
            "section_path": ("Results",),
            "results": (values["result"],),
            "warnings": (),
        }[collection_name]
    )


@pytest.mark.parametrize(
    "collection_name",
    ["authors", "section_path", "results", "warnings"],
)
def test_response_dtos_reject_mutable_nested_collections(
    collection_name: str,
) -> None:
    """Mutable lists cannot be retained inside frozen public response DTOs."""
    module = _public_api()
    values = _valid_response_values(module)

    if collection_name == "authors":
        _assert_invalid_dto_collection(
            module,
            lambda: values["paper_type"](
                title="Example title",
                authors=[values["author"]],
                journal="PLOS ONE",
                publication_year=2013,
                language="EN",
                license="CC BY 4.0",
                source_url="https://doi.org/10.1371/journal.pone.0077354",
            ),
        )
    elif collection_name == "section_path":
        _assert_invalid_dto_collection(
            module,
            lambda: values["result_type"](
                rank=1,
                chunk_id="a" * 64,
                text="Exact preserved chunk text.",
                doi="10.1371/journal.pone.0077354",
                source_locator=(
                    "jats:v1:xml-sha256:/article[1]/body[1]/sec[1]/p[1]"
                ),
                section_id="10.1371/journal.pone.0077354#sec-1",
                section_path=["Results"],
                normalized_type="results",
                paper=values["paper"],
                scores=values["result"].scores,
            ),
        )
    else:
        response_values = dict(values["response_values"])
        response_values[collection_name] = (
            [values["result"]]
            if collection_name == "results"
            else ["EMPTY_RESULT"]
        )
        _assert_invalid_dto_collection(
            module,
            lambda: values["response_type"](**response_values),
        )


def test_public_import_isolation_loads_no_database_or_private_core() -> None:
    """Public imports do not load database, SQLAlchemy, or private core."""
    _public_api()
    command = """
import importlib
import sys
sys.path.insert(0, 'src')
module = importlib.import_module('sciscope.retrieval')
required = {
    'RetrievalRequest', 'RetrievalResponse', 'RetrievalException',
    'RetrievalErrorCode', 'RetrievalFilters',
}
missing = sorted(name for name in required if not hasattr(module, name))
forbidden = sorted(
    name for name in sys.modules
    if name.startswith(('sqlalchemy', 'pgvector', 'sciscope.database',
                        'sciscope.retrieval._core'))
)
assert not missing, missing
assert not forbidden, forbidden
"""
    completed = subprocess.run(
        [sys.executable, "-c", command],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
