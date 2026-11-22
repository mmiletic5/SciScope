"""RED tests for the public retrieval-service construction boundary."""

from __future__ import annotations

import importlib
import inspect
import subprocess
import sys
from dataclasses import FrozenInstanceError, replace
from types import ModuleType
from typing import Any

import pytest

from sciscope.retrieval._core import (
    _Corpus,
    _EmbeddingConfig,
    _Hit,
    _Response,
    _Score,
)
from sciscope.retrieval._errors import RetrievalErrorCode, RetrievalFailure
from sciscope.retrieval._validation import InternalFilters
from sciscope.retrieval.errors import PUBLIC_MESSAGES


def _public_api() -> ModuleType:
    """Import the public package after requiring T007-C exports."""
    module = importlib.import_module("sciscope.retrieval")
    missing = [
        name
        for name in ("RetrievalService", "QueryEmbedder")
        if not hasattr(module, name)
    ]
    assert not missing, f"Missing public retrieval exports: {missing}"
    return module


def _valid_response(module: ModuleType) -> Any:
    """Build the smallest valid public response for forwarding tests."""
    corpus = module.CorpusIdentity(
        delivery_digest="sha256:" + "a" * 64,
        source_contract_version="0.3.0",
        corpus_version="pilot17-xml-1fff1573b610",
    )
    metadata = module.RetrievalMetadata(
        mode="lexical",
        top_k=3,
        candidate_pool_size=None,
        applied_filters=None,
        rrf_constant=None,
    )
    return module.RetrievalResponse(
        contract_version="retrieval.v1",
        request_id="service-red-1",
        corpus=corpus,
        embedding=None,
        retrieval=metadata,
        results=(),
        warnings=("EMPTY_RESULT",),
    )


def _valid_request(module: ModuleType) -> Any:
    """Build a request that exercises all public forwarding fields."""
    filters = module.RetrievalFilters(
        publication_year_from=2010,
        publication_year_to=2020,
        normalized_types=("results",),
        journals=("PLOS ONE",),
        languages=("EN",),
        dois=("10.1371/journal.pone.0077354",),
    )
    ranking = module.RankingOptions(candidate_pool_size=9)
    return module.RetrievalRequest(
        contract_version="retrieval.v2",
        request_id="service-red-1",
        query_text="honey bee homing",
        mode="hybrid",
        top_k=3,
        filters=filters,
        ranking=ranking,
    )


def test_public_package_exports_service_and_embedder() -> None:
    """The root package exports the approved public facade types."""
    module = _public_api()
    assert module.RetrievalService.__module__ == "sciscope.retrieval.service"
    assert module.QueryEmbedder.__module__ == "sciscope.retrieval.service"


def test_query_embedder_is_a_public_keyword_config_protocol() -> None:
    """The public embedder seam accepts only the documented configuration."""
    module = _public_api()
    protocol = module.QueryEmbedder
    parameters = inspect.signature(protocol.embed_query).parameters

    assert getattr(protocol, "_is_protocol", False)
    assert tuple(parameters) == ("self", "text", "config")
    assert parameters["config"].kind is inspect.Parameter.KEYWORD_ONLY


def test_public_import_isolated_from_private_and_database_modules() -> None:
    """A fresh public import has no private-core or database-driver imports."""
    script = """
import sys
sys.path.insert(0, 'src')
import sciscope.retrieval as retrieval
assert hasattr(retrieval, 'RetrievalService')
assert hasattr(retrieval, 'QueryEmbedder')
forbidden = (
    'sqlalchemy',
    'pgvector',
    'psycopg',
    'asyncpg',
    'sciscope.retrieval._core',
)
loaded = set(sys.modules)
assert not any(
    name == forbidden_name or name.startswith(forbidden_name + '.')
    for forbidden_name in forbidden
    for name in loaded
), sorted(name for name in loaded if name.startswith(forbidden))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout


def test_constructor_injection_does_not_execute_the_executor() -> None:
    """Construction uses a driver-independent executor and performs no work."""
    module = _public_api()

    class FakeExecutor:
        def __init__(self) -> None:
            self.calls: list[Any] = []

        def retrieve(self, request: Any) -> Any:
            self.calls.append(request)
            raise AssertionError(
                "The executor must not run during construction"
            )

    executor = FakeExecutor()
    module.RetrievalService(executor=executor)

    assert executor.calls == []


def test_service_forwards_the_exact_public_request_to_executor() -> None:
    """The facade forwards canonical values without version substitution."""
    module = _public_api()
    response = _valid_response(module)

    class FakeExecutor:
        def __init__(self) -> None:
            self.calls: list[Any] = []

        def retrieve(self, request: Any) -> Any:
            self.calls.append(request)
            return response

    executor = FakeExecutor()
    service = module.RetrievalService(executor=executor)
    request = _valid_request(module)

    assert service.retrieve(request) is response
    assert executor.calls == [request]
    forwarded = executor.calls[0]
    assert forwarded.contract_version == "retrieval.v2"
    assert forwarded.request_id == "service-red-1"
    assert forwarded.query_text == "honey bee homing"
    assert forwarded.mode == "hybrid"
    assert forwarded.top_k == 3
    assert forwarded.filters is request.filters
    assert forwarded.ranking is request.ranking


def _private_response(
    *,
    contract_version: str = "retrieval.v2",
    results: tuple[_Hit, ...] | None = None,
) -> _Response:
    """Build a representative private-core response using actual core shapes."""
    filters = InternalFilters(
        publication_year_from=2010,
        publication_year_to=2020,
        normalized_types=("results",),
        journals=("PLOS ONE",),
        languages=("en",),
        dois=("10.1371/journal.pone.0077354",),
    )
    config = _EmbeddingConfig(
        provider="openai",
        model="text-embedding-3-small",
        dimensions=1536,
        query_prefix="query: ",
    )
    corpus = _Corpus(
        import_id=41,
        embedding_set_id=42,
        delivery_digest="sha256:" + "c" * 64,
        source_contract_version="0.3.0",
        corpus_version="pilot17-xml-1fff1573b610",
        embedding_config=config,
        embedding_compatible=True,
    )
    hit = _Hit(
        rank=1,
        chunk_id="d" * 64,
        text="Exact persisted source passage.",
        doi="10.1371/journal.pone.0077354",
        source_locator="jats:v1:xml-sha256:/article[1]/body[1]/sec[2]/p[3]",
        section_id="10.1371/journal.pone.0077354#sec-2",
        section_path=("Results", "Subsection"),
        normalized_type="results",
        paper={
            "title": "Exact source title",
            "authors": (
                {"surname": "Zeta", "given_names": "Z."},
                {"surname": "Alpha", "given_names": "A."},
            ),
            "journal": "PLOS ONE",
            "publication_year": 2013,
            "language": "EN",
            "license": "CC BY 4.0",
            "source_url": "https://doi.org/10.1371/journal.pone.0077354",
        },
        scores=_Score(
            dense_similarity=0.8125,
            dense_rank=2,
            lexical_score=0.125,
            lexical_rank=1,
            fusion_score=0.03252,
        ),
    )
    response_results = (hit,) if results is None else results
    return _Response(
        contract_version=contract_version,
        request_id="service-red-1",
        mode="hybrid",
        top_k=3,
        candidate_pool_size=9,
        applied_filters=filters,
        rrf_constant=60,
        corpus=corpus,
        embedding=config,
        results=response_results,
        warnings=("EMPTY_RESULT",) if not response_results else (),
    )


class _PrivateResponseExecutor:
    """Fake executor returning one private-core response for mapping tests."""

    def __init__(self, outcome: object) -> None:
        self.calls: list[Any] = []
        self._outcome = outcome

    def retrieve(self, request: Any) -> Any:
        """Record a call then return or raise the configured outcome."""
        self.calls.append(request)
        if isinstance(self._outcome, BaseException):
            raise self._outcome
        return self._outcome


@pytest.mark.parametrize("contract_version", ["retrieval.v1", "retrieval.v2"])
def test_service_maps_private_response_with_exact_provenance(
    contract_version: str,
) -> None:
    """Map private values without changing provenance or version."""
    module = _public_api()
    private_response = _private_response(contract_version=contract_version)
    executor = _PrivateResponseExecutor(private_response)
    service = module.RetrievalService(executor=executor)

    response = service.retrieve(_valid_request(module))

    assert isinstance(response, module.RetrievalResponse)
    assert response.contract_version == contract_version
    assert response.request_id == "service-red-1"
    assert response.corpus == module.CorpusIdentity(
        delivery_digest="sha256:" + "c" * 64,
        source_contract_version="0.3.0",
        corpus_version="pilot17-xml-1fff1573b610",
    )
    assert response.embedding == module.EmbeddingConfig(
        provider="openai",
        model="text-embedding-3-small",
        dimensions=1536,
        query_prefix="query: ",
    )
    assert response.retrieval == module.RetrievalMetadata(
        mode="hybrid",
        top_k=3,
        candidate_pool_size=9,
        applied_filters=module.RetrievalFilters(
            publication_year_from=2010,
            publication_year_to=2020,
            normalized_types=("results",),
            journals=("PLOS ONE",),
            languages=("en",),
            dois=("10.1371/journal.pone.0077354",),
        ),
        rrf_constant=60,
    )
    assert len(response.results) == 1
    result = response.results[0]
    assert result.chunk_id == "d" * 64
    assert result.text == "Exact persisted source passage."
    assert result.doi == "10.1371/journal.pone.0077354"
    assert result.source_locator == (
        "jats:v1:xml-sha256:/article[1]/body[1]/sec[2]/p[3]"
    )
    assert result.section_id == "10.1371/journal.pone.0077354#sec-2"
    assert result.section_path == ("Results", "Subsection")
    assert result.normalized_type == "results"
    assert result.paper.title == "Exact source title"
    assert tuple(
        (author.surname, author.given_names) for author in result.paper.authors
    ) == (("Zeta", "Z."), ("Alpha", "A."))
    assert result.paper.journal == "PLOS ONE"
    assert result.paper.publication_year == 2013
    assert result.paper.language == "EN"
    assert result.paper.license == "CC BY 4.0"
    assert (
        result.paper.source_url
        == "https://doi.org/10.1371/journal.pone.0077354"
    )
    assert result.scores == module.RetrievalScore(0.8125, 2, 0.125, 1, 0.03252)
    assert executor.calls == [_valid_request(module)]


def test_service_maps_empty_private_response_with_corpus_identity() -> None:
    """Map an empty private response as successful and reproducible."""
    module = _public_api()
    private_response = _private_response(results=())
    executor = _PrivateResponseExecutor(private_response)

    response = module.RetrievalService(executor=executor).retrieve(
        _valid_request(module)
    )

    assert isinstance(response, module.RetrievalResponse)
    assert response.results == ()
    assert response.warnings == ("EMPTY_RESULT",)
    assert response.corpus.delivery_digest == "sha256:" + "c" * 64
    assert response.corpus.source_contract_version == "0.3.0"
    assert response.corpus.corpus_version == "pilot17-xml-1fff1573b610"
    assert executor.calls == [_valid_request(module)]


def test_service_translates_private_failure_without_leaking_private_type() -> (
    None
):
    """A private failure becomes a fresh sanitized public exception once."""
    module = _public_api()
    failure = RetrievalFailure(
        RetrievalErrorCode.DATABASE_UNAVAILABLE,
        request_id="service-red-1",
        retryable=True,
    )
    executor = _PrivateResponseExecutor(failure)

    with pytest.raises(module.RetrievalException) as raised:
        module.RetrievalService(executor=executor).retrieve(
            _valid_request(module)
        )

    assert type(raised.value) is module.RetrievalException
    assert raised.value.code is module.RetrievalErrorCode.DATABASE_UNAVAILABLE
    assert raised.value.request_id == "service-red-1"
    assert raised.value.retryable is True
    assert (
        raised.value.public_message
        == "The retrieval database is temporarily unavailable."
    )
    assert "DATABASE_UNAVAILABLE" not in str(raised.value)
    assert executor.calls == [_valid_request(module)]


def test_service_sanitizes_unexpected_executor_exception_once() -> None:
    """Unexpected implementation text never crosses the public boundary."""
    module = _public_api()
    executor = _PrivateResponseExecutor(ValueError("postgres://secret@host/db"))

    with pytest.raises(module.RetrievalException) as raised:
        module.RetrievalService(executor=executor).retrieve(
            _valid_request(module)
        )

    assert type(raised.value) is module.RetrievalException
    assert (
        raised.value.code is module.RetrievalErrorCode.RETRIEVAL_INTERNAL_ERROR
    )
    assert raised.value.request_id == "service-red-1"
    assert raised.value.retryable is False
    assert raised.value.public_message == "Retrieval could not complete."
    assert "secret" not in str(raised.value)
    assert executor.calls == [_valid_request(module)]


class _RecordingPrivateCore:
    """Offline private-core fake that records raw adapter input."""

    def __init__(self, outcome: object) -> None:
        self.calls: list[dict[str, object]] = []
        self._outcome = outcome

    def retrieve(self, value: dict[str, object]) -> object:
        """Record the raw request without opening a database connection."""
        self.calls.append(value)
        return self._outcome


def _private_executor(service_module: ModuleType, core: object) -> Any:
    """Require the selected private adapter seam without exporting it."""
    return service_module._PrivateCoreExecutor(core)


def test_private_executor_converts_a_canonical_public_request() -> None:
    """The private adapter emits only the core's documented raw fields."""
    module = _public_api()
    service_module = importlib.import_module("sciscope.retrieval.service")
    core = _RecordingPrivateCore(_private_response())
    request = _valid_request(module)

    outcome = _private_executor(service_module, core).retrieve(request)

    assert outcome is core._outcome
    assert core.calls == [
        {
            "contract_version": "retrieval.v2",
            "request_id": "service-red-1",
            "query_text": "honey bee homing",
            "mode": "hybrid",
            "top_k": 3,
            "filters": {
                "publication_year_from": 2010,
                "publication_year_to": 2020,
                "normalized_types": ("results",),
                "journals": ("PLOS ONE",),
                "languages": ("en",),
                "dois": ("10.1371/journal.pone.0077354",),
            },
            "ranking": {"candidate_pool_size": 9},
        }
    ]


@pytest.mark.parametrize(
    ("filters", "ranking", "expected_filters"),
    [
        (None, None, None),
        (
            {"journals": ("PLOS ONE",)},
            {},
            {"journals": ("PLOS ONE",)},
        ),
    ],
)
def test_private_executor_omits_unset_optional_request_fields(
    filters: dict[str, tuple[str, ...]] | None,
    ranking: dict[str, object] | None,
    expected_filters: dict[str, tuple[str, ...]] | None,
) -> None:
    """Unset public fields do not become invalid None-valued core fields."""
    module = _public_api()
    service_module = importlib.import_module("sciscope.retrieval.service")
    public_filters = (
        None
        if filters is None
        else module.RetrievalFilters(journals=filters["journals"])
    )
    public_ranking = (
        None
        if ranking is None
        else module.RankingOptions(candidate_pool_size=None)
    )
    request = module.RetrievalRequest(
        contract_version="retrieval.v2",
        request_id="optional-fields-1",
        query_text="honey bee homing",
        mode="hybrid" if public_ranking is not None else "lexical",
        top_k=3,
        filters=public_filters,
        ranking=public_ranking,
    )
    core = _RecordingPrivateCore(_private_response())

    _private_executor(service_module, core).retrieve(request)

    raw_request = core.calls[0]
    assert raw_request["contract_version"] == "retrieval.v2"
    assert raw_request["mode"] == (
        "hybrid" if public_ranking is not None else "lexical"
    )
    assert raw_request.get("filters") == expected_filters
    assert "ranking" not in raw_request


@pytest.mark.parametrize(
    ("contract_version", "mode"),
    [
        ("retrieval.v1", "dense"),
        ("retrieval.v2", "lexical"),
        ("retrieval.v2", "hybrid"),
    ],
)
def test_private_executor_preserves_explicit_version_and_mode(
    contract_version: str, mode: str
) -> None:
    """Private execution does not substitute a version, mode, or request."""
    module = _public_api()
    service_module = importlib.import_module("sciscope.retrieval.service")
    request = module.RetrievalRequest(
        contract_version=contract_version,
        request_id=f"forward-{contract_version}-{mode}",
        query_text="honey bee homing",
        mode=mode,
        top_k=3,
    )
    core = _RecordingPrivateCore(_private_response())

    _private_executor(service_module, core).retrieve(request)

    assert len(core.calls) == 1
    assert core.calls[0]["contract_version"] == contract_version
    assert core.calls[0]["mode"] == mode
    assert request.contract_version == contract_version
    assert request.mode == mode


def test_private_embedder_bridge_copies_private_config_exactly() -> None:
    """The private embedder sees no public types and preserves vectors."""
    module = _public_api()
    service_module = importlib.import_module("sciscope.retrieval.service")
    vector = (0.6, 0.8)

    class PublicEmbedder:
        def __init__(self) -> None:
            self.calls: list[tuple[str, Any]] = []

        def embed_query(self, text: str, *, config: Any) -> tuple[float, ...]:
            self.calls.append((text, config))
            return vector

    embedder = PublicEmbedder()
    private_config = _EmbeddingConfig(
        provider="offline",
        model="offline-query-model",
        dimensions=2,
        query_prefix="query: ",
    )

    returned = service_module._PrivateEmbedderBridge(embedder).embed_query(
        "honey bee homing", config=private_config
    )

    assert returned is vector
    assert embedder.calls == [
        (
            "honey bee homing",
            module.EmbeddingConfig(
                provider="offline",
                model="offline-query-model",
                dimensions=2,
                query_prefix="query: ",
            ),
        )
    ]
    with pytest.raises(FrozenInstanceError):
        embedder.calls[0][1].model = "changed"


def test_private_executor_flows_private_response_through_public_mapping() -> (
    None
):
    """A concrete core response reaches the established public mapper."""
    module = _public_api()
    service_module = importlib.import_module("sciscope.retrieval.service")
    private_response = _private_response()
    core = _RecordingPrivateCore(private_response)

    response = module.RetrievalService(
        executor=_private_executor(service_module, core)
    ).retrieve(_valid_request(module))

    assert isinstance(response, module.RetrievalResponse)
    assert response.results[0].chunk_id == "d" * 64
    assert response.results[0].source_locator == (
        "jats:v1:xml-sha256:/article[1]/body[1]/sec[2]/p[3]"
    )
    assert response.corpus.delivery_digest == "sha256:" + "c" * 64


def test_private_composition_passes_dependencies_without_eager_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lazy composition gives the core exact dependencies without execution."""
    _public_api()
    service_module = importlib.import_module("sciscope.retrieval.service")
    core_module = importlib.import_module("sciscope.retrieval._core")

    class NoConnectionEngine:
        def connect(self) -> None:
            raise AssertionError("Composition must not open a connection")

    class PublicEmbedder:
        def embed_query(self, text: str, *, config: Any) -> tuple[float, ...]:
            raise AssertionError("Composition must not call the embedder")

    class RecordingCore:
        instances: list[Any] = []

        def __init__(
            self, engine: object, embedder: object, *, reranker: object | None
        ) -> None:
            self.engine = engine
            self.embedder = embedder
            self.reranker = reranker
            self.calls: list[dict[str, object]] = []
            type(self).instances.append(self)

        def retrieve(self, value: dict[str, object]) -> _Response:
            self.calls.append(value)
            raise AssertionError("Composition must not retrieve")

    engine = NoConnectionEngine()
    embedder = PublicEmbedder()
    reranker = object()
    monkeypatch.setattr(core_module, "_RetrievalCore", RecordingCore)

    executor = service_module._compose_private_executor(
        engine=engine, embedder=embedder, reranker=reranker
    )

    assert type(executor).__name__ == "_PrivateCoreExecutor"
    assert len(RecordingCore.instances) == 1
    core = RecordingCore.instances[0]
    assert core.engine is engine
    assert type(core.embedder).__name__ == "_PrivateEmbedderBridge"
    assert core.reranker is reranker
    assert core.calls == []


@pytest.mark.parametrize("contract_version", ["retrieval.v1", "retrieval.v2"])
def test_service_preserves_matching_request_and_response_versions(
    contract_version: str,
) -> None:
    """A public service call preserves one explicitly selected version."""
    module = _public_api()
    request = replace(_valid_request(module), contract_version=contract_version)
    executor = _PrivateResponseExecutor(
        _private_response(contract_version=contract_version)
    )

    response = module.RetrievalService(executor=executor).retrieve(request)

    assert isinstance(response, module.RetrievalResponse)
    assert executor.calls == [request]
    assert response.contract_version == contract_version
    assert response.request_id == request.request_id
    assert response.corpus.delivery_digest == "sha256:" + "c" * 64
    assert response.results[0].chunk_id == "d" * 64


@pytest.mark.parametrize(
    ("code", "retryable"),
    [
        (RetrievalErrorCode.INVALID_REQUEST, False),
        (RetrievalErrorCode.UNSUPPORTED_CONTRACT_VERSION, False),
        (RetrievalErrorCode.CORPUS_NOT_LOADED, False),
        (RetrievalErrorCode.EMBEDDING_CONFIGURATION_MISMATCH, False),
        (RetrievalErrorCode.EMBEDDING_UNAVAILABLE, True),
        (RetrievalErrorCode.DATABASE_UNAVAILABLE, True),
        (RetrievalErrorCode.RETRIEVAL_INTERNAL_ERROR, False),
    ],
)
def test_service_translates_each_approved_private_failure_code(
    code: RetrievalErrorCode, retryable: bool
) -> None:
    """Every approved private failure maps to a fresh public error once."""
    module = _public_api()
    request = _valid_request(module)
    failure = RetrievalFailure(
        code, request_id=request.request_id, retryable=retryable
    )
    object.__setattr__(failure, "diagnostic", "private diagnostic secret")
    executor = _PrivateResponseExecutor(failure)

    with pytest.raises(module.RetrievalException) as raised:
        module.RetrievalService(executor=executor).retrieve(request)

    assert type(raised.value) is module.RetrievalException
    assert raised.value is not failure
    assert not isinstance(raised.value, RetrievalFailure)
    assert raised.value.code is code
    assert raised.value.request_id == request.request_id
    assert raised.value.retryable is retryable
    assert raised.value.public_message == PUBLIC_MESSAGES[code]
    assert "private diagnostic secret" not in str(raised.value)
    assert executor.calls == [request]


def test_consumer_subprocess_uses_facade_without_private_imports() -> None:
    """A consumer can use the facade without loading private dependencies."""
    script = """
import sys
sys.path.insert(0, 'src')
from sciscope.retrieval import (
    CorpusIdentity,
    RetrievalMetadata,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalService,
)

class FakeExecutor:
    def __init__(self, response):
        self.calls = []
        self.response = response

    def retrieve(self, request):
        self.calls.append(request)
        return self.response

request = RetrievalRequest(
    contract_version='retrieval.v2',
    request_id='consumer-isolation-1',
    query_text='honey bee homing',
    mode='lexical',
    top_k=1,
)
response = RetrievalResponse(
    contract_version='retrieval.v2',
    request_id='consumer-isolation-1',
    corpus=CorpusIdentity(
        delivery_digest='sha256:' + 'a' * 64,
        source_contract_version='0.3.0',
        corpus_version='pilot17-xml-1fff1573b610',
    ),
    embedding=None,
    retrieval=RetrievalMetadata('lexical', 1, None, None, None),
    results=(),
    warnings=('EMPTY_RESULT',),
)
executor = FakeExecutor(response)
returned = RetrievalService(executor=executor).retrieve(request)
assert returned is response
assert executor.calls == [request]
assert returned.contract_version == request.contract_version
assert returned.results == ()
forbidden = (
    'sqlalchemy', 'pgvector', 'psycopg', 'asyncpg',
    'sciscope.retrieval._core', 'openai', 'google', 'anthropic',
)
loaded = set(sys.modules)
assert not any(
    name == prefix or name.startswith(prefix + '.')
    for prefix in forbidden
    for name in loaded
), sorted(name for name in loaded if name.startswith(forbidden))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
