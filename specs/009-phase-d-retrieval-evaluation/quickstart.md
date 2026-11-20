# Phase D native Windows verification quickstart

Run from the repository root in Windows PowerShell with the approved Python
3.12 `.venv`. Do not use Docker, WSL, or a shell other than PowerShell for
Person 2 verification.

## Offline checks

```powershell
$env:PYTHONPATH = '.;src'
.\.venv\Scripts\python.exe -m pytest tests/evaluation tests/retrieval -q -p no:cacheprovider
.\.venv\Scripts\ruff.exe check src tests scripts
.\.venv\Scripts\ruff.exe format --check src tests scripts
.\.venv\Scripts\mypy.exe src/sciscope/evaluation src/sciscope/retrieval src/sciscope/database scripts/phase_d_run_retrieval_evaluation.py scripts/phase_d_generate_query_vectors.py
```

The commands above are offline checks. They do not authorize protected data
access or run retrieval evaluation. Record actual command output, exit codes,
environment, and any skipped tests in `EVIDENCE.md`.

## Protected evaluation artifacts

Golden v0/v1 records, query vectors, authorization receipts, T005 reports,
and T006 result reports are kept under Git-ignored protected locations. The
final review package contains only its explicit allowlist and the six reports
selected by the protected T006 manifest. It excludes question text, source
passages, vectors, caches, database contents, and credentials. Do not use
protected held-out results for development, debugging, tuning, or model
selection.

The T006 runner has a run-manifest guard and refuses to repeat an existing
protected run. Do not rerun it as a routine verification command. Any future
protected evaluation requires its own explicit authorization and must follow
the frozen protocol and safeguards in `docs/person2/RETRIEVAL_EVALUATION_PROTOCOL.md`.

## Review archive

Build the allowlisted evidence archive only after all included documentation
and source changes are final:

```powershell
$env:PYTHONPATH = '.;src'
.\.venv\Scripts\python.exe scripts/phase_d_package_review_evidence.py
```

The command prints the archive path and SHA-256 only. Independently verify
the supplied archive's member manifest before review. The archive is a
technical review artifact; independent review and final human acceptance are
separate gates.
