"""Live smoke run of the MVP backend over five dev golden questions.

Builds the app with ``create_server_app()`` from the process environment and
calls ``POST /api/v2/questions`` through the FastAPI ``TestClient``. Refuses to
start unless the live opt-in is explicit. Messages name variables, never
values; no key or URL is printed or written.

Run (PowerShell)::

    $env:SCISCOPE_LIVE_OPENAI="1"
    uv run --locked --env-file .env python scripts/mvp_smoke.py
"""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

GOLDEN_PATH = Path("evals/golden_questions.v0.json")
OUTPUT_DIR = Path("scratch/mvp_smoke")
QUESTION_IDS = (
    "gq-sp-001",
    "gq-cmp-001",
    "gq-conf-001",
    "gq-gap-001",
    "gq-ins-001",
)
INSUFFICIENT_EXPECTED_ID = "gq-ins-001"
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
        One dict per id with ``id``, ``question``, ``relevant_dois`` and
        ``expect_insufficient``.

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
        "relevant_doi_hit": any(
            item.get("doi") in relevant for item in evidence
        ),
        "origins": {
            name: (metadata.get(name) or {}).get("configured_origin")
            for name in ("retrieval", "answer_provider")
        },
    }


def format_line(
    question_id: str,
    http_status: int,
    body: Mapping[str, Any],
    latency: float,
    facts: Mapping[str, Any] | None,
    expect_insufficient: bool,
) -> str:
    """Build the one-line summary for a question."""
    status = body.get("status", "error")
    parts = [
        question_id,
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


def main(environ: Mapping[str, str] | None = None) -> int:
    """Run the smoke test.

    Args:
        environ: Mapping to read; defaults to ``os.environ``.

    Returns:
        Process exit code: 0 when all requests ran, 1 on HTTP errors,
        2 on refused start or configuration failure.
    """
    import os

    env = os.environ if environ is None else environ
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
    questions = select_golden(golden)
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
        for item in questions:
            started = time.perf_counter()
            response = client.post(
                "/api/v2/questions",
                json={
                    "workflow": "research_question",
                    "question": item["question"],
                },
            )
            latency = time.perf_counter() - started
            try:
                body = response.json()
            except ValueError:
                body = {"error": {"code": "non_json_response"}}
            _write_json(OUTPUT_DIR / f"{item['id']}.json", body)
            ok = response.status_code == 200
            facts = analyze(body, item["relevant_dois"]) if ok else None
            print(
                format_line(
                    item["id"],
                    response.status_code,
                    body,
                    latency,
                    facts,
                    item["expect_insufficient"],
                )
            )
            if ok:
                reviews.append((item["id"], format_review(body)))
            else:
                exit_code = 1
                print(f"  error: {json.dumps(body.get('error'))}")
            summary.append(
                {
                    "id": item["id"],
                    "http_status": response.status_code,
                    "response_status": body.get("status"),
                    "latency_seconds": round(latency, 2),
                    "expect_insufficient": item["expect_insufficient"],
                    **(facts or {}),
                }
            )
    _write_json(OUTPUT_DIR / "summary.json", summary)

    print("\n=== Review ===")
    for question_id, lines in reviews:
        print(f"\n[{question_id}]")
        print("\n".join(lines))
    print(f"\nSaved to {OUTPUT_DIR.as_posix()}/")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
