"""Deterministic evaluation helpers over the private retrieval core."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from sciscope.evaluation.matching import (
    EvidenceReference,
    RetrievedEvidence,
    match_evidence_units,
)
from sciscope.evaluation.metrics import (
    QuestionMetrics,
    compute_question_metrics,
)

TOP_K = 20
METRIC_CUTOFFS = (1, 3, 5, 10, 20)
REPETITIONS = 2


class RankedHit(Protocol):
    """Minimal exact evidence fields returned by the private core."""

    rank: int
    chunk_id: str
    doi: str
    source_locator: str
    section_path: Sequence[str]
    text: str


class RetrievalResponse(Protocol):
    """Minimal response interface used by the evaluation adapter."""

    mode: str
    results: Sequence[RankedHit]
    corpus: CorpusIdentity


class CorpusIdentity(Protocol):
    """Frozen corpus identity attached to each private-core response."""

    import_id: int
    embedding_set_id: int
    corpus_version: str


class RetrievalCore(Protocol):
    """Minimal private core interface required by a Phase D run."""

    def retrieve(self, value: dict[str, object]) -> RetrievalResponse:
        """Execute one already-authorized retrieval request."""
        ...


def build_retrieval_request(
    question: Mapping[str, Any],
    *,
    cohort: str,
    arm: str,
    repetition: int,
) -> dict[str, object]:
    """Build one frozen request without adding filters or ranking overrides.

    Args:
        question: One explicitly authorized question record.
        cohort: Frozen held-out cohort identifier.
        arm: One of the three preregistered retrieval modes.
        repetition: Zero-based deterministic repeat index.

    Returns:
        A request accepted by the private `retrieval.v1` core.

    Raises:
        ValueError: If the cohort, question, arm, or repeat is invalid.
    """
    question_id = question.get("question_id")
    query = question.get("question")
    if (
        not isinstance(question_id, str)
        or not question_id
        or not isinstance(query, str)
        or not query.strip()
    ):
        raise ValueError("authorized question identity is invalid")
    if cohort not in {"v0-held-out", "v1-held-out"}:
        raise ValueError("evaluation cohort is invalid")
    if arm not in {"dense", "lexical", "hybrid"}:
        raise ValueError("retrieval arm is invalid")
    if type(repetition) is not int or repetition < 0:
        raise ValueError("retrieval repetition is invalid")
    request_id = f"phase-d-{cohort}-{question_id}-{arm}-r{repetition}"
    return {
        "contract_version": "retrieval.v1",
        "request_id": request_id,
        "query_text": query,
        "mode": arm,
        "top_k": TOP_K,
    }


def build_gold_references(
    question: Mapping[str, Any],
    *,
    section_by_locator: Mapping[str, str],
) -> tuple[EvidenceReference, ...]:
    """Convert frozen annotations using source-derived section locators.

    Args:
        question: One authorized Golden question.
        section_by_locator: Exact source-locator to section-path mapping from
            the frozen pilot chunk delivery.

    Returns:
        Evidence references in annotation order, including nonrelevant labels.

    Raises:
        ValueError: If a DOI, locator, label, or section cannot be verified.
    """
    references: list[EvidenceReference] = []
    papers = question.get("relevant_papers", [])
    if not isinstance(papers, list):
        raise ValueError("Golden paper references are invalid")
    for paper in papers:
        if not isinstance(paper, dict):
            raise ValueError("Golden paper reference is invalid")
        doi = paper.get("doi")
        evidence_items = paper.get("evidence")
        if not isinstance(doi, str) or not isinstance(evidence_items, list):
            raise ValueError("Golden evidence references are invalid")
        for evidence in evidence_items:
            if not isinstance(evidence, dict):
                raise ValueError("Golden evidence annotation is invalid")
            locator = evidence.get("source_locator")
            label_value = evidence.get("relevance_label")
            section = (
                section_by_locator.get(locator)
                if isinstance(locator, str)
                else None
            )
            if (
                not isinstance(locator, str)
                or not locator
                or not isinstance(section, str)
                or not section
                or not isinstance(label_value, str)
                or label_value not in {"0", "1", "2", "3"}
            ):
                raise ValueError("Golden evidence locator cannot be verified")
            quote = evidence.get("quotation")
            if quote is not None and not isinstance(quote, str):
                raise ValueError("Golden evidence quotation is invalid")
            references.append(
                EvidenceReference(
                    doi=doi,
                    section=section,
                    source_locator=locator,
                    relevance_label=int(label_value),
                    quotation=quote,
                )
            )
    return tuple(references)


def calculate_question_metrics(
    question: Mapping[str, Any],
    references: Sequence[EvidenceReference],
    retrieved: Sequence[RankedHit] = (),
) -> QuestionMetrics:
    """Apply the frozen matcher and metric definitions to one question.

    Args:
        question: Authorized question with its category/answerability label.
        references: Exact DOI/locator references derived from the frozen data.
        retrieved: Ranked private-core hits for one arm.

    Returns:
        Per-question metrics with the established positive denominator rules.
    """
    question_id = question.get("question_id")
    question_type = question.get("question_type")
    insufficient = question.get("expected_insufficient_evidence")
    if insufficient is None:
        insufficient = question_type == "insufficient_evidence"
    if type(insufficient) is not bool or not isinstance(question_id, str):
        raise ValueError("Golden answerability identity is invalid")
    candidates = tuple(
        RetrievedEvidence(
            chunk_id=hit.chunk_id,
            doi=hit.doi,
            section_path=tuple(hit.section_path),
            source_locator=hit.source_locator,
            span_locators=tuple(getattr(hit, "span_locators", ())),
            text=hit.text,
        )
        for hit in retrieved
    )
    matched = match_evidence_units(references, candidates)
    return compute_question_metrics(
        gold_unit_ids=matched.relevant_unit_ids,
        first_rank_by_unit=matched.first_rank_by_unit,
        expected_insufficient_evidence=insufficient,
        cutoffs=METRIC_CUTOFFS,
        question_id=question_id,
    )


def response_signature(response: RetrievalResponse) -> tuple[object, ...]:
    """Return exact ranked evidence identity for deterministic comparison."""
    return tuple(
        (
            hit.rank,
            hit.chunk_id,
            hit.doi,
            hit.source_locator,
            tuple(hit.section_path),
            hit.text,
        )
        for hit in response.results
    )


def run_reproducible_retrieval(
    core: RetrievalCore,
    question: Mapping[str, Any],
    *,
    cohort: str,
    arm: str,
    clock: Any,
) -> tuple[RetrievalResponse, tuple[float, ...]]:
    """Run fixed duplicate queries and require identical ranked evidence.

    Args:
        core: Existing private SciScope retrieval core.
        question: One frozen authorized question record.
        cohort: Frozen cohort identifier.
        arm: Dense, lexical, or hybrid retrieval mode.
        clock: Monotonic timer, injectable for synthetic tests.

    Returns:
        The first response and all measured wall durations in milliseconds.

    Raises:
        ValueError: If repeated results differ; no score is then reportable.
    """
    responses: list[RetrievalResponse] = []
    durations: list[float] = []
    for repetition in range(REPETITIONS):
        request = build_retrieval_request(
            question,
            cohort=cohort,
            arm=arm,
            repetition=repetition,
        )
        start = clock()
        response = core.retrieve(request)
        durations.append(max(0.0, (clock() - start) * 1000.0))
        if response.mode != arm:
            raise ValueError("retrieval response mode mismatch")
        responses.append(response)
    if response_signature(responses[0]) != response_signature(responses[1]):
        raise ValueError("retrieval results are not reproducible")
    return responses[0], tuple(durations)


def question_metrics_for_response(
    question: Mapping[str, Any],
    references: Sequence[EvidenceReference],
    response: RetrievalResponse,
) -> QuestionMetrics:
    """Return frozen retrieval metrics for a successful core response."""
    return calculate_question_metrics(question, references, response.results)
