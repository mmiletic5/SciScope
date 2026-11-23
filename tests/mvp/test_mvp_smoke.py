"""Offline tests for the smoke script helpers (no DB, no network)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_SCRIPT = Path(__file__).parents[2] / "scripts" / "mvp_smoke.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("mvp_smoke", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["mvp_smoke"] = module
    spec.loader.exec_module(module)
    return module


smoke = _load()

_LIVE = {
    "AI_PROVIDER": "openai",
    "RETRIEVAL_BACKEND": "postgres",
    "SCISCOPE_LIVE_OPENAI": "1",
}


def test_live_opt_in_complete() -> None:
    """All three variables set correctly yields no missing names."""
    assert smoke.check_live_opt_in(_LIVE) == []


def test_live_opt_in_names_missing_without_values() -> None:
    """Missing or wrong variables are listed by name only."""
    env = {"AI_PROVIDER": "fake-secret-value", "RETRIEVAL_BACKEND": "postgres"}
    missing = smoke.check_live_opt_in(env)
    assert missing == ["AI_PROVIDER", "SCISCOPE_LIVE_OPENAI"]
    assert "fake-secret-value" not in " ".join(missing)


def test_main_refuses_before_any_work(capsys) -> None:  # type: ignore[no-untyped-def]
    """Refusal returns 2 and prints names, never values."""
    assert smoke.main({"AI_PROVIDER": "secret-x"}) == 2
    err = capsys.readouterr().err
    assert "SCISCOPE_LIVE_OPENAI" in err
    assert "secret-x" not in err


def test_select_golden_keeps_only_requested() -> None:
    """Only requested ids are extracted, with unique sorted DOIs."""
    document = {
        "questions": [
            {
                "question_id": "gq-sp-001",
                "question": "Q1?",
                "relevant_papers": [{"doi": "10.1/b"}, {"doi": "10.1/a"}],
            },
            {
                "question_id": "gq-ins-001",
                "question": "Q2?",
                "relevant_papers": [{"doi": "10.1/c"}],
                "expected_insufficient_evidence": True,
            },
            {
                "question_id": "gq-other",
                "question": "no",
                "relevant_papers": [],
            },
        ]
    }
    out = smoke.select_golden(document, ("gq-sp-001", "gq-ins-001"))
    assert [q["id"] for q in out] == ["gq-sp-001", "gq-ins-001"]
    assert out[0]["relevant_dois"] == ["10.1/a", "10.1/b"]
    assert out[1]["expect_insufficient"] is True


def test_analyze_detects_dangling_citation_and_doi_hit() -> None:
    """Citation validity and DOI overlap are computed from the response."""
    body = {
        "evidence": [{"chunk_id": "c1", "doi": "10.1/a"}],
        "claims": [
            {"claim_id": "k1", "citation_chunk_ids": ["c1"]},
            {"claim_id": "k2", "citation_chunk_ids": ["zzz"]},
        ],
        "metadata": {
            "retrieval": {"configured_origin": "real"},
            "answer_provider": {"configured_origin": "real"},
        },
    }
    facts = smoke.analyze(body, ["10.1/a"])
    assert facts["citations_valid"] is False
    assert facts["relevant_doi_hit"] is True
    assert facts["evidence_count"] == 1
    assert facts["claim_count"] == 2
    assert facts["origins"] == {"retrieval": "real", "answer_provider": "real"}


def test_format_line_insufficient_note() -> None:
    """The insufficient-evidence expectation is shown but not graded."""
    facts = smoke.analyze({"evidence": [], "claims": []}, [])
    line = smoke.format_line(
        "gq-ins-001", 200, {"status": "x"}, 1.0, facts, True
    )
    assert "insufficient_evidence" in line
    assert "not pass/fail" in line
