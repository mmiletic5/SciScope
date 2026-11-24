"""v2 API for the four workflows: contract fixtures, fake mode, routing."""

from __future__ import annotations

import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from typing import Any, cast, get_args

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter, ValidationError

from backend import workflow_fixtures as fx
from sciscope.api import server
from sciscope.api.app import create_app
from sciscope.api.composition import create_application
from sciscope.api.http_models import QuestionRequest, Workflow
from sciscope.api.http_models_v2 import (
    ErrorResponseV2,
    HealthResponse,
    QuestionRequestV2,
    SuccessResponseV2,
    WorkflowV2,
)
from sciscope.api.server import WORKFLOW_TOP_K, create_server_app
from sciscope.question_service.contracts import (
    WORKFLOWS,
    ComparisonPayload,
    ComponentMetadata,
    ProviderOutcome,
    QuestionMetadata,
    RetrievalOutcome,
)
from sciscope.question_service.fakes import (
    ComponentFakeAnswerProvider,
    ComponentFakeRetrieval,
)

SUCCESS: TypeAdapter[Any] = TypeAdapter(cast(Any, SuccessResponseV2))
SUCCESS_FIXTURES = (
    "research_question.answered.json",
    "research_question.insufficient_evidence.json",
    "no_results.json",
    "insufficient_evidence.json",
    "evidence_comparison.answered.json",
    "conflicting_evidence.answered.json",
    "research_gap.answered.json",
)
ERROR_FIXTURES = (
    "error.invalid_request.json",
    "error.provider_unavailable.json",
)
PAYLOAD_FIELDS = {
    "evidence_comparison": "comparison",
    "conflicting_evidence": "conflicts",
    "research_gap": "gap_analysis",
}
RESEARCH_QUESTION_KEYS = {
    "api_version",
    "request_id",
    "workflow",
    "status",
    "answer",
    "claims",
    "evidence",
    "corpus",
    "metadata",
}
FAKE_KEY = "sk-FAKE" + "q" * 40
SYNTHETIC = ComponentMetadata("synthetic", executed=True, is_test_data=True)
FAKE = ComponentMetadata("fake", executed=True, is_test_data=True)
METADATA = QuestionMetadata(
    retrieval=replace(SYNTHETIC, executed=False),
    answer_provider=replace(FAKE, executed=False),
)


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fail any real urllib request (the provider transport uses urllib).

    Sockets stay usable: the TestClient event loop needs a local socketpair.
    """

    def blocked(*args: object, **kwargs: object) -> None:
        raise AssertionError("Real network access is forbidden")

    monkeypatch.setattr(urllib.request, "urlopen", blocked)
    yield


def _ask(client: TestClient, workflow: str) -> Any:
    return client.post(
        "/api/v2/questions",
        json={"workflow": workflow, "question": "Synthetic question?"},
    )


def _app(retrieval: object, provider: object, **kwargs: Any) -> TestClient:
    return TestClient(
        create_app(
            retrieval=retrieval,
            provider=provider,
            v2_metadata=METADATA,
            **kwargs,
        ),
        raise_server_exceptions=False,
    )


# Models versus the frozen contract fixtures.


@pytest.mark.parametrize("name", SUCCESS_FIXTURES)
def test_success_fixtures_parse_and_round_trip(name: str) -> None:
    """Every v2 success fixture parses and serializes to the same JSON."""
    document = fx.load(name)

    model = SUCCESS.validate_python(document)

    assert SUCCESS.dump_python(model, mode="json") == document


@pytest.mark.parametrize("name", ERROR_FIXTURES)
def test_error_fixtures_parse_and_round_trip(name: str) -> None:
    """Error fixtures parse; metadata stays absent when the fixture omits it."""
    document = fx.load(name)

    model = ErrorResponseV2.model_validate(document)

    assert model.model_dump(mode="json", exclude_none=True) == document


def test_health_fixture_parses_and_round_trips() -> None:
    """The health model accepts the contract example."""
    document = fx.load("health.json")

    assert HealthResponse.model_validate(document).model_dump() == document


def test_workflow_literals_match_the_contract_and_v1_is_unchanged() -> None:
    """v2 gains four workflows; v1 keeps only research_question."""
    assert get_args(WorkflowV2) == WORKFLOWS
    assert get_args(Workflow) == ("research_question",)
    request_workflow = QuestionRequestV2.model_fields["workflow"].annotation
    assert get_args(request_workflow) == WORKFLOWS
    with pytest.raises(ValidationError):
        QuestionRequest.model_validate(
            {"workflow": "evidence_comparison", "question": "q"}
        )


@pytest.mark.parametrize(
    ("name", "change"),
    [
        # Payload present on a non-answered status.
        ("evidence_comparison.answered.json", {"status": "no_results"}),
        (
            "conflicting_evidence.answered.json",
            {"status": "insufficient_evidence", "answer": None},
        ),
        # Payload of another workflow.
        ("research_gap.answered.json", {"workflow": "evidence_comparison"}),
        # Payload as explicit null.
        ("research_question.answered.json", {"comparison": None}),
        # Answered payload workflow without its payload.
        ("evidence_comparison.answered.json", {"comparison": "__drop__"}),
        # Hypotheses are always speculative.
        ("research_gap.answered.json", {"gap_analysis.speculative": False}),
        # review_note is the fixed server text.
        ("conflicting_evidence.answered.json", {"conflicts.note": "x"}),
    ],
)
def test_models_reject_payload_on_the_wrong_response(
    name: str, change: dict[str, Any]
) -> None:
    """Payload fields exist only for the matching answered workflow."""
    document = fx.load(name)
    for key, value in change.items():
        if key == "gap_analysis.speculative":
            document["gap_analysis"]["hypotheses"][0]["is_speculative"] = value
        elif key == "conflicts.note":
            document["conflicts"]["review_note"] = value
        elif value == "__drop__":
            del document[key]
        else:
            document[key] = value

    with pytest.raises(ValidationError):
        SUCCESS.validate_python(document)


# Fake mode end to end through the configured server.


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_fake_server_answers_every_workflow(workflow: str) -> None:
    """Zero-config server serves all four workflows with synthetic data."""
    with TestClient(create_server_app({})) as client:
        response = _ask(client, workflow)

    assert response.status_code == 200
    body = response.json()
    SUCCESS.validate_python(body)
    assert body["workflow"] == workflow
    assert body["status"] == "answered"
    payload_field = PAYLOAD_FIELDS.get(workflow)
    present = set(body) & set(PAYLOAD_FIELDS.values())
    assert present == ({payload_field} if payload_field else set())
    if workflow == "research_question":
        assert set(body) == RESEARCH_QUESTION_KEYS
    evidence_ids = {item["chunk_id"] for item in body["evidence"]}
    for claim in body["claims"]:
        assert set(claim["citation_chunk_ids"]) <= evidence_ids
    assert body["metadata"] == {
        "retrieval": {
            "configured_origin": "synthetic",
            "executed": True,
            "is_test_data": True,
        },
        "answer_provider": {
            "configured_origin": "fake",
            "executed": True,
            "is_test_data": True,
        },
    }


def test_fake_conflicts_response_carries_the_server_review_note() -> None:
    """The review note in responses is the contract constant."""
    with TestClient(create_server_app({})) as client:
        body = _ask(client, "conflicting_evidence").json()

    expected = fx.load("conflicting_evidence.answered.json")
    assert (
        body["conflicts"]["review_note"]
        == (expected["conflicts"]["review_note"])
    )


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_no_results_with_component_retrieval_metadata(workflow: str) -> None:
    """Empty retrieval returns no_results without payload or provider call."""
    with _app(
        ComponentFakeRetrieval(mode="empty"), ComponentFakeAnswerProvider()
    ) as client:
        response = _ask(client, workflow)

    assert response.status_code == 200
    body = response.json()
    SUCCESS.validate_python(body)
    assert body["status"] == "no_results"
    assert body["workflow"] == workflow
    assert set(body) == RESEARCH_QUESTION_KEYS
    assert body["metadata"]["answer_provider"] == {
        "configured_origin": "fake",
        "executed": False,
        "is_test_data": True,
    }


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_insufficient_evidence_has_no_payload(workflow: str) -> None:
    """A declining provider keeps evidence and omits the payload field."""
    with _app(
        ComponentFakeRetrieval(),
        ComponentFakeAnswerProvider(mode="insufficient_evidence"),
    ) as client:
        body = _ask(client, workflow).json()

    SUCCESS.validate_python(body)
    assert body["status"] == "insufficient_evidence"
    assert body["workflow"] == workflow
    assert body["evidence"]
    assert set(body) == RESEARCH_QUESTION_KEYS


@dataclass(slots=True)
class _SinglePaperComparisonProvider:
    """Answers a comparison that cites only one paper."""

    def answer(self, *args: Any, **kwargs: Any) -> ProviderOutcome:
        document = fx.load("evidence_comparison.answered.json")
        payload = fx.payload(document)
        assert isinstance(payload, ComparisonPayload)
        return replace(
            fx.provider(document),
            metadata=FAKE,
            payload=replace(
                payload,
                subjects=payload.subjects[:1],
                similarities=(),
                differences=(),
            ),
        )


def test_comparison_citing_one_paper_is_insufficient_over_http() -> None:
    """Downgrade rule surfaces as HTTP 200 insufficient_evidence."""
    document = fx.load("evidence_comparison.answered.json")
    retrieval = replace(
        fx.retrieval(document),
        metadata=SYNTHETIC,
    )

    @dataclass(frozen=True, slots=True)
    class _Fixed:
        def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
            return retrieval

    with _app(_Fixed(), _SinglePaperComparisonProvider()) as client:
        body = _ask(client, "evidence_comparison").json()

    assert body["status"] == "insufficient_evidence"
    assert body["claims"] == []
    assert "comparison" not in body


# Per-workflow retrieval selection.


@dataclass(slots=True)
class _RecordingRetrieval:
    name: str
    calls: list[str] = field(default_factory=list)

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        self.calls.append(self.name)
        return ComponentFakeRetrieval().retrieve(question, request_id)


def test_route_uses_the_retrieval_configured_for_the_workflow() -> None:
    """Each workflow is served by its own retrieval profile."""
    retrievals = {w: _RecordingRetrieval(w) for w in WORKFLOWS}
    default = _RecordingRetrieval("default")
    with _app(
        default,
        ComponentFakeAnswerProvider(),
        workflow_retrievals=retrievals,
    ) as client:
        for workflow in WORKFLOWS:
            assert _ask(client, workflow).status_code == 200

    assert default.calls == []
    assert {w: r.calls for w, r in retrievals.items()} == {
        w: [w] for w in WORKFLOWS
    }


def test_workflow_retrievals_must_cover_every_workflow() -> None:
    """Missing a profile is a startup error, not a silent fallback."""
    with pytest.raises(ValueError, match="every workflow"):
        create_app(
            retrieval=ComponentFakeRetrieval(),
            provider=ComponentFakeAnswerProvider(),
            v2_metadata=METADATA,
            workflow_retrievals={"research_question": ComponentFakeRetrieval()},
        )


class _Engine:
    def dispose(self) -> None:
        pass


@pytest.mark.parametrize(
    ("mode", "pool", "env"),
    [
        ("lexical", None, {}),
        ("hybrid", 50, {"OPENAI_API_KEY": FAKE_KEY}),
    ],
)
def test_postgres_server_builds_one_profile_per_workflow(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    pool: int | None,
    env: dict[str, str],
) -> None:
    """top_k 5 for research_question, 10 otherwise; pool 50 only in hybrid."""
    monkeypatch.setattr(
        server, "create_database_engine", lambda settings: _Engine()
    )
    app = create_server_app(
        {
            "RETRIEVAL_BACKEND": "postgres",
            "RETRIEVAL_MODE": mode,
            "DATABASE_URL": "postgresql://u:p@localhost/db",
            **env,
        }
    )

    adapters = app.state.dependencies.workflow_retrievals
    settings = {w: adapters[w]._settings for w in WORKFLOWS}
    assert {w: s.top_k for w, s in settings.items()} == {
        "research_question": 5,
        "evidence_comparison": 10,
        "conflicting_evidence": 10,
        "research_gap": 10,
    }
    assert dict(WORKFLOW_TOP_K) == {w: s.top_k for w, s in settings.items()}
    for value in settings.values():
        assert value.contract_version == "retrieval.v2"
        assert value.mode == mode
        assert value.filters is None
        assert (
            None if value.ranking is None else value.ranking.candidate_pool_size
        ) == pool
    assert len({id(adapter) for adapter in adapters.values()}) == 4


# Health and the OpenAI provider.


def test_fake_health_lists_all_workflows_like_the_fixture() -> None:
    """Fake provider enables all four workflows."""
    body = TestClient(create_server_app({})).get("/api/health").json()

    assert body["workflows"] == fx.load("health.json")["workflows"]


_OPENAI_ENV = {
    "AI_PROVIDER": "openai",
    "OPENAI_API_KEY": FAKE_KEY,
    "OPENAI_ANSWER_MODEL": "test-model",
}


def test_openai_health_lists_all_four_workflows() -> None:
    """Health reflects the configured provider."""
    body = TestClient(create_server_app(_OPENAI_ENV)).get("/api/health").json()

    assert body["workflows"] == [
        "research_question",
        "evidence_comparison",
        "conflicting_evidence",
        "research_gap",
    ]
    assert FAKE_KEY not in str(body)


def test_composition_requires_settings_for_every_workflow() -> None:
    """Incomplete per-workflow settings fail before the engine is used."""
    real = ComponentMetadata("real", executed=False, is_test_data=False)
    settings = server.retrieval_settings_for(
        "research_question", "lexical", real
    )

    with pytest.raises(ValueError, match="every workflow"):
        create_application(
            engine=_Engine(),  # type: ignore[arg-type]
            engine_factory=None,
            query_embedder=None,
            retrieval_settings=settings,
            provider=ComponentFakeAnswerProvider(),
            metadata=QuestionMetadata(retrieval=real, answer_provider=real),
            workflow_retrieval_settings={"research_question": settings},
        )
