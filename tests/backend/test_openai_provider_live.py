"""Opt-in live smoke test for the OpenAI answer provider.

Skipped unless ``SCISCOPE_LIVE_OPENAI=1`` and ``OPENAI_API_KEY`` are set.
The model defaults to ``gpt-4o-mini`` and can be overridden with
``SCISCOPE_LIVE_OPENAI_MODEL``. This test makes one paid API call.
"""

from __future__ import annotations

import os

import pytest

from sciscope.question_service.contracts import (
    CorpusProvenance,
    Evidence,
    ProviderOutcomeStatus,
)
from sciscope.question_service.openai_provider import OpenAIAnswerProvider

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("SCISCOPE_LIVE_OPENAI") != "1"
        or not os.environ.get("OPENAI_API_KEY", "").strip(),
        reason="live OpenAI test requires SCISCOPE_LIVE_OPENAI=1 and a key",
    ),
]

_EVIDENCE = (
    Evidence(
        "live-chunk-1",
        "10.0000/synthetic.live.1",
        "synthetic:sec-1:p-1",
        "In this synthetic study, colonies fed a mixed pollen diet had a "
        "median worker lifespan of 32 days, compared with 24 days for "
        "colonies fed a single-source pollen diet.",
        "Synthetic Pollen Diet Study",
    ),
)
_CORPUS = CorpusProvenance("live-digest", "live-source", "live-corpus")


def test_live_research_question_is_grounded() -> None:
    """A live answer is either declined or cites only supplied evidence."""
    provider = OpenAIAnswerProvider(
        api_key=os.environ["OPENAI_API_KEY"],
        model=os.environ.get("SCISCOPE_LIVE_OPENAI_MODEL", "gpt-4o-mini"),
    )

    outcome = provider.answer(
        "How does pollen diet diversity affect worker lifespan?",
        _EVIDENCE,
        _CORPUS,
        "live-req-1",
    )

    if outcome.status is ProviderOutcomeStatus.ANSWERED:
        assert outcome.answer
        assert outcome.claims
        for claim in outcome.claims:
            assert set(claim.citation_chunk_ids) <= {"live-chunk-1"}
    else:
        assert outcome.answer is None
        assert outcome.claims == ()
