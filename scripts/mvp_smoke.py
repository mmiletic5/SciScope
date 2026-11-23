"""Live smoke run of the MVP backend over five dev golden questions.

Builds the app with ``create_server_app()`` from the process environment and
calls ``POST /api/v2/questions`` through the FastAPI ``TestClient``, one
workflow per question (``QUESTION_WORKFLOWS``). Workflows that the configured
provider does not support yet (per ``GET /api/health``) are skipped with a
message. Refuses to start unless the live opt-in is explicit. Messages name
variables, never values; no key or URL is printed or written.

Run (PowerShell)::

    $env:SCISCOPE_LIVE_OPENAI="1"
    uv run --locked --env-file .env python scripts/mvp_smoke.py

``--agentic`` sets ``SCISCOPE_AGENTIC_RETRIEVAL=1`` for the run (otherwise
it is forced to ``0``, so a comparison is never mixed up) and appends the
stage 1 counters of the agentic workflows to each line: model rounds,
searches, merged chunks, fallback (with reason) and retrieval-step latency.
Outputs then get an ``.agentic`` suffix.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

GOLDEN_PATH = Path("evals/golden_questions.v0.json")
OUTPUT_DIR = Path("scratch/mvp_smoke")
QUESTION_WORKFLOWS: dict[str, str] = {
    "gq-sp-001": "research_question",
    "gq-cmp-001": "evidence_comparison",
    "gq-conf-001": "conflicting_evidence",
    "gq-gap-001": "research_gap",
    "gq-ins-001": "research_question",
}
QUESTION_IDS = tuple(QUESTION_WORKFLOWS)
INSUFFICIENT_EXPECTED_ID = "gq-ins-001"
_HEX_ID = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])")
_TEXT_KEYS = frozenset({"answer", "text", "summary", "topic", "rationale"})
_TEXT_CONTAINERS = (
    "claims",
    "comparison",
    "conflicts",
    "gap_analysis",
)
AGENTIC_FLAG = "SCISCOPE_AGENTIC_RETRIEVAL"
AGENTIC_LOGGER = "sciscope.agentic_retrieval"
_REQUIRED_ENV = (
    ("AI_PROVIDER", "openai"),
    ("RETRIEVAL_BACKEND", "postgres"),
    ("SCISCOPE_LIVE_OPENAI", "1"),
)


def check_live_opt_in(environ: Mapping[str, str]) -> list[str]:
    """Return the names of variables that lack the required live value.

    Args:
        environ: Process environment.

    Returns:
        Variable names only (never values); empty when the opt-in is complete.
    """
    return [
        name
        for name, required in _REQUIRED_ENV
        if environ.get(name, "").strip() != required
    ]


def select_golden(
    document: Mapping[str, Any], ids: Sequence[str] = QUESTION_IDS
) -> list[dict[str, Any]]:
    """Extract only id, question text and relevant DOIs for the given ids.

    Args:
        document: Parsed golden questions file.
        ids: Question ids to keep, in output order.

    Returns:
        One dict per id with ``id``, ``workflow``, ``question``,
        ``relevant_dois`` and ``expect_insufficient``.

    Raises:
        KeyError: If an id is missing from the document.
    """
    by_id = {
        record["question_id"]: record
        for record in document["questions"]
        if record.get("question_id") in ids
    }
    selected = []
    for question_id in ids:
        record = by_id[question_id]
        selected.append(
            {
                "id": question_id,
                "workflow": QUESTION_WORKFLOWS.get(
                    question_id, "research_question"
                ),
                "question": record["question"],
                "relevant_dois": sorted(
                    {paper["doi"] for paper in record["relevant_papers"]}
                ),
                "expect_insufficient": bool(
                    record.get("expected_insufficient_evidence", False)
                ),
            }
        )
    return selected


def _text_values(value: object) -> list[str]:
    """Collect free-text strings; skip citations, evidence and provenance."""
    if isinstance(value, list):
        return [text for item in value for text in _text_values(item)]
    if not isinstance(value, dict):
        return []
    found: list[str] = []
    for key, child in value.items():
        if key in _TEXT_KEYS and isinstance(child, str):
            found.append(child)
        elif isinstance(child, list | dict):
            found.extend(_text_values(child))
    return found


def has_ids_in_text(body: Mapping[str, Any]) -> bool:
    """Return whether any 64-hex id appears in a free-text response field.

    Args:
        body: Parsed v2 response body.

    Returns:
        True if the answer, a claim, or any workflow payload text (summaries,
        similarities, differences, topics, positions, gaps, hypotheses,
        rationales) contains a 64-hex token. Citation lists, evidence and
        corpus provenance are not inspected.
    """
    texts = _text_values({"answer": body.get("answer")})
    for key in _TEXT_CONTAINERS:
        texts.extend(_text_values(body.get(key)))
    return any(_HEX_ID.search(text) for text in texts)


def analyze(
    body: Mapping[str, Any], relevant_dois: Sequence[str]
) -> dict[str, Any]:
    """Compute the compact review facts for one successful response.

    Args:
        body: Parsed v2 response body.
        relevant_dois: Golden relevant DOIs for the question.

    Returns:
        Counts, citation consistency, DOI overlap and metadata origins.
    """
    evidence = body.get("evidence") or []
    claims = body.get("claims") or []
    evidence_ids = {item.get("chunk_id") for item in evidence}
    cited = [
        chunk_id
        for claim in claims
        for chunk_id in claim.get("citation_chunk_ids", [])
    ]
    relevant = set(relevant_dois)
    metadata = body.get("metadata") or {}
    return {
        "evidence_count": len(evidence),
        "claim_count": len(claims),
        "citations_valid": all(chunk_id in evidence_ids for chunk_id in cited),
        "ids_in_text": has_ids_in_text(body),
        "relevant_doi_hit": any(
            item.get("doi") in relevant for item in evidence
        ),
        "origins": {
            name: (metadata.get(name) or {}).get("configured_origin")
            for name in ("retrieval", "answer_provider")
        },
    }


class AgenticCapture(logging.Handler):
    """Collect the content-free stats of agentic retrieval log records."""

    def __init__(self) -> None:
        """Start with no records."""
        super().__init__(logging.INFO)
        self.stats: list[Any] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Keep the stats object attached to the record, if any."""
        stats = getattr(record, "agentic_stats", None)
        if stats is not None:
            self.stats.append(stats)


def agentic_facts(stats: Any | None) -> dict[str, Any]:
    """Return the agentic counters of one request for the summary.

    Args:
        stats: ``AgenticStats`` of the request, or None when its workflow is
            not agentic.

    Returns:
        Counters only; ``agentic`` is False when no stats were logged.
    """
    if stats is None:
        return {"agentic": False}
    return {
        "agentic": True,
        "agentic_rounds": stats.rounds,
        "agentic_searches": stats.searches,
        "agentic_merged_chunks": stats.merged_chunks,
        "agentic_fallback": stats.fallback,
        "agentic_fallback_reason": stats.reason,
        "agentic_latency_seconds": round(stats.latency_seconds, 2),
    }


def format_agentic(facts: Mapping[str, Any]) -> str:
    """Build the agentic part of a summary line."""
    if not facts.get("agentic"):
        return "agentic=n/a"
    fallback = "yes" if facts["agentic_fallback"] else "no"
    if facts["agentic_fallback_reason"]:
        fallback += f"({facts['agentic_fallback_reason']})"
    return (
        f"agentic rounds={facts['agentic_rounds']} "
        f"searches={facts['agentic_searches']} "
        f"merged={facts['agentic_merged_chunks']} fallback={fallback} "
        f"stage1={facts['agentic_latency_seconds']:.1f}s"
    )


def skip_line(question_id: str, workflow: str) -> str:
    """Build the summary line for a question whose workflow is skipped."""
    return (
        f"{question_id} | workflow={workflow} | SKIPPED: the configured "
        "provider does not support this workflow yet (see /api/health)"
    )


def format_line(
    question_id: str,
    http_status: int,
    body: Mapping[str, Any],
    latency: float,
    facts: Mapping[str, Any] | None,
    expect_insufficient: bool,
    workflow: str | None = None,
) -> str:
    """Build the one-line summary for a question."""
    status = body.get("status", "error")
    parts = [question_id]
    if workflow is not None:
        parts.append(f"workflow={workflow}")
    parts += [
        f"http={http_status}",
        f"status={status}",
        f"{latency:.1f}s",
    ]
    if facts is not None:
        origins = facts["origins"]
        parts += [
            f"evidence={facts['evidence_count']}",
            f"claims={facts['claim_count']}",
            f"citations_in_evidence={facts['citations_valid']}",
            f"golden_doi_in_evidence={facts['relevant_doi_hit']}",
            f"origins={origins['retrieval']}/{origins['answer_provider']}",
            f"ids_in_text={str(facts['ids_in_text']).lower()}",
        ]
    if expect_insufficient:
        parts.append("expectation=insufficient_evidence (not pass/fail)")
    return " | ".join(parts)


def format_review(body: Mapping[str, Any]) -> list[str]:
    """Return full answer text and claims with citations for human review."""
    lines = [f"  answer: {body.get('answer')}"]
    for claim in body.get("claims") or []:
        cites = ", ".join(claim.get("citation_chunk_ids", []))
        lines.append(f"  claim {claim.get('claim_id')}: {claim.get('text')}")
        lines.append(f"    cites: [{cites}]")
    return lines


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """Parse ``--only``, ``--repeat`` and ``--agentic``."""
    parser = argparse.ArgumentParser(description="MVP live smoke run.")
    parser.add_argument(
        "--only",
        choices=QUESTION_IDS,
        help="Run only this question id.",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Run each selected question this many times (default 1).",
    )
    parser.add_argument(
        "--agentic",
        action="store_true",
        help=f"Run with {AGENTIC_FLAG}=1 and print stage 1 counters.",
    )
    args = parser.parse_args(list(argv))
    if args.repeat < 1:
        parser.error("--repeat must be at least 1")
    return args


def main(
    environ: Mapping[str, str] | None = None,
    argv: Sequence[str] | None = None,
) -> int:
    """Run the smoke test.

    Args:
        environ: Mapping to read; defaults to ``os.environ``.
        argv: Command-line arguments; ``--only <id>``, ``--repeat <n>``
            and ``--agentic``.

    Returns:
        Process exit code: 0 when all requests ran, 1 on HTTP errors,
        2 on refused start or configuration failure.
    """
    import os

    args = parse_args(argv or ())
    env = dict(os.environ if environ is None else environ)
    missing = check_live_opt_in(env)
    if missing:
        print(
            "Refusing to start: live opt-in incomplete. Set/fix these "
            "variables: " + ", ".join(missing),
            file=sys.stderr,
        )
        return 2

    from fastapi.testclient import TestClient

    from sciscope.api.server import ServerConfigError, create_server_app

    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    questions = select_golden(
        golden, (args.only,) if args.only else QUESTION_IDS
    )
    env[AGENTIC_FLAG] = "1" if args.agentic else "0"
    mode_suffix = ".agentic" if args.agentic else ""
    capture = AgenticCapture()
    agentic_logger = logging.getLogger(AGENTIC_LOGGER)
    agentic_logger.setLevel(logging.INFO)
    agentic_logger.addHandler(capture)
    try:
        app = create_server_app(env)
    except ServerConfigError as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 2

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary: list[dict[str, Any]] = []
    reviews: list[tuple[str, list[str]]] = []
    exit_code = 0
    with TestClient(app, raise_server_exceptions=False) as client:
        enabled = set(client.get("/api/health").json().get("workflows", []))
        for item, run in (
            (item, run)
            for item in questions
            for run in range(1, args.repeat + 1)
        ):
            if item["workflow"] not in enabled:
                if run > 1:
                    continue
                print(skip_line(item["id"], item["workflow"]))
                summary.append(
                    {
                        "id": item["id"],
                        "workflow": item["workflow"],
                        "skipped": "workflow not supported by provider",
                    }
                )
                continue
            capture.stats.clear()
            started = time.perf_counter()
            response = client.post(
                "/api/v2/questions",
                json={
                    "workflow": item["workflow"],
                    "question": item["question"],
                },
            )
            latency = time.perf_counter() - started
            try:
                body = response.json()
            except ValueError:
                body = {"error": {"code": "non_json_response"}}
            suffix = mode_suffix + (f".run{run}" if args.repeat > 1 else "")
            _write_json(OUTPUT_DIR / f"{item['id']}{suffix}.json", body)
            ok = response.status_code == 200
            facts = analyze(body, item["relevant_dois"]) if ok else None
            extra = (
                agentic_facts(capture.stats[-1] if capture.stats else None)
                if args.agentic
                else {}
            )
            line = format_line(
                item["id"],
                response.status_code,
                body,
                latency,
                facts,
                item["expect_insufficient"],
                item["workflow"],
            )
            if args.agentic:
                line += " | " + format_agentic(extra)
            print(line)
            if ok:
                reviews.append((f"{item['id']}{suffix}", format_review(body)))
            else:
                exit_code = 1
                print(f"  error: {json.dumps(body.get('error'))}")
            summary.append(
                {
                    "id": item["id"],
                    "run": run,
                    "workflow": item["workflow"],
                    "http_status": response.status_code,
                    "response_status": body.get("status"),
                    "latency_seconds": round(latency, 2),
                    "expect_insufficient": item["expect_insufficient"],
                    **(facts or {}),
                    **extra,
                }
            )
    agentic_logger.removeHandler(capture)
    _write_json(OUTPUT_DIR / f"summary{mode_suffix}.json", summary)

    print("\n=== Review ===")
    for question_id, lines in reviews:
        print(f"\n[{question_id}]")
        print("\n".join(lines))
    print(f"\nSaved to {OUTPUT_DIR.as_posix()}/")
    return exit_code


if __name__ == "__main__":
    sys.exit(main(argv=sys.argv[1:]))
