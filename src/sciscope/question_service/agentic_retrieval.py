"""Opt-in agentic retrieval (stage 1) in front of the grounded answer call.

With ``SCISCOPE_AGENTIC_RETRIEVAL=1`` the server wraps the retrieval of each
workflow in ``AGENTIC_WORKFLOWS`` with ``AgenticRetrieval``. A planner (the
configured answer provider) issues up to ``MAX_TOOL_CALLS`` calls of one
search tool; every call runs the workflow's own retrieval with only the
query text changed. The merged, capped union of the passages found becomes
the evidence of the unchanged grounded answer call (stage 2), so citations
can only name chunks that were actually retrieved.

Any stage 1 problem (an exception, the time budget, zero tool calls, an
empty union) falls back to the single-shot retrieval of the original
question, so the agentic path never adds a new kind of error. Only counts,
a reason code and latency are logged; never queries, passages, prompts or
keys.
"""

from __future__ import annotations

import logging
import time
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Final, Protocol, runtime_checkable

from sciscope.question_service.contracts import (
    CorpusProvenance,
    Evidence,
    OutcomeMetadata,
    RetrievalOutcome,
    RetrievalService,
    Workflow,
)

AGENTIC_FLAG_ENV: Final = "SCISCOPE_AGENTIC_RETRIEVAL"
AGENTIC_WORKFLOWS: Final[frozenset[Workflow]] = frozenset(
    {"evidence_comparison"}
)
"""Workflows that honor the flag; other workflows opt in by being added."""

MAX_TOOL_CALLS: Final = 3
MAX_MERGED_CHUNKS: Final = 12
MAX_MERGED_CHARS: Final = 60_000
"""Equal to the answer provider's evidence cap, so stage 2 never refuses."""
STAGE1_BUDGET_SECONDS: Final = 20.0
MAX_QUERY_CHARS: Final = 300

LOGGER_NAME: Final = "sciscope.agentic_retrieval"
_LOGGER = logging.getLogger(LOGGER_NAME)


class SearchLimitExceeded(RuntimeError):
    """A planner tried to search beyond the tool-call limit."""


class StageBudgetExceeded(RuntimeError):
    """A planner tried to search after the stage 1 deadline."""


class CorpusMismatch(RuntimeError):
    """Two searches of one request reported different corpus identities."""


def sanitize_query(raw: object) -> str | None:
    """Normalize a model-supplied search query, which is untrusted.

    Control and format characters (Unicode categories ``Cc`` and ``Cf``, for
    example NUL, newlines or bidirectional overrides) become spaces,
    whitespace is collapsed and the result is cut to ``MAX_QUERY_CHARS``.

    Args:
        raw: The ``query`` argument as decoded from the tool call.

    Returns:
        The cleaned query, or None when ``raw`` is not a string or nothing
        remains.
    """
    if not isinstance(raw, str):
        return None
    cleaned = "".join(
        " " if unicodedata.category(char) in ("Cc", "Cf") else char
        for char in raw
    )
    cleaned = " ".join(cleaned.split())[:MAX_QUERY_CHARS].strip()
    return cleaned or None


@dataclass(frozen=True, slots=True)
class AgenticStats:
    """Content-free counters of one agentic retrieval.

    Attributes:
        workflow: Workflow served.
        rounds: Model calls made in stage 1.
        searches: Tool calls counted against the limit (executed or refused).
        merged_chunks: Size of the union passed to stage 2; 0 on fallback.
        fallback: Whether the single-shot retrieval was used instead.
        reason: Fallback reason code, or None.
        latency_seconds: Wall time of the whole retrieval step.
    """

    workflow: Workflow
    rounds: int
    searches: int
    merged_chunks: int
    fallback: bool
    reason: str | None
    latency_seconds: float


class AgenticSession:
    """Budgets, counters and the search tool of one stage 1 run.

    Planners call ``note_model_call`` before every model request and
    ``search`` (or ``refuse_call``) once per tool call. The session enforces
    the limits itself, so a faulty planner causes a fallback, not overuse.
    """

    def __init__(
        self,
        *,
        retrieval: RetrievalService,
        request_id: str,
        max_calls: int,
        deadline: float,
        monotonic: Callable[[], float],
    ) -> None:
        """Bind the wrapped retrieval and the limits.

        Args:
            retrieval: The workflow's single-shot retrieval.
            request_id: Request correlation ID passed to each search.
            max_calls: Tool-call limit.
            deadline: Monotonic time after which no search may start.
            monotonic: Clock used for the deadline.
        """
        self._retrieval = retrieval
        self._request_id = request_id
        self._max_calls = max_calls
        self.deadline = deadline
        self._monotonic = monotonic
        self.rounds = 0
        self.calls = 0
        self.corpus: CorpusProvenance | None = None
        self.metadata: OutcomeMetadata | None = None
        self.ranked_lists: list[tuple[Evidence, ...]] = []
        self._seen: set[str] = set()

    @property
    def remaining_calls(self) -> int:
        """Return how many tool calls may still be made."""
        return self._max_calls - self.calls

    def note_model_call(self) -> None:
        """Count one stage 1 model request."""
        self.rounds += 1

    def refuse_call(self) -> None:
        """Count a tool call that is not executed (bad name or arguments)."""
        self._take_call()

    def search(self, query: object) -> tuple[Evidence, ...]:
        """Run the wrapped retrieval for a model-supplied query.

        Only the query text reaches the retrieval; its filters, mode and
        ``top_k`` stay those of the server-owned profile.

        Args:
            query: Untrusted query argument; see ``sanitize_query``.

        Returns:
            Passages of this search not returned by an earlier search of the
            session, in rank order. Empty for an unusable query.

        Raises:
            SearchLimitExceeded: If the tool-call limit is already used up.
            StageBudgetExceeded: If the stage 1 deadline has passed.
            CorpusMismatch: If the corpus identity changed between searches.
        """
        self._take_call()
        if self._monotonic() >= self.deadline:
            raise StageBudgetExceeded()
        cleaned = sanitize_query(query)
        if cleaned is None:
            return ()
        outcome = self._retrieval.retrieve(cleaned, self._request_id)
        if self.corpus is None:
            self.corpus = outcome.corpus
            self.metadata = outcome.metadata
        elif outcome.corpus != self.corpus:
            raise CorpusMismatch()
        self.ranked_lists.append(outcome.evidence)
        new = tuple(
            item for item in outcome.evidence if item.chunk_id not in self._seen
        )
        self._seen.update(item.chunk_id for item in new)
        return new

    def _take_call(self) -> None:
        """Consume one tool call or fail when none is left."""
        if self.calls >= self._max_calls:
            raise SearchLimitExceeded()
        self.calls += 1


@runtime_checkable
class SearchPlanner(Protocol):
    """Decides which searches to run for a question (stage 1)."""

    def plan_searches(self, question: str, session: AgenticSession) -> None:
        """Run searches through ``session`` until done or out of budget."""


def merge_ranked(
    ranked_lists: list[tuple[Evidence, ...]],
    *,
    max_chunks: int = MAX_MERGED_CHUNKS,
    max_chars: int = MAX_MERGED_CHARS,
) -> tuple[Evidence, ...]:
    """Merge per-search rankings round-robin into a capped unique union.

    Rank 1 of every search comes first, then rank 2, and so on; a chunk seen
    earlier is skipped. A passage that would push the total passage length
    over ``max_chars`` is skipped.

    Args:
        ranked_lists: Full result list of each search, in search order.
        max_chunks: Maximum number of passages kept.
        max_chars: Maximum total passage characters kept.

    Returns:
        The merged evidence.
    """
    merged: list[Evidence] = []
    seen: set[str] = set()
    chars = 0
    depth = max((len(results) for results in ranked_lists), default=0)
    for rank in range(depth):
        for results in ranked_lists:
            if rank >= len(results) or len(merged) >= max_chunks:
                continue
            item = results[rank]
            if item.chunk_id in seen or chars + len(item.passage) > max_chars:
                continue
            seen.add(item.chunk_id)
            chars += len(item.passage)
            merged.append(item)
    return tuple(merged)


class AgenticRetrieval:
    """Retrieval that lets a planner search before the answer call.

    Implements the question-service ``RetrievalService`` protocol, so the
    question service and the answer provider stay unchanged.
    """

    def __init__(
        self,
        *,
        retrieval: RetrievalService,
        planner: SearchPlanner,
        workflow: Workflow,
        max_calls: int = MAX_TOOL_CALLS,
        max_chunks: int = MAX_MERGED_CHUNKS,
        budget_seconds: float = STAGE1_BUDGET_SECONDS,
        monotonic: Callable[[], float] = time.monotonic,
        logger: logging.Logger = _LOGGER,
    ) -> None:
        """Bind the wrapped retrieval, the planner and the limits.

        Args:
            retrieval: The workflow's single-shot retrieval; also the
                fallback.
            planner: Stage 1 planner, normally the answer provider.
            workflow: Workflow served, for logging only.
            max_calls: Tool-call limit.
            max_chunks: Cap on the merged union.
            budget_seconds: Stage 1 time budget.
            monotonic: Clock for the budget and latency.
            logger: Receives one content-free line per request.
        """
        self._retrieval = retrieval
        self._planner = planner
        self._workflow = workflow
        self._max_calls = max_calls
        self._max_chunks = max_chunks
        self._budget_seconds = budget_seconds
        self._monotonic = monotonic
        self._logger = logger

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        """Return the merged stage 1 evidence, or the single-shot outcome.

        Args:
            question: Validated question text.
            request_id: Request correlation ID.

        Returns:
            Merged evidence with the corpus and metadata of the searches, or
            exactly what the wrapped retrieval returns for ``question``.

        Raises:
            Exception: Only what the wrapped retrieval raises on fallback.
        """
        started = self._monotonic()
        session = AgenticSession(
            retrieval=self._retrieval,
            request_id=request_id,
            max_calls=self._max_calls,
            deadline=started + self._budget_seconds,
            monotonic=self._monotonic,
        )
        reason: str | None = None
        merged: tuple[Evidence, ...] = ()
        try:
            self._planner.plan_searches(question, session)
        except Exception as error:  # noqa: BLE001  any stage 1 error falls back
            reason = f"error:{type(error).__name__}"
        if reason is None:
            if session.calls == 0:
                reason = "no_tool_calls"
            elif self._monotonic() > session.deadline:
                reason = "timeout"
            else:
                merged = merge_ranked(
                    session.ranked_lists, max_chunks=self._max_chunks
                )
                if not merged:
                    reason = "empty_union"
        try:
            if reason is not None:
                return self._retrieval.retrieve(question, request_id)
            assert session.corpus is not None and session.metadata is not None
            return RetrievalOutcome(
                evidence=merged,
                corpus=session.corpus,
                metadata=session.metadata,
            )
        finally:
            self._log(
                AgenticStats(
                    workflow=self._workflow,
                    rounds=session.rounds,
                    searches=session.calls,
                    merged_chunks=len(merged) if reason is None else 0,
                    fallback=reason is not None,
                    reason=reason,
                    latency_seconds=self._monotonic() - started,
                )
            )

    def _log(self, stats: AgenticStats) -> None:
        """Log counts, reason code and latency only."""
        self._logger.info(
            "agentic_retrieval workflow=%s rounds=%d searches=%d merged=%d "
            "fallback=%s reason=%s latency_ms=%d",
            stats.workflow,
            stats.rounds,
            stats.searches,
            stats.merged_chunks,
            "yes" if stats.fallback else "no",
            stats.reason or "-",
            round(stats.latency_seconds * 1000),
            extra={"agentic_stats": stats},
        )


def wrap_agentic(
    retrievals: Mapping[Workflow, RetrievalService],
    planner: SearchPlanner,
) -> dict[Workflow, RetrievalService]:
    """Wrap the retrieval of each workflow in ``AGENTIC_WORKFLOWS``.

    Args:
        retrievals: One retrieval per workflow.
        planner: Stage 1 planner shared by the wrapped workflows.

    Returns:
        A new mapping; workflows outside the registry keep their retrieval.
    """
    return {
        workflow: (
            AgenticRetrieval(
                retrieval=retrieval, planner=planner, workflow=workflow
            )
            if workflow in AGENTIC_WORKFLOWS
            else retrieval
        )
        for workflow, retrieval in retrievals.items()
    }
