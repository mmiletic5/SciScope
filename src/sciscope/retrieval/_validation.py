"""Private request and query-vector validation for retrieval algorithms."""

from __future__ import annotations

import math
import struct
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, cast

from sciscope.plos_pilot.doi import normalize_doi
from sciscope.retrieval._errors import RetrievalErrorCode, RetrievalFailure

RetrievalMode = Literal["dense", "lexical", "hybrid"]
NormalizedType = Literal[
    "abstract",
    "introduction",
    "methods",
    "results",
    "results_discussion",
    "discussion",
    "conclusions",
    "other",
]

_MODES = {"dense", "lexical", "hybrid"}
_TYPES = {
    "abstract",
    "introduction",
    "methods",
    "results",
    "results_discussion",
    "discussion",
    "conclusions",
    "other",
}
_REQUEST_ID_CHARS = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:-"
)


@dataclass(frozen=True, slots=True)
class InternalFilters:
    """Canonicalized private filters; persisted metadata is never rewritten."""

    publication_year_from: int | None = None
    publication_year_to: int | None = None
    normalized_types: tuple[NormalizedType, ...] | None = None
    journals: tuple[str, ...] | None = None
    languages: tuple[str, ...] | None = None
    dois: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class InternalRequest:
    """Validated private request used by the retrieval core."""

    contract_version: str
    request_id: str
    query_text: str
    mode: RetrievalMode
    top_k: int
    filters: InternalFilters
    candidate_pool_size: int | None


def validate_request(value: Mapping[str, object]) -> InternalRequest:
    """Validate untrusted request data before provider/database access.

    Args:
        value: Mapping parsed from the internal request boundary.

    Returns:
        Canonicalized request values for the private retrieval core.

    Raises:
        RetrievalFailure: If request fields or values are invalid.
    """
    if not isinstance(value, Mapping):
        raise _invalid()
    allowed = {
        "contract_version",
        "request_id",
        "query_text",
        "mode",
        "top_k",
        "filters",
        "ranking",
    }
    if set(value) - allowed:
        raise _invalid()
    if "contract_version" not in value:
        raise _invalid(_valid_request_id(value.get("request_id")))
    contract_version = value.get("contract_version")
    if not isinstance(contract_version, str) or contract_version not in {
        "retrieval.v1",
        "retrieval.v2",
    }:
        raise RetrievalFailure(
            RetrievalErrorCode.UNSUPPORTED_CONTRACT_VERSION,
            request_id=_valid_request_id(value.get("request_id")),
        )
    request_id = _require_request_id(value.get("request_id"))
    query_text = value.get("query_text")
    if not isinstance(query_text, str):
        raise _invalid(request_id)
    query_text = query_text.strip()
    if not query_text or len(query_text) > 2000:
        raise _invalid(request_id)
    mode_value = value.get("mode")
    if not isinstance(mode_value, str) or mode_value not in _MODES:
        raise _invalid(request_id)
    top_k = _bounded_int(value.get("top_k"), 1, 50, request_id)
    filters_value = value.get("filters", _MISSING)
    if filters_value is _MISSING:
        filters = InternalFilters()
    elif isinstance(filters_value, Mapping):
        filters = _validate_filters(filters_value, request_id)
    else:
        raise _invalid(request_id)
    ranking_value = value.get("ranking", _MISSING)
    if ranking_value is _MISSING:
        ranking: Mapping[str, object] = {}
    elif isinstance(ranking_value, Mapping):
        ranking = ranking_value
    else:
        raise _invalid(request_id)
    if set(ranking) - {"candidate_pool_size"}:
        raise _invalid(request_id)
    candidate_pool_size: int | None = None
    if "candidate_pool_size" in ranking:
        if mode_value != "hybrid":
            raise _invalid(request_id)
        candidate_pool_size = _bounded_int(
            ranking["candidate_pool_size"], 1, 250, request_id
        )
        if candidate_pool_size < top_k:
            raise _invalid(request_id)
    return InternalRequest(
        contract_version=contract_version,
        request_id=request_id,
        query_text=query_text,
        mode=cast(RetrievalMode, mode_value),
        top_k=top_k,
        filters=filters,
        candidate_pool_size=candidate_pool_size,
    )


def validate_query_embedding(
    value: object,
    *,
    expected_dimensions: int,
    request_id: str | None = None,
) -> tuple[float, ...]:
    """Validate provider output and float32 representability."""
    if (
        isinstance(value, (str, bytes, bytearray))
        or not isinstance(value, Sequence)
        or len(value) != expected_dimensions
    ):
        raise _embedding_mismatch(request_id)
    result: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise _embedding_mismatch(request_id)
        number = float(item)
        if not math.isfinite(number):
            raise _embedding_mismatch(request_id)
        try:
            number = struct.unpack("f", struct.pack("f", number))[0]
        except (OverflowError, struct.error):
            raise _embedding_mismatch(request_id) from None
        if not math.isfinite(number):
            raise _embedding_mismatch(request_id)
        result.append(number)
    if not result or math.hypot(*result) == 0.0:
        raise _embedding_mismatch(request_id)
    return tuple(result)


def _validate_filters(
    value: Mapping[str, object], request_id: str
) -> InternalFilters:
    allowed = {
        "publication_year_from",
        "publication_year_to",
        "normalized_types",
        "journals",
        "languages",
        "dois",
    }
    if set(value) - allowed:
        raise _invalid(request_id)
    year_from = _optional_year(value, "publication_year_from", request_id)
    year_to = _optional_year(value, "publication_year_to", request_id)
    if year_from is not None and year_to is not None and year_from > year_to:
        raise _invalid(request_id)
    types = _string_array(value, "normalized_types", request_id)
    if types is not None:
        if any(item not in _TYPES for item in types) or len(set(types)) != len(
            types
        ):
            raise _invalid(request_id)
        canonical_types = cast(tuple[NormalizedType, ...], types)
    else:
        canonical_types = None
    journals = _string_array(value, "journals", request_id)
    if journals is not None:
        journals = tuple(item.strip() for item in journals)
        if any(not item for item in journals) or len(set(journals)) != len(
            journals
        ):
            raise _invalid(request_id)
    languages = _string_array(value, "languages", request_id)
    if languages is not None:
        if any(not item.isascii() for item in languages):
            raise _invalid(request_id)
        languages = tuple(item.strip().lower() for item in languages)
        if any(not item for item in languages) or len(set(languages)) != len(
            languages
        ):
            raise _invalid(request_id)
    dois = _string_array(value, "dois", request_id)
    if dois is not None:
        try:
            dois = tuple(normalize_doi(item).doi for item in dois)
        except ValueError:
            raise _invalid(request_id) from None
        if len(set(dois)) != len(dois):
            raise _invalid(request_id)
    return InternalFilters(
        year_from, year_to, canonical_types, journals, languages, dois
    )


_MISSING = object()


def _optional_year(
    filters: Mapping[str, object], name: str, request_id: str
) -> int | None:
    if name not in filters:
        return None
    return _bounded_int(filters[name], 1, 9999, request_id)


def _string_array(
    filters: Mapping[str, object], name: str, request_id: str
) -> tuple[str, ...] | None:
    if name not in filters:
        return None
    value = filters[name]
    if (
        not isinstance(value, (list, tuple))
        or not value
        or len(value) > 100
        or any(not isinstance(item, str) for item in value)
    ):
        raise _invalid(request_id)
    return tuple(cast(str, item) for item in value)


def _bounded_int(
    value: object, minimum: int, maximum: int, request_id: str
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise _invalid(request_id)
    return value


def _require_request_id(value: object) -> str:
    request_id = _valid_request_id(value)
    if request_id is None:
        raise _invalid()
    return request_id


def _valid_request_id(value: object) -> str | None:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 128
        or any(char not in _REQUEST_ID_CHARS for char in value)
    ):
        return None
    return value


def _invalid(request_id: str | None = None) -> RetrievalFailure:
    return RetrievalFailure(
        RetrievalErrorCode.INVALID_REQUEST, request_id=request_id
    )


def _embedding_mismatch(request_id: str | None = None) -> RetrievalFailure:
    return RetrievalFailure(
        RetrievalErrorCode.EMBEDDING_CONFIGURATION_MISMATCH,
        request_id=request_id,
    )
