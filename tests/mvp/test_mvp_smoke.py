"""Offline tests for the smoke script helpers (no DB, no network)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
from fastapi import FastAPI

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


def test_dev_questions_map_to_workflows() -> None:
    """Each dev question runs the workflow it was written for."""
    assert smoke.QUESTION_WORKFLOWS == {
        "gq-sp-001": "research_question",
        "gq-cmp-001": "evidence_comparison",
        "gq-conf-001": "conflicting_evidence",
        "gq-gap-001": "research_gap",
        "gq-ins-001": "research_question",
    }
    document = {
        "questions": [
            {
                "question_id": "gq-cmp-001",
                "question": "Q?",
                "relevant_papers": [],
            }
        ]
    }
    assert smoke.select_golden(document, ("gq-cmp-001",))[0]["workflow"] == (
        "evidence_comparison"
    )


def test_skip_line_names_the_workflow() -> None:
    """Unsupported workflows are reported as skipped, not as failures."""
    line = smoke.skip_line("gq-gap-001", "research_gap")
    assert "SKIPPED" in line
    assert "workflow=research_gap" in line


def test_format_line_shows_workflow() -> None:
    """The summary line names the workflow when given."""
    line = smoke.format_line(
        "gq-cmp-001", 200, {"status": "answered"}, 1.0, None, False, "x_wf"
    )
    assert "workflow=x_wf" in line


def test_main_skips_workflows_the_provider_does_not_support(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Offline: a provider enabling only research_question skips the rest."""
    import json

    from sciscope.api import server
    from sciscope.api.app import create_app
    from sciscope.question_service.contracts import (
        ComponentMetadata,
        QuestionMetadata,
    )
    from sciscope.question_service.fakes import (
        ComponentFakeAnswerProvider,
        ComponentFakeRetrieval,
    )

    def fake_server_app(environ: object) -> FastAPI:
        metadata = QuestionMetadata(
            ComponentMetadata("synthetic", executed=False, is_test_data=True),
            ComponentMetadata("fake", executed=False, is_test_data=True),
        )
        app = create_app(
            retrieval=ComponentFakeRetrieval(),
            provider=ComponentFakeAnswerProvider(),
            v2_metadata=metadata,
        )
        server._health_route(app, metadata, ("research_question",))
        return app

    golden = tmp_path / "golden.json"
    golden.write_text(
        json.dumps(
            {
                "questions": [
                    {
                        "question_id": qid,
                        "question": f"Synthetic {qid}?",
                        "relevant_papers": [],
                    }
                    for qid in smoke.QUESTION_IDS
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(server, "create_server_app", fake_server_app)
    monkeypatch.setattr(smoke, "GOLDEN_PATH", golden)
    monkeypatch.setattr(smoke, "OUTPUT_DIR", tmp_path / "out")

    assert smoke.main(_LIVE) == 0

    out = capsys.readouterr().out
    for qid in ("gq-cmp-001", "gq-conf-001", "gq-gap-001"):
        assert f"{qid} | workflow=" in out
    assert out.count("SKIPPED") == 3
    assert "gq-sp-001 | workflow=research_question | http=200" in out
    summary = json.loads((tmp_path / "out" / "summary.json").read_text())
    assert [row["workflow"] for row in summary] == list(
        smoke.QUESTION_WORKFLOWS.values()
    )
