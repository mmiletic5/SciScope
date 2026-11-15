"""Labeled synthetic XML bytes for JATS behavior tests."""


def synthetic_xml(markup: str) -> bytes:
    """Encode synthetic markup as an in-memory UTF-8 XML source."""
    return ("<!-- SYNTHETIC TEST FIXTURE -->" + markup).encode("utf-8")
