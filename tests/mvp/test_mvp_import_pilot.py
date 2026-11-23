"""Offline tests for the demo import script's argument and guard logic."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from sciscope.ingestion.contract import ImportMode

_SCRIPT = Path(__file__).parents[2] / "scripts" / "mvp_import_pilot.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("mvp_import_pilot", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["mvp_import_pilot"] = module
    spec.loader.exec_module(module)
    return module


script = _load()


def test_defaults_build_initialize_request() -> None:
    """Defaults target the pilot package in INITIALIZE mode."""
    request = script.build_request(script.parse_args([]))
    assert request.mode is ImportMode.INITIALIZE
    assert request.package_dir == Path("data/delivery/pilot")
    assert request.embedding_report == Path("data/pilot/embedding_report.json")


def test_guard_accepts_demo_database() -> None:
    """The demo database URL passes the guard."""
    url = "postgresql+psycopg://u:p@127.0.0.1:5432/sciscope_test_005"
    assert script.database_url_from({"DATABASE_URL": url}) == url


def test_guard_refuses_other_database() -> None:
    """Any other database name is refused."""
    url = "postgresql+psycopg://u:p@127.0.0.1:5432/other"
    with pytest.raises(ValueError, match="sciscope_test_005"):
        script.database_url_from({"DATABASE_URL": url})


def test_main_refuses_without_leaking_url(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Refusal output never contains credentials."""
    secret_url = "postgresql+psycopg://u:topsecret@127.0.0.1:5432/other"
    monkeypatch.setenv("DATABASE_URL", secret_url)
    assert script.main([]) == 2
    captured = capsys.readouterr()
    assert "topsecret" not in captured.out + captured.err
