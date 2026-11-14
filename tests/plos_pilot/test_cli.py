"""Mocked command flow checks with no network or real sleeping."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sciscope.plos_pilot.download import DownloadSummary

from sciscope.plos_pilot import cli
from sciscope.plos_pilot.search import SearchResult

NOW = datetime(2026, 1, 2, tzinfo=UTC)


def _injected() -> dict[str, object]:
    """Return inert dependencies for every CLI call."""

    def fetch(url: str, timeout: float) -> bytes:
        raise AssertionError("A mocked command must not access HTTP")

    return {
        "fetch": fetch,
        "sleep": lambda _: None,
        "clock": lambda: 0.0,
        "now": lambda: NOW,
    }


def test_search_prints_six_hit_counts_and_never_downloads(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Search reports hit counts, candidate count, and request count only."""
    arms = {f"SYNTHETIC arm {index}": index + 1 for index in range(6)}

    def search(**kwargs: object) -> SearchResult:
        assert kwargs["output_path"] == tmp_path / "candidates.jsonl"
        return SearchResult(arms, candidate_count=9, request_count=6)

    monkeypatch.setattr(cli, "search_candidates", search)
    monkeypatch.setattr(
        cli,
        "download_selected",
        lambda **_: pytest.fail("search called download"),
    )
    monkeypatch.setattr(
        cli, "write_metadata", lambda *_: pytest.fail("search wrote metadata")
    )
    code = cli.main(
        ["search", "--candidates", str(tmp_path / "candidates.jsonl")],
        **_injected(),
    )
    output = capsys.readouterr().out
    assert code == 0
    assert output.count("hits (not eligible papers)") == 6
    assert all(
        arm in output and str(count) in output for arm, count in arms.items()
    )
    assert "9" in output and "6" in output


def test_download_invalid_selection_exits_two_before_http(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every validation error is printed and no download is attempted."""
    monkeypatch.setattr(
        cli,
        "validate_selection",
        lambda **_: ["SYNTHETIC error one", "SYNTHETIC error two"],
    )
    monkeypatch.setattr(
        cli,
        "download_selected",
        lambda **_: pytest.fail("invalid selection downloaded"),
    )
    code = cli.main(["download"], **_injected())
    output = capsys.readouterr().out
    assert code == 2
    assert "SYNTHETIC error one" in output
    assert "SYNTHETIC error two" in output


@pytest.mark.parametrize(
    ("summary", "expected_exit"),
    [
        (
            DownloadSummary(
                accepted=["10.9999/synthetic-a"],
                duplicate=[],
                conflict={},
                failed={},
                pending=[],
            ),
            0,
        ),
        (
            DownloadSummary(
                accepted=[],
                duplicate=["10.9999/synthetic-a"],
                conflict={},
                failed={},
                pending=[],
            ),
            0,
        ),
        (
            DownloadSummary(
                accepted=[],
                duplicate=[],
                conflict={"10.9999/synthetic-a": "SYNTHETIC digests differ"},
                failed={},
                pending=[],
            ),
            1,
        ),
        (
            DownloadSummary(
                accepted=[],
                duplicate=[],
                conflict={},
                failed={"10.9999/synthetic-a": "SYNTHETIC invalid license"},
                pending=[],
            ),
            1,
        ),
        (
            DownloadSummary(
                accepted=[],
                duplicate=[],
                conflict={},
                failed={},
                pending=["10.9999/synthetic-a"],
            ),
            1,
        ),
    ],
)
def test_download_summary_exit_codes_and_selected_paths(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    summary: DownloadSummary,
    expected_exit: int,
) -> None:
    """CLI validates, downloads, writes metadata, and reports status."""
    events: list[str] = []
    screening = tmp_path / "screening.tsv"
    selection = tmp_path / "selection.tsv"
    candidates = tmp_path / "candidates.jsonl"
    manifest = tmp_path / "manifest.jsonl"
    metadata = tmp_path / "metadata.jsonl"
    raw_dir = tmp_path / "raw"

    def validate(**kwargs: object) -> list[str]:
        events.append("validate")
        assert kwargs == {
            "screening_path": screening,
            "selection_path": selection,
            "candidate_path": candidates,
        }
        return []

    def download(**kwargs: object) -> DownloadSummary:
        events.append("download")
        assert kwargs["selection_path"] == selection
        assert kwargs["candidate_path"] == candidates
        assert kwargs["manifest_path"] == manifest
        assert kwargs["raw_dir"] == raw_dir
        return summary

    def write(manifest_path: Path, output_path: Path, repo_root: Path) -> None:
        events.append("metadata")
        assert manifest_path == manifest
        assert output_path == metadata
        assert repo_root == tmp_path

    monkeypatch.setattr(cli, "validate_selection", validate)
    monkeypatch.setattr(cli, "download_selected", download)
    monkeypatch.setattr(cli, "write_metadata", write)
    code = cli.main(
        [
            "download",
            "--screening",
            str(screening),
            "--selection",
            str(selection),
            "--candidates",
            str(candidates),
            "--manifest",
            str(manifest),
            "--metadata",
            str(metadata),
            "--raw-dir",
            str(raw_dir),
            "--repo-root",
            str(tmp_path),
        ],
        **_injected(),
    )
    output = capsys.readouterr().out
    assert code == expected_exit
    assert events == ["validate", "download", "metadata"]
    for label in ("accepted", "duplicate", "conflict", "failed", "pending"):
        assert label in output.lower()
    for reason in (*summary.conflict.values(), *summary.failed.values()):
        assert reason in output
