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


_ID = "ab" * 32


def test_ids_in_text_flags_every_text_field_but_not_citations() -> None:
    """A 64-hex id in free text is flagged; citations and evidence are not."""
    clean = {
        "answer": "Fine.",
        "claims": [{"text": "ok", "citation_chunk_ids": [_ID]}],
        "evidence": [{"chunk_id": _ID, "passage": _ID}],
        "corpus": {"delivery_digest": _ID},
        "comparison": {
            "subjects": [{"summary": "s", "citation_chunk_ids": [_ID]}]
        },
    }
    assert smoke.has_ids_in_text(clean) is False
    leaks = [
        {**clean, "answer": f"x [{_ID}]"},
        {**clean, "claims": [{"text": f"x {_ID.upper()}"}]},
        {
            **clean,
            "comparison": {"subjects": [{"summary": f"({_ID})"}]},
        },
        {
            **clean,
            "conflicts": {
                "items": [
                    {
                        "topic": "t",
                        "summary": "s",
                        "positions": [{"text": f"[{_ID}]"}],
                    }
                ]
            },
        },
        {
            **clean,
            "gap_analysis": {
                "gaps": [],
                "hypotheses": [{"text": "h", "rationale": f"[{_ID}]"}],
            },
        },
    ]
    assert all(smoke.has_ids_in_text(body) for body in leaks)


def test_analyze_and_line_report_ids_in_text() -> None:
    """The flag is part of the facts and of the printed line."""
    facts = smoke.analyze({"answer": f"[{_ID}]", "evidence": []}, [])
    assert facts["ids_in_text"] is True
    line = smoke.format_line(
        "q", 200, {"status": "answered"}, 1.0, facts, False
    )
    assert "ids_in_text=true" in line


def test_parse_args_only_and_repeat() -> None:
    """Defaults run everything once; options are validated."""
    defaults = smoke.parse_args([])
    assert (defaults.only, defaults.repeat) == (None, 1)
    chosen = smoke.parse_args(["--only", "gq-cmp-001", "--repeat", "3"])
    assert (chosen.only, chosen.repeat) == ("gq-cmp-001", 3)
    with pytest.raises(SystemExit):
        smoke.parse_args(["--only", "nope"])
    with pytest.raises(SystemExit):
        smoke.parse_args(["--repeat", "0"])


def test_main_only_and_repeat_run_one_question_several_times(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Offline: --only/--repeat select one question and number the runs."""
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

    argv = ["--only", "gq-sp-001", "--repeat", "2"]
    assert smoke.main(_LIVE, argv) == 0

    out = capsys.readouterr().out
    assert out.count("gq-sp-001 | workflow=research_question | http=200") == 2
    assert "ids_in_text=false" in out
    assert "gq-cmp-001" not in out
    summary = json.loads((tmp_path / "out" / "summary.json").read_text())
    assert [(row["id"], row["run"]) for row in summary] == [
        ("gq-sp-001", 1),
        ("gq-sp-001", 2),
    ]
    assert (tmp_path / "out" / "gq-sp-001.run2.json").exists()


def test_parse_args_agentic_defaults_off() -> None:
    """--agentic is opt-in."""
    assert smoke.parse_args([]).agentic is False
    assert smoke.parse_args(["--agentic"]).agentic is True


def test_format_agentic_reports_counts_and_fallback_reason() -> None:
    """Counters, fallback flag with reason, and stage 1 latency."""
    from sciscope.question_service.agentic_retrieval import AgenticStats

    facts = smoke.agentic_facts(
        AgenticStats("evidence_comparison", 2, 1, 0, True, "empty_union", 1.26)
    )
    assert smoke.format_agentic(facts) == (
        "agentic rounds=2 searches=1 merged=0 fallback=yes(empty_union) "
        "stage1=1.3s"
    )
    assert smoke.format_agentic(smoke.agentic_facts(None)) == "agentic=n/a"


@pytest.mark.parametrize("agentic", [False, True])
def test_main_agentic_sets_the_flag_and_prints_counters(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    agentic: bool,
) -> None:
    """Offline (fake mode): the flag is forced on or off for the run."""
    import json

    from sciscope.api import server

    real_factory = server.create_server_app
    seen: list[str] = []

    def fake_mode_app(environ: dict[str, str]) -> FastAPI:
        seen.append(environ["SCISCOPE_AGENTIC_RETRIEVAL"])
        return real_factory(
            {
                "SCISCOPE_AGENTIC_RETRIEVAL": environ[
                    "SCISCOPE_AGENTIC_RETRIEVAL"
                ]
            }
        )

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
    monkeypatch.setattr(server, "create_server_app", fake_mode_app)
    monkeypatch.setattr(smoke, "GOLDEN_PATH", golden)
    monkeypatch.setattr(smoke, "OUTPUT_DIR", tmp_path / "out")
    env = {**_LIVE, "SCISCOPE_AGENTIC_RETRIEVAL": "1"}

    argv = ["--only", "gq-cmp-001"] + (["--agentic"] if agentic else [])
    assert smoke.main(env, argv) == 0

    out = capsys.readouterr().out
    assert seen == ["1" if agentic else "0"]
    suffix = ".agentic" if agentic else ""
    summary = json.loads(
        (tmp_path / "out" / f"summary{suffix}.json").read_text()
    )
    if agentic:
        assert "agentic rounds=3 searches=2 merged=4 fallback=no stage1=" in out
        assert summary[0]["agentic_searches"] == 2
        assert (tmp_path / "out" / "gq-cmp-001.agentic.json").exists()
    else:
        assert "agentic rounds" not in out and "agentic=n/a" not in out
        assert "agentic" not in summary[0]
