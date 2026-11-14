"""Offline safeguards for PLOS pilot tests."""

import urllib.request
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fail a test if it attempts a real urllib request."""

    def blocked_urlopen(*args: object, **kwargs: object) -> None:
        raise AssertionError("Real network access is forbidden in pilot tests")

    monkeypatch.setattr(urllib.request, "urlopen", blocked_urlopen)
    yield
