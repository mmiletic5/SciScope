"""Driver-independent public data contracts for versioned retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

from sciscope.plos_pilot.doi import normalize_doi
from sciscope.retrieval.errors import (
    PUBLIC_MESSAGES,
    RetrievalErrorCode,
    RetrievalException,
)

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

_CONTRACT_VERSIONS = frozenset({"retrieval.v1", "retrieval.v2"})
_MODES = frozenset({"dense", "lexical", "hybrid"})
_NORMALIZED_TYPES = frozenset(
    {
        "abstract",
        "introduction",
        "methods",
        "results",
        "results_discussion",
        "discussion",
        "conclusions",
        "other",
    }
)
_REQUEST_ID_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:-"
)


def _valid_request_id(value: object) -> str | None:
    """Return a valid public request ID, or None when it is unusable."""
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 128
        or any(character not in _REQUEST_ID_CHARS for character in value)
    ):
        return None
    return value


def _exception(
    code: RetrievalErrorCode, request_id: str | None = None
) -> RetrievalException:
    """Create a public exception with its approved stable message."""
    return RetrievalException(
        code=code,
        request_id=request_id,
        retryable=False,
        public_message=PUBLIC_MESSAGES[code],
    )


def _invalid(request_id: str | None = None) -> RetrievalException:
    """Create the canonical invalid-request exception."""
    return _exception(RetrievalErrorCode.INVALID_REQUEST, request_id)


def _require_tuple(
    value: object, request_id: str | None = None
) -> tuple[object, ...]:
    """Reject mutable or otherwise unsupported public collections."""
    if type(value) is not tuple:
        raise _invalid(request_id)
    return value


def _bounded_int(
    value: object,
    minimum: int,
    maximum: int,
    request_id: str | None = None,
) -> int:
    """Validate a contract integer without accepting booleans."""
    if type(value) is not int or not minimum <= value <= maximum:
        raise _invalid(request_id)
    return value


@dataclass(frozen=True, slots=True)
class RetrievalFilters:
    """Canonicalized optional metadata filters for retrieval requests."""

    publication_year_from: int | None = None
    publication_year_to: int | None = None
    normalized_types: tuple[NormalizedType, ...] | None = None
    journals: tuple[str, ...] | None = None
    languages: tuple[str, ...] | None = None
    dois: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        """Validate and canonicalize documented filter values."""
        year_from = self._year(self.publication_year_from)
        year_to = self._year(self.publication_year_to)
        if (
            year_from is not None
            and year_to is not None
            and year_from > year_to
        ):
            raise _invalid()
        object.__setattr__(self, "publication_year_from", year_from)
        object.__setattr__(self, "publication_year_to", year_to)
        object.__setattr__(
            self,
            "normalized_types",
            self._normalized_types(self.normalized_types),
        )
        object.__setattr__(self, "journals", self._journals(self.journals))
        object.__setattr__(self, "languages", self._languages(self.languages))
        object.__setattr__(self, "dois", self._dois(self.dois))

    @staticmethod
    def _year(value: object) -> int | None:
        if value is None:
            return None
        return _bounded_int(value, 1, 9999)

    @staticmethod
    def _values(value: object) -> tuple[object, ...] | None:
        if value is None:
            return None
        values = _require_tuple(value)
        if not values or len(values) > 100:
            raise _invalid()
        return values

    @classmethod
    def _normalized_types(
        cls, value: object
    ) -> tuple[NormalizedType, ...] | None:
        values = cls._values(value)
        if values is None:
            return None
        if any(
            not isinstance(item, str) or item not in _NORMALIZED_TYPES
            for item in values
        ) or len(set(values)) != len(values):
            raise _invalid()
        return cast(tuple[NormalizedType, ...], values)

    @classmethod
    def _journals(cls, value: object) -> tuple[str, ...] | None:
        values = cls._values(value)
        if values is None:
            return None
        if any(not isinstance(item, str) for item in values):
            raise _invalid()
        strings = cast(tuple[str, ...], values)
        canonical = tuple(item.strip() for item in strings)
        if any(not item for item in canonical) or len(set(canonical)) != len(
            canonical
        ):
            raise _invalid()
        return canonical

    @classmethod
    def _languages(cls, value: object) -> tuple[str, ...] | None:
        values = cls._values(value)
        if values is None:
            return None
        if any(
            not isinstance(item, str) or not item.isascii() for item in values
        ):
            raise _invalid()
        strings = cast(tuple[str, ...], values)
        canonical = tuple(item.strip().lower() for item in strings)
        if any(not item for item in canonical) or len(set(canonical)) != len(
            canonical
        ):
            raise _invalid()
        return canonical

    @classmethod
    def _dois(cls, value: object) -> tuple[str, ...] | None:
        values = cls._values(value)
        if values is None:
            return None
        if any(not isinstance(item, str) for item in values):
            raise _invalid()
        strings = cast(tuple[str, ...], values)
        try:
            canonical = tuple(normalize_doi(item).doi for item in strings)
        except ValueError:
            raise _invalid() from None
        if len(set(canonical)) != len(canonical):
            raise _invalid()
        return canonical


@dataclass(frozen=True, slots=True)
class RankingOptions:
    """Optional hybrid branch candidate-pool configuration."""

    candidate_pool_size: int | None = None

    def __post_init__(self) -> None:
        """Validate the independently bounded candidate pool."""
        if self.candidate_pool_size is not None:
            _bounded_int(self.candidate_pool_size, 1, 250)


@dataclass(frozen=True, slots=True)
class RetrievalRequest:
    """Validated public retrieval request for v1 or explicitly selected v2."""

    contract_version: str
    request_id: str
    query_text: str
    mode: RetrievalMode
    top_k: int
    filters: RetrievalFilters | None = None
    ranking: RankingOptions | None = None

    def __post_init__(self) -> None:
        """Validate request fields before provider or database access."""
        request_id = _valid_request_id(self.request_id)
        if request_id is None:
            raise _invalid()
        if self.contract_version not in _CONTRACT_VERSIONS:
            raise _exception(
                RetrievalErrorCode.UNSUPPORTED_CONTRACT_VERSION, request_id
            )
        if not isinstance(self.query_text, str):
            raise _invalid(request_id)
        query_text = self.query_text.strip()
        if not query_text or len(query_text) > 2000:
            raise _invalid(request_id)
        if self.mode not in _MODES:
            raise _invalid(request_id)
        top_k = _bounded_int(self.top_k, 1, 50, request_id)
        if self.filters is not None and not isinstance(
            self.filters, RetrievalFilters
        ):
            raise _invalid(request_id)
        if self.ranking is not None and not isinstance(
            self.ranking, RankingOptions
        ):
            raise _invalid(request_id)
        if self.ranking is not None:
            if self.mode != "hybrid":
                raise _invalid(request_id)
            candidate_pool_size = self.ranking.candidate_pool_size
            if candidate_pool_size is not None and candidate_pool_size < top_k:
                raise _invalid(request_id)
        object.__setattr__(self, "request_id", request_id)
        object.__setattr__(self, "query_text", query_text)
        object.__setattr__(self, "top_k", top_k)


@dataclass(frozen=True, slots=True)
class EmbeddingConfig:
    """Immutable active query-embedding identity."""

    provider: str
    model: str
    dimensions: int
    query_prefix: str


@dataclass(frozen=True, slots=True)
class Author:
    """One ordered source-author record."""

    surname: str
    given_names: str


@dataclass(frozen=True, slots=True)
class PaperMetadata:
    """Exact source paper metadata associated with a retrieval result."""

    title: str
    authors: tuple[Author, ...]
    journal: str
    publication_year: int
    language: str
    license: str
    source_url: str

    def __post_init__(self) -> None:
        """Reject mutable author collections at the public boundary."""
        authors = _require_tuple(self.authors)
        if any(not isinstance(author, Author) for author in authors):
            raise _invalid()
        object.__setattr__(self, "authors", authors)


@dataclass(frozen=True, slots=True)
class RetrievalScore:
    """Ranking signals and one-based ranks for one evidence chunk."""

    dense_similarity: float | None
    dense_rank: int | None
    lexical_score: float | None
    lexical_rank: int | None
    fusion_score: float | None


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """Exact evidence text, source identity, provenance, and ranking signals."""

    rank: int
    chunk_id: str
    text: str
    doi: str
    source_locator: str
    section_id: str
    section_path: tuple[str, ...]
    normalized_type: NormalizedType
    paper: PaperMetadata
    scores: RetrievalScore

    def __post_init__(self) -> None:
        """Reject mutable section paths at the public boundary."""
        section_path = _require_tuple(self.section_path)
        if any(not isinstance(section, str) for section in section_path):
            raise _invalid()
        object.__setattr__(self, "section_path", section_path)


@dataclass(frozen=True, slots=True)
class CorpusIdentity:
    """Identity of the active corpus snapshot serving a response."""

    delivery_digest: str
    source_contract_version: str
    corpus_version: str


@dataclass(frozen=True, slots=True)
class RetrievalMetadata:
    """Effective retrieval configuration for a response."""

    mode: RetrievalMode
    top_k: int
    candidate_pool_size: int | None
    applied_filters: RetrievalFilters | None
    rrf_constant: int | None


@dataclass(frozen=True, slots=True)
class RetrievalResponse:
    """Public response with exact evidence and corpus provenance."""

    contract_version: str
    request_id: str
    corpus: CorpusIdentity
    embedding: EmbeddingConfig | None
    retrieval: RetrievalMetadata
    results: tuple[RetrievalResult, ...]
    warnings: tuple[Literal["EMPTY_RESULT"], ...]

    def __post_init__(self) -> None:
        """Reject mutable result and warning collections at the boundary."""
        results = _require_tuple(self.results)
        warnings = _require_tuple(self.warnings)
        if any(not isinstance(result, RetrievalResult) for result in results):
            raise _invalid()
        if any(warning != "EMPTY_RESULT" for warning in warnings):
            raise _invalid()
        object.__setattr__(self, "results", results)
        object.__setattr__(self, "warnings", warnings)
