"""Private exact dense, PostgreSQL FTS, and deterministic hybrid retrieval."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any, Protocol, cast

from sqlalchemy import Engine, and_, bindparam, func, literal_column, select
from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import ColumnElement

from sciscope.database.models import (
    Chunk,
    ChunkEmbedding,
    DeliveryImport,
    EmbeddingSet,
    Paper,
    Section,
)
from sciscope.retrieval._bm25 import BM25Document, BM25OkapiRetriever
from sciscope.retrieval._errors import RetrievalErrorCode, RetrievalFailure
from sciscope.retrieval._ranking import (
    BranchHit,
    FusedHit,
    fuse_ranked_candidates,
)
from sciscope.retrieval._reranking import Reranker, rank_with_reranker
from sciscope.retrieval._validation import (
    InternalFilters,
    InternalRequest,
    validate_query_embedding,
    validate_request,
)

RRF_CONSTANT = 60
_ENGLISH: ColumnElement[Any] = literal_column("'english'::regconfig")


@dataclass(frozen=True, slots=True)
class _EmbeddingConfig:
    """Fixed query embedding identity for the accepted Phase A corpus."""

    provider: str = "openai"
    model: str = "text-embedding-3-small"
    dimensions: int = 1536
    query_prefix: str = ""


@dataclass(frozen=True, slots=True)
class _Corpus:
    """Active snapshot identity captured within one retrieval transaction."""

    import_id: int
    embedding_set_id: int
    delivery_digest: str
    source_contract_version: str
    corpus_version: str
    embedding_config: _EmbeddingConfig
    embedding_compatible: bool


@dataclass(frozen=True, slots=True)
class _Score:
    """Branch scores and one-based ranks for one returned chunk."""

    dense_similarity: float | None = None
    dense_rank: int | None = None
    lexical_score: float | None = None
    lexical_rank: int | None = None
    fusion_score: float | None = None


@dataclass(frozen=True, slots=True)
class _Hit:
    """Exact chunk and source provenance returned by the private core."""

    rank: int
    chunk_id: str
    text: str
    doi: str
    source_locator: str
    section_id: str
    section_path: tuple[str, ...]
    normalized_type: str
    paper: dict[str, Any]
    scores: _Score


@dataclass(slots=True)
class _RankingCandidate:
    """Mutable structural adapter for the existing Phase C ranker protocol."""

    chunk_id: str
    doi: str
    source_locator: str
    text: str
    retrieval_hit: _Hit


@dataclass(frozen=True, slots=True)
class _Response:
    """Private result object; this is not the shared retrieval.v1 facade."""

    contract_version: str
    request_id: str
    mode: str
    top_k: int
    candidate_pool_size: int | None
    applied_filters: InternalFilters
    rrf_constant: int | None
    corpus: _Corpus
    embedding: _EmbeddingConfig | None
    results: tuple[_Hit, ...]
    warnings: tuple[str, ...]


class QueryEmbedder(Protocol):
    """Minimal private seam used by deterministic test fakes."""

    def embed_query(
        self, text: str, *, config: _EmbeddingConfig
    ) -> Sequence[float]: ...


class QueryEmbeddingUnavailable(Exception):
    """Explicit adapter signal for transient provider unavailability."""


class _RetrievalCore:
    """Internal retrieval engine without the shared production service API."""

    def __init__(
        self,
        engine: Engine,
        embedder: QueryEmbedder | None,
        *,
        reranker: Reranker | None = None,
    ) -> None:
        """Bind database access and an optional offline/live adapter seam."""
        self._engine = engine
        self._embedder = embedder
        self._reranker = reranker
        self._runtime_config = _EmbeddingConfig()

    def retrieve(self, value: dict[str, object]) -> _Response:
        """Validate and run one private retrieval request.

        Args:
            value: Parsed request fields, validated before provider access.

        Returns:
            Internal response with exact chunk provenance and branch scores.

        Raises:
            RetrievalFailure: A sanitized validation, data, provider, or
                database error.
        """
        request = validate_request(value)
        vector: tuple[float, ...] | None = None
        if request.mode in ("dense", "hybrid"):
            preflight = self._read_preflight(request.request_id)
            self._ensure_compatible(preflight, request.request_id)
            if self._embedder is None:
                raise RetrievalFailure(
                    RetrievalErrorCode.EMBEDDING_UNAVAILABLE,
                    request_id=request.request_id,
                    retryable=False,
                )
            try:
                embedded = self._embedder.embed_query(
                    request.query_text, config=self._runtime_config
                )
            except QueryEmbeddingUnavailable:
                raise RetrievalFailure(
                    RetrievalErrorCode.EMBEDDING_UNAVAILABLE,
                    request_id=request.request_id,
                    retryable=True,
                ) from None
            except Exception:
                raise RetrievalFailure(
                    RetrievalErrorCode.RETRIEVAL_INTERNAL_ERROR,
                    request_id=request.request_id,
                ) from None
            vector = validate_query_embedding(
                embedded,
                expected_dimensions=self._runtime_config.dimensions,
                request_id=request.request_id,
            )
        return self._retrieve_in_snapshot(request, vector)

    def _read_preflight(self, request_id: str) -> _Corpus:
        try:
            with self._engine.connect() as connection:
                with connection.begin():
                    _set_read_only_repeatable_read(connection)
                    return _read_corpus(connection, request_id)
        except RetrievalFailure:
            raise
        except SQLAlchemyError as error:
            raise _database_failure(error, request_id) from None

    def _retrieve_in_snapshot(
        self, request: InternalRequest, vector: tuple[float, ...] | None
    ) -> _Response:
        try:
            with self._engine.connect() as connection:
                with connection.begin():
                    _set_read_only_repeatable_read(connection)
                    corpus = _read_corpus(connection, request.request_id)
                    if vector is not None:
                        self._ensure_compatible(corpus, request.request_id)
                    use_vectors = request.mode in ("dense", "hybrid")
                    eligible_count = _eligible_count(
                        connection, corpus, request.filters, use_vectors
                    )
                    effective_pool = _effective_pool(request, eligible_count)
                    dense_hits: tuple[BranchHit, ...] = ()
                    lexical_hits: tuple[BranchHit, ...] = ()
                    fused: tuple[FusedHit, ...] = ()
                    version2 = request.contract_version == "retrieval.v2"
                    if request.mode in ("dense", "hybrid"):
                        assert vector is not None
                        dense_limit = (
                            effective_pool
                            if request.mode == "hybrid"
                            else request.top_k
                        )
                        dense_hits = _dense_branch(
                            connection,
                            corpus,
                            request.filters,
                            vector,
                            dense_limit,
                        )
                    if request.mode in ("lexical", "hybrid"):
                        lexical_limit = (
                            effective_pool
                            if request.mode == "hybrid"
                            else request.top_k
                        )
                        if version2:
                            lexical_hits = _bm25_branch(
                                connection,
                                corpus,
                                request.filters,
                                request.query_text,
                                lexical_limit,
                                require_vectors=request.mode == "hybrid",
                            )
                        else:
                            lexical_hits = _lexical_branch(
                                connection,
                                corpus,
                                request.filters,
                                request.query_text,
                                lexical_limit,
                            )
                    if request.mode == "hybrid":
                        fused = fuse_ranked_candidates(
                            dense_hits,
                            lexical_hits,
                            constant=RRF_CONSTANT,
                            top_k=(
                                min(2 * effective_pool, 500)
                                if version2
                                else request.top_k
                            ),
                        )
                        candidate_ids = [item.chunk_id for item in fused]
                    elif request.mode == "dense":
                        candidate_ids = [item.chunk_id for item in dense_hits]
                    else:
                        candidate_ids = [item.chunk_id for item in lexical_hits]
                    rows = _load_result_rows(
                        connection, corpus, request.filters, candidate_ids
                    )
                    scores = _score_map(
                        request.mode, dense_hits, lexical_hits, fused
                    )
                    candidate_hits = tuple(
                        _make_hit(index, rows[chunk_id], scores[chunk_id])
                        for index, chunk_id in enumerate(candidate_ids, start=1)
                    )
                    if version2 and request.mode == "hybrid":
                        try:
                            selected_ids = list(
                                _select_v2_hybrid_candidate_ids(
                                    candidate_hits,
                                    query_text=request.query_text,
                                    top_k=request.top_k,
                                    reranker=self._reranker,
                                )
                            )
                        except Exception:
                            raise RetrievalFailure(
                                RetrievalErrorCode.RETRIEVAL_INTERNAL_ERROR,
                                request_id=request.request_id,
                            ) from None
                        by_id = {hit.chunk_id: hit for hit in candidate_hits}
                        results = tuple(
                            replace(by_id[chunk_id], rank=index)
                            for index, chunk_id in enumerate(
                                selected_ids, start=1
                            )
                        )
                    else:
                        selected_ids = candidate_ids[: request.top_k]
                        by_id = {hit.chunk_id: hit for hit in candidate_hits}
                        results = tuple(
                            replace(by_id[chunk_id], rank=index)
                            for index, chunk_id in enumerate(
                                selected_ids, start=1
                            )
                        )
                    return _Response(
                        contract_version=request.contract_version,
                        request_id=request.request_id,
                        mode=request.mode,
                        top_k=request.top_k,
                        candidate_pool_size=(
                            effective_pool if request.mode == "hybrid" else None
                        ),
                        applied_filters=request.filters,
                        rrf_constant=(
                            RRF_CONSTANT if request.mode == "hybrid" else None
                        ),
                        corpus=corpus,
                        embedding=(
                            corpus.embedding_config
                            if vector is not None
                            else None
                        ),
                        results=results,
                        warnings=("EMPTY_RESULT",) if not results else (),
                    )
        except RetrievalFailure:
            raise
        except SQLAlchemyError as error:
            raise _database_failure(error, request.request_id) from None
        except (KeyError, TypeError, ValueError, OverflowError):
            raise RetrievalFailure(
                RetrievalErrorCode.RETRIEVAL_INTERNAL_ERROR,
                request_id=request.request_id,
            ) from None

    def _ensure_compatible(self, corpus: _Corpus, request_id: str) -> None:
        if (
            not corpus.embedding_compatible
            or corpus.embedding_config != self._runtime_config
        ):
            raise RetrievalFailure(
                RetrievalErrorCode.EMBEDDING_CONFIGURATION_MISMATCH,
                request_id=request_id,
            )


def _set_read_only_repeatable_read(connection: Any) -> None:
    connection.exec_driver_sql(
        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
    )


def _read_corpus(connection: Any, request_id: str) -> _Corpus:
    row = connection.execute(
        select(
            DeliveryImport.id,
            DeliveryImport.delivery_digest,
            DeliveryImport.contract_version,
            EmbeddingSet.id.label("embedding_set_id"),
            EmbeddingSet.provider,
            EmbeddingSet.model,
            EmbeddingSet.dimensions,
            EmbeddingSet.query_prefix,
            EmbeddingSet.passage_prefix,
            EmbeddingSet.dtype,
        )
        .join(
            EmbeddingSet,
            EmbeddingSet.delivery_import_id == DeliveryImport.id,
        )
        .where(DeliveryImport.is_active.is_(True))
    ).one_or_none()
    if row is None:
        active = connection.execute(
            select(DeliveryImport.id).where(DeliveryImport.is_active.is_(True))
        ).scalar_one_or_none()
        if active is None:
            raise RetrievalFailure(
                RetrievalErrorCode.CORPUS_NOT_LOADED,
                request_id=request_id,
            )
        raise RetrievalFailure(
            RetrievalErrorCode.RETRIEVAL_INTERNAL_ERROR,
            request_id=request_id,
        )
    config = _EmbeddingConfig(
        provider=row.provider,
        model=row.model,
        dimensions=row.dimensions,
        query_prefix=row.query_prefix,
    )
    embedding_compatible = (
        row.dtype == "float32-le" and row.passage_prefix == ""
    )
    papers = connection.execute(
        select(Paper.doi, Paper.xml_sha256)
        .where(Paper.delivery_import_id == row.id)
        .order_by(Paper.doi.asc())
    ).all()
    version_hash = hashlib.sha256()
    for paper in papers:
        version_hash.update(f"{paper.doi}\t{paper.xml_sha256}\n".encode())
    return _Corpus(
        import_id=row.id,
        embedding_set_id=row.embedding_set_id,
        delivery_digest=row.delivery_digest,
        source_contract_version=row.contract_version,
        corpus_version=f"pilot17-xml-{version_hash.hexdigest()[:12]}",
        embedding_config=config,
        embedding_compatible=embedding_compatible,
    )


def _eligible_count(
    connection: Any,
    corpus: _Corpus,
    filters: InternalFilters,
    use_vectors: bool,
) -> int:
    statement = select(func.count()).select_from(Chunk)
    statement = _join_metadata(statement)
    if use_vectors:
        statement = statement.join(
            ChunkEmbedding,
            and_(
                ChunkEmbedding.chunk_id == Chunk.chunk_id,
                ChunkEmbedding.delivery_import_id == Chunk.delivery_import_id,
                ChunkEmbedding.embedding_set_id == corpus.embedding_set_id,
            ),
        )
    statement = statement.where(
        Chunk.delivery_import_id == corpus.import_id,
        *_filter_predicates(filters),
    )
    return int(connection.execute(statement).scalar_one())


def _effective_pool(request: InternalRequest, eligible_count: int) -> int:
    if request.mode != "hybrid":
        return request.top_k
    if request.candidate_pool_size is not None:
        return min(eligible_count, request.candidate_pool_size)
    default_size = min(250, max(50, 5 * request.top_k))
    return min(eligible_count, default_size)


def _dense_branch(
    connection: Any,
    corpus: _Corpus,
    filters: InternalFilters,
    vector: tuple[float, ...],
    limit: int,
) -> tuple[BranchHit, ...]:
    distance = ChunkEmbedding.embedding.cosine_distance(list(vector))
    statement = select(
        Chunk.chunk_id, (1.0 - distance).label("similarity")
    ).select_from(Chunk)
    statement = _join_metadata(statement)
    statement = statement.join(
        ChunkEmbedding,
        and_(
            ChunkEmbedding.chunk_id == Chunk.chunk_id,
            ChunkEmbedding.delivery_import_id == Chunk.delivery_import_id,
            ChunkEmbedding.embedding_set_id == corpus.embedding_set_id,
        ),
    ).where(
        Chunk.delivery_import_id == corpus.import_id,
        *_filter_predicates(filters),
    )
    statement = statement.order_by(distance.asc(), Chunk.chunk_id.asc()).limit(
        limit
    )
    return tuple(
        BranchHit(str(row.chunk_id), float(row.similarity))
        for row in connection.execute(statement)
    )


def _lexical_branch(
    connection: Any,
    corpus: _Corpus,
    filters: InternalFilters,
    query_text: str,
    limit: int,
) -> tuple[BranchHit, ...]:
    query = func.websearch_to_tsquery(_ENGLISH, bindparam("query_text"))
    node_count = connection.execute(
        select(func.numnode(query)), {"query_text": query_text}
    ).scalar_one()
    if not node_count:
        return ()
    vector = func.to_tsvector(_ENGLISH, Chunk.text)
    rank = func.ts_rank_cd(vector, query)
    statement = select(Chunk.chunk_id, rank.label("rank_score")).select_from(
        Chunk
    )
    statement = _join_metadata(statement)
    statement = statement.where(
        Chunk.delivery_import_id == corpus.import_id,
        vector.op("@@")(query),
        *_filter_predicates(filters),
    )
    statement = statement.order_by(rank.desc(), Chunk.chunk_id.asc()).limit(
        limit
    )
    return tuple(
        BranchHit(str(row.chunk_id), float(row.rank_score))
        for row in connection.execute(statement, {"query_text": query_text})
    )


def _bm25_branch(
    connection: Any,
    corpus: _Corpus,
    filters: InternalFilters,
    query_text: str,
    limit: int,
    *,
    require_vectors: bool,
) -> tuple[BranchHit, ...]:
    statement = select(Chunk.chunk_id, Chunk.text).select_from(Chunk)
    statement = _join_metadata(statement)
    if require_vectors:
        statement = statement.join(
            ChunkEmbedding,
            and_(
                ChunkEmbedding.chunk_id == Chunk.chunk_id,
                ChunkEmbedding.delivery_import_id == Chunk.delivery_import_id,
                ChunkEmbedding.embedding_set_id == corpus.embedding_set_id,
            ),
        )
    statement = statement.where(
        Chunk.delivery_import_id == corpus.import_id,
        *_filter_predicates(filters),
    )
    rows = connection.execute(statement.order_by(Chunk.chunk_id.asc())).all()
    retriever = BM25OkapiRetriever(
        tuple(BM25Document(str(row.chunk_id), row.text) for row in rows)
    )
    return tuple(
        BranchHit(hit.chunk_id, hit.score)
        for hit in retriever.search(query_text, limit=limit)
    )


def _select_v2_hybrid_candidate_ids(
    candidates: Sequence[_Hit],
    *,
    query_text: str,
    top_k: int,
    reranker: Reranker | None,
) -> tuple[str, ...]:
    if reranker is None:
        return tuple(hit.chunk_id for hit in candidates[:top_k])
    rankable = tuple(
        _RankingCandidate(
            chunk_id=hit.chunk_id,
            doi=hit.doi,
            source_locator=hit.source_locator,
            text=hit.text,
            retrieval_hit=hit,
        )
        for hit in candidates
    )
    ranked = rank_with_reranker(
        rankable,
        query_text=query_text,
        reranker=reranker,
        max_per_doi=None,
    )
    return tuple(item.hit.chunk_id for item in ranked.candidates[:top_k])


def _join_metadata(statement: Select[Any]) -> Select[Any]:
    return statement.join(
        Paper,
        and_(
            Paper.delivery_import_id == Chunk.delivery_import_id,
            Paper.doi == Chunk.doi,
        ),
    ).join(
        Section,
        and_(
            Section.delivery_import_id == Chunk.delivery_import_id,
            Section.doi == Chunk.doi,
            Section.section_id == Chunk.section_id,
        ),
    )


def _filter_predicates(filters: InternalFilters) -> list[Any]:
    predicates: list[Any] = []
    if filters.publication_year_from is not None:
        predicates.append(
            Paper.publication_year >= filters.publication_year_from
        )
    if filters.publication_year_to is not None:
        predicates.append(Paper.publication_year <= filters.publication_year_to)
    if filters.normalized_types is not None:
        predicates.append(Chunk.normalized_type.in_(filters.normalized_types))
    if filters.journals is not None:
        predicates.append(Paper.journal.in_(filters.journals))
    if filters.languages is not None:
        predicates.append(func.lower(Paper.language).in_(filters.languages))
    if filters.dois is not None:
        predicates.append(Paper.doi.in_(filters.dois))
    return predicates


def _load_result_rows(
    connection: Any,
    corpus: _Corpus,
    filters: InternalFilters,
    chunk_ids: list[str],
) -> dict[str, Any]:
    if not chunk_ids:
        return {}
    statement = select(
        Chunk.chunk_id,
        Chunk.text,
        Chunk.doi,
        Chunk.source_locator.label("chunk_locator"),
        Chunk.section_id,
        Chunk.section_path,
        Chunk.normalized_type,
        Section.source_locator.label("section_locator"),
        Paper.title,
        Paper.authors,
        Paper.journal,
        Paper.publication_year,
        Paper.language,
        Paper.license,
        Paper.source_url,
    ).select_from(Chunk)
    statement = _join_metadata(statement).where(
        Chunk.delivery_import_id == corpus.import_id,
        Chunk.chunk_id.in_(chunk_ids),
        *_filter_predicates(filters),
    )
    return {str(row.chunk_id): row for row in connection.execute(statement)}


def _score_map(
    mode: str,
    dense: Sequence[BranchHit],
    lexical: Sequence[BranchHit],
    fused: Sequence[FusedHit],
) -> dict[str, _Score]:
    dense_values = {
        hit.chunk_id: (hit.score, rank)
        for rank, hit in enumerate(dense, start=1)
    }
    lexical_values = {
        hit.chunk_id: (hit.score, rank)
        for rank, hit in enumerate(lexical, start=1)
    }
    fused_values = {hit.chunk_id: hit for hit in fused}
    ids = dense_values.keys() | lexical_values.keys()
    result: dict[str, _Score] = {}
    for chunk_id in ids:
        dense_value = dense_values.get(chunk_id)
        lexical_value = lexical_values.get(chunk_id)
        fused_value = fused_values.get(chunk_id)
        result[chunk_id] = _Score(
            dense_similarity=(dense_value[0] if dense_value else None),
            dense_rank=(dense_value[1] if dense_value else None),
            lexical_score=(lexical_value[0] if lexical_value else None),
            lexical_rank=(lexical_value[1] if lexical_value else None),
            fusion_score=(
                fused_value.score if mode == "hybrid" and fused_value else None
            ),
        )
    return result


def _make_hit(index: int, row: Any, scores: _Score) -> _Hit:
    path = row.section_path
    authors = row.authors
    if not isinstance(path, list) or not isinstance(authors, list):
        raise ValueError("Invalid persisted provenance")
    return _Hit(
        rank=index,
        chunk_id=row.chunk_id,
        text=row.text,
        doi=row.doi,
        source_locator=row.chunk_locator,
        section_id=row.section_id,
        section_path=tuple(cast(list[str], path)),
        normalized_type=row.normalized_type,
        paper={
            "title": row.title,
            "authors": tuple(dict(author) for author in authors),
            "journal": row.journal,
            "publication_year": row.publication_year,
            "language": row.language,
            "license": row.license,
            "source_url": row.source_url,
        },
        scores=scores,
    )


def _database_failure(
    error: SQLAlchemyError, request_id: str
) -> RetrievalFailure:
    if isinstance(error, DBAPIError):
        sqlstate = getattr(error.orig, "sqlstate", None)
        retryable = (
            error.connection_invalidated
            or (
                isinstance(sqlstate, str)
                and (
                    sqlstate.startswith("08") or sqlstate in {"40001", "40P01"}
                )
            )
            or (isinstance(error, OperationalError) and sqlstate is None)
        )
        if retryable:
            return RetrievalFailure(
                RetrievalErrorCode.DATABASE_UNAVAILABLE,
                request_id=request_id,
                retryable=True,
            )
    return RetrievalFailure(
        RetrievalErrorCode.RETRIEVAL_INTERNAL_ERROR,
        request_id=request_id,
    )
