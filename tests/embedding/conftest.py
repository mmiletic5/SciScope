"""Offline safeguards for synthetic embedding contract tests."""

from __future__ import annotations

import socket
import urllib.request
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fail any urllib request or socket connection outside fake seams."""

    def blocked(*args: object, **kwargs: object) -> None:
        raise AssertionError("Real network access is forbidden in pilot tests")

    monkeypatch.setattr(urllib.request, "urlopen", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)
    yield
